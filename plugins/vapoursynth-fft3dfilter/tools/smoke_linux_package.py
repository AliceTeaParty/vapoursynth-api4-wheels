from __future__ import annotations

import argparse
import hashlib
import json
import sys
import tempfile
import zipfile
from pathlib import Path


PLUGIN_NAME = "fft3dfilter"


def package_from_zip(path: Path, extraction_root: Path) -> Path:
    with zipfile.ZipFile(path) as archive:
        names = {name.replace("\\", "/") for name in archive.namelist() if not name.endswith("/")}
        required = {f"{PLUGIN_NAME}/fft3dfilter.so", f"{PLUGIN_NAME}/manifest.vs"}
        missing = required - names
        if missing:
            raise RuntimeError(f"release zip is missing required files: {sorted(missing)}")
        top_levels = {name.split("/", 1)[0] for name in names}
        if top_levels != {PLUGIN_NAME}:
            raise RuntimeError(f"release zip must contain exactly one top-level {PLUGIN_NAME!r} directory: {sorted(top_levels)}")
        archive.extractall(extraction_root)
    return extraction_root / PLUGIN_NAME


def frame_digest(frame: object) -> str:
    digest = hashlib.sha256()
    for plane in range(frame.format.num_planes):
        digest.update(bytes(frame[plane]))
    return digest.hexdigest()


def create_core(vs: object, disable_autoload: bool) -> object:
    try:
        environment = vs.create_environment(flags=vs.DISABLE_AUTO_LOADING if disable_autoload else 0)
        return environment.get_core()
    except AttributeError:
        return vs.core


def exercise(core: object, vs: object) -> dict[str, object]:
    clip = core.std.BlankClip(
        format=vs.YUV420P8,
        width=64,
        height=48,
        length=12,
        color=[96, 128, 128],
    )
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
    hashes: dict[str, str] = {}
    frame_info: dict[str, object] | None = None
    for index in (0, 3, 11):
        frame = filtered.get_frame(index)
        hashes[str(index)] = frame_digest(frame)
        if frame_info is None:
            frame_info = {
                "width": frame.width,
                "height": frame.height,
                "format": frame.format.name,
                "num_frames": filtered.num_frames,
            }
    stats = core.std.PlaneStats(filtered, plane=0).get_frame(0).props
    return {
        "frames": frame_info,
        "hashes": hashes,
        "plane_stats": {
            "min": stats["PlaneStatsMin"],
            "max": stats["PlaneStatsMax"],
            "average": stats["PlaneStatsAverage"],
        },
    }


def invalid_input(core: object, vs: object) -> str:
    clip = core.std.BlankClip(format=vs.YUV420P8, width=64, height=48, length=1)
    try:
        core.fft3dfilter.FFT3DFilter(clip=clip, bt=6)
    except Exception as exc:
        message = str(exc)
        expected = "bt must be -1(Sharpen), 0(Kalman) or 1,2,3,4,5(Wiener)"
        if expected not in message:
            raise RuntimeError(f"unexpected invalid-input error: {message}") from exc
        return message
    raise RuntimeError("bt=6 unexpectedly succeeded")


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Smoke-test a Linux FFT3DFilter release zip or installed wheel.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--artifact-zip")
    group.add_argument("--installed-wheel", action="store_true")
    args = parser.parse_args(argv)

    import vapoursynth as vs

    result: dict[str, object] = {"mode": "installed-wheel" if args.installed_wheel else "release-zip"}
    if args.artifact_zip:
        with tempfile.TemporaryDirectory(prefix="fft3dfilter-smoke-") as temporary:
            plugin_dir = package_from_zip(Path(args.artifact_zip).resolve(), Path(temporary))
            result["plugin_dir"] = str(plugin_dir)
            core = create_core(vs, disable_autoload=True)
            core.std.LoadPlugin(str(plugin_dir / "fft3dfilter.so"))
            if not hasattr(core, PLUGIN_NAME) or not hasattr(core.fft3dfilter, "FFT3DFilter"):
                raise RuntimeError("core.fft3dfilter.FFT3DFilter is absent after explicit LoadPlugin")
            result["load"] = "explicit LoadPlugin succeeded"
            result.update(exercise(core, vs))
            result["invalid_input"] = invalid_input(core, vs)
    else:
        plugin_dir = Path(vs.__file__).resolve().parent / "plugins" / PLUGIN_NAME
        required = [plugin_dir / "fft3dfilter.so", plugin_dir / "manifest.vs"]
        missing = [str(path) for path in required if not path.exists()]
        if missing:
            raise RuntimeError(f"installed wheel files missing: {missing}")
        result["plugin_dir"] = str(plugin_dir)
        core = create_core(vs, disable_autoload=False)
        if not hasattr(core, PLUGIN_NAME) or not hasattr(core.fft3dfilter, "FFT3DFilter"):
            raise RuntimeError("core.fft3dfilter.FFT3DFilter is absent after manifest autoload")
        result["load"] = "manifest autoload succeeded"
        result.update(exercise(core, vs))
        result["invalid_input"] = invalid_input(core, vs)

    print(json.dumps(result, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
