from __future__ import annotations

import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch


spec = importlib.util.spec_from_file_location(
    "vsmlrt_dll_paths",
    Path(__file__).parents[1] / "scripts/vsmlrt_dll_paths.py",
)
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)


class ManifestTests(unittest.TestCase):
    def test_linux_manifest_follows_installed_plugins(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for name in ("vsncnn.so", "vsov.so", "vstrt.so", "vstrt_rtx.so"):
                (root / name).write_bytes(b"plugin")
            with patch.object(module.platform, "system", return_value="Linux"):
                module._sync_vsmlrt_manifest(root)
            self.assertEqual(
                (root / "manifest.vs").read_text(encoding="ascii").splitlines(),
                ["[VapourSynth Manifest V1]", "vsncnn", "vsov", "vstrt", "vstrt_rtx"],
            )


if __name__ == "__main__":
    unittest.main()
