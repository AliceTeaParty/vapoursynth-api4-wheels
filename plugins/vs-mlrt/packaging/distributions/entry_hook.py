from __future__ import annotations

from pathlib import Path
import tomllib

from hatchling.builders.hooks.plugin.interface import BuildHookInterface


class EntryBuildHook(BuildHookInterface):
    def initialize(self, version: str, build_data: dict) -> None:
        if self.target_name != "wheel":
            return
        root = Path(self.root).resolve()
        source_root = root.parents[2]
        force_include = build_data.setdefault("force_include", {})
        for name in ("vsmlrt.py", "vsmlrt_dll_paths.py", "vs_mlrt_dll_paths.pth"):
            force_include[str(source_root / "scripts" / name)] = name
        force_include[str(source_root / "scripts" / "rm_vsmlrt")] = "rm_vsmlrt"
        project = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))["project"]
        distribution = project["name"].replace("-", "_")
        distribution_version = project["version"]
        force_include[str(source_root / "scripts" / "rm_vsmlrt.cmd")] = (
            f"{distribution}-{distribution_version}.data/scripts/rm_vsmlrt.cmd"
        )
        force_include[str(root / "manifest.vs")] = "vapoursynth/plugins/vsmlrt/manifest.vs"
        build_data["tag"] = "py3-none-any"
