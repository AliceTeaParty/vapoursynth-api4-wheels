from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch


MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "rm_vsmlrt_helper" / "cli.py"
SPEC = importlib.util.spec_from_file_location("rm_vsmlrt_helper_cli", MODULE_PATH)
module = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(module)


class RemoveVsmlrtHelperTests(unittest.TestCase):
    def test_command_uses_the_reviewed_allowlist(self):
        command = module.uninstall_command(["vs-mlrt-cu129", "vs-trt-cu129"])
        self.assertEqual(command[-2:], ["vs-mlrt-cu129", "vs-trt-cu129"])

    def test_helper_only_prints_the_reviewed_command(self):
        with patch.object(module, "selected_distributions", return_value=["vs-mlrt-generic", "vs-ov"]):
            with patch.object(module, "print") as output:
                self.assertEqual(module.main([]), 0)
        rendered = "\n".join(str(call.args[0]) for call in output.call_args_list)
        self.assertIn("pip uninstall -y vs-mlrt-generic vs-ov", rendered)
        self.assertIn("does not run pip", rendered)


if __name__ == "__main__":
    unittest.main()
