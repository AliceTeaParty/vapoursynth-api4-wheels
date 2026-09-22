from __future__ import annotations

import os
import platform
import importlib.util
import shlex
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
PLUGIN_NAME = "retinex"
PACKAGE_NAME = "Retinex"
DEFAULT_REPOSITORY = "AliceTeaParty/vapoursynth-api4-wheels"
WINDOWS_PREBUILT_ASSET = "retinex-msys2-ucrt64.zip"
LINUX_PREBUILT_ASSET = "retinex-linux-x86_64.zip"


def _truthy(value: str | None) -> bool:
    return bool(value and value.strip().lower() not in {"", "0", "false", "no", "off"})


def _project_version() -> str:
    override = os.environ.get("RETINEX_PREBUILT_VERSION")
    if override:
        return override
    with (ROOT / "pyproject.toml").open("rb") as handle:
        data = tomllib.load(handle)
    version = data.get("project", {}).get("version")
    if not isinstance(version, str) or not version.strip():
        raise RuntimeError("project.version is missing from pyproject.toml")
    return version


def _default_prebuilt_asset() -> str:
    if sys.platform == "linux" and platform.machine().lower() in {"amd64", "x86_64"}:
        return LINUX_PREBUILT_ASSET
    return WINDOWS_PREBUILT_ASSET


def _default_prebuilt_url(version: str) -> str:
    repository = os.environ.get("RETINEX_PREBUILT_REPOSITORY") or os.environ.get("GITHUB_REPOSITORY") or DEFAULT_REPOSITORY
    tag = os.environ.get("RETINEX_PREBUILT_TAG") or f"vapoursynth-retinex-v{version}"
    asset = os.environ.get("RETINEX_PREBUILT_ASSET_NAME") or _default_prebuilt_asset()
    return f"https://github.com/{repository}/releases/download/{tag}/{asset}"


def _prebuilt_source(version: str) -> tuple[str, bool]:
    explicit = os.environ.get("RETINEX_PREBUILT_URL")
    if explicit:
        return explicit, True
    return _default_prebuilt_url(version), False


def _supports_prebuilt() -> bool:
    return sys.platform in {"win32", "linux"} and platform.machine().lower() in {"amd64", "x86_64"}


def _plugin_filename() -> str:
    if sys.platform == "win32":
        return f"{PLUGIN_NAME}.dll"
    if sys.platform == "darwin":
        return f"{PLUGIN_NAME}.dylib"
    return f"{PLUGIN_NAME}.so"


def _fetch_prebuilt_archive(source: str, destination: Path) -> None:
    candidate = Path(source)
    if candidate.exists():
        shutil.copy2(candidate, destination)
        return
    request = urllib.request.Request(source, headers={"User-Agent": "vapoursynth-retinex-build-hook"})
    with urllib.request.urlopen(request, timeout=60) as response, destination.open("wb") as handle:
        shutil.copyfileobj(response, handle)


def _write_manifest(target_dir: Path) -> None:
    (target_dir / "manifest.vs").write_text(
        "[VapourSynth Manifest V1]\n"
        f"{PLUGIN_NAME}\n",
        encoding="ascii",
        newline="\n",
    )


def _stage_package_from_zip(archive_path: Path, target_dir: Path) -> None:
    with zipfile.ZipFile(archive_path) as zf:
        package_members = [
            name for name in zf.namelist()
            if name.replace("\\", "/").startswith(f"{PLUGIN_NAME}/") and not name.endswith("/")
        ]
        if not package_members:
            raise FileNotFoundError(f"prebuilt archive does not contain a {PLUGIN_NAME}/ package directory")
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
    if not (target_dir / "manifest.vs").exists():
        _write_manifest(target_dir)


def _stage_prebuilt_plugin(version: str, target_dir: Path) -> bool:
    if _truthy(os.environ.get("RETINEX_FORCE_BUILD")):
        print(f"{PACKAGE_NAME} wheel build: skipping prebuilt asset because RETINEX_FORCE_BUILD is set")
        return False
    if not _supports_prebuilt():
        print(f"{PACKAGE_NAME} wheel build: no matching platform release asset; falling back to local build")
        return False
    source, explicit = _prebuilt_source(version)
    asset_name = Path(source).name or _default_prebuilt_asset()
    try:
        with tempfile.TemporaryDirectory(prefix="retinex-prebuilt-") as temp_dir_text:
            archive_path = Path(temp_dir_text) / asset_name
            _fetch_prebuilt_archive(source, archive_path)
            _stage_package_from_zip(archive_path, target_dir)
    except Exception as exc:
        if explicit:
            raise RuntimeError(f"failed to use explicit {PACKAGE_NAME} prebuilt asset {source!r}") from exc
        print(f"{PACKAGE_NAME} wheel build: prebuilt asset unavailable at {source}; falling back to local build ({exc})")
        return False
    print(f"{PACKAGE_NAME} wheel build: using prebuilt release asset {source}")
    return True


def _run(cmd: list[str], *, env: dict[str, str]) -> None:
    print("+ " + subprocess.list2cmdline(cmd), flush=True)
    subprocess.run(cmd, cwd=ROOT, check=True, env=env)


def _prepend_path_entries(env: dict[str, str], entries: list[Path]) -> None:
    parts = [str(entry) for entry in entries if entry.exists()]
    if parts:
        existing = env.get("PATH")
        env["PATH"] = os.pathsep.join(parts + ([existing] if existing else []))


