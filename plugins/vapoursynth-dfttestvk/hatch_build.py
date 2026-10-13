"""Central wheel wrapper for the pinned DFTTestVK submodule and Release payloads."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import platform
from pathlib import Path, PurePosixPath
import shutil
import subprocess
import sys
import tempfile
import tomllib
import urllib.error
import urllib.request
import zipfile

from hatchling.builders.hooks.plugin.interface import BuildHookInterface
from packaging import tags

ROOT = Path(__file__).resolve().parent
NAME = "vapoursynth-dfttestvk"
PLUGIN = "dfttestvk"
REPOSITORY = "AliceTeaParty/vapoursynth-api4-wheels"
ENV_PREFIX = "DFTTESTVK"


def source_record():
    return json.loads((ROOT / "source.json").read_text(encoding="utf-8"))


def version():
    return tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]["version"]


def platform_info():
    if platform.machine().lower() not in ("amd64", "x86_64") or sys.platform not in ("win32", "linux"):
        raise RuntimeError("DFTTestVK wheels support Windows and Linux x86_64")
    return ("windows-x86_64", ".dll", "win_amd64") if sys.platform == "win32" else ("linux-x86_64", ".so", "manylinux_2_28_x86_64")


def prebuilt_url():
    system, _, _ = platform_info()
    return f"https://github.com/{REPOSITORY}/releases/download/{NAME}-v{version()}/{PLUGIN}-{system}.zip"


def stage_archive(archive_path: Path, target: Path):
    _, suffix, _ = platform_info()
    prefix = PLUGIN + "/"
    with zipfile.ZipFile(archive_path) as archive:
        members = {}
        for info in archive.infolist():
            if info.is_dir():
                continue
            path = PurePosixPath(info.filename)
            if path.is_absolute() or ".." in path.parts or "\\" in info.filename or ":" in info.filename or not info.filename.startswith(prefix):
                raise ValueError("Invalid native package member")
            relative = info.filename[len(prefix):]
            if relative in members:
                raise ValueError("Duplicate native package member")
            members[relative] = info
        required = {PLUGIN + suffix, "manifest.vs", "manifest.json", "LICENSE", "THIRD_PARTY.md"}
        if not required.issubset(members):
            raise ValueError("Native package is missing plugin, manifests or license files")
        manifest = json.loads(archive.read(members["manifest.json"]))
        record = source_record()
        if manifest["distribution"] != NAME or manifest["version"] != version() or manifest["upstream_commit"] != record["commit"]:
            raise ValueError("Prebuilt package source/version does not match the registered submodule")
        if manifest["platform"] != platform_info()[0]:
            raise ValueError("Prebuilt native package belongs to another platform")
        if not (required - {"manifest.json"}).issubset(manifest.get("sha256", {})):
            raise ValueError("Native package lacks required file hashes")
        for relative, info in members.items():
            data = archive.read(info)
            if relative in manifest.get("sha256", {}) and hashlib.sha256(data).hexdigest() != manifest["sha256"][relative]:
                raise ValueError(f"Native package hash mismatch: {relative}")
            destination = target / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(data)


def stage_prebuilt(target: Path):
    if os.environ.get("DFTTESTVK_FORCE_BUILD", "").lower() in ("1", "true", "yes"):
        print("dfttestvk wheel: forced native build", flush=True)
        return False
    explicit = os.environ.get("DFTTESTVK_PREBUILT_URL")
    source = explicit or prebuilt_url()
    with tempfile.TemporaryDirectory(prefix="dfttestvk-prebuilt-") as directory:
        archive = Path(directory) / "payload.zip"
        candidate = Path(source)
        if candidate.is_file():
            shutil.copyfile(candidate, archive)
        else:
            request = urllib.request.Request(source, headers={"User-Agent": NAME + "-wheel"})
            try:
                with urllib.request.urlopen(request, timeout=45) as response, archive.open("wb") as output:
                    shutil.copyfileobj(response, output)
            except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, OSError) as error:
                if explicit:
                    raise RuntimeError("Could not obtain explicit DFTTestVK native package") from error
                print("dfttestvk wheel: Release unavailable; compiling registered source", flush=True)
                return False
        stage_archive(archive, target) # an invalid downloaded asset must not be silently ignored
    print("dfttestvk wheel: using matching Release payload", flush=True)
    return True


def native_source():
    bundled = ROOT / "native"
    # Source archives contain an explicit snapshot without Git metadata.
    # A checkout's native/ is the registered submodule and must retain pin checks.
    if (bundled / "CMakeLists.txt").is_file() and not (bundled / ".git").exists():
        return bundled
    record = source_record()
    submodule = ROOT.parents[1] / record["submodule"]
    if not (submodule / "CMakeLists.txt").is_file():
        raise RuntimeError("Initialize the registered source: git submodule update --init --recursive")
    actual = subprocess.check_output(["git", "-C", str(submodule), "rev-parse", "HEAD"], text=True).strip()
    if actual != record["commit"]:
        raise RuntimeError("Submodule checkout differs from source.json")
    if subprocess.check_output(["git", "-C", str(submodule), "status", "--porcelain", "--untracked-files=no"], text=True).strip():
        raise RuntimeError("The native submodule has uncommitted changes")
    return submodule


def stage_native(source: Path, target: Path):
    env = os.environ.copy()
    include = env.get("DFTTESTVK_VAPOURSYNTH_INCLUDE")
    if not include:
        spec = importlib.util.find_spec("vapoursynth")
        if spec is None or spec.origin is None:
            raise RuntimeError("VapourSynth R81 headers are required for a native build")
        include = str(Path(spec.origin).parent / "include")
    with tempfile.TemporaryDirectory(prefix="dfttestvk-native-") as directory:
        build = Path(directory) / "build"
        headers = env.get("DFTTESTVK_VULKAN_HEADERS")
        if not headers:
            deps = Path(directory) / "dependencies"
            subprocess.run([sys.executable, str(source / "tools/fetch_dependencies.py"), "--destination", str(deps)], check=True, env=env)
            headers = str(deps / "vulkan-headers/include")
        command = ["cmake", "-S", str(source), "-B", str(build), "-G", "Ninja", "-DCMAKE_BUILD_TYPE=Release",
                   "-DVAPOURSYNTH_INCLUDE_DIR=" + include, "-DVULKAN_HEADERS=" + headers]
        if env.get("CXX"):
            command += ["-DCMAKE_CXX_COMPILER=" + env["CXX"]]
        if sys.platform == "linux":
            command += ["-DCMAKE_MODULE_LINKER_FLAGS=-static-libstdc++ -static-libgcc -Wl,--exclude-libs,ALL"]
        subprocess.run(command, check=True, env=env)
        subprocess.run(["cmake", "--build", str(build)], check=True, env=env)
        system, suffix, _ = platform_info()
        shutil.copyfile(build / (PLUGIN + suffix), target / (PLUGIN + suffix))
    for source_file, name in ((source / "LICENSE", "LICENSE"), (source / "THIRD_PARTY.md", "THIRD_PARTY.md")):
        shutil.copyfile(source_file, target / name)
    (target / "manifest.vs").write_text("[VapourSynth Manifest V1]\ndfttestvk\n", encoding="ascii", newline="\n")
    record = source_record()
    manifest = {"distribution": NAME, "version": version(), "platform": system,
                "upstream_repository": record["repository"], "upstream_commit": record["commit"],
                "runtime": "VapourSynth R81 / API4.3 and Vulkan 1.4", "license": "GPL-3.0-or-later",
                "sha256": {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in target.iterdir() if p.is_file()}}
    (target / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8", newline="\n")


class CustomHook(BuildHookInterface):
    def initialize(self, version_name, build_data):
        if version() != source_record()["version"]:
            raise RuntimeError("Wheel version must equal the registered upstream version")
        if self.target_name == "sdist":
            source = native_source()
            self._snapshot = tempfile.TemporaryDirectory(prefix="dfttestvk-sdist-")
            target = Path(self._snapshot.name) / "native"
            target.mkdir()
            for relative in ("CMakeLists.txt", "LICENSE", "THIRD_PARTY.md", "src", "reference"):
                item = source / relative
                if item.is_dir():
                    shutil.copytree(item, target / relative, ignore=shutil.ignore_patterns("__pycache__"))
                else:
                    shutil.copyfile(item, target / relative)
            (target / "tools").mkdir()
            for name in ("fetch_dependencies.py", "generate_shaders.py"):
                shutil.copyfile(source / "tools" / name, target / "tools" / name)
            build_data.setdefault("force_include", {})[str(target)] = "native"
            return
        system, _, release_tag = platform_info()
        self._stage = ROOT / "vapoursynth/plugins" / PLUGIN
        if self._stage.exists():
            shutil.rmtree(self._stage)
        self._stage.mkdir(parents=True)
        used_prebuilt = stage_prebuilt(self._stage)
        if not used_prebuilt:
            stage_native(native_source(), self._stage)
        platform_tag = os.environ.get("DFTTESTVK_PLATFORM_TAG") or (release_tag if used_prebuilt else str(next(tags.platform_tags())))
        build_data["pure_python"] = False
        build_data["tag"] = "py3-none-" + platform_tag

    def finalize(self, version_name, build_data, artifact_path):
        if hasattr(self, "_snapshot"):
            self._snapshot.cleanup()
        if hasattr(self, "_stage") and self._stage.exists():
            shutil.rmtree(self._stage)
