from __future__ import annotations

import argparse
import os
import site
import sys
import sysconfig
from pathlib import Path


PLUGIN_NAME = "fft3dfilter"


def resolve_vapoursynth_paths(root: Path | None) -> tuple[Path | None, list[Path], list[Path]]:
    if root is None:
        return None, [], []

    root = root.resolve()
    candidates = [
        (root, root / "vapoursynth"),
        (root / "Lib" / "site-packages", root / "Lib" / "site-packages" / "vapoursynth"),
        (root.parent, root),
    ]
    for sys_path, dll_path in candidates:
        if (dll_path / "libvapoursynth.dll").exists() and (dll_path / "__init__.py").exists():
            return dll_path, [sys_path], [dll_path]
    return None, [root], [root]


def resolve_artifact(root: Path) -> Path:
    root = root.resolve()
    candidates = [
        root,
        root / PLUGIN_NAME,
        root / "vapoursynth" / "plugins" / PLUGIN_NAME,
    ]
    for candidate in candidates:
        if (candidate / f"{PLUGIN_NAME}.dll").exists():
            return candidate
    raise FileNotFoundError(root / PLUGIN_NAME / f"{PLUGIN_NAME}.dll")


def add_existing_dll_dirs(paths: list[Path]) -> None:
    for path in paths:
        if path.exists():
            os.add_dll_directory(str(path))


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Smoke-load a built FFT3DFilter artifact with VapourSynth.")
    parser.add_argument("--vapoursynth-root", help="VapourSynth portable root or extracted wheel root.")
    parser.add_argument("--artifact-dir", required=True)
    parser.add_argument("--autoload", action="store_true", help="Load through VAPOURSYNTH_EXTRA_PLUGIN_PATH instead of std.LoadPlugin.")
    parser.add_argument("--exercise-filter", action="store_true", help="Create a FFT3DFilter node and request a frame.")
    args = parser.parse_args(argv)

    vs_root = Path(args.vapoursynth_root).resolve() if args.vapoursynth_root else None
    artifact_root = Path(args.artifact_dir).resolve()
    artifact = resolve_artifact(artifact_root)

    required = [
        artifact / f"{PLUGIN_NAME}.dll",
        artifact / "manifest.vs",
    ]
    for path in required:
        if not path.exists():
            print(f"missing required path: {path}", file=sys.stderr)
            return 1

    _vs_pkg, sys_paths, dll_paths = resolve_vapoursynth_paths(vs_root)
    for path in reversed(sys_paths):
        if path.exists():
            sys.path.insert(0, str(path))

    add_existing_dll_dirs(
        [
            artifact,
            Path(sys.executable).resolve().parent,
            Path(sysconfig.get_paths().get("platlib", "")),
            Path(sysconfig.get_paths().get("purelib", "")),
            *(Path(p) for p in site.getsitepackages()),
            *dll_paths,
        ]
    )

    if args.autoload:
        plugin_root = artifact.parent
        if artifact_root.joinpath("vapoursynth", "plugins").exists():
            plugin_root = artifact_root / "vapoursynth" / "plugins"
        elif artifact_root.joinpath(PLUGIN_NAME).exists():
            plugin_root = artifact_root
        os.environ["VAPOURSYNTH_EXTRA_PLUGIN_PATH"] = str(plugin_root)

    try:
        import vapoursynth as vs
    except ImportError as exc:
        print(f"failed to import VapourSynth Python module: {exc}", file=sys.stderr)
        print("install VapourSynth into this Python or pass --vapoursynth-root pointing at an extracted wheel", file=sys.stderr)
        return 1

    try:
        flags = 0 if args.autoload else vs.DISABLE_AUTO_LOADING
        env = vs.create_environment(flags=flags)
        core = env.get_core()
    except AttributeError:
        core = vs.core

    if not args.autoload:
        core.std.LoadPlugin(str(artifact / f"{PLUGIN_NAME}.dll"))
    if not hasattr(core, PLUGIN_NAME) or not hasattr(core.fft3dfilter, "FFT3DFilter"):
        print("core.fft3dfilter.FFT3DFilter missing after loading artifact", file=sys.stderr)
        return 1
    print(core.fft3dfilter.FFT3DFilter)

    if args.exercise_filter:
        try:
            clip = core.std.BlankClip(format=vs.YUV420P8, width=64, height=32, length=5, color=[96, 128, 128])
            filtered = core.fft3dfilter.FFT3DFilter(
                clip=clip,
                sigma=1.5,
                planes=[0, 1, 2],
                bt=1,
                bw=16,
                bh=16,
                ow=8,
                oh=8,
                measure=0,
            )
            frame = filtered.get_frame(0)
            stats = core.std.PlaneStats(filtered).get_frame(0).props
        except Exception as exc:
            print(f"filter exercise failed: {exc}", file=sys.stderr)
            return 1

        print(f"frame={frame.width}x{frame.height}")
        print(f"PlaneStatsMin={stats['PlaneStatsMin']}")
        print(f"PlaneStatsMax={stats['PlaneStatsMax']}")
        print(f"PlaneStatsAverage={stats['PlaneStatsAverage']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
