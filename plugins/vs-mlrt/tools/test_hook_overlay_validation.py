from __future__ import annotations

import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile


spec = importlib.util.spec_from_file_location("vsmlrt_hook", Path(__file__).parents[1] / "packaging/vsmlrt_build.py")
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)


class HookOverlayTests(unittest.TestCase):
    def test_cuda_overlay_removes_generic_payload_and_manifest(self):
        hook = object.__new__(module.CustomBuildHook)
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            stage = root / "stage"
            stage.mkdir()
            (stage / "vsncnn.dll").write_bytes(b"cuda-build-generic")
            (stage / "vstrt.dll").write_bytes(b"cuda-plugin")
            (stage / "manifest.vs").write_text("self-contained", encoding="ascii")
            archive = root / "generic.zip"
            with zipfile.ZipFile(archive, "w") as payload:
                payload.writestr("vsmlrt/vsncnn.dll", b"published-generic")
                payload.writestr("vsmlrt/manifest.vs", b"generic")

            with (
                patch.object(hook, "_source_root", return_value=root),
                patch.object(hook, "_resolve_generic_reference", return_value=[archive]),
                patch.object(module.platform, "system", return_value="Windows"),
                patch.dict(module.os.environ, {"VSMLRT_OVERLAY_SHARDS": "1", "VSMLRT_OVERLAY_SHARD": "1"}),
            ):
                hook._prepare_cuda_overlay(stage)

            self.assertFalse((stage / "vsncnn.dll").exists())
            self.assertFalse((stage / "manifest.vs").exists())
            self.assertEqual((stage / "vstrt.dll").read_bytes(), b"cuda-plugin")

    def test_overlay_shards_are_disjoint_and_complete(self):
        hook = object.__new__(module.CustomBuildHook)
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            expected = {f"file-{index}.bin" for index in range(9)}
            selected = []
            for shard in range(1, 4):
                stage = root / f"shard-{shard}"
                stage.mkdir()
                for index, name in enumerate(sorted(expected), start=1):
                    (stage / name).write_bytes(bytes([index]) * index)
                with patch.dict(
                    module.os.environ,
                    {"VSMLRT_OVERLAY_SHARDS": "3", "VSMLRT_OVERLAY_SHARD": str(shard)},
                ):
                    hook._select_overlay_shard(stage)
                selected.append({path.name for path in stage.iterdir()})

            self.assertEqual(set().union(*selected), expected)
            self.assertFalse(selected[0] & selected[1])
            self.assertFalse(selected[0] & selected[2])
            self.assertFalse(selected[1] & selected[2])

    def test_complete_variants_validate(self):
        hook = object.__new__(module.CustomBuildHook)
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            variants = {
                "generic": ["vsncnn.dll", "vsov.dll"],
                "cu121": ["vsncnn.dll", "vsov.dll", "vstrt.dll"],
                "cu129": ["vsncnn.dll", "vsov.dll", "vstrt.dll", "vstrt_rtx.dll"],
            }
            for variant, plugins in variants.items():
                directory = root / variant
                directory.mkdir()
                (directory / "models").mkdir()
                for plugin in plugins:
                    (directory / plugin).write_bytes(b"plugin")
                if variant != "generic":
                    helper = directory / "vsmlrt-cuda"
                    helper.mkdir()
                    for name in ("trtexec.exe", "trtexec-build.json"):
                        (helper / name).write_bytes(b"helper")
                if variant == "cu129":
                    (directory / "vsmlrt-cuda" / "tensorrt_rtx.exe").write_bytes(b"helper")
                with patch.object(module.platform, "system", return_value="Windows"):
                    hook._validate_plugin_dir(directory, variant)

    def test_missing_builder_fails_cuda_variant(self):
        hook = object.__new__(module.CustomBuildHook)
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            (directory / "models").mkdir()
            for plugin in ("vsncnn.dll", "vsov.dll", "vstrt.dll"):
                (directory / plugin).write_bytes(b"plugin")
            with patch.object(module.platform, "system", return_value="Windows"):
                with self.assertRaisesRegex(RuntimeError, "builder helper"):
                    hook._validate_plugin_dir(directory, "cu121")


if __name__ == "__main__":
    unittest.main()
