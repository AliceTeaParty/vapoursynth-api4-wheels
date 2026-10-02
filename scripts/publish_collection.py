"""Manually publish one verified, complete vs-collection-rk wheel set."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
import subprocess
import urllib.parse
from pathlib import Path

from build_collection import validate_set
from collection_common import MATRIX, REGISTRY_PATH, WORKFLOW, make_plans, sha256
from module_common import CENTRAL_REPOSITORY, CENTRAL_REPOSITORY_ID, GitHub, read_json, require, write_json
from publish_module import asset_matches, release_state


def verify_run(github: GitHub, run_id: str) -> dict:
    require(run_id.isdigit() and int(run_id) > 0, "invalid build run")
    repo = github.request(f"repos/{CENTRAL_REPOSITORY}")
    run = github.request(f"repos/{CENTRAL_REPOSITORY}/actions/runs/{run_id}")
    require(run["repository"]["id"] == CENTRAL_REPOSITORY_ID, "wrong build repository")
    require(run["path"].split("@", 1)[0] == WORKFLOW and run["event"] == "workflow_dispatch", "not a manual collection preview")
    require(run["head_branch"] == repo["default_branch"], "publish only previews from the central default branch")
    require(run["status"] == "completed" and run["conclusion"] == "success", "preview is not successful")
    comparison = github.request(f"repos/{CENTRAL_REPOSITORY}/compare/{run['head_sha']}...{urllib.parse.quote(repo['default_branch'], safe='')}")
    require(comparison["status"] in ("ahead", "identical"), "preview commit is not in default-branch history")
    return run


def validate_candidate(github: GitHub, run: dict, plan: dict, wheel_dir: Path, validation_dir: Path, expected_version: str) -> dict:
    require(plan["kind"] == "collection" and plan["schema_version"] == 1, "invalid collection plan")
    require(plan["central_sha"] == run["head_sha"] and plan["version"] == expected_version, "selected preview/version mismatch")
    raw = github.contents(CENTRAL_REPOSITORY, REGISTRY_PATH, run["head_sha"])
    require(sha256(raw) == plan["registry_sha256"], "registry hash mismatch")
    registry = json.loads(raw)
    reader = lambda path: github.contents(CENTRAL_REPOSITORY, path, run["head_sha"])
    # Resolve source plans from immutable central Git objects, not from metadata
    # written by a module build hook.
    expected = make_plans(registry, run["head_sha"], reader)
    require(plan["components"] == expected, "source plan differs from the selected central commit")
    result = validate_set(plan, wheel_dir)
    require({path.stem for path in validation_dir.glob("*.json")} == set(MATRIX), "missing or unexpected validation environments")
    for label, (system, python) in MATRIX.items():
        tested = read_json(validation_dir / f"{label}.json")
        require(tested["central_sha"] == plan["central_sha"] and tested["registry_sha256"] == plan["registry_sha256"], "validation belongs to another source")
        require(tested.get("fresh_install") == "passed" and tested.get("monolith_migration") == "passed", "entry resolution or migration was not verified")
        require(len(tested["wheels"]) == len(result["wheels"]), "incomplete validated wheel set")
        for actual, verified in zip(result["wheels"], tested["wheels"]):
            for key in ("distribution", "version", "wheel", "sha256", "file_sha256", "pyproject_sha256"):
                require(actual[key] == verified[key], f"validated wheel mismatch: {label}/{key}")
            gates = verified["validation"]
            require(gates.get("installed_files") == "passed" and gates["platform"] == system and gates["python"].startswith(python), "wrong or incomplete installation validation")
    result["build_run_id"] = run["id"]
    result["build_run_url"] = run["html_url"]
    return result


def load_asset_manifest(asset: dict) -> dict:
    require(type(asset.get("id")) is int and asset["id"] > 0 and 0 < asset["size"] < 5 * 1024 * 1024, "invalid collection manifest asset")
    raw = subprocess.check_output(["gh", "api", f"repos/{CENTRAL_REPOSITORY}/releases/assets/{asset['id']}", "-H", "Accept: application/octet-stream"])
    require(asset_matches(asset, hashlib.sha256(raw).hexdigest()), "release manifest digest mismatch")
    return json.loads(raw)


def publish(github: GitHub, manifest: dict, wheel_dir: Path) -> str:
    tag = f"vs-collection-rk-v{manifest['version']}"
    expected = {item["wheel"]: item["sha256"] for item in manifest["wheels"]}
    manifest_path = wheel_dir / "collection-manifest.json"
    write_json(manifest_path, manifest)
    expected["collection-manifest.json"] = sha256(manifest_path.read_bytes())
    default_branch = github.request(f"repos/{CENTRAL_REPOSITORY}")["default_branch"]
    release = release_state(github, tag)
    if release is None:
        release = github.request(f"repos/{CENTRAL_REPOSITORY}/releases", method="POST", data={
            "tag_name": tag, "target_commitish": default_branch, "draft": True, "make_latest": "false",
            "name": f"vs-collection-rk {manifest['version']}",
            "body": f"Manually published entry and component wheel set.\n\nVerified build: {manifest['build_run_url']}\n\nCentral source: {manifest['central_sha']}\n\nSee collection-manifest.json and VERSIONS.md for source history.",
        })
    assets = {item["name"]: item for item in release["assets"]}
    require(len(assets) == len(release["assets"]) and set(assets) <= set(expected), "unexpected or duplicate release assets")
    if release["draft"]:
        for name, asset in list(assets.items()):
            if asset.get("state") == "starter":
                github.request(f"repos/{CENTRAL_REPOSITORY}/releases/assets/{asset['id']}", method="DELETE")
                del assets[name]
    for name, asset in assets.items():
        if name == "collection-manifest.json":
            old = load_asset_manifest(asset)
            require(old["registry_sha256"] == manifest["registry_sha256"], "existing collection has different sources; bump entry version")
            require({item["wheel"]: item["sha256"] for item in old["wheels"]} == {item["wheel"]: item["sha256"] for item in manifest["wheels"]}, "existing collection has different wheels")
        else:
            require(asset_matches(asset, expected[name]), "existing version has a different wheel; never overwrite")
    if not release["draft"]:
        require(set(assets) == set(expected), "published collection is incomplete")
        return release["html_url"]
    for name in expected.keys() - assets.keys():
        path = wheel_dir / name
        url = f"https://uploads.github.com/repos/{CENTRAL_REPOSITORY}/releases/{release['id']}/assets?name={urllib.parse.quote(name, safe='')}"
        subprocess.run(["gh", "api", "--method", "POST", url, "-H", "Content-Type: application/octet-stream", "--input", str(path), "--silent"], check=True)
    release = github.request(f"repos/{CENTRAL_REPOSITORY}/releases/{release['id']}")
    uploaded = {item["name"]: item for item in release["assets"]}
    require(set(uploaded) == set(expected) and len(uploaded) == len(release["assets"]), "draft collection assets are incomplete")
    for name, asset in uploaded.items():
        if name != "collection-manifest.json":
            require(asset_matches(asset, expected[name]), f"uploaded digest mismatch: {name}")
    saved = load_asset_manifest(uploaded["collection-manifest.json"])
    require(saved["registry_sha256"] == manifest["registry_sha256"], "uploaded source manifest mismatch")
    require({item["wheel"]: item["sha256"] for item in saved["wheels"]} == {item["wheel"]: item["sha256"] for item in manifest["wheels"]}, "uploaded manifest wheel set mismatch")
    published = github.request(f"repos/{CENTRAL_REPOSITORY}/releases/{release['id']}", method="PATCH", data={"draft": False, "target_commitish": default_branch, "make_latest": "false"})
    return published["html_url"]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["preflight", "publish"])
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--expected-version", required=True)
    parser.add_argument("--plan", type=Path)
    parser.add_argument("--wheel-dir", type=Path)
    parser.add_argument("--validation-dir", type=Path)
    args = parser.parse_args()
    try:
        require(os.environ.get("GITHUB_REPOSITORY", CENTRAL_REPOSITORY) == CENTRAL_REPOSITORY, "wrong publishing repository")
        github = GitHub()
        run = verify_run(github, args.run_id)
        if args.command == "preflight":
            print(run["html_url"])
            return
        require(args.plan and args.wheel_dir and args.validation_dir, "missing artifacts")
        result = validate_candidate(github, run, read_json(args.plan), args.wheel_dir, args.validation_dir, args.expected_version)
        url = publish(github, result, args.wheel_dir)
        github.request(f"repos/{CENTRAL_REPOSITORY}/dispatches", method="POST", data={"event_type": "index"})
        print(url)
    except (ValueError, KeyError, RuntimeError) as error:
        parser.exit(1, f"{error}\n")


if __name__ == "__main__":
    main()
