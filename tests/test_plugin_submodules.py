"""Keep independently maintained native sources aligned with central pins."""
from __future__ import annotations

import json
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


class PluginSubmoduleTests(unittest.TestCase):
    def test_native_layout_and_source_records_match_registered_gitlinks(self):
        paths = git("config", "-f", ".gitmodules", "--get-regexp", r"submodule\..*\.path")
        registered = {}
        for line in paths.splitlines():
            key, path = line.split(None, 1)
            if not path.startswith("plugins/"):
                continue
            url = git("config", "-f", ".gitmodules", "--get", key.removesuffix(".path") + ".url")
            registered[path] = url
        self.assertEqual(set(registered), {
            "plugins/vapoursynth-krigbilateralvk/native",
            "plugins/vapoursynth-dfttestvk/native",
        })
        for path, url in registered.items():
            with self.subTest(source=path):
                parent = Path(path).parent
                record = json.loads((ROOT / parent / "source.json").read_text(encoding="utf-8"))
                self.assertEqual(record["submodule"], path)
                self.assertEqual(record["repository"], url)
                self.assertRegex(record["commit"], r"^[0-9a-f]{40}$")
                mode, commit, stage, indexed_path = git("ls-files", "--stage", "--", path).split()
                self.assertEqual((mode, stage, indexed_path), ("160000", "0", path))
                self.assertEqual(commit, record["commit"])
                self.assertTrue((ROOT / parent / "README.md").is_file())

    def test_source_version_table_matches_each_registration(self):
        versions = (ROOT / "VERSIONS.md").read_text(encoding="utf-8")
        for file in sorted((ROOT / "plugins").glob("*/source.json")):
            with self.subTest(source=file.parent.name):
                record = json.loads(file.read_text(encoding="utf-8"))
                parent = file.parent.relative_to(ROOT).as_posix()
                self.assertIn(
                    f"| {record['submodule']} | {parent} | {record['version']} | {record['commit']} |",
                    versions,
                )


if __name__ == "__main__":
    unittest.main()
