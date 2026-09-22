#!/usr/bin/env python3
"""Create TCanny Release zip and wheel assets from verified package output."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PLUGIN_NAME = "tcanny"


def create_package_zip(package_dir: Path, output: Path) -> None:
    if not package_dir.is_dir():
        raise FileNotFoundError(f"missing package directory: {package_dir}")
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for file_path in sorted(package_dir.rglob("*")):
            if file_path.is_file():
                archive.write(file_path, f"{PLUGIN_NAME}/{file_path.relative_to(package_dir).as_posix()}")


def copy_wheels(wheel_dir: Path, output_dir: Path) -> list[Path]:
    wheels = sorted(wheel_dir.glob("*.whl"))
    if not wheels:
        raise FileNotFoundError(f"no wheels found under {wheel_dir}")
    copied = []
    for wheel in wheels:
        destination = output_dir / wheel.name
        shutil.copy2(wheel, destination)
        copied.append(destination)
    return copied


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Create Release-ready TCanny assets.")
    parser.add_argument("--package-dir", required=True, help="Built tcanny plugin directory.")
    parser.add_argument("--wheel-dir", required=True, help="Directory containing TCanny wheels.")
    parser.add_argument("--out-dir", default="dist/release-assets", help="Release asset output directory.")
    parser.add_argument("--zip-name", required=True, help="Name of the Release zip asset.")
    parser.add_argument("--clean", action="store_true", help="Remove the output directory first.")
    parser.add_argument("--json", action="store_true", help="Emit JSON output.")
    args = parser.parse_args(argv)

    package_dir = (ROOT / args.package_dir).resolve()
    wheel_dir = (ROOT / args.wheel_dir).resolve()
    output_dir = (ROOT / args.out_dir).resolve()
    if args.clean:
        shutil.rmtree(output_dir, ignore_errors=True)
    output_dir.mkdir(parents=True, exist_ok=True)

    zip_path = output_dir / args.zip_name
    create_package_zip(package_dir, zip_path)
    wheel_paths = copy_wheels(wheel_dir, output_dir)
    result = {
        "package_dir": str(package_dir),
        "zip": str(zip_path),
        "wheels": [str(path) for path in wheel_paths],
    }
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        for key, value in result.items():
            print(f"{key}={value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
