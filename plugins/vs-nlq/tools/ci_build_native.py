from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PACKAGE_DIR_NAME = "vs-nlq"


def plugin_filename() -> str:
    if sys.platform == "darwin":
        return "libvs_nlq.dylib"
    if sys.platform.startswith("linux"):
        return "libvs_nlq.so"
    raise RuntimeError(f"ci_build_native.py does not support {sys.platform}")


def run(cmd: list[str]) -> None:
    print("+ " + subprocess.list2cmdline(cmd), flush=True)
    subprocess.run(cmd, cwd=ROOT, check=True)


def cargo_target_dir() -> Path:
    configured = Path(os.environ["CARGO_TARGET_DIR"]) if "CARGO_TARGET_DIR" in os.environ else ROOT / "target"
    return configured.resolve()


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Build and stage the vs-nlq native plugin package.")
    parser.add_argument("--dist-dir", default=str(ROOT / "dist" / sys.platform), help="Directory that receives the vs-nlq package folder.")
    parser.add_argument("--clean", action="store_true", help="Remove the staged package and run cargo clean.")
    args = parser.parse_args(argv)

    dist_dir = Path(args.dist_dir).resolve()
    package_dir = dist_dir / PACKAGE_DIR_NAME
    if args.clean:
        shutil.rmtree(package_dir, ignore_errors=True)
        run(["cargo", "clean"])

    run(["cargo", "build", "--release", "--locked"])
    plugin = cargo_target_dir() / "release" / plugin_filename()
    if not plugin.exists():
        raise FileNotFoundError(plugin)

    package_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(plugin, package_dir / plugin.name)
    shutil.copy2(ROOT / "LICENSE", package_dir / "LICENSE")
    (package_dir / "manifest.vs").write_text(
        f"[VapourSynth Manifest V1]\n{plugin.stem}\n",
        encoding="ascii",
        newline="\n",
    )
    print(package_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
