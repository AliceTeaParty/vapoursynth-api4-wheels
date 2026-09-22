#!/usr/bin/env python3
"""Exercise a native vs-nlq package with a deterministic profile-7 RPU."""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PACKAGE_DIR_NAME = "vs-nlq"
# quietvoid/dovi_tool's MIT-licensed fel_orig.bin fixture, SHA-256
# b2b27714b7279c4e24d1a795cb6f95d3ad06745db96d360698ee0932184117a0.
PROFILE7_RPU_BASE64 = (
    "AAAAARkICQhAYTZQriAAIAgCAIAgCAIAf4Af/AD/wAH/+gAAAwEAAAMA0AAACAAABoAAAEAAADQAAAMCAAADAaAAABAAAA0AAAMAgAAAaAAABAAAAwNAAAAgAAAKhtnmey+GPvwYnmAp6YwGuMVmp81fjf/LbYw544qZgbhspnkPQF9DTLfYDp4Ew0n9O7d+ws1d46FH1EwKLoBiFkoCm11ZUA7Tj1jEbE7BOhRYLP8wI1NtV7u25BFIO5KWZBNpj85rwxvWIPrdQFu+9GQxYLHwG/Lu+/Kl4vPMtKvzzDmDd551aDEbAEgAAEAEAEAAAEASAAAQAQAQAAAQBIAABABABAAAByVmAAA16iVm+fzrHCVmRMoAAAMBAAADAAgAAAMACAAAAwAcNiJDAYYKXjCOBRQAAAMBpj5a//8AAAMAAAMAAAMAAGAgD4DhUYAwCABZyhIAwCghjfglgAgAYUAAAgIqUSCIBQAAAwACKBFQEgwH0AACDWABXrjynYKA"
)


def plugin_filename() -> str:
    if sys.platform == "win32":
        return "vs_nlq.dll"
    if sys.platform == "darwin":
        return "libvs_nlq.dylib"
    return "libvs_nlq.so"


def frame_hash(frame: Any) -> str:
    digest = hashlib.sha256()
    for plane in range(frame.format.num_planes):
        digest.update(bytes(frame[plane]))
    return digest.hexdigest()


class IsolatedEnvironmentPolicy:
    """Use R79's policy API to create a core with autoload disabled."""

    def __init__(self, flags: int) -> None:
        self._api: Any = None
        self._environment: Any = None
        self._flags = flags

    def on_policy_registered(self, api: Any) -> None:
        self._api = api
        self._environment = api.create_environment(self._flags)

    def on_policy_cleared(self) -> None:
        self._api = None
        self._environment = None

    def get_current_environment(self) -> Any:
        return self._environment

    def set_environment(self, environment: Any) -> Any:
        previous = self._environment
        if environment is not None:
            self._environment = environment
        return previous

    def is_alive(self, environment: Any) -> bool:
        return environment is self._environment

    def close(self) -> None:
        if self._api is not None and self._environment is not None:
            self._api.destroy_environment(self._environment)
            self._environment = None


def install_isolated_policy(vs_module: Any) -> IsolatedEnvironmentPolicy | None:
    if not hasattr(vs_module, "register_policy") or vs_module.has_policy():
        return None
    policy = IsolatedEnvironmentPolicy(int(vs_module.DISABLE_AUTO_LOADING))
    vs_module.register_policy(policy)
    return policy


def resolve_artifact(args: argparse.Namespace) -> tuple[Path, Path | None]:
    if args.artifact_zip:
        archive = Path(args.artifact_zip).resolve()
        if not archive.exists():
            raise FileNotFoundError(archive)
        temp_dir = Path(tempfile.mkdtemp(prefix="vs-nlq-package-"))
        with zipfile.ZipFile(archive) as zf:
            roots = {Path(name.replace("\\", "/")).parts[0] for name in zf.namelist() if name and not name.endswith("/")}
            if roots != {PACKAGE_DIR_NAME}:
                raise RuntimeError(f"expected only {PACKAGE_DIR_NAME}/ in {archive}, found {sorted(roots)}")
            zf.extractall(temp_dir)
        return temp_dir / PACKAGE_DIR_NAME, temp_dir
    return Path(args.artifact_dir).resolve(), None


