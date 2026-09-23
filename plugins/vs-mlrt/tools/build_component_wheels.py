from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
from pathlib import Path
import shutil
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = ROOT.parents[1]
COMPONENT_ROOT = ROOT / "packaging" / "components"
ENTRY_ROOT = ROOT / "packaging" / "distributions"
MODELS_ROOT = ROOT / "packaging" / "payloads" / "models"
COMPONENTS = {
    "generic": ("vs-ov", "vs-ncnn"),
    "cu121": (
        "vs-ov", "vs-ncnn", "vs-cublas-cu121", "vs-cudnn-cu121", "vs-tensorrt-core-cu121",
        "vs-tensorrt-builder-cu121", "vs-trtexec-cu121", "vs-trt-cu121",
    ),
    "cu129": (
        "vs-ov", "vs-ncnn", "vs-tensorrt-core-cu129", "vs-tensorrt-builder-cu129-base",
        "vs-tensorrt-builder-cu129-modern", "vs-trtexec-cu129", "vs-trt-cu129",
        "vs-tensorrt-rtx-cu129", "vs-trt-rtx-cu129",
    ),
}


def digest(path: Path) -> str:
    result = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            result.update(chunk)
    return result.hexdigest()


def write_inventory(variant: str, output: Path) -> Path:
    source_revision = os.environ.get("GITHUB_SHA") or subprocess.check_output(
        ["git", "-c", f"safe.directory={REPOSITORY_ROOT.as_posix()}", "rev-parse", "HEAD"],
        cwd=REPOSITORY_ROOT,
        text=True,
    ).strip()
    inventory = {
        "variant": variant,
        "platform": platform.system().lower(),
        "source_revision": source_revision,
        "wheels": [
            {"name": path.name, "sha256": digest(path), "size": path.stat().st_size}
            for path in sorted(output.glob("*.whl"))
        ],
    }
    destination = output / f"component-wheel-inventory-{variant}-{inventory['platform']}.json"
    destination.write_text(json.dumps(inventory, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {destination}")
    return destination


def run(command: list[str], env: dict[str, str]) -> None:
    print("component wheels:", subprocess.list2cmdline(command), flush=True)
    subprocess.run(command, cwd=ROOT, env=env, check=True)


def build(variant: str, stage: Path, models: Path, output: Path, *, clean: bool) -> None:
    if clean:
        shutil.rmtree(output, ignore_errors=True)
    output.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env["VSMLRT_COMPONENT_SOURCE"] = str(stage.resolve(strict=True))
    env["VSMLRT_MODELS_PREBUILT_PATH"] = str(models.resolve(strict=True))
    base = [sys.executable, "-m", "build"]
    tail = ["--wheel", "--no-isolation", "--outdir", str(output)]
    for component in COMPONENTS[variant]:
        run([*base, str(COMPONENT_ROOT / component), *tail], env)
    run([*base, str(MODELS_ROOT), *tail], env)
    run([*base, str(ENTRY_ROOT / variant), *tail], env)
    run(
        [
            sys.executable,
            str(ROOT / "tools" / "verify_component_wheels.py"),
            str(output),
            "--entry",
            f"vs-mlrt-{variant}",
        ],
        env,
    )
    write_inventory(variant, output)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--variant", choices=sorted(COMPONENTS), required=True)
    parser.add_argument("--stage-dir", type=Path, required=True)
    parser.add_argument("--models", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--clean", action="store_true")
    parser.add_argument("--inventory-only", action="store_true")
    args = parser.parse_args()
    output = args.output.resolve()
    if args.inventory_only:
        write_inventory(args.variant, output)
    else:
        build(args.variant, args.stage_dir, args.models, output, clean=args.clean)


if __name__ == "__main__":
    main()
