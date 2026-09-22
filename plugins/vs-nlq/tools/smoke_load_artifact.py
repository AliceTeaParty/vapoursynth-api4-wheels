from __future__ import annotations

import argparse
import os
import site
import sys
import sysconfig
from pathlib import Path


PACKAGE_DIR_NAME = "vs-nlq"
DLL_BASENAME = "vs_nlq"


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
        root / PACKAGE_DIR_NAME,
        root / "vapoursynth" / "plugins" / PACKAGE_DIR_NAME,
    ]
    for candidate in candidates:
        if (candidate / f"{DLL_BASENAME}.dll").exists():
            return candidate
    raise FileNotFoundError(root / PACKAGE_DIR_NAME / f"{DLL_BASENAME}.dll")


def add_existing_dll_dirs(paths: list[Path]) -> None:
    if not hasattr(os, "add_dll_directory"):
        return
    for path in paths:
        if path.exists():
            os.add_dll_directory(str(path))


def create_core(vs: object, *, autoload: bool):
    if hasattr(vs, "create_environment"):
        flags = 0 if autoload else vs.DISABLE_AUTO_LOADING
        env = vs.create_environment(flags=flags)
        return env.get_core()
    return vs.core


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Smoke-load a built vs-nlq artifact with VapourSynth.")
    parser.add_argument("--vapoursynth-root", help="VapourSynth portable root or extracted wheel root.")
    parser.add_argument("--artifact-dir", required=True)
    parser.add_argument("--autoload", action="store_true", help="Load through VAPOURSYNTH_EXTRA_PLUGIN_PATH instead of std.LoadPlugin.")
    parser.add_argument("--exercise-filter", action="store_true", help="Create a MapNLQ node without requesting a frame.")
    args = parser.parse_args(argv)

    vs_root = Path(args.vapoursynth_root).resolve() if args.vapoursynth_root else None
    artifact_root = Path(args.artifact_dir).resolve()
    artifact = resolve_artifact(artifact_root)

    required = [
        artifact / f"{DLL_BASENAME}.dll",
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
        elif artifact_root.joinpath(PACKAGE_DIR_NAME).exists():
            plugin_root = artifact_root
        os.environ["VAPOURSYNTH_EXTRA_PLUGIN_PATH"] = str(plugin_root)

    try:
        import vapoursynth as vs
    except ImportError as exc:
        print(f"failed to import VapourSynth Python module: {exc}", file=sys.stderr)
        print("install VapourSynth into this Python or pass --vapoursynth-root pointing at an extracted wheel", file=sys.stderr)
        return 1

    core = create_core(vs, autoload=args.autoload)

    if not args.autoload:
        core.std.LoadPlugin(str(artifact / f"{DLL_BASENAME}.dll"))
    if not hasattr(core, "vsnlq") or not hasattr(core.vsnlq, "MapNLQ"):
        print("core.vsnlq.MapNLQ missing after loading artifact", file=sys.stderr)
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