def exercise_filter(core: Any, vs: Any) -> dict[str, Any]:
    rpu = base64.b64decode(PROFILE7_RPU_BASE64)
    if hashlib.sha256(rpu).hexdigest() != "b2b27714b7279c4e24d1a795cb6f95d3ad06745db96d360698ee0932184117a0":
        raise RuntimeError("embedded profile-7 RPU fixture hash mismatch")

    with tempfile.TemporaryDirectory(prefix="vs-nlq-rpu-") as temp_dir_text:
        rpu_path = Path(temp_dir_text) / "fel_orig.bin"
        # MapNLQ indexes a supplied RPU file by frame number, so use three
        # identical NAL units for the three static representative frames.
        rpu_path.write_bytes(rpu * 3)
        bl = core.std.BlankClip(
            format=vs.YUV420P16,
            width=64,
            height=32,
            length=3,
            color=[4096, 32768, 32768],
        )
        el = core.std.BlankClip(
            format=vs.YUV420P10,
            width=64,
            height=32,
            length=3,
            color=[64, 512, 512],
        ).std.SetFrameProp(prop="DolbyVisionRPU", data=rpu)
        out = core.vsnlq.MapNLQ(bl, el, str(rpu_path))
        frames = {number: out.get_frame(number) for number in (0, 1, 2)}
        hashes = {number: frame_hash(frame) for number, frame in frames.items()}
        if len(set(hashes.values())) != 1:
            raise RuntimeError(f"static MapNLQ input produced inconsistent hashes: {hashes}")
        frame = frames[1]
        stats = dict(core.std.PlaneStats(out).get_frame(1).props)

        invalid_error = ""
        try:
            float_el = core.std.BlankClip(
                format=vs.YUV420PS,
                width=64,
                height=32,
                length=1,
                color=[0.0625, 0.5, 0.5],
            ).std.SetFrameProp(prop="DolbyVisionRPU", data=rpu)
            core.vsnlq.MapNLQ(bl[:1], float_el, str(rpu_path)).get_frame(0)
        except vs.Error as exc:
            invalid_error = str(exc)
        if "Floating point formats are not supported" not in invalid_error:
            raise RuntimeError(f"unexpected floating-point error path: {invalid_error!r}")

    return {
        "width": frame.width,
        "height": frame.height,
        "format": frame.format.name,
        "frames": out.num_frames,
        "frame_hashes": hashes,
        "frame_property_keys": sorted(frame.props.keys()),
        "plane_stats_average": float(stats["PlaneStatsAverage"]),
        "plane_stats_min": float(stats["PlaneStatsMin"]),
        "plane_stats_max": float(stats["PlaneStatsMax"]),
        "invalid_error": invalid_error,
        "rpu_sha256": hashlib.sha256(rpu).hexdigest(),
    }


def installed_plugin_dir(module_file: str) -> Path:
    module_dir = Path(module_file).resolve().parent
    package_dir = module_dir if module_dir.name.casefold() == "vapoursynth" else module_dir / "vapoursynth"
    return package_dir / "plugins" / PACKAGE_DIR_NAME


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Smoke test a native vs-nlq package.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--artifact-dir", help="Top-level vs-nlq package directory.")
    group.add_argument("--artifact-zip", help="Release zip containing the top-level vs-nlq package directory.")
    group.add_argument("--installed-wheel", action="store_true", help="Test an installed wheel through manifest autoload.")
    parser.add_argument("--json", action="store_true", help="Emit a JSON result.")
    args = parser.parse_args(argv)

    import vapoursynth as vs  # pylint: disable=import-outside-toplevel

    temp_dir: Path | None = None
    policy: IsolatedEnvironmentPolicy | None = None
    try:
        if args.installed_wheel:
            package_dir = installed_plugin_dir(vs.__file__)
            mode = "installed-wheel-autoload"
            core = vs.core
            if not hasattr(core, "vsnlq"):
                raise RuntimeError("core.vsnlq is missing after installed-wheel manifest autoload")
        else:
            package_dir, temp_dir = resolve_artifact(args)
            mode = "explicit-load"
            plugin = package_dir / plugin_filename()
            if not plugin.exists():
                raise FileNotFoundError(plugin)
            policy = install_isolated_policy(vs)
            core = vs.core
            core.std.LoadPlugin(str(plugin))

        manifest = package_dir / "manifest.vs"
        native = package_dir / plugin_filename()
        for required in (manifest, native):
            if not required.exists():
                raise FileNotFoundError(required)
        if not hasattr(core, "vsnlq") or not hasattr(core.vsnlq, "MapNLQ"):
            raise RuntimeError("core.vsnlq.MapNLQ is missing after plugin load")

        result = {
            "mode": mode,
            "plugin": str(native),
            "manifest": str(manifest),
            "vapoursynth": vs.__version__,
            **exercise_filter(core, vs),
        }
        if args.json:
            print(json.dumps(result, indent=2, sort_keys=True))
        else:
            for key, value in result.items():
                print(f"{key}={value}")
        return 0
    finally:
        if policy is not None:
            policy.close()
        if temp_dir is not None:
            shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
