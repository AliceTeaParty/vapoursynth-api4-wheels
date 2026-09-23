from __future__ import annotations

import argparse
import re
import tomllib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PYPROJECT = ROOT / "pyproject.toml"
VARIANT_MARKER = ROOT / ".dfttest2-variant"
PACKAGES = {
    "cpu": "vapoursynth-dfttest2-generic",
    "cu121": "vapoursynth-dfttest2-cu121",
    "cu129": "vapoursynth-dfttest2-cu129",
}
NAME_LINE = re.compile(r'(?m)^name = "[^"]+"$')


def select_distribution(
    variant: str,
    *,
    pyproject: Path = PYPROJECT,
    variant_marker: Path = VARIANT_MARKER,
) -> str:
    package = PACKAGES[variant]
    source = pyproject.read_text(encoding="utf-8")
    current = tomllib.loads(source)["project"]["name"]
    if current not in PACKAGES.values():
        raise RuntimeError(f"unexpected project name {current!r}")
    updated, count = NAME_LINE.subn(f'name = "{package}"', source, count=1)
    if count != 1:
        raise RuntimeError("could not select the pyproject distribution name")
    if tomllib.loads(updated)["project"]["name"] != package:
        raise RuntimeError("selected pyproject metadata did not validate")
    pyproject.write_text(updated, encoding="utf-8", newline="\n")
    variant_marker.write_text(f"{variant}\n", encoding="ascii", newline="\n")
    return package


def main() -> None:
    parser = argparse.ArgumentParser(description="Select one DFTTest2 wheel distribution.")
    parser.add_argument("variant", choices=sorted(PACKAGES))
    args = parser.parse_args()
    print(select_distribution(args.variant))


if __name__ == "__main__":
    main()
