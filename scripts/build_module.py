"""Resolve registered upstream sources, then build without editing their metadata."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

from module_common import (
    GitHub, ROOT, check_plan, git_sha, load_registry, project_metadata,
    read_json, relative_path, require, resolve_plan, validate_request, write_json,
)


def resolve(args: argparse.Namespace) -> None:
    if args.request:
        path = relative_path(args.request)
        request_path = (ROOT / path).resolve()
        require(request_path.is_relative_to((ROOT / "modules").resolve()), "update request must be under modules/")
        require(request_path.parent.name == "updates" and request_path.suffix == ".json", "expected modules/<id>/updates/<version>.json")
        require(not any((args.source_ref, args.source_sha, args.expected_version)), "request file cannot be combined with source overrides")
        request = validate_request(read_json(request_path), author_request=True)
        require(request_path.parent.parent.name == request["module"], "update request is under the wrong module")
        require(args.module in (request["module"], ""), "module does not match request file")
    else:
        request = validate_request({
            "api_version": args.api_version, "module": args.module,
            "source_ref": args.source_ref, "source_sha": args.source_sha,
            "expected_version": args.expected_version, "request_id": args.request_id,
        })
    registry = load_registry()
    selected = sorted(registry) if request["module"] == "all" else [request["module"]]
    require(all(module in registry for module in selected), "unknown module")
    matrix = {"include": []}
    github = GitHub()
    for module in selected:
        plan = resolve_plan(registry[module], request, github, actor=args.actor, central_sha=git_sha())
        write_json(args.output / f"{module}.json", plan)
        matrix["include"].append({"module": module, "repository": plan["repository"], "source_sha": plan["source_sha"]})
        print(f"{module}: {plan['repository']}@{plan['source_sha']} version {plan['version']}")
    write_json(args.output / "matrix.json", matrix)
    if output := os.environ.get("GITHUB_OUTPUT"):
        with open(output, "a", encoding="utf-8") as stream:
            stream.write("matrix=" + json.dumps(matrix, separators=(",", ":")) + "\n")


def build(args: argparse.Namespace) -> None:
    plan = read_json(args.plan)
    check_plan(plan, load_registry())
    source = args.source.resolve()
    require(source == (ROOT / "modules" / plan["module"] / "src").resolve(), "source must be modules/<id>/src")
    actual_sha = subprocess.check_output(["git", "-C", str(source), "rev-parse", "HEAD"], text=True).strip()
    require(actual_sha == plan["source_sha"], "checked out source SHA does not match plan")
    status = subprocess.check_output(["git", "-C", str(source), "status", "--porcelain"], text=True).strip()
    require(not status, "source checkout must be clean before building")
    directory = (source / plan["project_subdirectory"]).resolve()
    require(directory.is_relative_to(source), "project directory escapes source checkout")
    content = (directory / "pyproject.toml").read_bytes()
    project_path = "pyproject.toml" if plan["project_subdirectory"] == "." else f"{plan['project_subdirectory']}/pyproject.toml"
    git_content = subprocess.check_output(["git", "-C", str(source), "show", f"HEAD:{project_path}"])
    require(hashlib.sha256(git_content).hexdigest() == plan["pyproject_sha256"], "pyproject.toml changed after resolution")
    for key, value in project_metadata(content, plan["distribution"]).items():
        require(plan[key] == value, f"source metadata changed: {key}")
    output = args.output.resolve()
    require(output == (ROOT / "modules" / plan["module"] / "dist").resolve(), "output must be modules/<id>/dist")
    output.mkdir(parents=True, exist_ok=True)
    require(not list(output.iterdir()), "output directory must be empty")
    subprocess.run([sys.executable, "-m", "build", "--wheel", "--outdir", str(output), str(directory)], check=True)
    require(len(list(output.glob("*.whl"))) == 1, "expected exactly one module wheel")
    print(f"Built {plan['module']} from unchanged upstream metadata.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    resolver = commands.add_parser("resolve")
    resolver.add_argument("--api-version", default="1")
    resolver.add_argument("--module", default="")
    resolver.add_argument("--source-ref", default="")
    resolver.add_argument("--source-sha", default="")
    resolver.add_argument("--expected-version", default="")
    resolver.add_argument("--request-id", default="")
    resolver.add_argument("--request", default="")
    resolver.add_argument("--actor", required=True)
    resolver.add_argument("--output", type=Path, required=True)
    builder = commands.add_parser("build")
    builder.add_argument("--plan", type=Path, required=True)
    builder.add_argument("--source", type=Path, required=True)
    builder.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        (resolve if args.command == "resolve" else build)(args)
    except (ValueError, RuntimeError) as error:
        parser.exit(1, f"{error}\n")


if __name__ == "__main__":
    main()
