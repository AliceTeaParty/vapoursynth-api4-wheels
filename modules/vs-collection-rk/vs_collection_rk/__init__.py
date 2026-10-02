"""Metadata for the separately installed Collection components."""
from __future__ import annotations

import json
from importlib.metadata import version
from importlib.resources import files
from typing import Any

__all__ = ["__version__", "bundled_scripts", "find_script", "load_registry"]
__version__ = version("vs-collection-rk")


def load_registry() -> list[dict[str, Any]]:
    return json.loads(files(__package__).joinpath("_registry.json").read_text(encoding="utf-8"))


def bundled_scripts() -> list[str]:
    return [entry["import_name"] for entry in load_registry()]


def find_script(name: str) -> dict[str, Any]:
    for entry in load_registry():
        if name in (entry["slug"], entry["import_name"], entry["distribution"]):
            return entry
    raise KeyError(name)
