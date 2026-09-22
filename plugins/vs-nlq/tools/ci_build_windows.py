from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PACKAGE_DIR_NAME = "vs-nlq"
DLL_BASENAME = "vs_nlq"
DEFAULT_DIST = ROOT / "dist" / "windows-x86_64"


def run(cmd: list[str]) -> None:
    print("+ " + subprocess.list2cmdline(cmd), flush=True)
    subprocess.run(cmd, cwd=ROOT, check=True)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Build and stage the vs-nlq Windows plugin package.")
    parser.add_argument("--dist-dir", default=str(DEFAULT_DIST), help="Directory that will receive the vs-nlq package folder.")
    parser.add_argument("--clean", action="store_true", help="Remove the destination package and run cargo clean first.")
    args = parser.parse_args(argv)

    dist_dir = Path(args.dist_dir).resolve()
    package_dir = dist_dir / PACKAGE_DIR_NAME
    if args.clean:
        shutil.rmtree(package_dir, ignore_errors=True)
        run(["cargo", "clean"])

    run(["cargo", "build", "--release", "--locked"])

    dll = ROOT / "target" / "release" / f"{DLL_BASENAME}.dll"
    if not dll.exists():
        raise FileNotFoundError(dll)

    package_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(dll, package_dir / dll.name)
    shutil.copy2(ROOT / "LICENSE", package_dir / "LICENSE")
    (package_dir / "manifest.vs").write_text(
        f"[VapourSynth Manifest V1]\n{DLL_BASENAME}\n",
        encoding="ascii",
        newline="\n",
    )

    print(package_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
