"""EEDI3 backend policy and lazy-error fallback, without native GPU dependencies."""
from __future__ import annotations
import ast
from pathlib import Path
from threading import Lock
from types import SimpleNamespace
import unittest
import warnings


class FilterError(Exception):
    pass


class Node:
    format = SimpleNamespace(num_planes=1)
    def __init__(self, backend='template', failures=(), callback=None):
        self.backend, self.failures, self.callback = backend, failures, callback
    def get_frame(self, n):
        if self.callback:
            return self.callback(n, None)
        if n in self.failures:
            raise FilterError(f'{self.backend} failed at {n}')
        return (self.backend, n)


def load_dispatcher(module, core):
    paths = {'havsfunc': 'modules/havsfunc/havsfunc.py',
             'vstaambk': 'modules/vstaambk/vsTAAmbk.py',
             'yvsfunc': 'modules/yvsfunc/yvsfunc/resample.py'}
    path = Path(__file__).parents[1] / paths[module]
    tree = ast.parse(path.read_text(encoding='utf-8'))
    nodes = [n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.ClassDef))
             and n.name in {'_normalize_aa_core', '_filter_kwargs', '_EEDI3Dispatcher'}]
    compiled = ast.Module(body=[ast.ImportFrom(module='__future__', names=[ast.alias(name='annotations')], level=0), *nodes], type_ignores=[])
    ast.fix_missing_locations(compiled)
    env = dict(vs=SimpleNamespace(core=core, Error=FilterError), MODULE_NAME='vsTAAmbk',
               Lock=Lock, warnings=warnings,
               _AA_BACKEND_EXCEPTIONS=(AttributeError, TypeError, RuntimeError, FilterError))
    exec(compile(compiled, str(path), 'exec'), env)
    return env['_EEDI3Dispatcher']


class EEDI3RoutingTests(unittest.TestCase):
    modules = ['havsfunc', 'vstaambk', 'yvsfunc']

    def exercise(self, module, init_failures=(), frame_failures=None, **options):
        calls = []
        core = SimpleNamespace()
        for name in ['eedi3vk2', 'vszipcl', 'vszip']:
            def native(clip, name=name, **kwargs):
                calls.append((name, kwargs))
                if name in init_failures:
                    raise FilterError(f'{name} unavailable')
                return Node(name, (frame_failures or {}).get(name, ()))
            setattr(core, name, SimpleNamespace(EEDI3=native))
        core.std = SimpleNamespace(BlankClip=lambda **kwargs: Node(),
                                   ModifyFrame=lambda template, clips, callback: Node(callback=callback))
        dispatcher = load_dispatcher(module, core)(**options)
        return dispatcher, calls

    def test_default_is_cpu_and_ignores_legacy_negative_device(self):
        for module in self.modules:
            with self.subTest(module=module):
                dispatch, calls = self.exercise(module, device=-1)
                out = dispatch(Node(), field=1, dh=True)
                self.assertEqual(out.get_frame(0), ('vszip', 0))
                self.assertEqual([name for name, _ in calls], ['vszip'])

    def test_gpu_mode_uses_vulkan_and_normalizes_negative_index(self):
        for module in self.modules:
            with self.subTest(module=module):
                dispatch, calls = self.exercise(module, opencl=True, device=-1)
                self.assertEqual(dispatch(Node(), field=1).get_frame(0), ('eedi3vk2', 0))
                self.assertEqual([name for name, _ in calls], ['eedi3vk2'])
                self.assertNotIn('device_index', calls[0][1])

    def test_gpu_init_failure_falls_back_only_to_opencl(self):
        for module in self.modules:
            with self.subTest(module=module), warnings.catch_warnings(record=True):
                dispatch, calls = self.exercise(module, opencl=True, init_failures=['eedi3vk2'])
                self.assertEqual(dispatch(Node(), field=1).get_frame(0), ('vszipcl', 0))
                self.assertEqual([name for name, _ in calls], ['eedi3vk2', 'vszipcl'])
                self.assertEqual(dispatch.selected, 'vszipcl')

    def test_late_frame_error_switches_to_opencl_and_stays_there(self):
        for module in self.modules:
            with self.subTest(module=module), warnings.catch_warnings(record=True):
                dispatch, calls = self.exercise(module, opencl=True, frame_failures={'eedi3vk2': [1]})
                out = dispatch(Node(), field=1)
                self.assertEqual(out.get_frame(0), ('eedi3vk2', 0))
                self.assertEqual(out.get_frame(1), ('vszipcl', 1))
                self.assertEqual(out.get_frame(2), ('vszipcl', 2))
                self.assertEqual([name for name, _ in calls], ['eedi3vk2', 'vszipcl'])
                self.assertEqual(dispatch.selected, 'vszipcl')

    def test_no_cpu_fallback_when_both_gpu_backends_fail(self):
        for module in self.modules:
            with self.subTest(module=module):
                dispatch, calls = self.exercise(module, opencl=True, init_failures=['eedi3vk2', 'vszipcl'])
                with self.assertRaises(FilterError):
                    dispatch(Node(), field=1)
                self.assertEqual([name for name, _ in calls], ['eedi3vk2', 'vszipcl'])

    def test_explicit_cpu_or_opencl_is_fixed(self):
        for module in self.modules:
            for preferred, expected in [('cpu', 'vszip'), ('vszip', 'vszip'), ('vszipcl', 'vszipcl')]:
                with self.subTest(module=module, preferred=preferred):
                    dispatch, calls = self.exercise(module, preferred=preferred, opencl=True)
                    self.assertEqual(dispatch(Node(), field=1).get_frame(0), (expected, 0))
                    self.assertEqual([name for name, _ in calls], [expected])

    def test_eedi3vk_alias_and_gpu_parameter_forwarding(self):
        for module in self.modules:
            with self.subTest(module=module):
                dispatch, calls = self.exercise(module, preferred='eedi3vk', device=0)
                dispatch(Node(), field=1, num_streams=4, hp=True, vcheck=3).get_frame(0)
                self.assertEqual(calls[0], ('eedi3vk2', dict(field=1, dh=False, num_streams=4,
                                                           hp=True, vcheck=3, device_index=0)))


if __name__ == '__main__':
    unittest.main()
