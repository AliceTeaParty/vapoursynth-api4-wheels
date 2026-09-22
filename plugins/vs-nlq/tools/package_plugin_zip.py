from __future__ import annotations

import argparse
import sys
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PACKAGE_DIR_NAME = "vs-nlq"


def plugin_filename() -> str:
    if sys.platform == "win32":
        return "vs_nlq.dll"
    if sys.platform == "darwin":
        return "libvs_nlq.dylib"
    return "libvs_nlq.so"


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Create a vs-nlq plugin package zip.")
    parser.add_argument("--input-dir", default=str(ROOT / "dist" / "windows-x86_64"))
    parser.add_argument("--output", default=str(ROOT / "dist" / "vs-nlq-windows-x86_64.zip"))
    args = parser.parse_args(argv)

    input_dir = Path(args.input_dir).resolve()
    output = Path(args.output).resolve()
    package_dir = input_dir / PACKAGE_DIR_NAME
    required = [
        package_dir / plugin_filename(),
        package_dir / "manifest.vs",
    ]
    for path in required:
        if not path.exists():
            raise FileNotFoundError(path)

    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        output.unlink()

    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(package_dir.rglob("*")):
            if path.is_file():
                zf.write(path, path.relative_to(input_dir))

    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
