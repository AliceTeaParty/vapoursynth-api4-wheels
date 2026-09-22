from __future__ import annotations

import os
import platform
import shutil
import subprocess
import sys
import tempfile
import tomllib
import urllib.request
import zipfile
from pathlib import Path
from typing import Any

from hatchling.builders.hooks.plugin.interface import BuildHookInterface
from packaging import tags


ROOT = Path(__file__).resolve().parent
PACKAGE_DIR_NAME = "vs-nlq"
PLUGIN_BASENAME = "vs_nlq"
DEFAULT_REPOSITORY = "AliceTeaParty/vapoursynth-api4-wheels"
WINDOWS_PREBUILT_ASSET = "vs-nlq-windows-x86_64.zip"
LINUX_PREBUILT_ASSET = "vs-nlq-linux-x86_64.zip"
ENV_PREFIX = "VS_NLQ"


def _truthy(value: str | None) -> bool:
    return bool(value and value.strip().lower() not in {"", "0", "false", "no", "off"})


def _project_version() -> str:
    override = os.environ.get(f"{ENV_PREFIX}_PREBUILT_VERSION")
    if override:
        return override
    with (ROOT / "pyproject.toml").open("rb") as handle:
        data = tomllib.load(handle)
    version = data.get("project", {}).get("version")
    if not isinstance(version, str) or not version.strip():
        raise RuntimeError("project.version is missing from pyproject.toml")
    return version


def _default_prebuilt_url(version: str) -> str:
    repository = os.environ.get(f"{ENV_PREFIX}_PREBUILT_REPOSITORY") or os.environ.get("GITHUB_REPOSITORY") or DEFAULT_REPOSITORY
    tag = os.environ.get(f"{ENV_PREFIX}_PREBUILT_TAG") or f"vs-nlq-v{version}"
    asset = os.environ.get(f"{ENV_PREFIX}_PREBUILT_ASSET_NAME") or _default_prebuilt_asset()
    return f"https://github.com/{repository}/releases/download/{tag}/{asset}"


def _prebuilt_source(version: str) -> tuple[str, bool]:
    explicit = os.environ.get(f"{ENV_PREFIX}_PREBUILT_URL")
    if explicit:
        return explicit, True
    return _default_prebuilt_url(version), False


def _default_prebuilt_asset() -> str:
    if sys.platform == "linux" and platform.machine().lower() in {"amd64", "x86_64"}:
        return LINUX_PREBUILT_ASSET
    return WINDOWS_PREBUILT_ASSET


def _supports_prebuilt() -> bool:
    return sys.platform in {"win32", "linux"} and platform.machine().lower() in {"amd64", "x86_64"}


def _ensure_supported_platform() -> None:
    if not _supports_prebuilt():
        raise RuntimeError("vs-nlq wheels support only Windows and Linux x86_64")


def _plugin_filename() -> str:
    if sys.platform == "win32":
        return f"{PLUGIN_BASENAME}.dll"
    if sys.platform == "darwin":
        return f"lib{PLUGIN_BASENAME}.dylib"
    return f"lib{PLUGIN_BASENAME}.so"


def _manifest_plugin_name() -> str:
    return Path(_plugin_filename()).stem


def _fetch_prebuilt_archive(source: str, destination: Path) -> None:
    candidate = Path(source)
    if candidate.exists():
        shutil.copy2(candidate, destination)
        return

    request = urllib.request.Request(source, headers={"User-Agent": "vs-nlq-build-hook"})
    with urllib.request.urlopen(request, timeout=60) as response, destination.open("wb") as handle:
        shutil.copyfileobj(response, handle)


