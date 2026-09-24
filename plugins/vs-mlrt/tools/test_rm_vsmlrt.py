from __future__ import annotations

from contextlib import redirect_stderr
import io
import importlib.util
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch


MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "rm_vsmlrt" / "cli.py"
SPEC = importlib.util.spec_from_file_location("rm_vsmlrt_cli", MODULE_PATH)
module = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(module)


class RemoveVsmlrtTests(unittest.TestCase):
    def test_distribution_selection_is_an_exact_allowlist(self):
        installed = {
            "vs-mlrt-cu129": "vs-mlrt-cu129",
            "vs-trt-cu129": "vs-trt-cu129",
            "unrelated-mlrt-helper": "unrelated-mlrt-helper",
        }
        with patch.object(module, "installed_distributions", return_value=installed):
            self.assertEqual(module.selected_distributions(), ["vs-mlrt-cu129", "vs-trt-cu129"])

    def test_cleanup_targets_are_scoped_to_site_packages(self):
        with TemporaryDirectory() as temp:
            site = Path(temp)
            targets = module.cleanup_targets(site)
            self.assertEqual(targets[0], site / "vapoursynth" / "plugins" / "vsmlrt")
            for target in targets:
                module.ensure_safe_target(site, target)

    def test_path_escape_is_rejected(self):
        with TemporaryDirectory() as temp:
            site = Path(temp) / "site"
            site.mkdir()
            with self.assertRaisesRegex(RuntimeError, "outside site-packages"):
                module.ensure_safe_target(site, site / ".." / "other")

    def test_dry_run_does_not_remove_files_or_run_pip(self):
        with TemporaryDirectory() as temp:
            site = Path(temp)
            plugin = site / "vapoursynth" / "plugins" / "vsmlrt"
            plugin.mkdir(parents=True)
            (plugin / "vstrt.dll").write_bytes(b"plugin")
            with (
                patch.object(module, "site_packages_root", return_value=site),
                patch.object(module, "selected_distributions", return_value=["vs-mlrt-cu129"]),
                patch.object(module.subprocess, "run") as run,
            ):
                self.assertEqual(module.main(["--dry-run"]), 0)
            run.assert_not_called()
            self.assertTrue((plugin / "vstrt.dll").is_file())

    def test_cleanup_removes_only_reviewed_paths(self):
        with TemporaryDirectory() as temp:
            site = Path(temp)
            plugin = site / "vapoursynth" / "plugins" / "vsmlrt"
            unrelated = site / "vapoursynth" / "plugins" / "other" / "plugin.dll"
            plugin.mkdir(parents=True)
            unrelated.parent.mkdir(parents=True)
            (plugin / "generated.engine").write_bytes(b"engine")
            unrelated.write_bytes(b"other")
            for target in module.cleanup_targets(site):
                module.remove_target(site, target, dry_run=False, verbose=False)
            self.assertFalse(plugin.exists())
            self.assertEqual(unrelated.read_bytes(), b"other")

    def test_background_worker_arguments_are_not_accepted(self):
        with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            module.parse_args(["--worker"])

    def test_windows_wrapper_runs_the_module_in_the_foreground(self):
        wrapper = Path(__file__).resolve().parents[1] / "scripts" / "rm_vsmlrt.cmd"
        contents = wrapper.read_text(encoding="ascii")
        self.assertIn('"%~dp0python.exe" -m rm_vsmlrt %*', contents)
        self.assertIn("python -m rm_vsmlrt %*", contents)
        self.assertIn("exit /b !ERRORLEVEL!", contents)
        self.assertEqual(len(contents.splitlines()), 3)
        self.assertNotIn("start ", contents.lower())

    def test_posix_wrapper_runs_the_module_in_the_foreground(self):
        wrapper = Path(__file__).resolve().parents[1] / "scripts" / "rm_vsmlrt.sh"
        contents = wrapper.read_text(encoding="ascii")
        self.assertTrue(contents.startswith("#!/bin/sh\n"))
        self.assertIn('exec "$script_dir/python" -m rm_vsmlrt "$@"', contents)
        self.assertIn('exec "$script_dir/python.exe" -m rm_vsmlrt "$@"', contents)
        self.assertIn("exec python -m rm_vsmlrt", contents)
        self.assertNotIn("nohup", contents)
        self.assertNotIn("setsid", contents)


if __name__ == "__main__":
    unittest.main()
