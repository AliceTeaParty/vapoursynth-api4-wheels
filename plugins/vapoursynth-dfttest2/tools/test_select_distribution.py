from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

import select_distribution


class SelectDistributionTests(unittest.TestCase):
    def test_public_package_mapping(self) -> None:
        self.assertEqual(
            select_distribution.PACKAGES,
            {
                "cpu": "vapoursynth-dfttest2-generic",
                "cu121": "vapoursynth-dfttest2-cu121",
                "cu129": "vapoursynth-dfttest2-cu129",
            },
        )

    def test_selects_distribution_and_marker(self) -> None:
        with TemporaryDirectory() as temp_dir:
            pyproject = Path(temp_dir) / "pyproject.toml"
            marker = Path(temp_dir) / "variant"
            pyproject.write_text('[project]\nname = "vapoursynth-dfttest2-generic"\n', encoding="utf-8")
            result = select_distribution.select_distribution(
                "cu121", pyproject=pyproject, variant_marker=marker
            )
            self.assertEqual(result, "vapoursynth-dfttest2-cu121")
            self.assertIn('name = "vapoursynth-dfttest2-cu121"', pyproject.read_text(encoding="utf-8"))
            self.assertEqual(marker.read_text(encoding="ascii"), "cu121\n")

    def test_rejects_unexpected_existing_project(self) -> None:
        with TemporaryDirectory() as temp_dir:
            pyproject = Path(temp_dir) / "pyproject.toml"
            marker = Path(temp_dir) / "variant"
            pyproject.write_text('[project]\nname = "unrelated"\n', encoding="utf-8")
            with self.assertRaisesRegex(RuntimeError, "unexpected project name"):
                select_distribution.select_distribution("cpu", pyproject=pyproject, variant_marker=marker)


if __name__ == "__main__":
    unittest.main()
