from __future__ import annotations

import argparse
import os
import site
import sys
import sysconfig
from pathlib import Path


PACKAGE_DIR_NAME = "vs-nlq"
DLL_BASENAME = "vs_nlq"


def add_existing_dll_dirs(paths: list[Path]) -> None:
    if not hasattr(os, "add_dll_directory"):
        return
    for path in paths:
        if path.exists():
            os.add_dll_directory(str(path))


def create_core(vs: object):
    if hasattr(vs, "create_environment"):
        env = vs.create_environment()
        return env.get_core()
    return vs.core


def installed_plugin_dir(module_file: str) -> Path:
    module_dir = Path(module_file).resolve().parent
    package_dir = module_dir if module_dir.name.casefold() == "vapoursynth" else module_dir / "vapoursynth"
    return package_dir / "plugins" / PACKAGE_DIR_NAME


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Smoke-test an installed vs-nlq wheel.")
    parser.add_argument("--exercise-filter", action="store_true", help="Create a MapNLQ node without requesting a frame.")
    args = parser.parse_args(argv)

    try:
        import vapoursynth as vs
    except ImportError as exc:
        print(f"failed to import VapourSynth Python module: {exc}", file=sys.stderr)
        return 1

    vs_module_dir = Path(vs.__file__).resolve().parent
    plugin_dir = installed_plugin_dir(vs.__file__)
    required = [
        plugin_dir / f"{DLL_BASENAME}.dll",
        plugin_dir / "manifest.vs",
    ]
    for path in required:
        if not path.exists():
            print(f"missing installed file: {path}", file=sys.stderr)
            return 1

    add_existing_dll_dirs(
        [
            plugin_dir,
            vs_module_dir,
            Path(sys.executable).resolve().parent,
            Path(sysconfig.get_paths().get("platlib", "")),
            Path(sysconfig.get_paths().get("purelib", "")),
            *(Path(p) for p in site.getsitepackages()),
        ]
    )

    core = create_core(vs)

    if not hasattr(core, "vsnlq") or not hasattr(core.vsnlq, "MapNLQ"):
        print("core.vsnlq.MapNLQ missing after installed-wheel autoload", file=sys.stderr)
        return 1
    print(core.vsnlq.MapNLQ)

    if args.exercise_filter:
        try:
            bl = core.std.BlankClip(format=vs.YUV420P16, width=64, height=32, length=1, color=[4096, 32768, 32768])
            el = core.std.BlankClip(format=vs.YUV420P10, width=64, height=32, length=1, color=[64, 512, 512])
            mapped = core.vsnlq.MapNLQ(bl, el)
        except Exception as exc:
            print(f"filter node creation failed: {exc}", file=sys.stderr)
            return 1

        if mapped.width != 64 or mapped.height != 32 or mapped.format.name != "YUV420P12":
            print(
                f"unexpected MapNLQ output: {mapped.width}x{mapped.height} {mapped.format.name}",
                file=sys.stderr,
            )
            return 1
        print(f"MapNLQ node: {mapped.width}x{mapped.height} {mapped.format.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
