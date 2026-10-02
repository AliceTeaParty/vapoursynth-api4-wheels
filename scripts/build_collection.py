"""Build and verify the central-owned vs-collection-rk component wheel set."""
from __future__ import annotations
import argparse
import fnmatch
import json
import os
import subprocess
import sys
import tempfile
import venv
from pathlib import Path

from packaging.utils import parse_wheel_filename

from collection_common import load_collection, source_plan
from module_common import ROOT, read_json, require, write_json
from validate_module_wheel import validate_wheel


def validate_set(plan: dict, wheel_dir: Path) -> dict:
    expected = {item["distribution"]: item for item in plan["components"]}
    wheels = {}
    for file in wheel_dir.glob("*.whl"):
        distribution, _, _, _ = parse_wheel_filename(file.name)
        require(distribution not in wheels, "duplicate distribution in wheel set")
        wheels[distribution] = file
    require(set(wheels) == set(expected), "collection wheel set is incomplete or contains unexpected distributions")
    results = []
    for distribution, item in expected.items():
        manifest = validate_wheel(wheels[distribution], item)
        for relative, digest in item["runtime_sha256"].items():
            require(manifest["file_sha256"].get(relative) == digest, f"wheel changed Collection runtime file: {relative}")
        if item["kind"] == "collection-component":
            matches = [name for name in manifest["file_sha256"] if fnmatch.fnmatchcase(name, "*.dist-info/extra_metadata/provenance.toml")]
            require(len(matches) == 1 and manifest["file_sha256"][matches[0]] == item["provenance_sha256"], "wheel provenance differs from committed source")
        results.append(manifest)
    return {**plan, "wheels": results}


def verify_install(plan: dict, validated: dict, wheel_dir: Path, legacy_wheel: Path | None) -> None:
    with tempfile.TemporaryDirectory(prefix="vs-collection-install-") as directory:
        temporary = Path(directory)
        environment = temporary / "env"
        venv.EnvBuilder(with_pip=True).create(environment)
        python = environment / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        if legacy_wheel:
            subprocess.run([str(python), "-m", "pip", "install", "--no-index", "--no-deps", str(legacy_wheel.resolve())], check=True)
            # The old distribution owns the same script paths. Remove it before
            # installing component dependencies, as documented for users.
            subprocess.run([str(python), "-m", "pip", "uninstall", "-y", "vs-collection-rk"], check=True)
        subprocess.run([
            str(python), "-m", "pip", "install", "--no-index", "--find-links", str(wheel_dir.resolve()),
            f"vs-collection-rk=={plan['version']}",
        ], check=True)
        subprocess.run([str(python), "-m", "pip", "check"], check=True)
        by_distribution = {item["distribution"]: item for item in plan["components"]}
        for manifest in validated["wheels"]:
            distribution = manifest["distribution"]
            plan_file = temporary / f"{distribution}-plan.json"
            manifest_file = temporary / f"{distribution}-manifest.json"
            write_json(plan_file, by_distribution[distribution])
            write_json(manifest_file, manifest)
            subprocess.run([
                str(python), "-I", str(ROOT / "scripts/smoke_installed_module.py"),
                "--plan", str(plan_file), "--manifest", str(manifest_file),
            ], check=True, cwd=temporary)
            manifest["validation"]["installed_files"] = "passed"
        expected = [item["import_name"] for item in plan["components"] if item["kind"] == "collection-component"]
        code = (
            "import importlib.util, json, sys; import vs_collection_rk as c; "
            "expected=json.loads(sys.argv[1]); "
            "assert c.__version__ == sys.argv[2]; "
            "assert c.bundled_scripts() == expected; "
            "assert all(importlib.util.find_spec(name) is not None for name in expected); "
            "assert all(c.find_script(name)['import_name'] == name for name in expected)"
        )
        subprocess.run([str(python), "-I", "-c", code, json.dumps(expected), plan["version"]], check=True, cwd=temporary)


def compare_baseline(registry: dict, baseline: Path) -> None:
    history = read_json(ROOT / "modules/collection-history.json")
    sha = subprocess.check_output(["git", "-C", str(baseline), "rev-parse", "HEAD"], text=True).strip()
    require(sha == history["collection_revision"], "wrong Collection baseline commit")
    for item in history["components"]:
        for relative in item["runtime_sha256"]:
            source = item["collection_source_root"] + "/" + relative
            original = subprocess.check_output(["git", "-C", str(baseline), "show", f"HEAD:{source}"])
            migrated = subprocess.check_output(["git", "-C", str(ROOT), "show", f"{item['patch_commit']}:{item['path']}/{relative}"])
            require(migrated == original, f"lost Collection edits in migration patch: {item['module']}/{relative}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["plan", "build", "validate"])
    parser.add_argument("--plan", type=Path, default=ROOT / ".work/collection-plan.json")
    parser.add_argument("--wheel-dir", type=Path, default=ROOT / "dist/collection")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--baseline", type=Path)
    parser.add_argument("--legacy-wheel", type=Path)
    parser.add_argument("--install", action="store_true")
    args = parser.parse_args()
    try:
        if args.command == "plan":
            plan = source_plan()
            if args.baseline:
                compare_baseline(load_collection(), args.baseline)
            write_json(args.plan, plan)
            print(f"Fixed {len(plan['components'])} distributions at {plan['central_sha']}")
            return
        plan = read_json(args.plan)
        if args.command == "build":
            require(source_plan() == plan, "worktree or source plan changed before build")
            args.wheel_dir.mkdir(parents=True, exist_ok=True)
            require(not list(args.wheel_dir.iterdir()), "build output must be empty")
            for item in plan["components"]:
                subprocess.run([
                    sys.executable, "-m", "build", "--wheel", "--no-isolation",
                    "--outdir", str(args.wheel_dir.resolve()), str(ROOT / item["path"]),
                ], check=True)
        result = validate_set(plan, args.wheel_dir)
        if args.install:
            verify_install(plan, result, args.wheel_dir, None)
            result["fresh_install"] = "passed"
            if args.legacy_wheel:
                verify_install(plan, result, args.wheel_dir, args.legacy_wheel)
                result["monolith_migration"] = "passed"
        if args.output:
            write_json(args.output, result)
        print(json.dumps({"version": plan["version"], "wheels": [item["wheel"] for item in result["wheels"]],
                          "fresh_install": result.get("fresh_install"), "monolith_migration": result.get("monolith_migration")}, indent=2))
    except (ValueError, KeyError) as error:
        parser.exit(1, f"{error}\n")


if __name__ == "__main__":
    main()
