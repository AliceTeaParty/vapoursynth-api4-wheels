from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch


spec = importlib.util.spec_from_file_location(
    "smoke_vcs_extras_install",
    Path(__file__).with_name("smoke_vcs_extras_install.py"),
)
smoke = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(smoke)


class DistributionVersionTests(unittest.TestCase):
    def test_named_distribution_is_verified(self) -> None:
        with patch.object(smoke.importlib.metadata, "version", return_value="16.2.3") as version:
            smoke.verify_distribution_version("vs-mlrt-generic")
        version.assert_called_once_with("vs-mlrt-generic")

    def test_wrong_version_is_rejected(self) -> None:
        with patch.object(smoke.importlib.metadata, "version", return_value="16.2.1"):
            with self.assertRaisesRegex(SystemExit, "vs-mlrt-cu121"):
                smoke.verify_distribution_version("vs-mlrt-cu121")


if __name__ == "__main__":
    unittest.main()
