from __future__ import annotations

import hashlib
import os
import platform
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.request
import zipfile
from pathlib import Path
from typing import Any

from hatchling.builders.hooks.plugin.interface import BuildHookInterface
from packaging import tags


ROOT = Path(__file__).resolve().parent
PLUGIN_NAME = "tcanny"
UPSTREAM_DLL = "TCanny.dll"
DEFAULT_REPOSITORY = "AliceTeaParty/vapoursynth-api4-wheels"
WINDOWS_PREBUILT_URL = (
    "https://github.com/HomeOfVapourSynthEvolution/VapourSynth-TCanny/"
    "releases/download/r14/TCanny-r14-win64.7z"
)
WINDOWS_PREBUILT_SHA256 = "4ff024b35da0f2320328d6c3166e943fbc9436543fef891c71bda3725c6d2527"
LINUX_PREBUILT_ASSET = "tcanny-linux-x86_64.zip"


def _supports_prebuilt() -> bool:
    return sys.platform in {"win32", "linux"} and platform.machine().lower() in {"amd64", "x86_64"}


def _truthy(value: str | None) -> bool:
    return bool(value and value.strip().lower() not in {"", "0", "false", "no", "off"})



def _prepend_env_path(env: dict[str, str], name: str, entries: list[Path]) -> None:
    values = [str(entry) for entry in entries if entry.is_dir()]
    if not values:
        return
    existing = env.get(name)
    env[name] = os.pathsep.join(values + ([existing] if existing else []))


def _vapoursynth_root() -> Path | None:
    configured = os.environ.get("TCANNY_VAPOURSYNTH_ROOT")
    if configured:
        root = Path(configured).expanduser().resolve()
        if not (root / "include").is_dir():
            raise RuntimeError(f"TCANNY_VAPOURSYNTH_ROOT has no include directory: {root}")
        return root
    try:
        import vapoursynth
    except ImportError:
        return None
    return Path(vapoursynth.__file__).resolve().parent


def _configure_build_env(env: dict[str, str]) -> dict[str, str]:
    root = _vapoursynth_root()
    if root is not None:
        # Prepend wheel metadata without discarding a caller's unrelated paths.
        _prepend_env_path(env, "PKG_CONFIG_PATH", [root / "pkgconfig", root / "lib" / "pkgconfig"])
    return env


def _meson_command() -> list[str]:
    meson = shutil.which("meson")
    if meson:
        return [meson]
    for module_name in ("mesonbuild", "mesonbuild.mesonmain"):
        command = [sys.executable, "-m", module_name]
        probe = subprocess.run(command + ["--version"], cwd=ROOT, capture_output=True, text=True)
        if probe.returncode == 0:
            return command
    raise FileNotFoundError("meson executable not found and python -m mesonbuild is unavailable")


def _default_prebuilt_url(version: str) -> str:
    if sys.platform == "win32":
        return WINDOWS_PREBUILT_URL
    repository = os.environ.get("TCANNY_PREBUILT_REPOSITORY") or os.environ.get("GITHUB_REPOSITORY") or DEFAULT_REPOSITORY
    tag = os.environ.get("TCANNY_PREBUILT_TAG") or f"vapoursynth-tcanny-v{version}"
    return f"https://github.com/{repository}/releases/download/{tag}/{LINUX_PREBUILT_ASSET}"


def _project_version() -> str:
    match = re.search(r'^version\s*=\s*["\']([^"\']+)["\']\s*$', (ROOT / "pyproject.toml").read_text(encoding="utf-8"), re.MULTILINE)
    if match is None:
        raise RuntimeError("project.version is missing from pyproject.toml")
    return match.group(1)


def _prebuilt_source(version: str) -> tuple[str, bool]:
    explicit = os.environ.get("TCANNY_PREBUILT_URL")
    if explicit:
        return explicit, True
    return _default_prebuilt_url(version), False


def _expected_sha256() -> str | None:
    explicit = os.environ.get("TCANNY_PREBUILT_SHA256")
    if explicit:
        return explicit
    if sys.platform == "win32":
        return WINDOWS_PREBUILT_SHA256
    return None

def _fetch_prebuilt_archive(source: str, destination: Path) -> None:
    candidate = Path(source)
    if candidate.exists():
        shutil.copy2(candidate, destination)
        return

    request = urllib.request.Request(source, headers={"User-Agent": "vapoursynth-tcanny-build-hook"})
    with urllib.request.urlopen(request, timeout=60) as response, destination.open("wb") as handle:
        shutil.copyfileobj(response, handle)


def _check_sha256(path: Path, expected: str) -> None:
    actual = hashlib.sha256(path.read_bytes()).hexdigest()
    if actual.lower() != expected.lower():
        raise RuntimeError(f"{path.name} sha256 mismatch: expected {expected}, got {actual}")


def _find_7z() -> str | None:
    found = shutil.which("7z") or shutil.which("7z.exe")
    if found:
        return found
    for candidate in [
        Path(r"C:\Program Files\7-Zip\7z.exe"),
        Path(r"C:\Program Files (x86)\7-Zip\7z.exe"),
    ]:
        if candidate.exists():
            return str(candidate)
    return None


def _extract_7z(archive_path: Path, extract_dir: Path) -> None:
    try:
        import py7zr
    except ModuleNotFoundError:
        seven_zip = _find_7z()
        if seven_zip is None:
            raise RuntimeError("extracting the upstream .7z asset requires py7zr or a 7z executable") from None
        extract_dir.mkdir(parents=True, exist_ok=True)
        subprocess.run([seven_zip, "x", str(archive_path), f"-o{extract_dir}", "-y"], check=True)
        return

    with py7zr.SevenZipFile(archive_path, mode="r") as archive:
        archive.extractall(path=extract_dir)


