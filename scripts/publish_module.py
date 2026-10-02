"""Manually publish only the exact wheel that passed the central build."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import urllib.parse
from pathlib import Path

from packaging.version import Version

from module_common import (
    BUILD_WORKFLOW, CENTRAL_REPOSITORY, CENTRAL_REPOSITORY_ID, GitHub,
    GitHubError, check_plan, digest_file, load_registry, read_json,
    require, resolve_plan, write_json,
)
from validate_module_wheel import validate_wheel

VALIDATION_LABELS = {
    "ubuntu-latest-3.12": ("linux", "3.12."),
    "ubuntu-latest-3.13": ("linux", "3.13."),
    "windows-latest-3.12": ("win32", "3.12."),
    "windows-latest-3.13": ("win32", "3.13."),
}


def verify_run(github: GitHub, run_id: str, module: str) -> dict:
    require(run_id.isdigit() and int(run_id) > 0, "invalid build run id")
    registry = load_registry()
    require(module in registry, "unregistered module")
    repo = github.request(f"repos/{CENTRAL_REPOSITORY}")
    require(repo["id"] == CENTRAL_REPOSITORY_ID, "central repository identity changed")
    run = github.request(f"repos/{CENTRAL_REPOSITORY}/actions/runs/{run_id}")
    require(run["repository"]["id"] == CENTRAL_REPOSITORY_ID, "build belongs to another repository")
    require(run["path"].split("@", 1)[0] == BUILD_WORKFLOW, "not a module packaging workflow run")
    require(run["event"] == "workflow_dispatch" and run["head_branch"] == repo["default_branch"], "publishing requires a manual build on the central default branch")
    require(run["status"] == "completed" and run["conclusion"] == "success", "build run is not successfully completed")
    require(run["actor"]["login"] in registry[module]["requesters"], "build actor is not registered")
    compare = github.request(f"repos/{CENTRAL_REPOSITORY}/compare/{run['head_sha']}...{urllib.parse.quote(repo['default_branch'], safe='')}")
    require(compare["status"] in ("ahead", "identical"), "build configuration is not in central default-branch history")
    return run


def validate_candidate(github: GitHub, run: dict, plan: dict, wheel_dir: Path, validation_dir: Path, expected_sha256: str) -> tuple[Path, dict]:
    cfg = check_plan(plan, load_registry())
    require(plan["central_sha"] == run["head_sha"] and plan["actor"] == run["actor"]["login"], "source plan does not belong to selected build")
    fresh = resolve_plan(cfg, {
        "source_ref": plan["source_sha"], "source_sha": plan["source_sha"],
        "expected_version": plan["version"], "request_id": plan["request_id"],
    }, github, actor=plan["actor"], central_sha=run["head_sha"])
    for key in fresh:
        if key != "source_ref":
            require(fresh[key] == plan[key], f"source plan disagrees with upstream: {key}")
    repo = github.request(f"repos/{cfg['repository']}")
    compare = github.request(f"repos/{cfg['repository']}/compare/{plan['source_sha']}...{urllib.parse.quote(repo['default_branch'], safe='')}")
    require(compare["status"] in ("ahead", "identical"), "merge upstream changes into its default branch and rebuild before publishing")
    wheels = list(wheel_dir.glob("*.whl"))
    require(len(wheels) == 1, "expected one build artifact wheel")
    wheel = wheels[0]
    require(len(expected_sha256) == 64 and all(ch in "0123456789abcdef" for ch in expected_sha256), "expected SHA256 must be 64 lowercase hex digits")
    require(digest_file(wheel) == expected_sha256, "wheel digest disagrees with manually selected SHA256")
    manifest = validate_wheel(wheel, plan)
    require({file.stem for file in validation_dir.glob("*.json")} == set(VALIDATION_LABELS), "missing or unexpected platform/Python validations")
    checks = {}
    for label, (system, python) in VALIDATION_LABELS.items():
        tested = read_json(validation_dir / f"{label}.json")
        for key in (*plan, "wheel", "sha256", "size", "file_sha256"):
            require(tested.get(key) == manifest.get(key), f"{label}: validation belongs to a different wheel or source")
        result = tested["validation"]
        require(result.get("platform") == system and result.get("python", "").startswith(python), f"{label}: wrong validation environment")
        require(result.get("installed_files") == "passed", f"{label}: installed wheel was not verified")
        for gate in ("metadata", "record", "required_files", "python_syntax"):
            require(result.get(gate) == "passed", f"{label}: failed {gate}")
        checks[label] = result
    manifest["validation"] = checks
    manifest["build_run_id"] = run["id"]
    manifest["build_run_url"] = run["html_url"]
    return wheel, manifest


def release_state(github: GitHub, tag: str) -> dict | None:
    try:
        return github.request(f"repos/{CENTRAL_REPOSITORY}/releases/tags/{urllib.parse.quote(tag, safe='')}")
    except GitHubError as error:
        if error.status != 404:
            raise
    # The tag endpoint returns published releases only. Authenticated release
    # listings also contain drafts, including drafts whose tag is not created.
    page = 1
    matches = []
    while True:
        releases = github.request(f"repos/{CENTRAL_REPOSITORY}/releases?per_page=100&page={page}")
        matches.extend(release for release in releases if release.get("draft") and release.get("tag_name") == tag)
        require(len(matches) <= 1, f"multiple drafts use {tag}; resolve the ambiguity before retrying")
        if len(releases) < 100:
            return matches[0] if matches else None
        page += 1


def asset_matches(asset: dict, digest: str) -> bool:
    return asset.get("digest") == f"sha256:{digest}"


def assert_existing_manifest(asset: dict, candidate: dict) -> None:
    require(type(asset.get("id")) is int and asset["id"] > 0, "invalid release asset id")
    require(type(asset.get("size")) is int and 0 < asset["size"] <= 1024 * 1024, "release manifest is too large")
    # Draft assets need authentication even in a public repository. gh handles
    # the API's signed-download redirect without exposing the token in a URL.
    raw = subprocess.check_output([
        "gh", "api", f"repos/{CENTRAL_REPOSITORY}/releases/assets/{asset['id']}",
        "-H", "Accept: application/octet-stream",
    ])
    require(len(raw) <= 1024 * 1024, "release manifest is too large")
    require(asset_matches(asset, hashlib.sha256(raw).hexdigest()), "existing release manifest digest mismatch")
    existing = json.loads(raw)
    for key in ("module", "repository", "repository_id", "distribution", "version", "source_sha", "config_sha256", "wheel", "sha256", "size"):
        require(existing.get(key) == candidate[key], f"published version already has different {key}; bump the upstream version")


def publish_release(github: GitHub, wheel: Path, manifest_file: Path, manifest: dict) -> tuple[str, str]:
    tag = f"module-{manifest['module']}-v{manifest['version']}"
    prerelease = Version(manifest["version"]).is_prerelease
    expected = {wheel.name: manifest["sha256"], "source-manifest.json": digest_file(manifest_file)}
    release = release_state(github, tag)
    publication_ref = github.request(f"repos/{CENTRAL_REPOSITORY}")["default_branch"]
    if release is None:
        # GITHUB_TOKEN cannot create tags at old commits whose workflows differ
        # from the current default branch. The manifest retains central_sha and
        # the build run; the release tag records publication on the default ref.
        release = github.request(f"repos/{CENTRAL_REPOSITORY}/releases", method="POST", data={
            "tag_name": tag, "target_commitish": publication_ref,
            "name": f"{manifest['distribution']} {manifest['version']}",
            "body": (
                f"Manually published Python module wheel.\n\n"
                f"Source: https://github.com/{manifest['repository']}/tree/{manifest['source_sha']}\n\n"
                f"Verified build: {manifest['build_run_url']}\n\n"
                f"Build configuration: {manifest['central_sha']}\n\n"
                "Runtime dependencies remain user-managed as declared by upstream.\n"
                "See source-manifest.json for hashes, source and validation results."
            ),
            "draft": True, "prerelease": prerelease, "make_latest": "false",
        })
    assets = {asset["name"]: asset for asset in release["assets"]}
    require(len(assets) == len(release["assets"]) and set(assets) <= set(expected), "unexpected or duplicate assets in module release")
    if release["draft"]:
        # GitHub can leave an empty starter asset after a failed upload. Only
        # remove that incomplete state; never replace an uploaded asset.
        for name, asset in list(assets.items()):
            if asset.get("state") == "starter":
                require(type(asset.get("id")) is int and asset["id"] > 0, "invalid starter asset id")
                github.request(f"repos/{CENTRAL_REPOSITORY}/releases/assets/{asset['id']}", method="DELETE")
                del assets[name]
    if wheel.name in assets:
        require(asset_matches(assets[wheel.name], manifest["sha256"]), "version already contains a different wheel; bump upstream version")
    if "source-manifest.json" in assets:
        assert_existing_manifest(assets["source-manifest.json"], manifest)
    if not release["draft"]:
        require(set(assets) == set(expected), "published release is incomplete; refusing to modify it")
        return release["html_url"], "already_published"
    for name, path in ((wheel.name, wheel), ("source-manifest.json", manifest_file)):
        if name not in assets:
            upload_url = f"https://uploads.github.com/repos/{CENTRAL_REPOSITORY}/releases/{release['id']}/assets?name={urllib.parse.quote(name, safe='')}"
            subprocess.run([
                "gh", "api", "--method", "POST", upload_url,
                "-H", "Content-Type: application/octet-stream", "--input", str(path), "--silent",
            ], check=True)
    release = github.request(f"repos/{CENTRAL_REPOSITORY}/releases/{release['id']}")
    assets = {asset["name"]: asset for asset in release["assets"]}
    require(set(assets) == set(expected) and len(assets) == len(release["assets"]), "draft release assets are incomplete")
    require(asset_matches(assets[wheel.name], manifest["sha256"]), "uploaded wheel digest mismatch")
    assert_existing_manifest(assets["source-manifest.json"], manifest)
    release = github.request(f"repos/{CENTRAL_REPOSITORY}/releases/{release['id']}", method="PATCH", data={"draft": False, "prerelease": prerelease, "make_latest": "false", "target_commitish": publication_ref})
    return release["html_url"], "published"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["preflight", "publish"])
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--module", required=True)
    parser.add_argument("--plan", type=Path)
    parser.add_argument("--wheel-dir", type=Path)
    parser.add_argument("--validation-dir", type=Path)
    parser.add_argument("--expected-sha256", default="")
    args = parser.parse_args()
    try:
        require(os.environ.get("GITHUB_REPOSITORY", CENTRAL_REPOSITORY) == CENTRAL_REPOSITORY, "only the central repository may publish")
        github = GitHub()
        run = verify_run(github, args.run_id, args.module)
        if args.command == "preflight":
            print(f"Selected verified build: {run['html_url']}")
            return
        require(args.plan is not None and args.wheel_dir is not None and args.validation_dir is not None, "plan, wheel and validation directories are required")
        plan = read_json(args.plan)
        require(plan["module"] == args.module, "plan belongs to another module")
        wheel, manifest = validate_candidate(github, run, plan, args.wheel_dir, args.validation_dir, args.expected_sha256)
        manifest_file = args.wheel_dir / "source-manifest.json"
        write_json(manifest_file, manifest)
        url, status = publish_release(github, wheel, manifest_file, manifest)
        print(f"{status}: {url}")
        github.request(f"repos/{CENTRAL_REPOSITORY}/dispatches", method="POST", data={"event_type": "index"})
        if summary := os.environ.get("GITHUB_STEP_SUMMARY"):
            with open(summary, "a", encoding="utf-8") as stream:
                stream.write(f"Module release: {url}\n\nStatus: {status}; Pages index refresh requested.\n")
    except (ValueError, KeyError, RuntimeError) as error:
        parser.exit(1, f"{error}\n")


if __name__ == "__main__":
    main()
