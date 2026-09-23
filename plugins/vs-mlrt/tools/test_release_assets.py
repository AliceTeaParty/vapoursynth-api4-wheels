from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest


SCRIPT = Path(__file__).with_name("verify_release_assets.py")
SPEC = importlib.util.spec_from_file_location("verify_release_assets", SCRIPT)
module = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(module)


class ReleaseAssetTests(unittest.TestCase):
    def setUp(self) -> None:
        self.inventory = {
            "wheels": [
                {"name": "entry.whl", "sha256": "abc"},
                {"name": "native.whl", "sha256": "def"},
            ]
        }
        self.release = {
            "isDraft": True,
            "assets": [
                {"name": "entry.whl", "digest": "sha256:abc", "state": "uploaded"},
                {"name": "native.whl", "digest": "sha256:def", "state": "uploaded"},
                {"name": "vs-mlrt-release-inventory.json", "digest": "sha256:inventory", "state": "uploaded"},
            ],
        }

    def test_draft_assets_with_matching_digests_pass(self) -> None:
        module.verify(self.inventory, self.release)

    def test_missing_or_unexpected_wheel_fails(self) -> None:
        self.release["assets"].pop(0)
        self.release["assets"].append({"name": "extra.whl", "digest": "sha256:abc", "state": "uploaded"})
        with self.assertRaisesRegex(RuntimeError, "wheel set differs"):
            module.verify(self.inventory, self.release)

    def test_incomplete_upload_fails(self) -> None:
        self.release["assets"][0]["state"] = "new"
        with self.assertRaisesRegex(RuntimeError, "not fully uploaded"):
            module.verify(self.inventory, self.release)

    def test_digest_mismatch_fails(self) -> None:
        self.release["assets"][0]["digest"] = "sha256:wrong"
        with self.assertRaisesRegex(RuntimeError, "digest mismatch"):
            module.verify(self.inventory, self.release)


if __name__ == "__main__":
    unittest.main()
