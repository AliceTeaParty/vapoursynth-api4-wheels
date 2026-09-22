"""Generate a PEP 503/691 package index from this repository's releases."""

from __future__ import annotations

import argparse
import html
import json
import os
import re
import urllib.request
from pathlib import Path
from typing import Any

API_VERSION = "2022-11-28"
WHEEL_SUFFIX = ".whl"


def normalize_name(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def wheel_project(filename: str) -> str:
    return normalize_name(filename.split("-", 1)[0])


def fetch_releases(repository: str, token: str | None) -> list[dict[str, Any]]:
    releases: list[dict[str, Any]] = []
    page = 1
    while True:
        url = f"https://api.github.com/repos/{repository}/releases?per_page=100&page={page}"
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": API_VERSION,
            "User-Agent": "vapoursynth-api4-wheels-index",
        }
        if token:
            headers["Authorization"] = f"Bearer {token}"
        with urllib.request.urlopen(urllib.request.Request(url, headers=headers)) as response:
            batch = json.load(response)
        if not batch:
            return releases
        releases.extend(batch)
        page += 1


def collect_wheels(releases: list[dict[str, Any]]) -> dict[str, list[dict[str, str]]]:
    projects: dict[str, list[dict[str, str]]] = {}
    for release in releases:
        if release.get("draft"):
            continue
        for asset in release.get("assets", []):
            filename = asset["name"]
            digest = asset.get("digest") or ""
            if not filename.endswith(WHEEL_SUFFIX) or not digest.startswith("sha256:"):
                continue
            project = wheel_project(filename)
            projects.setdefault(project, []).append(
                {
                    "filename": filename,
                    "url": asset["browser_download_url"],
                    "sha256": digest.removeprefix("sha256:"),
                }
            )
    return projects


def page(title: str, body: str) -> str:
    return (
        "<!doctype html>\n<html lang=\"en\"><head><meta charset=\"utf-8\">"
        f"<title>{html.escape(title)}</title></head><body>\n{body}\n</body></html>\n"
    )


def write_index(projects: dict[str, list[dict[str, str]]], output: Path) -> None:
    simple = output / "simple"
    simple.mkdir(parents=True, exist_ok=True)
    project_links = []
    for project in sorted(projects):
        project_links.append(f'<a href="{project}/">{html.escape(project)}</a><br>')
        links = []
        for wheel in sorted(projects[project], key=lambda item: item["filename"]):
            url = html.escape(f'{wheel["url"]}#sha256={wheel["sha256"]}', quote=True)
            filename = html.escape(wheel["filename"])
            links.append(f'<a href="{url}">{filename}</a><br>')
        project_dir = simple / project
        project_dir.mkdir(exist_ok=True)
        (project_dir / "index.html").write_text(
            page(f"Links for {project}", "\n".join(links)), encoding="utf-8"
        )
    (simple / "index.html").write_text(
        page("VapourSynth API4 Wheels", "\n".join(project_links)), encoding="utf-8"
    )
    (output / "index.html").write_text(
        page(
            "VapourSynth API4 Wheels",
            '<h1>VapourSynth API4 Wheels</h1><p><a href="simple/">PEP 503 package index</a></p>',
        ),
        encoding="utf-8",
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("_site"))
    parser.add_argument("--repository", default=os.environ.get("GITHUB_REPOSITORY"))
    parser.add_argument("--releases-json", type=Path)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.releases_json:
        releases = json.loads(args.releases_json.read_text(encoding="utf-8"))
    elif args.repository:
        releases = fetch_releases(args.repository, os.environ.get("GITHUB_TOKEN"))
    else:
        raise SystemExit("--repository or GITHUB_REPOSITORY is required")
    write_index(collect_wheels(releases), args.output)


if __name__ == "__main__":
    main()
