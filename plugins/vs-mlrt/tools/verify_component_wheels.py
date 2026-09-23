from __future__ import annotations

import argparse
from email.parser import BytesParser
from pathlib import Path, PurePosixPath
import re
import struct
import zipfile


ASSET_LIMIT = 2 * 1024 ** 3
ENTRY_FILES = {
    "rm_vsmlrt/__init__.py",
    "rm_vsmlrt/__main__.py",
    "rm_vsmlrt/cli.py",
    "vs_mlrt_dll_paths.pth",
    "vsmlrt.py",
    "vsmlrt_dll_paths.py",
    "vapoursynth/plugins/vsmlrt/manifest.vs",
}
CLOSURES = {
    "vs-mlrt-generic": {"vs-mlrt-generic", "vs-mlrt-models", "vs-ov", "vs-ncnn"},
    "vs-mlrt-cu121": {
        "vs-mlrt-cu121", "vs-mlrt-models", "vs-ov", "vs-ncnn", "vs-cublas-cu121",
        "vs-cudnn-cu121", "vs-tensorrt-core-cu121", "vs-tensorrt-builder-cu121",
        "vs-trtexec-cu121", "vs-trt-cu121",
    },
    "vs-mlrt-cu129": {
        "vs-mlrt-cu129", "vs-mlrt-models", "vs-ov", "vs-ncnn", "vs-tensorrt-core-cu129",
        "vs-tensorrt-builder-cu129-base", "vs-tensorrt-builder-cu129-modern",
        "vs-trtexec-cu129", "vs-trt-cu129", "vs-tensorrt-rtx-cu129", "vs-trt-rtx-cu129",
    },
}
REMOVED_CU129_PREFIXES = (
    "cudart", "cublas", "cudnn", "cufft", "nvblas", "nvrtc", "nvvm", "nvjitlink",
    "libcudart", "libcublas", "libcudnn", "libcufft", "libnvblas", "libnvrtc", "libnvvm", "libnvjitlink",
)


def normalize(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def elf_requests_executable_stack(payload: bytes) -> bool:
    if len(payload) < 64 or payload[:4] != b"\x7fELF" or payload[4:6] != b"\x02\x01":
        return False
    program_offset = struct.unpack_from("<Q", payload, 0x20)[0]
    entry_size, entry_count = struct.unpack_from("<HH", payload, 0x36)
    for index in range(entry_count):
        offset = program_offset + index * entry_size
        if offset + 8 > len(payload):
            break
        kind, flags = struct.unpack_from("<II", payload, offset)
        if kind == 0x6474E551:  # PT_GNU_STACK
            return bool(flags & 1)  # PF_X
    return False


def wheel_info(path: Path) -> tuple[str, set[str], zipfile.ZipFile]:
    archive = zipfile.ZipFile(path)
    metadata_name = next(name for name in archive.namelist() if name.endswith(".dist-info/METADATA"))
    message = BytesParser().parsebytes(archive.read(metadata_name))
    name = normalize(message["Name"])
    files = {
        value for value in archive.namelist()
        if ".dist-info/" not in value and not value.endswith("/")
    }
    return name, files, archive


def verify(
    wheelhouse: Path,
    entries: tuple[str, ...] | None = None,
    target_platform: str | None = None,
) -> None:
    wheels = sorted(wheelhouse.glob("*.whl"))
    if target_platform == "windows":
        wheels = [path for path in wheels if path.name.endswith(("-any.whl", "-win_amd64.whl"))]
    elif target_platform == "linux":
        wheels = [path for path in wheels if path.name.endswith("-any.whl") or "-manylinux_" in path.name]
    if not wheels:
        raise RuntimeError(f"No wheels found in {wheelhouse}")
    packages: dict[str, tuple[Path, set[str]]] = {}
    archives: list[zipfile.ZipFile] = []
    try:
        for wheel in wheels:
            if wheel.stat().st_size >= ASSET_LIMIT:
                raise RuntimeError(f"Wheel exceeds GitHub's 2 GiB asset limit: {wheel.name}")
            name, files, archive = wheel_info(wheel)
            archives.append(archive)
            if target_platform == "linux":
                executable_stack = [
                    filename for filename in archive.namelist()
                    if not filename.endswith("/") and elf_requests_executable_stack(archive.read(filename))
                ]
                if executable_stack:
                    raise RuntimeError(f"{wheel.name} contains ELF files requesting an executable stack: {executable_stack}")
            if name in packages:
                raise RuntimeError(f"Duplicate wheel distribution: {name}")
            packages[name] = (wheel, files)

        selected_closures = {entry: CLOSURES[entry] for entry in entries} if entries else CLOSURES
        for entry, closure in selected_closures.items():
            missing = sorted(closure - packages.keys())
            if missing:
                raise RuntimeError(f"{entry} closure is missing wheels: {missing}")
            owners: dict[str, str] = {}
            for package in sorted(closure):
                for filename in packages[package][1]:
                    if filename in owners:
                        raise RuntimeError(f"{entry} has overlapping file {filename}: {owners[filename]} and {package}")
                    owners[filename] = package

        for entry in selected_closures:
            files = packages[entry][1]
            if files != ENTRY_FILES:
                raise RuntimeError(f"{entry} owns unexpected entry files: {sorted(files ^ ENTRY_FILES)}")

        if "vs-mlrt-cu129" in selected_closures:
            cu129_files = {
                filename for package in CLOSURES["vs-mlrt-cu129"] for filename in packages[package][1]
            }
            forbidden = sorted(
                filename for filename in cu129_files
                if PurePosixPath(filename).name.lower().startswith(REMOVED_CU129_PREFIXES)
            )
            if forbidden:
                raise RuntimeError(f"cu129 closure restored removed runtime files: {forbidden}")

        for entry, expected_plugins in {
            "vs-mlrt-generic": ["vsncnn", "vsov"],
            "vs-mlrt-cu121": ["vsncnn", "vsov", "vstrt"],
            "vs-mlrt-cu129": ["vsncnn", "vsov", "vstrt", "vstrt_rtx"],
        }.items():
            if entry not in selected_closures:
                continue
            archive = next(item for item in archives if normalize(BytesParser().parsebytes(
                item.read(next(name for name in item.namelist() if name.endswith(".dist-info/METADATA")))
            )["Name"]) == entry)
            manifest = archive.read("vapoursynth/plugins/vsmlrt/manifest.vs").decode("ascii").splitlines()
            if manifest != ["[VapourSynth Manifest V1]", *expected_plugins]:
                raise RuntimeError(f"{entry} manifest is incorrect: {manifest}")
    finally:
        for archive in archives:
            archive.close()
    label = ", ".join(entries) if entries else "all three dependency closures"
    if target_platform:
        label += f" on {target_platform}"
    print(f"Verified {len(wheels)} split vs-mlrt wheels for {label}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("wheelhouse", type=Path)
    parser.add_argument("--entry", action="append", choices=sorted(CLOSURES))
    parser.add_argument("--platform", choices=("windows", "linux"))
    args = parser.parse_args()
    verify(args.wheelhouse.resolve(), tuple(args.entry) if args.entry else None, args.platform)


if __name__ == "__main__":
    main()
