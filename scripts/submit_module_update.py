"""Send an API v1 preview request from a registered upstream repository."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from module_common import (
    CENTRAL_REPOSITORY, GitHub, git_sha, load_registry, require,
    resolve_plan, validate_request,
)


def prepare_request(module: str, source_ref: str, caller_repository: str, actor: str, request_id: str, github: GitHub) -> dict:
    registry = load_registry()
    require(module in registry, "unregistered module")
    cfg = registry[module]
    require(caller_repository.lower() == cfg["repository"].lower(), "caller repository does not own the registered module")
    plan = resolve_plan(cfg, {
        "source_ref": source_ref or cfg["default_ref"], "source_sha": "",
        "expected_version": "", "request_id": request_id,
    }, github, actor=actor, central_sha=git_sha())
    return validate_request({
        "api_version": "1", "module": module,
        "source_ref": plan["source_sha"], "source_sha": plan["source_sha"],
        "expected_version": plan["version"],
        "request_id": request_id or f"{module}-{plan['version']}-{plan['source_sha']}",
    }, author_request=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--module", required=True)
    parser.add_argument("--source-ref", default="")
    parser.add_argument("--caller-repository", required=True)
    parser.add_argument("--actor", required=True)
    parser.add_argument("--request-id", default="")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    try:
        token = os.environ.get("WHEELS_UPDATE_TOKEN")
        require(args.dry_run or bool(token), "Set the upstream WHEELS_UPDATE_TOKEN secret to a central-repository Actions-write credential; GITHUB_TOKEN cannot trigger a different repository.")
        inputs = prepare_request(args.module, args.source_ref, args.caller_repository, args.actor, args.request_id, GitHub())
        if args.output:
            args.output.write_text(json.dumps(inputs, indent=2) + "\n", encoding="utf-8")
        if args.dry_run:
            print(json.dumps(inputs, indent=2))
            return
        central = GitHub(token).request(f"repos/{CENTRAL_REPOSITORY}")
        receipt = GitHub(token).request(
            f"repos/{CENTRAL_REPOSITORY}/actions/workflows/package-modules.yml/dispatches",
            method="POST", data={"ref": central["default_branch"], "inputs": inputs},
        )
        url = receipt.get("html_url") if isinstance(receipt, dict) else None
        url = url or f"https://github.com/{CENTRAL_REPOSITORY}/actions/workflows/package-modules.yml"
        message = f"Preview request accepted: {inputs['request_id']}\n\nCentral build: {url}\n\nThis receipt does not mean the wheel has been built or published.\n"
        print(message)
        if summary := os.environ.get("GITHUB_STEP_SUMMARY"):
            with open(summary, "a", encoding="utf-8") as stream:
                stream.write(message)
    except (ValueError, RuntimeError) as error:
        parser.exit(1, f"{error}\n")


if __name__ == "__main__":
    main()