def _write_manifest(target_dir: Path) -> None:
    (target_dir / "manifest.vs").write_text(
        "[VapourSynth Manifest V1]\n"
        f"{PLUGIN_NAME}\n",
        encoding="ascii",
        newline="\n",
    )


def _copy_zip_plugin(archive_path: Path, target_dir: Path) -> None:
    with zipfile.ZipFile(archive_path) as archive:
        members = [
            name.replace("\\", "/")
            for name in archive.namelist()
            if name.replace("\\", "/").startswith(f"{PLUGIN_NAME}/") and not name.endswith("/")
        ]
        if not members:
            raise FileNotFoundError(f"prebuilt archive does not contain a {PLUGIN_NAME}/ package directory")
        for member in members:
            relative = Path(member).relative_to(PLUGIN_NAME)
            if ".." in relative.parts:
                raise RuntimeError(f"unsafe archive member: {member}")
            output = target_dir / relative
            output.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(member) as source, output.open("wb") as destination:
                shutil.copyfileobj(source, destination)


def _stage_prebuilt_plugin(version: str, target_dir: Path) -> bool:
    if _truthy(os.environ.get("TCANNY_FORCE_BUILD")):
        print("TCanny wheel build: skipping prebuilt asset because TCANNY_FORCE_BUILD is set")
        return False
    if not _supports_prebuilt():
        print("TCanny wheel build: no matching prebuilt asset for this platform; falling back to a local build")
        return False

    source, explicit = _prebuilt_source(version)
    expected_sha256 = _expected_sha256()
    try:
        with tempfile.TemporaryDirectory(prefix="tcanny-prebuilt-") as temp_dir_text:
            temp_dir = Path(temp_dir_text)
            archive_path = temp_dir / (Path(source).name or f"{PLUGIN_NAME}.zip")
            extract_dir = temp_dir / "extract"
            _fetch_prebuilt_archive(source, archive_path)
            if expected_sha256:
                _check_sha256(archive_path, expected_sha256)

            target_dir.mkdir(parents=True, exist_ok=True)
            if sys.platform == "win32" and archive_path.suffix.lower() == ".7z":
                _extract_7z(archive_path, extract_dir)
                plugin_dll = extract_dir / UPSTREAM_DLL
                if not plugin_dll.exists():
                    raise FileNotFoundError(f"prebuilt archive did not contain {UPSTREAM_DLL}")
                shutil.copy2(plugin_dll, target_dir / f"{PLUGIN_NAME}.dll")
                shutil.copy2(ROOT / "LICENSE", target_dir / "LICENSE")
                _write_manifest(target_dir)
            else:
                _copy_zip_plugin(archive_path, target_dir)

            plugin = target_dir / (f"{PLUGIN_NAME}.dll" if sys.platform == "win32" else f"{PLUGIN_NAME}.so")
            if not plugin.exists():
                raise FileNotFoundError(f"prebuilt archive did not provide {plugin.name}")
            if not (target_dir / "manifest.vs").exists():
                _write_manifest(target_dir)
            if not (target_dir / "LICENSE").exists():
                shutil.copy2(ROOT / "LICENSE", target_dir / "LICENSE")
    except Exception as exc:
        if explicit:
            raise RuntimeError(f"failed to use explicit TCanny prebuilt asset {source!r}") from exc
        print(f"TCanny wheel build: prebuilt asset unavailable at {source}; falling back to a local build ({exc})")
        return False

    print(f"TCanny wheel build: using prebuilt release asset {source}")
    return True


def _find_built_plugin(build_dir: Path) -> Path:
    suffixes = [".dll"] if sys.platform == "win32" else [".so", ".dylib"]
    for suffix in suffixes:
        for stem in (PLUGIN_NAME, f"lib{PLUGIN_NAME}"):
            candidate = build_dir / f"{stem}{suffix}"
            if candidate.exists():
                return candidate
    raise FileNotFoundError(f"missing built plugin under {build_dir}")


class CustomHook(BuildHookInterface[Any]):
    build_dir = ROOT / "build-wheel"
    dist_dir = ROOT / "vapoursynth" / "plugins" / PLUGIN_NAME

    def initialize(self, version: str, build_data: dict[str, Any]) -> None:
        del version
        if not _supports_prebuilt():
            raise RuntimeError("vapoursynth-tcanny wheels support only Windows and Linux x86_64")
        build_data["pure_python"] = False
        platform_tag = os.environ.get("TCANNY_PLATFORM_TAG") or str(next(tags.platform_tags()))
        build_data["tag"] = f"py3-none-{platform_tag}"

        shutil.rmtree(self.build_dir, ignore_errors=True)
        shutil.rmtree(self.dist_dir.parent.parent, ignore_errors=True)
        self.dist_dir.mkdir(parents=True, exist_ok=True)

        if not _stage_prebuilt_plugin(_project_version(), self.dist_dir):
            env = _configure_build_env(os.environ.copy())
            meson = _meson_command()
            subprocess.run(meson + ["setup", str(self.build_dir), "--wipe"], cwd=ROOT, check=True, env=env)
            subprocess.run(meson + ["compile", "-C", str(self.build_dir)], cwd=ROOT, check=True, env=env)
            plugin = _find_built_plugin(self.build_dir)
            shutil.copy2(plugin, self.dist_dir / f"{PLUGIN_NAME}{plugin.suffix}")
            shutil.copy2(ROOT / "LICENSE", self.dist_dir / "LICENSE")
            _write_manifest(self.dist_dir)

    def finalize(self, version: str, build_data: dict[str, Any], artifact_path: str) -> None:
        del version, build_data, artifact_path
        shutil.rmtree(self.build_dir, ignore_errors=True)
        shutil.rmtree(self.dist_dir.parent.parent, ignore_errors=True)
