from __future__ import annotations

import os
from pathlib import Path
import stat
import zipfile
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
        force_include[str(source_root / "scripts" / "rm_vsmlrt.sh")] = (
            f"{distribution}-{distribution_version}.data/scripts/rm_vsmlrt"
        )
        force_include[str(root / "manifest.vs")] = "vapoursynth/plugins/vsmlrt/manifest.vs"
        build_data["tag"] = "py3-none-any"

    def finalize(self, version: str, build_data: dict, artifact_path: str) -> None:
        del version, build_data
        source_path = Path(artifact_path)
        temporary = source_path.with_suffix(".tmp")
        with zipfile.ZipFile(source_path) as source, zipfile.ZipFile(temporary, "w") as destination:
            destination.comment = source.comment
            for info in source.infolist():
                if info.filename.endswith(".data/scripts/rm_vsmlrt"):
                    info.create_system = 3
                    info.external_attr = (stat.S_IFREG | 0o755) << 16
                destination.writestr(info, source.read(info.filename))
        os.replace(temporary, source_path)
