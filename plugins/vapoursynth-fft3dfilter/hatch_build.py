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
PLUGIN_NAME = "fft3dfilter"
DEFAULT_REPOSITORY = "AliceTeaParty/vapoursynth-api4-wheels"
WINDOWS_PREBUILT_ASSET = "fft3dfilter-msys2-ucrt64.zip"
LINUX_PREBUILT_ASSET = "fft3dfilter-linux-x86_64.zip"


def _truthy(value: str | None) -> bool:
    return bool(value and value.strip().lower() not in {"", "0", "false", "no", "off"})


def _project_metadata() -> dict[str, Any]:
    with (ROOT / "pyproject.toml").open("rb") as handle:
        return tomllib.load(handle)


def _project_version() -> str:
    override = os.environ.get("FFT3DFILTER_PREBUILT_VERSION")
    if override:
        return override
    version = _project_metadata().get("project", {}).get("version")
    if not isinstance(version, str) or not version.strip():
        raise RuntimeError("project.version is missing from pyproject.toml")
    return version


def _release_tag_marker() -> str | None:
    tool = _project_metadata().get("tool", {})
    tag = tool.get("fft3dfilter", {}).get("release", {}).get("tag")
    return tag if isinstance(tag, str) and tag.strip() else None


def _native_suffix() -> str:
    if sys.platform == "win32":
        return ".dll"
    if sys.platform == "darwin":
        return ".dylib"
    return ".so"


def _platform_prebuilt_asset() -> str | None:
    if platform.machine().lower() not in {"amd64", "x86_64"}:
        return None
    if sys.platform == "win32":
        return WINDOWS_PREBUILT_ASSET
    if sys.platform.startswith("linux"):
        return LINUX_PREBUILT_ASSET
    return None


def _prebuilt_sources(version: str) -> tuple[list[str], bool]:
    explicit = os.environ.get("FFT3DFILTER_PREBUILT_URL")
    if explicit:
        return [explicit], True

    asset = os.environ.get("FFT3DFILTER_PREBUILT_ASSET_NAME") or _platform_prebuilt_asset()
    if asset is None:
        return [], False

    repository = (
        os.environ.get("FFT3DFILTER_PREBUILT_REPOSITORY")
        or os.environ.get("GITHUB_REPOSITORY")
        or DEFAULT_REPOSITORY
    )
    override_tag = os.environ.get("FFT3DFILTER_PREBUILT_TAG")
    # The checked-in marker fixes the asset/tag pairing for a source revision.
    # Legacy guesses remain only for old source distributions without the marker.
    tags_to_try = [override_tag] if override_tag else [_release_tag_marker(), f"R{version}", f"v{version}"]

    seen: set[str] = set()
    urls: list[str] = []
    for tag in tags_to_try:
        if not tag or tag in seen:
            continue
        seen.add(tag)
        urls.append(f"https://github.com/{repository}/releases/download/{tag}/{asset}")
    return urls, False


def _fetch_prebuilt_archive(source: str, destination: Path) -> None:
    candidate = Path(source)
    if candidate.exists():
        shutil.copy2(candidate, destination)
        return

    request = urllib.request.Request(source, headers={"User-Agent": "vapoursynth-fft3dfilter-build-hook"})
    with urllib.request.urlopen(request, timeout=60) as response, destination.open("wb") as handle:
        shutil.copyfileobj(response, handle)


def _write_manifest(target_dir: Path) -> None:
    (target_dir / "manifest.vs").write_text(
        "[VapourSynth Manifest V1]\n"
        f"{PLUGIN_NAME}\n",
        encoding="ascii",
        newline="\n",
    )


def _stage_package_from_zip(archive_path: Path, target_dir: Path, suffix: str) -> None:
    with zipfile.ZipFile(archive_path) as zf:
        members = [
            name.replace("\\", "/")
            for name in zf.namelist()
            if name.replace("\\", "/").startswith(f"{PLUGIN_NAME}/") and not name.endswith("/")
        ]
        if not members:
            raise FileNotFoundError(f"prebuilt archive does not contain a {PLUGIN_NAME}/ package directory")

        for member in members:
            relative = member.split("/", 1)[1]
            if not relative or Path(relative).is_absolute() or ".." in Path(relative).parts:
                raise RuntimeError(f"unsafe member in prebuilt archive: {member!r}")
            out_path = target_dir / relative
            out_path.parent.mkdir(parents=True, exist_ok=True)
            with zf.open(member) as src, out_path.open("wb") as dst:
                shutil.copyfileobj(src, dst)

    plugin = target_dir / f"{PLUGIN_NAME}{suffix}"
    if not plugin.exists():
        raise FileNotFoundError(f"prebuilt archive did not provide {plugin.name}")
    if not (target_dir / "manifest.vs").exists():
        _write_manifest(target_dir)


