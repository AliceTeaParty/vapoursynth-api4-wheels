"""Prevent same-name upstream wheels from satisfying our maintained requirements."""
from __future__ import annotations

import importlib.util
import json
import re
import subprocess
import sys
import tempfile
import tomllib
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from hatchling.builders.wheel import WheelBuilder
from packaging.requirements import Requirement
from packaging.utils import canonicalize_name
from packaging.version import Version

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from module_common import project_metadata, validate_ref


def projects():
    files = subprocess.check_output(["git", "ls-files", "*/pyproject.toml"], cwd=ROOT, text=True).splitlines()
    result = {}
    for relative in files:
        if not relative.startswith(("modules/", "plugins/")):
            continue
        path = ROOT / relative
        data = tomllib.loads(path.read_text(encoding="utf-8"))
        if "project" in data:
            result[canonicalize_name(data["project"]["name"])] = (path, data)
    return result


def load_hook(path):
    spec = importlib.util.spec_from_file_location("version_test_hook", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class WheelVersionTests(unittest.TestCase):
    def test_all_owned_versions_dependencies_and_readme_agree(self):
        catalog = projects()
        self.assertTrue(catalog)
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        for name, (path, data) in catalog.items():
            with self.subTest(project=name):
                project = data["project"]
                version = Version(project["version"])
                self.assertEqual(version.local, "alice.1")
                self.assertIn(f"| `{name}` | `{version}` |", readme)
                builder = WheelBuilder(str(path.parent))
                self.assertEqual(builder.metadata.version, str(version))
                requirements = [*project.get("dependencies", []), *data["build-system"]["requires"]]
                for group in project.get("optional-dependencies", {}).values():
                    requirements.extend(group)
                for value in requirements:
                    req = Requirement(value)
                    dependency = catalog.get(canonicalize_name(req.name))
                    if dependency:
                        expected = dependency[1]["project"]["version"]
                        self.assertEqual(str(req.specifier), f"=={expected}", value)
                        self.assertIsNone(req.url, value)
                for url in project.get("urls", {}).values():
                    if "/releases/tag/" in url:
                        self.assertTrue(url.endswith(f"-v{version}"), url)
        for item in json.loads((ROOT / "tests/module-snapshots.json").read_text()):
            self.assertIn(f"| `{item['module']}` | `{item['version']}` (upstream) |", readme)
            self.assertIsNone(Version(item["version"]).local)

    def test_exact_local_pin_excludes_public_and_higher_upstream_versions(self):
        requirement = Requirement("vapoursynth-bm3dcpu==2.16+alice.1")
        self.assertIn("2.16+alice.1", requirement.specifier)
        for version in ("2.16", "2.17", "2.16+another.1"):
            self.assertNotIn(version, requirement.specifier)
        self.assertLess(Version("2.16+alice.1"), Version("2.17"))

    def test_module_metadata_and_refs_accept_local_version(self):
        path = ROOT / "modules/vs-collection-rk/pyproject.toml"
        metadata = project_metadata(path.read_bytes(), "vs-collection-rk")
        self.assertEqual(metadata["version"], "0.4.0+alice.1")
        validate_ref("v0.4.0+alice.1")

    def test_variant_prebuilt_tags_track_project_version(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        for directory in ("vapoursynth-bm3dcuda", "vapoursynth-dfttest2"):
            root = ROOT / "plugins" / directory
            hook = load_hook(root / "hatch_build.py")
            version = tomllib.loads((root / "pyproject.toml").read_text())["project"]["version"]
            for tag in hook.RELEASE_TAGS.values():
                name, actual_version = tag.rsplit("-v", 1)
                self.assertEqual(actual_version, version)
                self.assertIn(f"| `{name}` | `{version}` |", readme)

    def test_legacy_vsmlrt_hook_uses_project_version_not_hatch_target(self):
        module = load_hook(ROOT / "plugins/vs-mlrt/packaging/vsmlrt_build.py")
        with tempfile.TemporaryDirectory() as directory:
            hook = module.CustomBuildHook(directory, {}, None, SimpleNamespace(version="16.2.2+alice.1"), directory, "wheel")
            with patch.object(hook, "_has_platform_release_payload", return_value=True), \
                 patch.object(hook, "_source_root", return_value=Path(directory)), \
                 patch.object(hook, "_detect_payload_tag", return_value="generic"), \
                 patch.object(hook, "_skip_prebuilt", return_value=True), \
                 patch.dict("os.environ", {}, clear=True):
                hook.initialize("standard", {})
                self.assertEqual(hook._release_tag("generic"), "vs-mlrt-generic-v16.2.2+alice.1")

    def test_release_asset_regexes_match_local_wheel_filenames(self):
        for file in (ROOT / ".github/workflows").glob("package-*.yml"):
            for pattern in re.findall(r"grep -Ex '([^']+\\.whl)'", file.read_text()):
                if "alice" in pattern:
                    filename = pattern.replace("\\", "")
                    self.assertIsNotNone(re.fullmatch(pattern, filename), file)
                    self.assertIsNone(re.fullmatch(pattern, filename.replace("+alice.1", "")), file)


if __name__ == "__main__":
    unittest.main()
