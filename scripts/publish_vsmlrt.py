"""Publish the complete vs-mlrt wheel set from three successful manual CI runs."""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import time
import tomllib
import urllib.error
import urllib.parse
import urllib.request
import zipfile

from module_common import CENTRAL_REPOSITORY, CENTRAL_REPOSITORY_ID, ROOT, SHA, GitHub, digest_file, read_json, require, write_json
from publish_module import asset_matches, release_state

WORKFLOWS = {
    "windows-generic": "package-vs-mlrt-windows-generic.yml",
    "windows-cuda": "package-vs-mlrt-windows-cuda.yml",
    "linux": "package-vs-mlrt-linux.yml",
}
ARTIFACTS = {
    "windows-generic": {"vs-mlrt-windows-x64-generic": "windows-generic"},
    "windows-cuda": {f"vs-mlrt-windows-x64-{v}": f"windows-cuda/{v}" for v in ("cu121", "cu129")},
    "linux": {f"vs-mlrt-linux-{v}": f"linux/{v}" for v in ("generic", "cu121", "cu129")},
}
PUBLICATION_ONLY = {
    "plugins/vs-mlrt/tools/assemble_component_release.py",
    "plugins/vs-mlrt/tools/test_release_assembly.py",
    "plugins/vs-mlrt/README.md",
}


def verify_run(run: dict, workflow: str, default_branch: str) -> str:
    require(run.get("repository", {}).get("id") == CENTRAL_REPOSITORY_ID, "build belongs to another repository")
    require(run.get("path") == f".github/workflows/{workflow}", "wrong native build workflow")
    require(run.get("event") == "workflow_dispatch" and run.get("head_branch") == default_branch,
            "only manual default-branch native builds may be published")
    require(run.get("status") == "completed" and run.get("conclusion") == "success", "native build has not succeeded")
    revision = run.get("head_sha", "")
    require(bool(SHA.fullmatch(revision)), "invalid build source revision")
    return revision


def verify_unchanged_sources(revision: str) -> None:
    # A publisher-only update can follow a tested build; native sources, wheel
    # metadata and the worker workflows must still match that build exactly.
    paths = ["plugins/vs-mlrt", *(f".github/workflows/{name}" for name in WORKFLOWS.values())]
    changed = subprocess.check_output(
        ["git", "diff", "--name-only", revision, "HEAD", "--", *paths], cwd=ROOT, text=True,
    ).splitlines()
    require(set(changed) <= PUBLICATION_ONLY, f"vs-mlrt source changed since the build: {changed}")


def entry_version() -> str:
    versions = {
        tomllib.loads(path.read_text(encoding="utf-8"))["project"]["version"]
        for path in (ROOT / "plugins/vs-mlrt/packaging/distributions").glob("*/pyproject.toml")
    }
    require(len(versions) == 1, "entry project versions disagree")
    return versions.pop()


def load_assembler():
    path = ROOT / "plugins/vs-mlrt/tools/assemble_component_release.py"
    spec = importlib.util.spec_from_file_location("vsmlrt_assembler", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def artifact_download_url(github: GitHub, artifact_id: int) -> str:
    # Keep the repository token on api.github.com. The blob request uses only
    # its short-lived signed URL, renewed on each resume attempt.
    url = f"https://api.github.com/repos/{CENTRAL_REPOSITORY}/actions/artifacts/{artifact_id}/zip"
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "vsmlrt-release-publisher"}
    if github.token:
        headers["Authorization"] = f"Bearer {github.token}"
    opener = urllib.request.build_opener(NoRedirect())
    try:
        with opener.open(urllib.request.Request(url, headers=headers), timeout=60):
            raise RuntimeError("artifact API did not return a download redirect")
    except urllib.error.HTTPError as error:
        require(error.code == 302, f"artifact download API returned HTTP {error.code}")
        location = error.headers.get("Location", "")
        require(urllib.parse.urlsplit(location).scheme == "https", "artifact download must use HTTPS")
        return location


