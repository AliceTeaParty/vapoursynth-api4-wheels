"""Ensure hardware validation cannot pass through a software or wrong device."""
import importlib.util
from pathlib import Path
from types import SimpleNamespace
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('hardware_device', ROOT / 'packaging/vapoursynth-krigbilateralvk/tools/hardware_device.py')
hardware = importlib.util.module_from_spec(spec)
spec.loader.exec_module(hardware)


def device(index, name, kind, version, usable, uuid):
    return {'index': index, 'name': name, 'type': kind, 'api_version': version,
            'usable': usable, 'uuid': uuid, 'device_memory': 1024, 'reason': ''}


class HardwareValidationTests(unittest.TestCase):
    def test_vulkan_14_software_is_rejected(self):
        core = SimpleNamespace(vulkan_devices=[device(0, 'llvmpipe', 'cpu', [1, 4, 305], True, 'cpu')])
        with self.assertRaisesRegex(RuntimeError, 'No usable Vulkan 1.4 hardware'):
            hardware.select_hardware_device(core)

    def test_vulkan_12_hardware_is_rejected(self):
        core = SimpleNamespace(vulkan_devices=[device(0, 'Dozen NVIDIA', 'discrete', [1, 2, 305], True, 'gpu')])
        with self.assertRaisesRegex(RuntimeError, 'No usable Vulkan 1.4 hardware'):
            hardware.select_hardware_device(core)

    def test_hardware_is_selected_when_software_is_also_available(self):
        gpu = device(1, 'NVIDIA', 'discrete', [1, 4, 351], True, 'gpu')
        core = SimpleNamespace(vulkan_devices=[device(0, 'llvmpipe', 'cpu', [1, 4, 305], True, 'cpu'), gpu],
                               vulkan_device_info={'uuid': 'cpu'})
        def select(index):
            self.assertEqual(index, 1)
            core.vulkan_device_info = {'uuid': 'gpu'}
        core.set_vulkan_device = select
        selected = hardware.select_hardware_device(core)
        self.assertEqual(selected['index'], 1)
        self.assertNotIn('uuid', selected)

    def test_active_device_must_match_the_selected_hardware(self):
        core = SimpleNamespace(vulkan_devices=[device(1, 'NVIDIA', 'discrete', [1, 4, 351], True, 'gpu')],
                               vulkan_device_info={'uuid': 'cpu'}, set_vulkan_device=lambda index: None)
        with self.assertRaisesRegex(RuntimeError, 'active Vulkan device does not match'):
            hardware.select_hardware_device(core)

    def test_explicit_device_can_select_a_different_physical_gpu(self):
        core = SimpleNamespace(vulkan_devices=[device(0, 'GPU0', 'discrete', [1, 4, 312], True, 'gpu0'),
                                               device(6, 'GPU6', 'discrete', [1, 4, 312], True, 'gpu6')],
                               vulkan_device_info={'uuid': 'gpu0'})
        def select(index):
            self.assertEqual(index, 6)
            core.vulkan_device_info = {'uuid': 'gpu6'}
        core.set_vulkan_device = select
        self.assertEqual(hardware.select_hardware_device(core, 6)['index'], 6)

    def test_explicit_software_device_is_rejected_even_when_hardware_exists(self):
        core = SimpleNamespace(vulkan_devices=[device(0, 'llvmpipe', 'cpu', [1, 4, 312], True, 'cpu'),
                                               device(6, 'NVIDIA', 'discrete', [1, 4, 312], True, 'gpu')])
        with self.assertRaisesRegex(RuntimeError, 'not a usable Vulkan 1.4 hardware'):
            hardware.select_hardware_device(core, 0)


if __name__ == '__main__':
    unittest.main()