def _stage_prebuilt_plugin(version: str, target_dir: Path) -> bool:
    if _truthy(os.environ.get("FFT3DFILTER_FORCE_BUILD")):
        print("FFT3DFilter wheel build: skipping prebuilt asset because FFT3DFILTER_FORCE_BUILD is set")
        return False

    sources, explicit = _prebuilt_sources(version)
    if not sources:
        print("FFT3DFilter wheel build: no Release asset applies to this platform; falling back to local build")
        return False

    failures: list[str] = []
    for source in sources:
        asset_name = Path(source).name or "fft3dfilter-prebuilt.zip"
        try:
            with tempfile.TemporaryDirectory(prefix="fft3dfilter-prebuilt-") as temp_dir_text:
                archive_path = Path(temp_dir_text) / asset_name
                _fetch_prebuilt_archive(source, archive_path)
                _stage_package_from_zip(archive_path, target_dir, _native_suffix())
            print(f"FFT3DFilter wheel build: using prebuilt release asset {source}")
            return True
        except Exception as exc:
            if explicit:
                raise RuntimeError(f"failed to use explicit FFT3DFilter prebuilt asset {source!r}") from exc
            failures.append(f"{source} ({exc})")

    print("FFT3DFilter wheel build: prebuilt assets unavailable; falling back to local build")
    for failure in failures:
        print(f"  {failure}")
    return False


def _run(cmd: list[str], *, env: dict[str, str]) -> None:
    print("+ " + subprocess.list2cmdline(cmd), flush=True)
    subprocess.run(cmd, cwd=ROOT, check=True, env=env)


def _prepend_path_entries(env: dict[str, str], entries: list[Path]) -> None:
    parts = [str(entry) for entry in entries if entry.exists()]
    if parts:
        env["PATH"] = os.pathsep.join(parts + ([env["PATH"]] if env.get("PATH") else []))


def _prepend_pkg_config(env: dict[str, str], entry: Path) -> None:
    if not (entry / "vapoursynth.pc").exists():
        raise FileNotFoundError(entry / "vapoursynth.pc")
    env["PKG_CONFIG_PATH"] = os.pathsep.join(
        [str(entry), *([env["PKG_CONFIG_PATH"]] if env.get("PKG_CONFIG_PATH") else [])]
    )
    print(f"FFT3DFilter wheel build: prepended VapourSynth pkg-config metadata {entry}")


def _configure_posix_build_env(env: dict[str, str]) -> dict[str, str]:
    try:
        import vapoursynth as vs
    except ImportError as exc:
        raise RuntimeError(
            "a local FFT3DFilter build requires the VapourSynth build dependency; "
            "install through isolated PEP 517 or install VapourSynth>=79 first"
        ) from exc

    package_dir = Path(vs.__file__).resolve().parent
    _prepend_pkg_config(env, package_dir / "pkgconfig")
    return env


def _candidate_msys2_prefixes(env: dict[str, str]) -> list[Path]:
    prefixes: list[Path] = []
    if env.get("MSYSTEM_PREFIX"):
        prefixes.append(Path(env["MSYSTEM_PREFIX"]))
    for var_name in ("MSYS2_ROOT", "MSYS2_DIR"):
        if env.get(var_name):
            root = Path(env[var_name])
            prefixes.extend([root / "ucrt64", root / "mingw64"])
    prefixes.extend([Path("/ucrt64"), Path(r"C:\msys64\ucrt64"), Path(r"C:\msys64\mingw64")])
    return list(dict.fromkeys(prefixes))


def _configure_windows_build_env(env: dict[str, str]) -> dict[str, str]:
    path_entries = [Path(sys.executable).resolve().parent / "Scripts"]
    for prefix in _candidate_msys2_prefixes(env):
        path_entries.extend([prefix / "bin", prefix.parent / "usr" / "bin"])
    _prepend_path_entries(env, path_entries)
    env.setdefault("CC", "gcc")
    env.setdefault("CXX", "g++")
    return env