def download_artifact(github: GitHub, artifact: dict, target: Path) -> None:
    require(type(artifact["id"]) is int and artifact["id"] > 0, "invalid artifact ID")
    require(bool(re.fullmatch(r"sha256:[0-9a-f]{64}", artifact.get("digest", ""))), "artifact lacks a SHA-256 digest")
    target.mkdir(parents=True)
    archive_path = target / "download.zip"
    print(f"Downloading {artifact['name']} ({artifact['size_in_bytes']} bytes)", flush=True)
    for attempt in range(1, 7):
        offset = archive_path.stat().st_size if archive_path.exists() else 0
        print(f"  attempt {attempt}, resuming at {offset} bytes", flush=True)
        location = artifact_download_url(github, artifact["id"])
        result = subprocess.run([
            "curl", "--fail", "--silent", "--show-error", "--location",
            "--connect-timeout", "30", "--speed-time", "60", "--speed-limit", "1024",
            "--max-time", "900", "--continue-at", "-", "--output", str(archive_path), "--config", "-",
        ], input="url = " + json.dumps(location) + "\n", text=True)
        if result.returncode == 0:
            break
        if attempt < 6:
            time.sleep(5)
    else:
        raise RuntimeError(f"artifact download failed after six resume attempts: {artifact['name']}")
    require(archive_path.stat().st_size == artifact["size_in_bytes"], "downloaded artifact size mismatch")
    require("sha256:" + digest_file(archive_path) == artifact["digest"], "downloaded artifact digest mismatch")
    with zipfile.ZipFile(archive_path) as archive:
        selected = set()
        for member in archive.infolist():
            name = PurePosixPath(member.filename)
            if member.is_dir() or not (name.suffix == ".whl" or name.name.startswith("component-wheel-inventory-")):
                continue
            require(not name.is_absolute() and ".." not in name.parts and "\\" not in member.filename and ":" not in member.filename,
                    "unsafe artifact member path")
            require(member.filename not in selected, "duplicate artifact member")
            selected.add(member.filename)
            path = target / name
            path.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(member) as source, path.open("xb") as destination:
                shutil.copyfileobj(source, destination, 1024 * 1024)
        require(bool(selected), "artifact has no wheel or inventory files")
    archive_path.unlink()
    print(f"Verified and extracted {artifact['name']}", flush=True)


def download_and_assemble(github: GitHub, runs: dict[str, str], directory: Path) -> tuple[Path, dict]:
    require(not directory.exists(), "publication work directory must be new")
    default_branch = github.request(f"repos/{CENTRAL_REPOSITORY}")["default_branch"]
    evidence = []
    revisions = set()
    for key, run_id in runs.items():
        require(run_id.isdigit(), "invalid run ID")
        run = github.request(f"repos/{CENTRAL_REPOSITORY}/actions/runs/{run_id}")
        revisions.add(verify_run(run, WORKFLOWS[key], default_branch))
        evidence.append({"run_id": run_id, "workflow": WORKFLOWS[key], "url": run["html_url"]})
    require(len(revisions) == 1, "native builds came from different source revisions")
    revision = revisions.pop()
    verify_unchanged_sources(revision)
    directory.mkdir(parents=True)
    for key, run_id in runs.items():
        artifacts = github.request(f"repos/{CENTRAL_REPOSITORY}/actions/runs/{run_id}/artifacts?per_page=100")["artifacts"]
        for name, relative in ARTIFACTS[key].items():
            matches = [item for item in artifacts if item["name"] == name and not item["expired"]]
            require(len(matches) == 1, f"missing or ambiguous artifact: {name}")
            target = directory / relative
            download_artifact(github, matches[0], target)
    canonical = directory / "canonical-shared"
    canonical.mkdir()
    selections = [
        ("linux/generic", "vs_mlrt_models-*-any.whl"),
        ("linux/generic", "vs_mlrt_generic-*-any.whl"),
        ("linux/cu121", "vs_mlrt_cu121-*-any.whl"),
        ("linux/cu129", "vs_mlrt_cu129-*-any.whl"),
        ("windows-generic", "vs_ncnn-*-win_amd64.whl"),
        ("windows-generic", "vs_ov-*-win_amd64.whl"),
        ("linux/generic", "vs_ncnn-*-manylinux_*.whl"),
        ("linux/generic", "vs_ov-*-manylinux_*.whl"),
    ]
    for relative, pattern in selections:
        matches = list((directory / relative).rglob(pattern))
        require(len(matches) == 1, f"expected one canonical wheel: {relative}/{pattern}")
        os.link(matches[0], canonical / matches[0].name)
    wheelhouse = directory / "release-wheelhouse"
    require(wheelhouse.resolve().parent == directory.resolve(), "invalid publication output")
    load_assembler().assemble(
        [directory / key for key in WORKFLOWS], wheelhouse, canonical, link=True,
    )
    inventory = read_json(wheelhouse / "vs-mlrt-release-inventory.json")
    require(inventory["source_revision"] == revision, "artifact source does not match the reviewed runs")
    inventory["build_runs"] = evidence
    write_json(wheelhouse / "vs-mlrt-release-inventory.json", inventory)
    return wheelhouse, inventory


