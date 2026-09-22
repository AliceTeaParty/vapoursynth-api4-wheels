from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "packaging"))

from vsmlrt_build import CustomBuildHook as BaseBuildHook


class CustomBuildHook(BaseBuildHook):
    def initialize(self, version: str, build_data: dict) -> None:
        self.root = str(ROOT)
        os.environ["VSMLRT_PAYLOAD_TAG"] = "generic"
        force_include = build_data.setdefault("force_include", {})
        for name in ("vsmlrt.py", "vsmlrt_dll_paths.py", "vs_mlrt_dll_paths.pth"):
            force_include[str(ROOT / "scripts" / name)] = name
        super().initialize(version, build_data)
