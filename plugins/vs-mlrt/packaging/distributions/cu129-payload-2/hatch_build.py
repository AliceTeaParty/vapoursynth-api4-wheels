from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "packaging"))

from vsmlrt_build import CustomBuildHook as BaseBuildHook


class CustomBuildHook(BaseBuildHook):
    def initialize(self, version: str, build_data: dict) -> None:
        os.environ["VSMLRT_SOURCE_ROOT"] = str(ROOT)
        os.environ["VSMLRT_PAYLOAD_TAG"] = "cu129"
        os.environ["VSMLRT_OVERLAY_SHARDS"] = "3"
        os.environ["VSMLRT_OVERLAY_SHARD"] = "2"
        super().initialize(version, build_data)


def get_build_hook():
    return CustomBuildHook