def publish(github: GitHub, wheelhouse: Path, inventory: dict, version: str) -> str:
    tag = f"vs-mlrt-v{version}"
    inventory_file = wheelhouse / "vs-mlrt-release-inventory.json"
    expected = {item["name"]: item["sha256"] for item in inventory["wheels"]}
    require(len(expected) == len(inventory["wheels"]) and bool(expected), "invalid wheel inventory")
    expected[inventory_file.name] = digest_file(inventory_file)
    require({path.name for path in wheelhouse.iterdir()} == set(expected), "unexpected wheelhouse files")
    for name, digest in expected.items():
        require(Path(name).name == name and digest_file(wheelhouse / name) == digest, f"local digest mismatch: {name}")
    release = release_state(github, tag)
    branch = github.request(f"repos/{CENTRAL_REPOSITORY}")["default_branch"]
    if release is None:
        release = github.request(f"repos/{CENTRAL_REPOSITORY}/releases", method="POST", data={
            "tag_name": tag, "target_commitish": branch, "name": tag,
            "body": (
                f"Complete Windows/Linux vs-mlrt wheel set. Entry version: {version}.\n\n"
                f"Build source: {inventory['source_revision']}\n\n"
                + "\n".join(f"Verified build: {run['url']}" for run in inventory["build_runs"])
                + "\n\nSee README for exact installation pins and CUDA compatibility. "
                "The attached inventory records each wheel hash and its verified source."
            ),
            "draft": True, "prerelease": False, "make_latest": "false",
        })
    assets = {item["name"]: item for item in release["assets"]}
    require(len(assets) == len(release["assets"]) and set(assets) <= set(expected), "unexpected release assets")
    for name, asset in list(assets.items()):
        if release["draft"] and asset["state"] == "starter":
            github.request(f"repos/{CENTRAL_REPOSITORY}/releases/assets/{asset['id']}", method="DELETE")
            del assets[name]
        else:
            require(asset_matches(asset, expected[name]), f"existing release digest differs: {name}")
    if not release["draft"]:
        require(set(assets) == set(expected), "published release is incomplete; refusing to modify it")
        return release["html_url"]
    for name in sorted(expected):
        if name not in assets:
            print(f"Uploading {name}", flush=True)
            url = f"https://uploads.github.com/repos/{CENTRAL_REPOSITORY}/releases/{release['id']}/assets?name={urllib.parse.quote(name, safe='')}"
            subprocess.run(["gh", "api", "--method", "POST", url, "-H", "Content-Type: application/octet-stream",
                            "--input", str(wheelhouse / name), "--silent"], check=True)
    release = github.request(f"repos/{CENTRAL_REPOSITORY}/releases/{release['id']}")
    assets = {item["name"]: item for item in release["assets"]}
    require(len(assets) == len(release["assets"]) and set(assets) == set(expected), "release upload is incomplete")
    require(all(asset_matches(assets[name], sha) for name, sha in expected.items()), "uploaded asset digest mismatch")
    release = github.request(f"repos/{CENTRAL_REPOSITORY}/releases/{release['id']}", method="PATCH",
                             data={"draft": False, "target_commitish": branch, "make_latest": "false"})
    return release["html_url"]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    for key in WORKFLOWS:
        parser.add_argument(f"--{key}-run", required=True)
    parser.add_argument("--expected-version", required=True)
    parser.add_argument("--work-dir", type=Path, default=ROOT / ".work/vsmlrt-publication")
    args = parser.parse_args()
    require(os.environ.get("GITHUB_REPOSITORY", CENTRAL_REPOSITORY) == CENTRAL_REPOSITORY, "only the central repository may publish")
    version = entry_version()
    require(args.expected_version == version, "expected version disagrees with entry metadata")
    runs = {key: getattr(args, key.replace("-", "_") + "_run") for key in WORKFLOWS}
    github = GitHub()
    wheelhouse, inventory = download_and_assemble(github, runs, args.work_dir.resolve())
    url = publish(github, wheelhouse, inventory, version)
    print(url)
    github.request(f"repos/{CENTRAL_REPOSITORY}/dispatches", method="POST", data={"event_type": "index"})
    if summary := os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(summary, "a", encoding="utf-8") as stream:
            stream.write(f"Published {len(inventory['wheels'])} verified wheels: {url}\n")


if __name__ == "__main__":
    main()
