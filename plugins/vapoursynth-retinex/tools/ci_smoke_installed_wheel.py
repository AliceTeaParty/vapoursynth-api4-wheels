#!/usr/bin/env python3
"""Smoke test an installed Retinex wheel through VapourSynth autoload."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any


PLUGIN_NAME = "retinex"


def frame_hash(frame: Any) -> str:
    digest = hashlib.sha256()
    for plane in range(frame.format.num_planes):
        digest.update(bytes(frame[plane]))
    return digest.hexdigest()


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Smoke test an installed Retinex wheel.")
    parser.add_argument("--site-dir", help="Optional site-packages directory to prepend before imports.")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    if args.site_dir:
        sys.path.insert(0, args.site_dir)

    import vapoursynth as vs

    package_dir = Path(vs.__file__).resolve().parent / "plugins" / PLUGIN_NAME
    native = package_dir / f"{PLUGIN_NAME}{'.dll' if sys.platform == 'win32' else '.dylib' if sys.platform == 'darwin' else '.so'}"
    manifest = package_dir / "manifest.vs"
    if not native.is_file() or not manifest.is_file():
        raise FileNotFoundError(f"installed payload is incomplete: {native}, {manifest}")
    core = vs.core
    namespace = getattr(core, PLUGIN_NAME, None)
    if namespace is None:
        raise RuntimeError("retinex plugin namespace was not autoloaded from the installed wheel")
    src = core.std.BlankClip(width=64, height=48, format=vs.YUV444P8, length=12, color=[96, 128, 128])
    out = core.retinex.MSRCP(src)
    frame = out.get_frame(3)
    stats = dict(core.std.PlaneStats(out).get_frame(3).props)
    result = {
        "vapoursynth_module": vs.__file__,
        "plugin": str(native),
        "namespace_loaded": namespace is not None,
        "width": frame.width,
        "height": frame.height,
        "format": frame.format.name,
        "frames": out.num_frames,
        "frame_hash": frame_hash(frame),
        "plane_stats_average": float(stats["PlaneStatsAverage"]),
        "plane_stats_min": float(stats["PlaneStatsMin"]),
        "plane_stats_max": float(stats["PlaneStatsMax"]),
    }
    print(json.dumps(result, indent=2, sort_keys=True) if args.json else "\n".join(f"{key}={value}" for key, value in result.items()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