def _configure_build_env(env: dict[str, str]) -> dict[str, str]:
    if sys.platform != "win32":
        header_dir: Path | None = None
        spec = importlib.util.find_spec("vapoursynth")
        if spec is not None and spec.origin is not None:
            pkgconfig_dir = Path(spec.origin).resolve().parent / "pkgconfig"
            if not pkgconfig_dir.is_dir():
                raise FileNotFoundError(f"VapourSynth pkg-config metadata is missing: {pkgconfig_dir}")
            existing = env.get("PKG_CONFIG_PATH")
            env["PKG_CONFIG_PATH"] = os.pathsep.join([str(pkgconfig_dir), *([existing] if existing else [])])
            header_dir = pkgconfig_dir.parent / "include"
        if header_dir is None:
            pkg_config = env.get("PKG_CONFIG", "pkg-config")
            result = subprocess.run(
                [pkg_config, "--variable=includedir", "vapoursynth"],
                capture_output=True,
                check=False,
                env=env,
                text=True,
            )
            if result.returncode == 0:
                header_dir = Path(result.stdout.strip())
        if header_dir is None or not (header_dir / "VapourSynth4.h").is_file():
            raise RuntimeError("native Retinex builds require the VapourSynth SDK wheel or vapoursynth.pc")

        # The Linux wheel installs flat headers while Retinex deliberately uses
        # the cross-platform <vapoursynth/...> include form. Stage a private
        # include root instead of changing the installed wheel.
        shim_root = ROOT / "build-wheel-sdk"
        shutil.rmtree(shim_root, ignore_errors=True)
        shutil.copytree(header_dir, shim_root / "vapoursynth")
        existing_flags = env.get("CXXFLAGS")
        env["CXXFLAGS"] = " ".join([f"-I{shlex.quote(str(shim_root))}", *([existing_flags] if existing_flags else [])])
        return env

    msystem_prefix = env.get("MSYSTEM_PREFIX")
    path_entries: list[Path] = []
    if msystem_prefix:
        prefix = Path(msystem_prefix)
        path_entries.extend([prefix / "bin", prefix.parent / "usr" / "bin"])
    else:
        path_entries.extend([Path(r"C:\msys64\ucrt64\bin"), Path(r"C:\msys64\usr\bin")])
    _prepend_path_entries(env, path_entries)
    env.setdefault("CC", "gcc")
    env.setdefault("CXX", "g++")
    return env


def _meson_command() -> list[str]:
    meson = shutil.which("meson")
    if meson:
        return [meson]
    for module in ("mesonbuild", "mesonbuild.mesonmain"):
        command = [sys.executable, "-m", module]
        if subprocess.run(command + ["--version"], cwd=ROOT, capture_output=True).returncode == 0:
            return command
    raise FileNotFoundError("Meson is not available in the build environment")


def _find_built_plugin(build_dir: Path) -> Path:
    suffixes = [".dll"] if sys.platform == "win32" else [".so", ".dylib"]
    for suffix in suffixes:
        for stem in (PLUGIN_NAME, f"lib{PLUGIN_NAME}"):
            candidate = build_dir / f"{stem}{suffix}"
            if candidate.exists():
                return candidate
    raise FileNotFoundError(f"missing built plugin under {build_dir}")


def _stage_local_build(target_dir: Path) -> None:
    env = _configure_build_env(os.environ.copy())
    if sys.platform == "win32":
        build_dir = ROOT / "build-wheel-msys2"
        _run([sys.executable, "tools/ci_prepare_msys2.py"], env=env)
        _run(
            [
                sys.executable,
                "tools/ci_build_msys2.py",
                "--clean",
                "--build-dir",
                str(build_dir),
                "--dist-dir",
                str(target_dir.parent),
            ],
            env=env,
        )
        if not (target_dir / _plugin_filename()).is_file():
            raise FileNotFoundError(target_dir / _plugin_filename())
        return
    meson = _meson_command()
    build_dir = ROOT / "build-wheel"
    _run(meson + ["setup", str(build_dir), "--wipe"], env=env)
    _run(meson + ["compile", "-C", str(build_dir)], env=env)
    plugin = _find_built_plugin(build_dir)
    shutil.copy2(plugin, target_dir / _plugin_filename())
    _write_manifest(target_dir)


class CustomHook(BuildHookInterface[Any]):
    build_dir = ROOT / "build-wheel"
    dist_dir = ROOT / "vapoursynth" / "plugins" / PLUGIN_NAME

    def initialize(self, version: str, build_data: dict[str, Any]) -> None:
        del version
        if not _supports_prebuilt():
            raise RuntimeError("vapoursynth-retinex wheels support only Windows and Linux x86_64")
        build_data["pure_python"] = False
        platform_tag = os.environ.get("RETINEX_PLATFORM_TAG") or str(next(tags.platform_tags()))
        build_data["tag"] = f"py3-none-{platform_tag}"
        project_version = _project_version()
        shutil.rmtree(self.build_dir, ignore_errors=True)
        shutil.rmtree(ROOT / "build-wheel-msys2", ignore_errors=True)
        shutil.rmtree(ROOT / "build-wheel-sdk", ignore_errors=True)
        shutil.rmtree(self.dist_dir.parent.parent, ignore_errors=True)
        self.dist_dir.mkdir(parents=True, exist_ok=True)
        if not _stage_prebuilt_plugin(project_version, self.dist_dir):
            _stage_local_build(self.dist_dir)

    def finalize(self, version: str, build_data: dict[str, Any], artifact_path: str) -> None:
        del version, build_data, artifact_path
        shutil.rmtree(self.build_dir, ignore_errors=True)
        shutil.rmtree(self.dist_dir.parent.parent, ignore_errors=True)
        shutil.rmtree(ROOT / "build-wheel-sdk", ignore_errors=True)
