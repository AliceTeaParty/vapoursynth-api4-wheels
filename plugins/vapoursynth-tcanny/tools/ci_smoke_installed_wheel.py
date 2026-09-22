#!/usr/bin/env python3
"""Autoload smoke test for an installed TCanny wheel."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from typing import Any


def frame_hash(frame: Any) -> str:
    digest = hashlib.sha256()
    for plane in range(frame.format.num_planes):
        digest.update(bytes(frame[plane]))
    return digest.hexdigest()


def representative_source(core: Any, vs_module: Any) -> Any:
    inner = core.std.BlankClip(width=48, height=32, format=vs_module.YUV420P8, length=12, color=[16, 128, 128])
    return core.std.AddBorders(inner, left=8, right=8, top=8, bottom=8, color=[235, 128, 128])


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Smoke test TCanny from an installed wheel.")
    parser.add_argument("--site-dir", help="Optional site-packages directory to prepend.")
    parser.add_argument("--json", action="store_true", help="Emit JSON output.")
    args = parser.parse_args(argv)
    if args.site_dir:
        sys.path.insert(0, args.site_dir)

    import vapoursynth as vs  # pylint: disable=import-outside-toplevel

    core = vs.core
    if getattr(core, "tcanny", None) is None:
        raise RuntimeError("tcanny namespace was not autoloaded from the installed wheel")
    source = representative_source(core, vs)
    output = core.tcanny.TCanny(source, opt=1)
    frames = {number: output.get_frame(number) for number in (0, 3, 11)}
    stats = dict(core.std.PlaneStats(output).get_frame(3).props)
    try:
        core.tcanny.TCanny(source, t_h=1.0, t_l=1.0)
    except vs.Error as error:
        invalid_error = str(error)
    else:
        raise RuntimeError("TCanny accepted t_h <= t_l")
    frame = frames[3]
    result = {
        "vapoursynth_module": vs.__file__,
        "namespace_loaded": True,
        "width": frame.width,
        "height": frame.height,
        "format": frame.format.name,
        "frames": output.num_frames,
        "frame_hashes": {number: frame_hash(value) for number, value in frames.items()},
        "plane_stats_average": float(stats["PlaneStatsAverage"]),
        "plane_stats_min": float(stats["PlaneStatsMin"]),
        "plane_stats_max": float(stats["PlaneStatsMax"]),
        "invalid_error": invalid_error,
    }
    print(json.dumps(result, indent=2, sort_keys=True) if args.json else result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
