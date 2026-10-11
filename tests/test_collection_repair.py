"""Detect file ownership damage even when pip's distribution metadata is intact."""
from __future__ import annotations

import base64
import hashlib
import importlib.util
from importlib.metadata import PackagePath
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
ENTRY = {"distribution": "mvsfunc", "wheel_version": "11.post1+alice.1",
         "runtime_kind": "package", "install_path": "mvsfunc", "import_name": "mvsfunc"}


def load_checker():
    spec = importlib.util.spec_from_file_location("vs_collection_rk.__main__", ROOT / "modules/vs-collection-rk/vs_collection_rk/__main__.py")
    module = importlib.util.module_from_spec(spec)
    with patch.dict(sys.modules, vs_collection_rk=SimpleNamespace(load_registry=lambda: [ENTRY])):
        spec.loader.exec_module(module)
    return module


class RepairTests(unittest.TestCase):
    def test_missing_runtime_is_detected_despite_installed_metadata(self):
        checker = load_checker()
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "mvsfunc").mkdir()
            (root / "mvsfunc/__init__.py").write_text("from .mvsfunc import *\n")
            dist = SimpleNamespace(version=ENTRY["wheel_version"],
                                   files=[PackagePath("mvsfunc/__init__.py"), PackagePath("mvsfunc/mvsfunc.py"), PackagePath("mvsfunc/_metadata.py")],
                                   locate_file=lambda file: root / file)
            for file in dist.files:
                file.hash = None
            record = "\n".join(f"{file},," for file in dist.files)
            dist.read_text = lambda name: record
            # Python 3.14 filters deleted files out of distribution.files.
            dist.files = dist.files[:1]
            with patch.object(checker.metadata, "distribution", return_value=dist):
                errors = checker.check_files()["mvsfunc"]
                self.assertIn("missing mvsfunc/mvsfunc.py", errors)
                self.assertIn("missing mvsfunc/_metadata.py", errors)

    def test_namespace_package_or_missing_record_cannot_pass(self):
        checker = load_checker()
        for records in (None, [], [PackagePath("mvsfunc/mvsfunc.py")]):
            with self.subTest(records=records):
                dist = SimpleNamespace(version=ENTRY["wheel_version"], files=records, locate_file=lambda file: ROOT / file)
                dist.read_text = lambda name: "\n".join(f"{file},," for file in records or [])
                with patch.object(checker.metadata, "distribution", return_value=dist):
                    self.assertIn("RECORD does not list mvsfunc/__init__.py", checker.check_files()["mvsfunc"])

    def test_changed_runtime_hash_is_detected(self):
        checker = load_checker()
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "mvsfunc").mkdir()
            (root / "mvsfunc/__init__.py").write_bytes(b"changed")
            file = PackagePath("mvsfunc/__init__.py")
            digest = base64.urlsafe_b64encode(hashlib.sha256(b"original").digest()).decode().rstrip("=")
            file.hash = SimpleNamespace(mode="sha256", value=digest)
            dist = SimpleNamespace(version=ENTRY["wheel_version"], files=[file], locate_file=lambda file: root / file)
            dist.read_text = lambda name: f"{file},sha256={digest},8\n"
            with patch.object(checker.metadata, "distribution", return_value=dist):
                self.assertEqual(checker.check_files(), {"mvsfunc": ["changed mvsfunc/__init__.py"]})

    def test_deleted_bytecode_does_not_require_repair(self):
        checker = load_checker()
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "mvsfunc").mkdir()
            (root / "mvsfunc/__init__.py").write_bytes(b"")
            dist = SimpleNamespace(version=ENTRY["wheel_version"], locate_file=lambda file: root / file,
                                   read_text=lambda name: "mvsfunc/__init__.py,,\nmvsfunc/__pycache__/__init__.cpython-314.pyc,,\n")
            with patch.object(checker.metadata, "distribution", return_value=dist):
                self.assertEqual(checker.check_files(), {})

    def test_repair_uses_same_interpreter_and_exact_pin_without_dependencies(self):
        checker = load_checker()
        with patch.object(checker, "check_files", side_effect=[{"mvsfunc": ["missing"]}, {}]), \
             patch.object(checker.subprocess, "run") as run, \
             patch.object(sys, "argv", ["checker", "repair", "--no-index", "--find-links", "wheels"]):
            self.assertEqual(checker.main(), 0)
            self.assertEqual(run.call_args.args[0], [sys.executable, "-m", "pip", "install", "--force-reinstall", "--no-deps", "--find-links", "wheels", "--no-index", "mvsfunc==11.post1+alice.1"])


if __name__ == "__main__":
    unittest.main()
