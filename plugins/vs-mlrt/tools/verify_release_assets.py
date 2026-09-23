from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess


def read_release(repo: str, tag: str) -> dict:
    output = subprocess.check_output(
        ["gh", "release", "view", tag, "--repo", repo, "--json", "assets,isDraft,tagName"],
        text=True,
    )
    return json.loads(output)


def verify(inventory: dict, release: dict) -> None:
    expected = {item["name"]: "sha256:" + item["sha256"] for item in inventory["wheels"]}
    assets = release.get("assets", [])
    remote = {item["name"]: item for item in assets if item["name"].endswith(".whl")}

    missing = sorted(set(expected) - set(remote))
    unexpected = sorted(set(remote) - set(expected))
    if missing or unexpected:
        raise RuntimeError(f"Remote release wheel set differs: missing={missing}, unexpected={unexpected}")

    incomplete = sorted(name for name, item in remote.items() if item.get("state") != "uploaded")
    if incomplete:
        raise RuntimeError(f"Remote release wheels are not fully uploaded: {incomplete}")

    mismatched = sorted(name for name, digest in expected.items() if remote[name].get("digest") != digest)
    if mismatched:
        raise RuntimeError(f"Remote release digest mismatch: {mismatched}")

    print(f"Verified {len(expected)} remote wheel digests")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--inventory", type=Path, required=True)
    parser.add_argument("--repo", required=True)
    parser.add_argument("--tag", required=True)
    args = parser.parse_args()
    inventory = json.loads(args.inventory.read_text(encoding="utf-8"))
    verify(inventory, read_release(args.repo, args.tag))


if __name__ == "__main__":
    main()