def _stage_package_from_zip(archive_path: Path, target_dir: Path) -> None:
    with zipfile.ZipFile(archive_path) as zf:
        package_members = [
            name
            for name in zf.namelist()
            if name.replace("\\", "/").startswith(f"{PACKAGE_DIR_NAME}/") and not name.endswith("/")
        ]
        if not package_members:
            raise FileNotFoundError(f"prebuilt archive does not contain a {PACKAGE_DIR_NAME}/ package directory")

        for member in package_members:
            normalized = member.replace("\\", "/")
            relative = normalized.split("/", 1)[1]
            out_path = target_dir / relative
            out_path.parent.mkdir(parents=True, exist_ok=True)
            with zf.open(member) as src, out_path.open("wb") as dst:
                shutil.copyfileobj(src, dst)

    plugin = target_dir / _plugin_filename()
    if not plugin.exists():
        raise FileNotFoundError(f"prebuilt archive did not provide {_plugin_filename()}")
    manifest = target_dir / "manifest.vs"
    if not manifest.exists():
        manifest.write_text(
            f"[VapourSynth Manifest V1]\n{_manifest_plugin_name()}\n",
            encoding="ascii",
            newline="\n",
        )


def _stage_prebuilt_plugin(version: str, target_dir: Path) -> bool:
    if _truthy(os.environ.get(f"{ENV_PREFIX}_FORCE_BUILD")):
        print("vs-nlq wheel build: skipping prebuilt asset because VS_NLQ_FORCE_BUILD is set")
        return False
    if not _supports_prebuilt():
        print("vs-nlq wheel build: no matching prebuilt release asset for this platform; falling back to local build")
        return False

    source, explicit = _prebuilt_source(version)
    asset_name = Path(source).name or _default_prebuilt_asset()
    try:
        with tempfile.TemporaryDirectory(prefix="vs-nlq-prebuilt-") as temp_dir_text:
            archive_path = Path(temp_dir_text) / asset_name
            _fetch_prebuilt_archive(source, archive_path)
            _stage_package_from_zip(archive_path, target_dir)
    except Exception as exc:
        if explicit:
            raise RuntimeError(f"failed to use explicit vs-nlq prebuilt asset {source!r}") from exc
        print(f"vs-nlq wheel build: prebuilt asset unavailable at {source}; falling back to local build ({exc})")
        return False

    print(f"vs-nlq wheel build: using prebuilt release asset {source}")
    return True


def _run(cmd: list[str], *, env: dict[str, str]) -> None:
    print("+ " + subprocess.list2cmdline(cmd), flush=True)
    subprocess.run(cmd, cwd=ROOT, check=True, env=env)


def _stage_local_build(target_dir: Path) -> None:
    env = os.environ.copy()
    plugins_root = target_dir.parent
    tool = "tools/ci_build_windows.py" if sys.platform == "win32" else "tools/ci_build_native.py"
    _run([sys.executable, tool, "--clean", "--dist-dir", str(plugins_root)], env=env)
    plugin = target_dir / _plugin_filename()
    if not plugin.exists():
        raise FileNotFoundError(plugin)


def _wheel_platform_tag(*, used_prebuilt: bool) -> str:
    override = os.environ.get(f"{ENV_PREFIX}_PLATFORM_TAG")
    if override:
        return override
    if used_prebuilt and sys.platform == "linux" and platform.machine().lower() in {"amd64", "x86_64"}:
        # R79 itself is manylinux_2_27, so this is the tested end-to-end floor.
        return "manylinux_2_27_x86_64"
    return str(next(tags.platform_tags()))


class CustomHook(BuildHookInterface[Any]):
    dist_dir = ROOT / "vapoursynth" / "plugins" / PACKAGE_DIR_NAME

    def initialize(self, version: str, build_data: dict[str, Any]) -> None:
        del version
        _ensure_supported_platform()
        build_data["pure_python"] = False
        project_version = _project_version()

        shutil.rmtree(self.dist_dir.parent.parent, ignore_errors=True)
        self.dist_dir.mkdir(parents=True, exist_ok=True)

        used_prebuilt = _stage_prebuilt_plugin(project_version, self.dist_dir)
        if not used_prebuilt:
            _stage_local_build(self.dist_dir)
        build_data["tag"] = f"py3-none-{_wheel_platform_tag(used_prebuilt=used_prebuilt)}"

    def finalize(self, version: str, build_data: dict[str, Any], artifact_path: str) -> None:
        del version, build_data, artifact_path
        shutil.rmtree(self.dist_dir.parent.parent, ignore_errors=True)
