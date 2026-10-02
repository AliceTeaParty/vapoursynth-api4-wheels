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
from module_common import CENTRAL_REPOSITORY, GitHubError, digest_file, read_json
import publish_collection as publisher
from unittest.mock import patch
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
        # Shared installed-wheel summaries must identify the central source;
        # canonical upstream identities remain in component provenance.
        self.assertTrue(all(plan["repository"] == "AliceTeaParty/vapoursynth-api4-wheels" and plan["source_sha"] == "a"*40 for plan in plans))

    def test_runtime_change_or_unpinned_entry_dependency_is_rejected(self):
        registry = load_collection()
        def edited_runtime(path):
            data = (ROOT/path).read_bytes()
            return data+b"\n# unrecorded edit\n" if path == "modules/havsfunc/havsfunc.py" else data
        with self.assertRaisesRegex(ValueError, "unrecorded runtime"):
            make_plans(registry, "a"*40, edited_runtime)
        def edited_pin(path):
            data = (ROOT/path).read_bytes()
            return data.replace(b"havsfunc==33.post1+alice.1", b"havsfunc>=33.post1") if path.endswith("vs-collection-rk/pyproject.toml") else data
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

    def test_group_release_recovers_without_exposing_an_incomplete_set(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            files = []
            for name in ("component-1-py3-none-any.whl", "entry-1-py3-none-any.whl"):
                path = directory / name
                path.write_bytes(name.encode())
                files.append({"wheel": name, "sha256": digest_file(path)})
            manifest = {"version": "1.0", "registry_sha256": "a"*64, "central_sha": "b"*40,
                        "build_run_url": "https://example.invalid/run", "wheels": files}
            state = {"release": None, "creates": 0, "failed": False, "uploads": [], "published": False}

            class API:
                def request(self, path, method="GET", data=None):
                    if path == f"repos/{CENTRAL_REPOSITORY}":
                        return {"default_branch": "main"}
                    if "/releases/tags/" in path:
                        if state["release"] is None or state["release"]["draft"]:
                            raise GitHubError(method, path, 404)
                        return state["release"]
                    if "/releases?" in path:
                        return [state["release"]] if state["release"] else []
                    if method == "POST":
                        state["creates"] += 1
                        state["release"] = {**data, "id": 99, "assets": [], "html_url": "https://example.invalid/release"}
                    if method == "PATCH":
                        self_names = {asset["name"] for asset in state["release"]["assets"]}
                        assert self_names == {item["wheel"] for item in files} | {"collection-manifest.json"}
                        state["published"] = True
                        state["release"].update(data)
                    return state["release"]

            def upload(command, **kwargs):
                path = Path(command[command.index("--input") + 1])
                if len(state["uploads"]) == 1 and not state["failed"]:
                    state["failed"] = True
                    raise subprocess.CalledProcessError(1, command)
                self.assertIn("/releases/99/assets?name=", command[4])
                state["uploads"].append(path.name)
                state["release"]["assets"].append({"name": path.name, "id": len(state["uploads"]),
                    "size": path.stat().st_size, "digest": "sha256:"+digest_file(path), "state": "uploaded"})

            def download(command, **kwargs):
                return (directory / "collection-manifest.json").read_bytes()

            with patch.object(publisher.subprocess, "run", side_effect=upload), patch.object(publisher.subprocess, "check_output", side_effect=download):
                with self.assertRaises(subprocess.CalledProcessError):
                    publisher.publish(API(), manifest, directory)
                self.assertFalse(state["published"])
                self.assertTrue(state["release"]["draft"])
                publisher.publish(API(), manifest, directory)
                self.assertTrue(state["published"])
                self.assertEqual(state["creates"], 1)
                self.assertEqual(len(state["uploads"]), 3)
                publisher.publish(API(), manifest, directory)
                self.assertEqual(len(state["uploads"]), 3)


if __name__ == "__main__":
    unittest.main()
