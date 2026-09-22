#!/usr/bin/env python3
"""Explicit-load smoke test for a TCanny package directory or Release zip."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import tempfile
import zipfile
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PLUGIN_NAME = "tcanny"


def plugin_suffix() -> str:
    if sys.platform == "win32":
        return ".dll"
    if sys.platform == "darwin":
        return ".dylib"
    return ".so"


def frame_hash(frame: Any) -> str:
    digest = hashlib.sha256()
    for plane in range(frame.format.num_planes):
        digest.update(bytes(frame[plane]))
    return digest.hexdigest()


class IsolatedEnvironmentPolicy:
    """Disable autoload so the explicit plugin path is the tested input."""

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


def resolve_artifact(artifact_dir_arg: str | None, artifact_zip_arg: str | None) -> tuple[Path, Path | None]:
    if artifact_zip_arg:
        archive_path = Path(artifact_zip_arg).resolve()
        if not archive_path.is_file():
            raise FileNotFoundError(f"missing artifact zip: {archive_path}")
        temporary = Path(tempfile.mkdtemp(prefix="tcanny-package-"))
        with zipfile.ZipFile(archive_path) as archive:
            archive.extractall(temporary)
        directories = [path for path in temporary.iterdir() if path.is_dir()]
        if len(directories) != 1 or directories[0].name != PLUGIN_NAME:
            raise RuntimeError(f"expected exactly one top-level {PLUGIN_NAME}/ directory in {archive_path}")
        return directories[0], temporary
    if not artifact_dir_arg:
        raise ValueError("provide --artifact-dir or --artifact-zip")
    return Path(artifact_dir_arg).resolve(), None


def representative_source(core: Any, vs_module: Any) -> Any:
    inner = core.std.BlankClip(width=48, height=32, format=vs_module.YUV420P8, length=12, color=[16, 128, 128])
    return core.std.AddBorders(inner, left=8, right=8, top=8, bottom=8, color=[235, 128, 128])


def run_filter_smoke(core: Any, vs_module: Any) -> dict[str, Any]:
    source = representative_source(core, vs_module)
    output = core.tcanny.TCanny(source, opt=1)
    frames = {number: output.get_frame(number) for number in (0, 3, 11)}
    hashes = {number: frame_hash(frame) for number, frame in frames.items()}
    stats = dict(core.std.PlaneStats(output).get_frame(3).props)
    try:
        core.tcanny.TCanny(source, t_h=1.0, t_l=1.0)
    except vs_module.Error as error:
        invalid_error = str(error)
    else:
        raise RuntimeError("TCanny accepted t_h <= t_l")
    frame = frames[3]
    return {
        "width": frame.width,
        "height": frame.height,
        "format": frame.format.name,
        "frames": output.num_frames,
        "frame_hashes": hashes,
        "plane_stats_average": float(stats["PlaneStatsAverage"]),
        "plane_stats_min": float(stats["PlaneStatsMin"]),
        "plane_stats_max": float(stats["PlaneStatsMax"]),
        "invalid_error": invalid_error,
    }


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Explicitly smoke test TCanny package output.")
    parser.add_argument("--artifact-dir", help="Packaged tcanny directory.")
    parser.add_argument("--artifact-zip", help="Release zip containing tcanny/.")
    parser.add_argument("--json", action="store_true", help="Emit JSON output.")
    args = parser.parse_args(argv)

    artifact_dir, temporary = resolve_artifact(args.artifact_dir, args.artifact_zip)
    plugin = artifact_dir / f"{PLUGIN_NAME}{plugin_suffix()}"
    manifest = artifact_dir / "manifest.vs"
    if not plugin.is_file() or not manifest.is_file():
        raise FileNotFoundError(f"missing native plugin or manifest under {artifact_dir}")

    handles = []
    add_dll_directory = getattr(os, "add_dll_directory", None)
    if add_dll_directory is not None:
        handles.append(add_dll_directory(str(artifact_dir)))

    import vapoursynth as vs  # pylint: disable=import-outside-toplevel

    policy = install_isolated_policy(vs)
    try:
        core = vs.core
        core.std.LoadPlugin(str(plugin))
        result = {"plugin": str(plugin), "manifest": str(manifest), **run_filter_smoke(core, vs)}
        print(json.dumps(result, indent=2, sort_keys=True) if args.json else result)
    finally:
        for handle in handles:
            handle.close()
        if policy is not None:
            policy.close()
        if temporary is not None:
            pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
