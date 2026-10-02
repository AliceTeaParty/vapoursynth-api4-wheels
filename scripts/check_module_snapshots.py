"""Verify fixed upstream snapshots using the real preview build/install path."""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
import venv
from pathlib import Path

from module_common import GitHub, ROOT, git_sha, load_registry, read_json, require, resolve_plan, write_json
from validate_module_wheel import validate_wheel


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshots", type=Path, default=ROOT / "tests/module-snapshots.json")
    parser.add_argument("--use-gh-auth", action="store_true", help="use local gh authentication for read-only metadata requests")
    args = parser.parse_args()
    token = subprocess.check_output(["gh", "auth", "token"], text=True).strip() if args.use_gh_auth else None
    github = GitHub(token)
    # A local gh login may have broader rights than CI. Never send its token,
    # or any notification/CI token, to a module build hook or installed module.
    clean_env = {key: value for key, value in os.environ.items() if key not in {"GH_TOKEN", "GITHUB_TOKEN", "WHEELS_UPDATE_TOKEN", "PYTHONPATH"}}
    registry = load_registry()
    records = []
    for snapshot in read_json(args.snapshots):
        module = snapshot["module"]
        cfg = registry[module]
        plan = resolve_plan(cfg, {
            "source_ref": snapshot["source_sha"], "source_sha": snapshot["source_sha"],
            "expected_version": snapshot["version"], "request_id": f"snapshot-{module}",
        }, github, actor=cfg["requesters"][0], central_sha=git_sha())
        require(plan["dependencies"] == [], "registered seed module snapshot must retain empty runtime dependencies")
        require(plan["requires_python"] == snapshot["requires_python"], "snapshot Python compatibility range changed")
        work = ROOT / ".work/snapshots"
        plan_file = work / f"{module}.json"
        write_json(plan_file, plan)
        source = ROOT / "modules" / module / "src"
        wheel_dir = ROOT / "modules" / module / "dist"
        require(not source.exists() and not wheel_dir.exists(), "snapshot verification needs a fresh modules/<id>/src and dist")
        source.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(["git", "init", str(source)], check=True, env=clean_env, capture_output=True)
        subprocess.run(["git", "-C", str(source), "config", "core.autocrlf", "false"], check=True, env=clean_env)
        subprocess.run(["git", "-C", str(source), "remote", "add", "origin", f"https://github.com/{cfg['repository']}.git"], check=True, env=clean_env)
        subprocess.run(["git", "-C", str(source), "fetch", "--depth", "1", "origin", plan["source_sha"]], check=True, env=clean_env, capture_output=True)
        subprocess.run(["git", "-C", str(source), "checkout", "--detach", "FETCH_HEAD"], check=True, env=clean_env, capture_output=True)
        subprocess.run([
            sys.executable, str(ROOT / "scripts/build_module.py"), "build",
            "--plan", str(plan_file), "--source", str(source), "--output", str(wheel_dir),
        ], check=True, cwd=ROOT, env=clean_env)
        wheel = next(wheel_dir.glob("*.whl"))
        manifest_file = work / f"{module}-manifest.json"
        write_json(manifest_file, validate_wheel(wheel, plan))
        env = work / f"env-{module}"
        venv.EnvBuilder(with_pip=True).create(env)
        python = env / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        subprocess.run([str(python), "-m", "pip", "install", "--no-deps", "--no-index", str(wheel)], check=True, env=clean_env, capture_output=True)
        subprocess.run([
            str(python), "-I", str(ROOT / "scripts/smoke_installed_module.py"),
            "--plan", str(plan_file), "--manifest", str(manifest_file),
        ], check=True, env=clean_env, cwd=work)
        imported = subprocess.run([
            str(python), "-I", "-c",
            "import importlib, sys; importlib.import_module(sys.argv[1])",
            cfg["import_name"],
        ], text=True, capture_output=True, cwd=work, env=clean_env)
        require(imported.returncode != 0 and "ModuleNotFoundError" in imported.stderr and snapshot["missing_runtime_import"] in imported.stderr, "normal import must expose the missing runtime dependency in this clean environment")
        manifest = read_json(manifest_file)
        records.append({
            "module": module, "version": plan["version"], "source_sha": plan["source_sha"],
            "wheel": wheel.name, "sha256": manifest["sha256"], "dependencies": plan["dependencies"],
            "validation": manifest["validation"],
            "normal_import": f"ModuleNotFoundError: {snapshot['missing_runtime_import']} (expected; no stubs or dependency additions)",
        })
    write_json(ROOT / ".work/snapshots/results.json", records)
    print("Both fixed upstream snapshots built, validated and installed; runtime dependency errors remain visible.")


if __name__ == "__main__":
    main()
