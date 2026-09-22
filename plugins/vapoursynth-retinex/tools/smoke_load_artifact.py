from __future__ import annotations

import argparse
import os
import site
import sys
import sysconfig
from pathlib import Path


PLUGIN_NAME = "retinex"


def find_package_dir(artifact_dir: Path) -> Path:
    candidates = [
        artifact_dir,
        artifact_dir / PLUGIN_NAME,
        artifact_dir / "vapoursynth" / "plugins" / PLUGIN_NAME,
    ]
    for candidate in candidates:
        if (candidate / "retinex.dll").exists():
            return candidate
    return artifact_dir / PLUGIN_NAME


def add_dll_dirs(paths: list[Path]) -> None:
    add_dll_directory = getattr(os, "add_dll_directory", None)
    if add_dll_directory is None:
        return
    for path in paths:
        if path.exists():
            add_dll_directory(str(path))


def create_core(vs, *, autoload: bool):
    try:
        flags = 0 if autoload else vs.DISABLE_AUTO_LOADING
        env = vs.create_environment(flags=flags)
        return env.get_core()
    except AttributeError:
        return vs.core


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
    print("filter exercise: PASS")


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Smoke-load a built Retinex artifact with VapourSynth.")
    parser.add_argument("--vapoursynth-root", help="VapourSynth portable root or extracted wheel root.")
    parser.add_argument("--artifact-dir", required=True)
    parser.add_argument("--autoload", action="store_true", help="Load through VAPOURSYNTH_EXTRA_PLUGIN_PATH instead of std.LoadPlugin.")
    parser.add_argument("--exercise-filter", action="store_true", help="Render small generated-source cases after loading.")
    args = parser.parse_args(argv)

    vs_root = Path(args.vapoursynth_root).resolve() if args.vapoursynth_root else None
    artifact_root = Path(args.artifact_dir).resolve()
    package_dir = find_package_dir(artifact_root)
    plugin = package_dir / "retinex.dll"
    manifest = package_dir / "manifest.vs"
    for path in [plugin, manifest]:
        if not path.exists():
            print(f"missing required path: {path}", file=sys.stderr)
            return 1

    dll_paths = [
        package_dir,
        Path(sys.executable).resolve().parent,
        Path(sysconfig.get_paths().get("platlib", "")),
        Path(sysconfig.get_paths().get("purelib", "")),
        *(Path(path) for path in site.getsitepackages()),
    ]
    if vs_root is not None:
        dll_paths.extend(
            [
                vs_root,
                vs_root / "Lib" / "site-packages",
                vs_root / "vapoursynth",
            ]
        )
        if (vs_root / "vapoursynth").exists():
            sys.path.insert(0, str(vs_root))
    add_dll_dirs(dll_paths)

    if args.autoload:
        plugin_root = package_dir.parent
        if artifact_root.joinpath("vapoursynth", "plugins").exists():
            plugin_root = artifact_root / "vapoursynth" / "plugins"
        os.environ["VAPOURSYNTH_EXTRA_PLUGIN_PATH"] = str(plugin_root)

    try:
        import vapoursynth as vs
    except ImportError as exc:
        print(f"failed to import VapourSynth Python module: {exc}", file=sys.stderr)
        print("install VapourSynth into this Python or pass --vapoursynth-root pointing at an extracted wheel", file=sys.stderr)
        return 1

    core = create_core(vs, autoload=args.autoload)
    if not args.autoload:
        core.std.LoadPlugin(str(plugin))
    if not hasattr(core, "retinex"):
        print("core.retinex missing after load", file=sys.stderr)
        return 1
    for function_name in ["MSRCP", "MSRCR"]:
        if not hasattr(core.retinex, function_name):
            print(f"core.retinex.{function_name} missing after load", file=sys.stderr)
            return 1
        print(getattr(core.retinex, function_name))
    if args.exercise_filter:
        exercise_filter(core, vs)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
