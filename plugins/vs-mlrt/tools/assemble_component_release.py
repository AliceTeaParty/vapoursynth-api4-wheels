from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import zipfile


SCRIPT_ROOT = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("verify_component_wheels", SCRIPT_ROOT / "verify_component_wheels.py")
verify_module = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(verify_module)


def digest(path: Path) -> str:
    result = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            result.update(chunk)
    return result.hexdigest()


def logical_wheel_digest(path: Path) -> str:
    result = hashlib.sha256()
    with zipfile.ZipFile(path) as archive:
        for name in sorted(
            value for value in archive.namelist()
            if not value.endswith(("/", ".dist-info/RECORD"))
        ):
            encoded = name.encode("utf-8")
            result.update(len(encoded).to_bytes(4, "big"))
            result.update(encoded)
            payload = archive.read(name)
            if name.endswith(".dist-info/WHEEL"):
                payload = b"\n".join(
                    line for line in payload.splitlines() if not line.startswith(b"Generator:")
                )
            result.update(len(payload).to_bytes(8, "big"))
            result.update(payload)
    return result.hexdigest()


def assemble(inputs: list[Path], output: Path, canonical_shared: Path | None = None) -> None:
    shutil.rmtree(output, ignore_errors=True)
    output.mkdir(parents=True)
    ordered_roots = ([canonical_shared] if canonical_shared else []) + inputs
    source_wheels = list(dict.fromkeys(path.resolve() for root in ordered_roots for path in sorted(root.rglob("*.whl"))))
    if not source_wheels:
        raise RuntimeError("No component wheels were found in the downloaded artifacts")

    authoritative_names = {
        path.name for path in canonical_shared.rglob("*.whl")
    } if canonical_shared else set()
    by_name: dict[str, tuple[Path, str, str]] = {}
    source_hashes: dict[str, set[str]] = {}
    for source in source_wheels:
        sha256 = digest(source)
        logical = logical_wheel_digest(source)
        source_hashes.setdefault(source.name, set()).add(sha256)
        previous = by_name.get(source.name)
        if previous and previous[2] != logical and source.name not in authoritative_names:
            raise RuntimeError(f"Conflicting wheels share the filename {source.name}: {previous[0]} and {source}")
        if previous is None:
            by_name[source.name] = (source, sha256, logical)
    for name, (source, _, _) in by_name.items():
        shutil.copy2(source, output / name)

    inventories = sorted({path.resolve() for root in inputs for path in root.rglob("component-wheel-inventory-*.json")})
    required_inventories = {
        f"component-wheel-inventory-{variant}-{system}.json"
        for variant in ("generic", "cu121", "cu129")
        for system in ("windows", "linux")
    }
    missing_inventories = sorted(required_inventories - {path.name for path in inventories})
    if missing_inventories:
        raise RuntimeError(f"Release artifacts are missing component inventories: {missing_inventories}")
    source_revisions = set()
    for inventory_path in inventories:
        inventory = json.loads(inventory_path.read_text(encoding="utf-8"))
        revision = inventory.get("source_revision")
        if not revision:
            raise RuntimeError(f"Component inventory has no source_revision: {inventory_path}")
        source_revisions.add(revision)
        for item in inventory["wheels"]:
            if item["sha256"] not in source_hashes.get(item["name"], set()):
                raise RuntimeError(f"Artifact does not match {inventory_path.name}: {item['name']}")
    if len(source_revisions) != 1:
        raise RuntimeError(f"Release artifacts came from different source revisions: {sorted(source_revisions)}")

    verify_module.verify(output, target_platform="windows")
    verify_module.verify(output, target_platform="linux")
    release = {
        "source_revision": next(iter(source_revisions)),
        "wheels": [
            {"name": path.name, "sha256": digest(path), "size": path.stat().st_size}
            for path in sorted(output.glob("*.whl"))
        ]
    }
    (output / "vs-mlrt-release-inventory.json").write_text(
        json.dumps(release, indent=2) + "\n", encoding="utf-8"
    )
    print(f"Assembled {len(release['wheels'])} unique wheels in {output}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", action="append", type=Path, required=True)
    parser.add_argument("--canonical-shared-input", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    assemble(
        [path.resolve(strict=True) for path in args.input],
        args.output.resolve(),
        args.canonical_shared_input.resolve(strict=True) if args.canonical_shared_input else None,
    )


if __name__ == "__main__":
    main()