def _find_native_module(build_dir: Path, suffix: str) -> Path:
    candidates = [
        build_dir / f"lib{PLUGIN_NAME}{suffix}",
        build_dir / f"{PLUGIN_NAME}{suffix}",
    ]
    candidates.extend(build_dir.rglob(f"*{PLUGIN_NAME}*{suffix}"))
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    raise FileNotFoundError(build_dir / f"{PLUGIN_NAME}{suffix}")


def _ensure_ninja_on_path(env: dict[str, str]) -> None:
    if shutil.which("ninja", path=env.get("PATH")):
        return
    try:
        import ninja
    except ImportError as exc:
        raise RuntimeError("ninja is required for a local FFT3DFilter build") from exc
    ninja_dir = Path(ninja.BIN_DIR)
    if not (ninja_dir / "ninja").exists():
        raise RuntimeError("the installed ninja package does not provide a ninja executable")
    env["PATH"] = os.pathsep.join([str(ninja_dir), env.get("PATH", "")])


def _stage_posix_local_build(target_dir: Path) -> Path:
    env = _configure_posix_build_env(os.environ.copy())
    _ensure_ninja_on_path(env)
    build_dir = ROOT / "build-wheel-native"
    shutil.rmtree(build_dir, ignore_errors=True)
    meson = shutil.which("meson", path=env.get("PATH"))
    meson_command = [meson] if meson else [sys.executable, "-m", "mesonbuild.mesonmain"]
    try:
        __import__("mesonbuild.mesonmain")
    except ImportError:
        if not meson:
            raise RuntimeError("meson is required for a local FFT3DFilter build") from None
    _run([*meson_command, "setup", str(build_dir), str(ROOT), "--buildtype", "release"], env=env)
    _run([*meson_command, "compile", "-C", str(build_dir)], env=env)
    module = _find_native_module(build_dir, _native_suffix())
    shutil.copy2(module, target_dir / f"{PLUGIN_NAME}{_native_suffix()}")
    _write_manifest(target_dir)
    return build_dir


def _stage_windows_local_build(target_dir: Path) -> Path:
    env = _configure_windows_build_env(os.environ.copy())
    build_dir = ROOT / "build-wheel-msys2"
    plugins_root = target_dir.parent
    _run([sys.executable, "tools/ci_prepare_msys2.py"], env=env)
    _run(
        [
            sys.executable,
            "tools/ci_build_msys2.py",
            "--clean",
            "--build-dir",
            str(build_dir),
            "--dist-dir",
            str(plugins_root),
        ],
        env=env,
    )
    if not (target_dir / f"{PLUGIN_NAME}.dll").exists():
        raise FileNotFoundError(target_dir / f"{PLUGIN_NAME}.dll")
    return build_dir


class CustomHook(BuildHookInterface[Any]):
    build_dir = ROOT / "build-wheel-native"
    dist_dir = ROOT / "vapoursynth" / "plugins" / PLUGIN_NAME

    def initialize(self, version: str, build_data: dict[str, Any]) -> None:
        del version
        if _platform_prebuilt_asset() is None:
            raise RuntimeError("vapoursynth-fft3dfilter supports only Windows and Linux x86_64")
        build_data["pure_python"] = False
        project_version = _project_version()

        shutil.rmtree(self.build_dir, ignore_errors=True)
        shutil.rmtree(ROOT / "build-wheel-msys2", ignore_errors=True)
        shutil.rmtree(self.dist_dir.parent.parent, ignore_errors=True)
        self.dist_dir.mkdir(parents=True, exist_ok=True)

        used_prebuilt = _stage_prebuilt_plugin(project_version, self.dist_dir)
        if not used_prebuilt:
            if sys.platform == "win32":
                self.build_dir = _stage_windows_local_build(self.dist_dir)
            else:
                self.build_dir = _stage_posix_local_build(self.dist_dir)

        if used_prebuilt and sys.platform.startswith("linux"):
            platform_tag = os.environ.get("FFT3DFILTER_WHEEL_PLATFORM_TAG", "manylinux_2_27_x86_64")
            build_data["tag"] = f"py3-none-{platform_tag}"
        else:
            build_data["tag"] = f"py3-none-{next(tags.platform_tags())}"

    def finalize(self, version: str, build_data: dict[str, Any], artifact_path: str) -> None:
        del version, build_data, artifact_path
        shutil.rmtree(self.build_dir, ignore_errors=True)
        shutil.rmtree(ROOT / "build-wheel-msys2", ignore_errors=True)
        shutil.rmtree(self.dist_dir.parent.parent, ignore_errors=True)
