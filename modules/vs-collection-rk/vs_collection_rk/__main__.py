"""Check and repair component files deleted by a monolithic Collection upgrade."""
from __future__ import annotations

import argparse
import base64
import csv
import hashlib
from importlib import metadata
import json
import io
import subprocess
import sys

from . import load_registry


def check_files() -> dict[str, list[str]]:
    problems = {}
    for entry in load_registry():
        name = entry["distribution"]
        errors = []
        try:
            dist = metadata.distribution(name)
        except metadata.PackageNotFoundError:
            problems[name] = ["distribution is not installed"]
            continue
        if dist.version != entry["wheel_version"]:
            errors.append(f"expected {entry['wheel_version']}, installed {dist.version}")
        # Python 3.14's distribution.files omits paths that no longer exist.
        # Read RECORD itself so a partially deleted package cannot pass.
        records = list(csv.reader(io.StringIO(dist.read_text("RECORD") or "")))
        if not records:
            errors.append("installed RECORD is missing or empty")
        root = entry["install_path"]
        if any(len(row) != 3 for row in records):
            problems[name] = [*errors, "installed RECORD is malformed"]
            continue
        pth = entry.get("pth_file")
        runtime = [row for row in records if row[0] == root or row[0].startswith(root + "/") or row[0] == pth]
        required = root if entry["runtime_kind"] == "module" else root + "/__init__.py"
        if required not in {row[0] for row in runtime}:
            errors.append(f"RECORD does not list {required}")
        if pth and pth not in {row[0] for row in runtime}:
            errors.append(f"RECORD does not list {pth}")
        for file, encoded_hash, _ in runtime:
            if file.endswith((".pyc", ".pyo")):
                continue
            path = dist.locate_file(file)
            if not path.is_file():
                errors.append(f"missing {file}")
            elif encoded_hash:
                algorithm, expected = encoded_hash.split("=", 1)
                digest = hashlib.new(algorithm, path.read_bytes()).digest()
                if base64.urlsafe_b64encode(digest).decode().rstrip("=") != expected:
                    errors.append(f"changed {file}")
        if errors:
            problems[name] = errors
    return problems


def check_imports() -> dict[str, str]:
    """Use a fresh isolated process for every module, including package children."""
    problems = {}
    for entry in load_registry():
        dist = metadata.distribution(entry["distribution"])
        expected = str(dist.locate_file(entry["install_path"]))
        names = {entry["import_name"]}
        if entry["runtime_kind"] == "package":
            for file in dist.files or []:
                path = str(file)
                if path.startswith(entry["install_path"] + "/") and path.endswith(".py"):
                    if "/" in entry["install_path"]:
                        path = path[len(entry["install_path"].rsplit("/", 1)[0]) + 1:]
                    name = path[:-3].replace("/", ".")
                    names.add(name.removesuffix(".__init__"))
        for name in sorted(names):
            code = "import importlib, sys; from pathlib import Path; m = importlib.import_module(sys.argv[1]); actual = Path(m.__file__).resolve(); expected = Path(sys.argv[2]).resolve()"
            if entry["runtime_kind"] == "package":
                code += "; assert actual.is_relative_to(expected), f'import resolved outside installed component: {actual}'"
            else:
                code += "; assert actual == expected, f'import resolved outside installed component: {actual}'"
            if name == "mvsfunc":
                code += "; assert callable(m.Depth); assert callable(m.BM3D)"
            try:
                result = subprocess.run([sys.executable, "-I", "-c", code, name, expected], capture_output=True, text=True, timeout=60)
            except subprocess.TimeoutExpired:
                problems[name] = "import timed out after 60 seconds"
                continue
            if result.returncode:
                problems[name] = result.stderr.strip() or f"process exited with {result.returncode}"
    return problems


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("check", "repair"))
    parser.add_argument("--imports", action="store_true", help="also import every component and package child; requires runtime dependencies")
    parser.add_argument("--index-url")
    parser.add_argument("--extra-index-url")
    parser.add_argument("--find-links")
    parser.add_argument("--no-index", action="store_true")
    args = parser.parse_args()
    problems = check_files()
    if args.command == "repair" and problems:
        pins = [f"{e['distribution']}=={e['wheel_version']}" for e in load_registry() if e["distribution"] in problems]
        command = [sys.executable, "-m", "pip", "install", "--force-reinstall", "--no-deps"]
        for option in ("index_url", "extra_index_url", "find_links"):
            if value := getattr(args, option):
                command.extend(["--" + option.replace("_", "-"), value])
        if args.no_index:
            command.append("--no-index")
        subprocess.run([*command, *pins], check=True)
        problems = check_files()
    imports = check_imports() if args.imports and not problems else {}
    print(json.dumps({"files": problems, "imports": imports}, indent=2))
    if problems:
        print("Component files are damaged. Run python -m vs_collection_rk repair with your wheel index or --find-links directory.", file=sys.stderr)
    return int(bool(problems or imports))


if __name__ == "__main__":
    raise SystemExit(main())
