"""Inspect installed files without importing user-managed runtime dependencies."""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path


def inspect(plan: dict, manifest: dict) -> None:
    distribution = importlib.metadata.distribution(plan["distribution"])
    if distribution.version != plan["version"]:
        raise ValueError("installed version disagrees with source plan")
    if sorted(distribution.requires or []) != sorted(manifest["requires_dist"]):
        raise ValueError("installed dependencies disagree with unchanged upstream metadata")
    module = plan.get("runtime_kind", "package") == "module"
    package = distribution.locate_file(plan["import_name"] + (".py" if module else ""))
    if not (package.is_file() if module else package.is_dir()):
        raise ValueError("installed module/package is missing")
    for name in manifest["files"]:
        if name.endswith("/RECORD"):
            continue
        path = distribution.locate_file(name)
        if not path.is_file():
            raise ValueError(f"installed file missing: {name}")
        if hashlib.sha256(path.read_bytes()).hexdigest() != manifest["file_sha256"][name]:
            raise ValueError(f"installed file changed: {name}")
        if name.endswith(".py"):
            compile(path.read_bytes(), name, "exec")
    print(f"Installed {plan['distribution']} {distribution.version}; package files and syntax verified.")
    print("Runtime dependencies are intentionally unmanaged; normal imports still raise when a dependency is missing.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    inspect(json.loads(args.plan.read_text(encoding="utf-8")), manifest)
    manifest["validation"]["installed_files"] = "passed"
    args.manifest.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if summary := os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(summary, "a", encoding="utf-8") as stream:
            stream.write(f"### {manifest['distribution']} {manifest['version']}\n\n")
            stream.write(f"Source: {manifest['repository']}@{manifest['source_sha']}\n\n")
            stream.write(f"Wheel: {manifest['wheel']}\n\nSHA256: {manifest['sha256']}\n\n")
            stream.write("Installed files verified. Runtime imports are not tested; dependencies remain user-managed.\n")


if __name__ == "__main__":
    main()
