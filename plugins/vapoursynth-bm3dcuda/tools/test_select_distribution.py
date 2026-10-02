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
                "cpu": "vapoursynth-bm3dcpu",
                "cu121": "vapoursynth-bm3dcuda-cu121",
                "cu129": "vapoursynth-bm3dcuda-cu129",
            },
        )

    def test_rejects_unexpected_existing_project(self) -> None:
        with TemporaryDirectory() as temp_dir:
            pyproject = Path(temp_dir) / "pyproject.toml"
            marker = Path(temp_dir) / "variant.txt"
            pyproject.write_text('[project]\nname = "unrelated"\n', encoding="utf-8")
            with self.assertRaisesRegex(RuntimeError, "unexpected project name"):
                select_distribution.select_distribution("cpu", pyproject=pyproject, variant_marker=marker)

    def test_selects_cuda_distribution_and_marker(self) -> None:
        with TemporaryDirectory() as temp_dir:
            pyproject = Path(temp_dir) / "pyproject.toml"
            marker = Path(temp_dir) / "variant.txt"
            pyproject.write_text('[project]\nname = "vapoursynth-bm3dcpu"\n', encoding="utf-8")
            package = select_distribution.select_distribution(
                "cu129", pyproject=pyproject, variant_marker=marker
            )
            self.assertEqual(package, "vapoursynth-bm3dcuda-cu129")
            self.assertIn('name = "vapoursynth-bm3dcuda-cu129"', pyproject.read_text(encoding="utf-8"))
            self.assertEqual(marker.read_text(encoding="ascii"), "cu129\n")


if __name__ == "__main__":
    unittest.main()
