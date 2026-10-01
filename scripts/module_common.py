"""Shared, data-only registry and GitHub helpers for module packaging."""
from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import subprocess
import tomllib
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path, PurePosixPath
from typing import Any

from packaging.requirements import Requirement
from packaging.utils import canonicalize_name
from packaging.version import Version

ROOT = Path(__file__).resolve().parents[1]
CENTRAL_REPOSITORY = "AliceTeaParty/vapoursynth-api4-wheels"
CENTRAL_REPOSITORY_ID = 1381471657
BUILD_WORKFLOW = ".github/workflows/package-modules.yml"
SHA = re.compile(r"[0-9a-f]{40}\Z")
MODULE_ID = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*\Z")
CONFIG_KEYS = {
    "schema_version", "repository", "repository_id", "distribution",
    "import_name", "project_subdirectory", "default_ref", "requesters",
    "required_files",
}
REQUEST_KEYS = {
    "api_version", "module", "source_ref", "source_sha",
    "expected_version", "request_id",
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def relative_path(value: str, *, allow_dot: bool = False) -> str:
    require(isinstance(value, str) and bool(value), "path must be a nonempty string")
    if allow_dot and value == ".":
        return value
    path = PurePosixPath(value)
    require(
        not path.is_absolute() and "\\" not in value and ":" not in value
        and all(part not in ("", ".", "..") for part in value.split("/"))
        and not any(ord(ch) < 32 for ch in value),
        f"unsafe relative path: {value!r}",
    )
    return value


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def digest_file(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def load_registry(root: Path = ROOT) -> dict[str, dict[str, Any]]:
    registry: dict[str, dict[str, Any]] = {}
    distributions: set[str] = set()
    for file in sorted((root / "modules").glob("*/module.toml")):
        module = file.parent.name
        require(bool(MODULE_ID.fullmatch(module)), f"invalid module id: {module}")
        raw = file.read_bytes()
        cfg = tomllib.loads(raw.decode("utf-8"))
        require(set(cfg) == CONFIG_KEYS, f"{module}: missing or unknown registry keys")
        require(type(cfg["schema_version"]) is int and cfg["schema_version"] == 1, "unsupported registry version")
        require(isinstance(cfg["repository"], str) and bool(re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", cfg["repository"])), "invalid repository")
        require(type(cfg["repository_id"]) is int and cfg["repository_id"] > 0, "invalid repository id")
        require(isinstance(cfg["distribution"], str) and bool(MODULE_ID.fullmatch(cfg["distribution"])), "distribution must be normalized")
        require(cfg["distribution"] not in distributions, "duplicate distribution")
        require(isinstance(cfg["import_name"], str) and cfg["import_name"].isascii() and cfg["import_name"].isidentifier(), "invalid import name")
        relative_path(cfg["project_subdirectory"], allow_dot=True)
        validate_ref(cfg["default_ref"])
        require(isinstance(cfg["requesters"], list) and bool(cfg["requesters"]), "requesters must be a nonempty list")
        require(all(isinstance(user, str) and re.fullmatch(r"[A-Za-z0-9-]+(?:\[bot\])?", user) for user in cfg["requesters"]), "invalid requester")
        require(len(set(cfg["requesters"])) == len(cfg["requesters"]), "duplicate requester")
        require(isinstance(cfg["required_files"], list) and bool(cfg["required_files"]), "required_files must be a nonempty list")
        for pattern in cfg["required_files"]:
            relative_path(pattern)
        require(len(set(cfg["required_files"])) == len(cfg["required_files"]), "duplicate required file")
        # Git's Windows checkout may use CRLF; registry identity must be the
        # same in Linux resolution and Windows artifact validation jobs.
        cfg = {**cfg, "module": module, "config_sha256": hashlib.sha256(raw.replace(b"\r\n", b"\n")).hexdigest()}
        registry[module] = cfg
        distributions.add(cfg["distribution"])
    require(bool(registry), "no registered modules")
    return registry


def validate_ref(ref: str) -> None:
    require(
        isinstance(ref, str) and 0 < len(ref) <= 200
        and bool(re.fullmatch(r"[A-Za-z0-9._/-]+", ref))
        and not ref.startswith(("-", "/")) and ".." not in ref
        and not ref.startswith("refs/pull/"),
        "invalid or unsupported source ref",
    )


def validate_request(request: dict[str, Any], *, author_request: bool = False) -> dict[str, str]:
    require(isinstance(request, dict) and set(request) == REQUEST_KEYS, "request keys do not match API v1")
    require(all(isinstance(value, str) for value in request.values()), "API inputs must be strings")
    require(request["api_version"] == "1", "unsupported API version")
    require(request["module"] == "all" or bool(MODULE_ID.fullmatch(request["module"])), "invalid module")
    require(not author_request or request["module"] != "all", "authors must select one module")
    if request["module"] == "all":
        require(not any(request[key] for key in ("source_ref", "source_sha", "expected_version")), "all cannot use a shared ref, SHA or version")
    if request["source_ref"]:
        validate_ref(request["source_ref"])
    if request["source_sha"]:
        require(bool(SHA.fullmatch(request["source_sha"])), "source_sha must be a full lowercase SHA")
    if request["expected_version"]:
        Version(request["expected_version"])
    require(len(request["request_id"]) <= 160 and not any(ord(ch) < 32 for ch in request["request_id"]), "invalid request_id")
    if author_request:
        require(bool(request["source_ref"] and request["source_sha"] and request["expected_version"] and request["request_id"]), "author requests require ref, SHA, version and request_id")
    return request


class GitHubError(RuntimeError):
    def __init__(self, method: str, path: str, status: int):
        super().__init__(f"GitHub API {method} {path}: HTTP {status}")
        self.status = status


class GitHub:
    def __init__(self, token: str | None = None):
        self.token = token or os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")

    def request(self, path: str, *, method: str = "GET", data: Any = None) -> Any:
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "vapoursynth-api4-wheels-modules",
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        payload = None if data is None else json.dumps(data).encode("utf-8")
        if payload is not None:
            headers["Content-Type"] = "application/json"
        request = urllib.request.Request("https://api.github.com/" + path, data=payload, headers=headers, method=method)
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                raw = response.read()
                return json.loads(raw) if raw else None
        except urllib.error.HTTPError as error:
            raise GitHubError(method, path, error.code) from error

    def contents(self, repository: str, path: str, sha: str) -> bytes:
        data = self.request(f"repos/{repository}/contents/{urllib.parse.quote(path, safe='/')}?ref={urllib.parse.quote(sha, safe='')}")
        require(isinstance(data, dict) and data.get("type") == "file" and data.get("encoding") == "base64", "expected a base64 file")
        return base64.b64decode(data["content"], validate=False)


def project_metadata(content: bytes, distribution: str) -> dict[str, Any]:
    document = tomllib.loads(content.decode("utf-8"))
    project = document.get("project", {})
    require(canonicalize_name(project.get("name", "")) == distribution, "source project.name does not match registration")
    version = project.get("version")
    require(isinstance(version, str) and "version" not in project.get("dynamic", []), "API v1 requires a static project.version")
    version = str(Version(version))
    require(not Version(version).local, "local versions are not supported for module releases")
    dependencies = project.get("dependencies", [])
    require(not project.get("optional-dependencies"), "API v1 optional-dependency metadata needs a reviewed extension")
    require(isinstance(dependencies, list) and all(isinstance(item, str) for item in dependencies), "invalid project.dependencies")
    require(not ({"name", "dependencies", "requires-python"} & set(project.get("dynamic", []))), "API v1 requires static project metadata")
    dependencies = sorted(str(Requirement(item)) for item in dependencies)
    requires_python = project.get("requires-python", "")
    require(isinstance(requires_python, str), "invalid requires-python")
    require(isinstance(document.get("build-system", {}).get("build-backend"), str), "build-backend is required")
    return {"version": version, "dependencies": dependencies, "requires_python": requires_python}


def resolve_plan(cfg: dict[str, Any], request: dict[str, str], github: GitHub, *, actor: str, central_sha: str) -> dict[str, Any]:
    require(actor in cfg["requesters"], f"{actor} is not a registered requester for {cfg['module']}")
    require(bool(SHA.fullmatch(central_sha)), "central commit must be a full SHA")
    repo = github.request(f"repos/{cfg['repository']}")
    require(repo["id"] == cfg["repository_id"] and repo["full_name"].lower() == cfg["repository"].lower(), "upstream repository identity changed")
    ref = request["source_ref"] or cfg["default_ref"]
    validate_ref(ref)
    commit = github.request(f"repos/{cfg['repository']}/commits/{urllib.parse.quote(ref, safe='')}")
    sha = commit["sha"]
    require(bool(SHA.fullmatch(sha)), "GitHub returned an invalid commit SHA")
    require(not request["source_sha"] or sha == request["source_sha"], "source_ref and source_sha disagree; retry with the fixed commit")
    subdirectory = cfg["project_subdirectory"]
    project_path = "pyproject.toml" if subdirectory == "." else f"{subdirectory}/pyproject.toml"
    raw = github.contents(cfg["repository"], project_path, sha)
    metadata = project_metadata(raw, cfg["distribution"])
    require(not request["expected_version"] or Version(metadata["version"]) == Version(request["expected_version"]), "expected_version does not match source")
    return {
        "schema_version": 1, "kind": "module", "module": cfg["module"],
        "repository": cfg["repository"], "repository_id": cfg["repository_id"],
        "distribution": cfg["distribution"], "import_name": cfg["import_name"],
        "project_subdirectory": subdirectory, "source_ref": ref, "source_sha": sha,
        "default_ref": cfg["default_ref"], "central_sha": central_sha,
        "config_sha256": cfg["config_sha256"], "pyproject_sha256": hashlib.sha256(raw).hexdigest(),
        "required_files": cfg["required_files"], "actor": actor,
        "request_id": request["request_id"], **metadata,
    }


def check_plan(plan: dict[str, Any], registry: dict[str, dict[str, Any]]) -> dict[str, Any]:
    require(isinstance(plan, dict) and plan.get("schema_version") == 1 and plan.get("kind") == "module", "invalid source plan")
    require(plan.get("module") in registry, "unregistered module in source plan")
    cfg = registry[plan["module"]]
    for key in ("repository", "repository_id", "distribution", "import_name", "project_subdirectory", "required_files", "default_ref", "config_sha256"):
        require(plan.get(key) == cfg[key], f"source plan registration changed: {key}; rebuild before publishing")
    for key in ("source_sha", "central_sha"):
        require(isinstance(plan.get(key), str) and bool(SHA.fullmatch(plan[key])), f"invalid {key}")
    require(bool(re.fullmatch(r"[0-9a-f]{64}", plan.get("pyproject_sha256", ""))), "invalid pyproject hash")
    Version(plan["version"])
    require(plan["actor"] in cfg["requesters"], "unregistered source plan requester")
    return cfg


def git_sha(root: Path = ROOT) -> str:
    return subprocess.check_output(["git", "-C", str(root), "rev-parse", "HEAD"], text=True).strip()
