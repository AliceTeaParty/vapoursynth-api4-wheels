from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock
import zipfile


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "assemble_component_release.py"
SPEC = importlib.util.spec_from_file_location("assemble_component_release", SCRIPT)
module = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(module)


def write_wheel(path: Path, newline: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    dist_info = "vs_mlrt_cu121-16.2.3.dist-info"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("vsmlrt.py", newline.join((b"from pathlib import Path", b"ROOT = Path(__file__).parent", b"")))
        archive.writestr(f"{dist_info}/METADATA", b"Name: vs-mlrt-cu121\nVersion: 16.2.3\n")
        archive.writestr(f"{dist_info}/WHEEL", b"Wheel-Version: 1.0\nGenerator: test\nTag: py3-none-any\n")
        archive.writestr(f"{dist_info}/RECORD", b"")


class ReleaseAssemblyTests(unittest.TestCase):
    def test_conflicting_platform_independent_wheels_require_canonical_copy(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            name = "vs_mlrt_cu121-16.2.3-py3-none-any.whl"
            windows = root / "windows" / name
            linux = root / "linux" / name
            write_wheel(windows, b"\r\n")
            write_wheel(linux, b"\n")

            with self.assertRaisesRegex(RuntimeError, "Conflicting wheels share the filename"):
                module.assemble([windows.parent, linux.parent], root / "output")

    def test_canonical_copy_wins_while_all_inventory_hashes_are_validated(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            name = "vs_mlrt_cu121-16.2.3-py3-none-any.whl"
            windows = root / "inputs" / "windows" / name
            linux = root / "inputs" / "linux" / name
            canonical = root / "canonical" / name
            write_wheel(windows, b"\r\n")
            write_wheel(linux, b"\n")
            canonical.parent.mkdir(parents=True)
            canonical.write_bytes(linux.read_bytes())

            hashes = {
                "windows": hashlib.sha256(windows.read_bytes()).hexdigest(),
                "linux": hashlib.sha256(linux.read_bytes()).hexdigest(),
            }
            for variant in ("generic", "cu121", "cu129"):
                for system in ("windows", "linux"):
                    inventory = {
                        "variant": variant,
                        "platform": system,
                        "source_revision": "abc123",
                        "wheels": [{"name": name, "sha256": hashes[system], "size": 0}],
                    }
                    destination = root / "inputs" / system / f"component-wheel-inventory-{variant}-{system}.json"
                    destination.write_text(json.dumps(inventory), encoding="utf-8")

            output = root / "output"
            with mock.patch.object(module.verify_module, "verify") as verify:
                module.assemble([root / "inputs"], output, root / "canonical")

            self.assertEqual((output / name).read_bytes(), canonical.read_bytes())
            self.assertEqual(verify.call_count, 2)

if __name__ == "__main__":
    unittest.main()
