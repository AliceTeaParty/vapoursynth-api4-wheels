from __future__ import annotations

import argparse
from importlib import metadata
import re
import subprocess
import sys


KNOWN_DISTRIBUTIONS = (
    "vs-mlrt-generic", "vs-mlrt-cu121", "vs-mlrt-cu129", "vs-mlrt-models", "vs-ov", "vs-ncnn",
    "vs-cublas-cu121", "vs-cudnn-cu121", "vs-tensorrt-core-cu121", "vs-tensorrt-builder-cu121",
    "vs-trtexec-cu121", "vs-trt-cu121", "vs-tensorrt-core-cu129", "vs-tensorrt-builder-cu129-base",
    "vs-tensorrt-builder-cu129-modern", "vs-trtexec-cu129", "vs-trt-cu129", "vs-tensorrt-rtx-cu129",
    "vs-trt-rtx-cu129", "vs-mlrt", "vs-mlrt-payload-generic", "vs-mlrt-payload-cu121",
    "vs-mlrt-payload-cu129", "vs-mlrt-cu129-payload-2", "vs-mlrt-cu129-payload-3",
)


def normalize(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def selected_distributions() -> list[str]:
    installed = {
        normalize(distribution.metadata["Name"]): distribution.metadata["Name"]
        for distribution in metadata.distributions()
        if distribution.metadata.get("Name")
    }
    return [installed[name] for item in KNOWN_DISTRIBUTIONS if (name := normalize(item)) in installed]


def uninstall_command(distributions: list[str]) -> list[str]:
    return [sys.executable, "-m", "pip", "uninstall", "-y", *distributions]


def main(argv: list[str] | None = None) -> int:
    argparse.ArgumentParser(description=__doc__).parse_args(argv)
    distributions = selected_distributions()
    if not distributions:
        print("rm_vsmlrt_helper: no reviewed vs-mlrt distributions are installed")
        return 0
    print("rm_vsmlrt_helper: review and run this command:")
    print(subprocess.list2cmdline(uninstall_command(distributions)))
    print("rm_vsmlrt_helper: this helper does not run pip or delete files")
    return 0
