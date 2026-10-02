"""Central-owned subtree collection metadata and source verification."""
from __future__ import annotations

import hashlib
import json
import subprocess
import tomllib
from pathlib import Path

from packaging.requirements import Requirement

from module_common import CENTRAL_REPOSITORY, ROOT, SHA, project_metadata, relative_path, require

REGISTRY_PATH = "modules/collection.json"
WORKFLOW = ".github/workflows/package-vs-collection-rk.yml"
MATRIX = {
    "ubuntu-latest-3.12": ("linux", "3.12."),
    "ubuntu-latest-3.13": ("linux", "3.13."),
    "windows-latest-3.12": ("win32", "3.12."),
    "windows-latest-3.13": ("win32", "3.13."),
}


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def git_blob(commit: str, path: str, root: Path = ROOT) -> bytes:
    require(bool(SHA.fullmatch(commit)), "expected full central commit SHA")
    relative_path(path)
    return subprocess.check_output(["git", "-C", str(root), "show", f"{commit}:{path}"])


def load_collection(root: Path = ROOT) -> dict:
    data = json.loads((root / REGISTRY_PATH).read_text(encoding="utf-8"))
    require(data["schema_version"] == 1 and data["distribution"] == "vs-collection-rk", "unsupported collection registry")
    require(bool(SHA.fullmatch(data["collection_revision"])), "invalid collection source revision")
    components = data["components"]
    require(bool(components), "empty collection")
    require(len({item["module"] for item in components}) == len(components), "duplicate component id")
    require(len({item["distribution"] for item in components}) == len(components), "duplicate component distribution")
    require(len({item["import_name"] for item in components}) == len(components), "overlapping runtime imports")
    for item in components:
        relative_path(item["path"])
        require(item["path"] == f"modules/{item['module']}", "component must have its own modules directory")
        require(item["runtime_kind"] in ("module", "package"), "unsupported runtime kind")
        expected = item["import_name"] + (".py" if item["runtime_kind"] == "module" else "")
        require(item["install_path"] == expected, "install path disagrees with import name")
        for commit in ("upstream_revision", "import_commit", "patch_commit", "collection_revision"):
            require(bool(SHA.fullmatch(item[commit])), f"invalid {commit}")
        require(item["collection_revision"] == data["collection_revision"], "mixed migration snapshots")
        require(bool(item["runtime_sha256"]), "missing runtime file hashes")
        for path, digest in item["runtime_sha256"].items():
            relative_path(path)
            require(path == expected or path.startswith(expected + "/"), "runtime hash outside component import")
            require(len(digest) == 64 and all(ch in "0123456789abcdef" for ch in digest), "invalid runtime hash")
    return data


def make_plans(registry: dict, commit: str, reader) -> list[dict]:
    """Reader(path) returns bytes from one fixed central Git commit."""
    plans = []
    for item in registry["components"]:
        project_path = item["path"] + "/pyproject.toml"
        project = reader(project_path)
        metadata = project_metadata(project, item["distribution"])
        require(metadata["version"] == item["version"], "component version disagrees with registry")
        require(metadata["dependencies"] == [], "components must preserve Collection's unmanaged runtime dependencies")
        require(metadata["requires_python"] == ">=3.12", "component Python range must preserve Collection policy")
        provenance_path = item["path"] + "/provenance.toml"
        provenance_bytes = reader(provenance_path)
        provenance = tomllib.loads(provenance_bytes.decode("utf-8"))
        for key in ("upstream_url", "upstream_revision", "collection_revision", "vendored_revision"):
            require(provenance[key] == item[key], f"provenance disagrees with registry: {key}")
        require(provenance["runtime_sha256"] == item["runtime_sha256"], "runtime hash records disagree")
        hashes = {}
        for relative, digest in item["runtime_sha256"].items():
            content = reader(item["path"] + "/" + relative)
            require(sha256(content) == digest, f"unrecorded runtime change: {item['module']}/{relative}")
            hashes[relative] = digest
        required = [*hashes, "*.dist-info/extra_metadata/provenance.toml"]
        required += [f"*.dist-info/licenses/{name}" for name in item["license_files"]]
        plans.append({
            "schema_version": 1, "kind": "collection-component", "module": item["module"],
            "distribution": item["distribution"], "import_name": item["import_name"],
            "runtime_kind": item["runtime_kind"], "path": item["path"], "central_sha": commit,
            "repository": CENTRAL_REPOSITORY, "source_sha": commit,
            "pyproject_sha256": sha256(project), "provenance_sha256": sha256(provenance_bytes),
            "runtime_sha256": hashes, "required_files": required, **metadata,
        })
    entry = registry["entry"]
    project = reader(entry["path"] + "/pyproject.toml")
    metadata = project_metadata(project, registry["distribution"])
    expected_dependencies = sorted(str(Requirement(f"{item['distribution']}=={item['version']}")) for item in registry["components"])
    require(metadata["version"] == registry["version"], "entry version disagrees with registry")
    require(metadata["dependencies"] == expected_dependencies, "entry must pin every component exactly once")
    package_registry = reader(entry["path"] + "/vs_collection_rk/_registry.json")
    installed = json.loads(package_registry)
    require(len(installed) == len(registry["components"]), "entry introspection registry is incomplete")
    for item, exposed in zip(registry["components"], installed):
        require(exposed["distribution"] == item["distribution"] and exposed["wheel_version"] == item["version"], "entry introspection version mismatch")
        require(exposed["import_name"] == item["import_name"], "entry import name mismatch")
        require(exposed["source_revision"] == item["upstream_revision"], "entry upstream revision mismatch")
    plans.append({
        "schema_version": 1, "kind": "collection-entry", "module": "vs-collection-rk",
        "distribution": registry["distribution"], "import_name": entry["import_name"],
        "runtime_kind": "package", "path": entry["path"], "central_sha": commit,
        "repository": CENTRAL_REPOSITORY, "source_sha": commit,
        "pyproject_sha256": sha256(project), "required_files": ["vs_collection_rk/__init__.py", "vs_collection_rk/_registry.json"],
        "runtime_sha256": {
            "vs_collection_rk/__init__.py": sha256(reader(entry["path"] + "/vs_collection_rk/__init__.py")),
            "vs_collection_rk/_registry.json": sha256(package_registry),
        }, **metadata,
    })
    return plans


def source_plan(root: Path = ROOT) -> dict:
    registry = load_collection(root)
    commit = subprocess.check_output(["git", "-C", str(root), "rev-parse", "HEAD"], text=True).strip()
    registry_bytes = git_blob(commit, REGISTRY_PATH, root)
    require(json.loads(registry_bytes) == registry, "commit collection registration before building")
    plans = make_plans(registry, commit, lambda path: git_blob(commit, path, root))
    for plan in plans:
        for path, digest in plan["runtime_sha256"].items():
            require(sha256((root / plan["path"] / path).read_bytes()) == digest, "worktree runtime differs from committed source")
        require(sha256((root / plan["path"] / "pyproject.toml").read_bytes()) == plan["pyproject_sha256"], "uncommitted packaging changes")
    return {
        "schema_version": 1, "kind": "collection", "distribution": registry["distribution"],
        "version": registry["version"], "central_sha": commit, "registry_sha256": sha256(registry_bytes),
        "collection_revision": registry["collection_revision"], "components": plans,
    }
