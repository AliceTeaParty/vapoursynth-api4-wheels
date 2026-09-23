from __future__ import annotations

import importlib.util
from pathlib import Path, PurePosixPath
import tomllib
import unittest


ROOT = Path(__file__).resolve().parents[1]
HOOK = ROOT / "packaging" / "components" / "component_hook.py"
SPEC = importlib.util.spec_from_file_location("component_hook", HOOK)
module = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(module)

VERIFY_SPEC = importlib.util.spec_from_file_location(
    "verify_component_wheels", ROOT / "tools" / "verify_component_wheels.py"
)
verify_module = importlib.util.module_from_spec(VERIFY_SPEC)
assert VERIFY_SPEC.loader is not None
VERIFY_SPEC.loader.exec_module(verify_module)


class ComponentPackagingTests(unittest.TestCase):
    def test_executable_stack_detector(self):
        payload = bytearray(128)
        payload[:6] = b"\x7fELF\x02\x01"
        import struct
        struct.pack_into("<Q", payload, 0x20, 64)
        struct.pack_into("<HH", payload, 0x36, 56, 1)
        struct.pack_into("<II", payload, 64, 0x6474E551, 7)
        self.assertTrue(verify_module.elf_requests_executable_stack(bytes(payload)))
        struct.pack_into("<II", payload, 64, 0x6474E551, 6)
        self.assertFalse(verify_module.elf_requests_executable_stack(bytes(payload)))

    def test_every_mapping_has_a_project_and_every_project_has_a_mapping(self):
        project_root = ROOT / "packaging" / "components"
        projects = {path.parent.name for path in project_root.glob("*/pyproject.toml")}
        self.assertEqual(projects, set(module.WINDOWS_FILES))
        self.assertEqual(projects, set(module.LINUX_FILES))

    def test_component_files_do_not_overlap(self):
        for files_by_component in (module.WINDOWS_FILES, module.LINUX_FILES):
            for variant in ("generic", "cu121", "cu129"):
                owners: dict[str, str] = {}
                selected = {
                    component: names for component, names in files_by_component.items()
                    if component in {"vs-ov", "vs-ncnn"} or component.endswith(variant)
                }
                for component, names in selected.items():
                    for name in names:
                        self.assertNotIn(
                            name,
                            owners,
                            f"{variant}: {name} is owned by {owners.get(name)} and {component}",
                        )
                        owners[name] = component

    def test_cuda_support_files_use_the_shared_subdirectory(self):
        plugin_names = {"vstrt.dll", "vstrt_rtx.dll", "vstrt.so", "vstrt_rtx.so"}
        for files_by_component in (module.WINDOWS_FILES, module.LINUX_FILES):
            for component, names in files_by_component.items():
                if component in {"vs-ov", "vs-ncnn"}:
                    continue
                for name in names:
                    if PurePosixPath(name).name in plugin_names:
                        self.assertEqual(len(PurePosixPath(name).parts), 1)
                    else:
                        self.assertEqual(PurePosixPath(name).parts[0], "vsmlrt-cuda", name)

    def test_cu129_does_not_restore_removed_runtime_families(self):
        removed = ("cudart", "cublas", "cudnn", "cufft", "nvblas", "nvrtc", "nvvm", "nvjitlink")
        for files_by_component in (module.WINDOWS_FILES, module.LINUX_FILES):
            cu129 = [name.lower() for component, names in files_by_component.items() if component.endswith("cu129") for name in names]
            self.assertFalse([name for name in cu129 if PurePosixPath(name).name.startswith(removed)])

    def test_entry_dependencies_are_direct_and_exact(self):
        entries = ROOT / "packaging" / "distributions"
        expected = {
            "generic": {"vs-mlrt-models", "vs-ov", "vs-ncnn"},
            "cu121": {
                "vs-mlrt-models", "vs-ov", "vs-ncnn", "vs-cublas-cu121", "vs-cudnn-cu121",
                "vs-tensorrt-core-cu121", "vs-tensorrt-builder-cu121", "vs-trtexec-cu121", "vs-trt-cu121",
            },
            "cu129": {
                "vs-mlrt-models", "vs-ov", "vs-ncnn", "vs-tensorrt-core-cu129",
                "vs-tensorrt-builder-cu129-base", "vs-tensorrt-builder-cu129-modern",
                "vs-trtexec-cu129", "vs-trt-cu129", "vs-tensorrt-rtx-cu129", "vs-trt-rtx-cu129",
            },
        }
        for entry, required in expected.items():
            data = tomllib.loads((entries / entry / "pyproject.toml").read_text(encoding="utf-8"))
            dependencies = data["project"]["dependencies"]
            internal = {value.split("==", 1)[0] for value in dependencies if value.startswith("vs-")}
            self.assertEqual(internal, required)
            self.assertTrue(all("==16.2.2" in value for value in dependencies if value.startswith("vs-")))
            self.assertNotIn("vs-mlrt-generic", internal)
            self.assertEqual(data["project"]["scripts"]["rm_vsmlrt"], "rm_vsmlrt.cli:console_main")


if __name__ == "__main__":
    unittest.main()
