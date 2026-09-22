from __future__ import annotations

import argparse
import os
import site
import sys
import sysconfig
from pathlib import Path


PLUGIN_NAME = "retinex"


def add_existing_dll_dirs(paths: list[Path]) -> None:
    add_dll_directory = getattr(os, "add_dll_directory", None)
    if add_dll_directory is None:
        return
    for path in paths:
        if path.exists():
            add_dll_directory(str(path))


def exercise_filter(core, vs) -> None:
    gray = core.std.BlankClip(width=64, height=32, format=vs.GRAY8, length=1, color=48)
    yuv = core.std.BlankClip(width=64, height=32, format=vs.YUV444P8, length=1, color=[96, 128, 128])
    rgb = core.std.BlankClip(width=64, height=32, format=vs.RGB24, length=1, color=[64, 96, 160])
    cases = [
        core.retinex.MSRCP(gray),
        core.retinex.MSRCP(yuv),
        core.retinex.MSRCP(rgb),
        core.retinex.MSRCR(rgb),
    ]
    for index, clip in enumerate(cases):
        frame = clip.get_frame(0)
        if frame.width != 64 or frame.height != 32:
            raise RuntimeError(f"unexpected output size in case {index}: {frame.width}x{frame.height}")
    stats = core.std.PlaneStats(cases[0]).get_frame(0).props
    print(f"filter exercise: {cases[0].width}x{cases[0].height}")
    print(f"PlaneStatsMin={stats['PlaneStatsMin']}")
    print(f"PlaneStatsMax={stats['PlaneStatsMax']}")
    print(f"PlaneStatsAverage={stats['PlaneStatsAverage']}")


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Smoke-test an installed vapoursynth-retinex wheel.")
    parser.add_argument("--exercise-filter", action="store_true", help="Create Retinex nodes and request one frame.")
    args = parser.parse_args(argv)

    try:
        import vapoursynth as vs
    except ImportError as exc:
        print(f"failed to import VapourSynth Python module: {exc}", file=sys.stderr)
        return 1

    vs_pkg = Path(vs.__file__).resolve().parent
    plugin_dir = vs_pkg / "plugins" / PLUGIN_NAME
    required = [
        plugin_dir / f"{PLUGIN_NAME}.dll",
        plugin_dir / "manifest.vs",
    ]
    for path in required:
        if not path.exists():
            print(f"missing installed file: {path}", file=sys.stderr)
            return 1

    add_existing_dll_dirs(
        [
            plugin_dir,
            vs_pkg,
            Path(sys.executable).resolve().parent,
            Path(sysconfig.get_paths().get("platlib", "")),
            Path(sysconfig.get_paths().get("purelib", "")),
            *(Path(p) for p in site.getsitepackages()),
        ]
    )

    try:
        env = vs.create_environment()
        core = env.get_core()
    except AttributeError:
        core = vs.core

    if not hasattr(core, "retinex"):
        print("core.retinex missing after installed-wheel autoload", file=sys.stderr)
        return 1
    for function_name in ["MSRCP", "MSRCR"]:
        if not hasattr(core.retinex, function_name):
            print(f"core.retinex.{function_name} missing after installed-wheel autoload", file=sys.stderr)
            return 1
        print(getattr(core.retinex, function_name))

    if args.exercise_filter:
        try:
            exercise_filter(core, vs)
        except Exception as exc:
            print(f"filter exercise failed: {exc}", file=sys.stderr)
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
