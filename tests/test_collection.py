"""Collection source history, entry requirements and wheel boundary checks."""
from __future__ import annotations
import hashlib
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
from collection_common import ROOT, load_collection, make_plans
from build_collection import validate_set
from module_common import read_json
from validate_module_wheel import validate_wheel
from test_modules import source_plan as fixture_plan, wheel_files, write_wheel


class CollectionTests(unittest.TestCase):
    def test_subtree_imports_and_single_combined_patches_preserve_migration(self):
        history = read_json(ROOT / "modules/collection-history.json")
        for item in history["components"]:
            with self.subTest(module=item["module"]):
                parent = subprocess.check_output(["git", "-C", str(ROOT), "rev-parse", item["patch_commit"]+"^"], text=True).strip()
                self.assertEqual(parent, item["import_commit"])
                baseline_tree = subprocess.check_output(["git", "-C", str(ROOT), "rev-parse", item["import_commit"]+":"+item["path"]], text=True).strip()
                self.assertEqual(baseline_tree, item["upstream_tree_sha"])
                marker = subprocess.check_output(["git", "-C", str(ROOT), "show", "-s", "--format=%B", item["import_commit"]+"^2"], text=True)
                self.assertIn("git-subtree-split: "+item["upstream_revision"], marker)
                changed = subprocess.check_output(["git", "-C", str(ROOT), "diff-tree", "--no-commit-id", "--name-only", "-r", item["patch_commit"]], text=True).splitlines()
                self.assertTrue(changed)
                self.assertTrue(all(path.startswith(item["path"]+"/") for path in changed))
                for relative, digest in item["runtime_sha256"].items():
                    content = subprocess.check_output(["git", "-C", str(ROOT), "show", item["patch_commit"]+":"+item["path"]+"/"+relative])
                    self.assertEqual(hashlib.sha256(content).hexdigest(), digest)

    def test_havsfunc_tracks_both_modification_layers_from_real_upstream(self):
        history = read_json(ROOT / "modules/collection-history.json")
        item = next(item for item in history["components"] if item["module"] == "havsfunc")
        self.assertEqual(item["upstream_url"], "https://github.com/HomeOfVapourSynthEvolution/havsfunc")
        self.assertEqual(item["upstream_revision"], "7f0a9a7a37b60a05b9f408024d203e511e544a61")
        self.assertEqual(item["vendored_revision"], "4e0d21258869283ce04568dda0173e4c8b890668")
        self.assertIn(item["vendored_revision"], item["intermediate_commits"])
        self.assertIn("4333dc71bbdc54e119ffb35d0b62a437909138f2", item["collection_commits"])
        layers = history["havsfunc_layers"]
        self.assertTrue(layers["initial_collection_equals_gist"])
        self.assertNotEqual(layers["gist_sha256"], layers["collection_sha256"])
        self.assertEqual(item["runtime_sha256"]["havsfunc.py"], layers["collection_sha256"])

    def test_entry_pins_every_current_component_and_keeps_external_deps_empty(self):
        registry = load_collection()
        plans = make_plans(registry, "a"*40, lambda path: (ROOT/path).read_bytes())
        self.assertEqual(len(plans), len(registry["components"])+1)
        self.assertTrue(all(plan["dependencies"] == [] for plan in plans[:-1]))
        self.assertEqual(len(plans[-1]["dependencies"]), len(registry["components"]))
        self.assertTrue(all(plan["requires_python"] == ">=3.12" for plan in plans))

    def test_runtime_change_or_unpinned_entry_dependency_is_rejected(self):
        registry = load_collection()
        def edited_runtime(path):
            data = (ROOT/path).read_bytes()
            return data+b"\n# unrecorded edit\n" if path == "modules/havsfunc/havsfunc.py" else data
        with self.assertRaisesRegex(ValueError, "unrecorded runtime"):
            make_plans(registry, "a"*40, edited_runtime)
        def edited_pin(path):
            data = (ROOT/path).read_bytes()
            return data.replace(b"havsfunc==", b"havsfunc>=") if path.endswith("vs-collection-rk/pyproject.toml") else data
        with self.assertRaisesRegex(ValueError, "pin every component"):
            make_plans(registry, "a"*40, edited_pin)

    def test_flat_modules_keep_the_original_import_filename(self):
        plan = fixture_plan()
        plan["runtime_kind"] = "module"
        plan["required_files"] = ["demo.py"]
        files = wheel_files()
        files["demo.py"] = files.pop("demo/__init__.py")
        del files["demo/data.glsl"]
        with tempfile.TemporaryDirectory() as temp:
            wheel = write_wheel(Path(temp), files)
            result = validate_wheel(wheel, plan)
            self.assertIn("demo.py", result["file_sha256"])
            plan["runtime_kind"] = "package"
            with self.assertRaises(ValueError):
                validate_wheel(wheel, plan)

    def test_incomplete_collection_cannot_be_published(self):
        plan = {"components":[fixture_plan(), {**fixture_plan(), "distribution":"missing"}]}
        with tempfile.TemporaryDirectory() as temp:
            write_wheel(Path(temp))
            with self.assertRaisesRegex(ValueError, "incomplete"):
                validate_set(plan, Path(temp))


if __name__ == "__main__":
    unittest.main()
