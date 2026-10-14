"""DFTTest backend priority across the complete pinned Collection runtime."""
from __future__ import annotations

import ast
import itertools
import json
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock
import warnings


ROOT = Path(__file__).resolve().parents[1]
MODULES = ('havsfunc', 'muvsfunc', 'fvsfunc')
SELECTOR = '_dfttest_preferring_dfttestvk'
BACKENDS = ('dfttest2_nvrtc', 'dfttest2_cpu', 'dfttest2_cuda')


def load_selector(module, core, importer):
    path = ROOT / 'modules' / module / (module + '.py')
    with warnings.catch_warnings():
        warnings.simplefilter('ignore', SyntaxWarning)
        tree = ast.parse(path.read_text(encoding='utf-8'))
    functions = [node for node in tree.body if isinstance(node, ast.FunctionDef)
                 and node.name in {'_get_dfttest2', SELECTOR}]
    compiled = ast.Module(body=[ast.ImportFrom(module='__future__',
                          names=[ast.alias(name='annotations')], level=0), *functions],
                          type_ignores=[])
    sentinel = object()
    env = dict(core=core, importlib=SimpleNamespace(import_module=importer),
               _DFTTEST2_UNSET=sentinel, _dfttest2_module=sentinel)
    ast.fix_missing_locations(compiled)
    exec(compile(compiled, str(path), 'exec'), env)
    return env[SELECTOR]


class DFTTestRoutingTests(unittest.TestCase):
    def exercise(self, module, available=(), wrapper=True):
        core = SimpleNamespace(**{name: object() for name in available})
        vk = Mock(return_value='vk')
        if 'dfttestvk' in available:
            core.dfttestvk = SimpleNamespace(DFTTest=vk)
        classic = Mock(return_value='classic')
        clip = SimpleNamespace(dfttest=SimpleNamespace(DFTTest=classic))
        dfttest2 = SimpleNamespace(Backend=SimpleNamespace(NVRTC='nvrtc', CPU='cpu', cuFFT='cufft'),
                                  DFTTest=Mock(return_value='dfttest2'))
        importer = Mock(return_value=dfttest2) if wrapper else Mock(side_effect=ModuleNotFoundError('dfttest2'))
        selector = load_selector(module, core, importer)
        return selector, clip, vk, dfttest2.DFTTest, classic, importer

    def test_vulkan_precedes_every_dfttest2_backend_for_all_windows(self):
        for module, wrapper, shape in itertools.product(MODULES, (True, False),
                ({}, {'sbsize': 16, 'tbsize': 1}, {'sbsize': 8, 'tbsize': 3},
                 {'sbsize': 16, 'tbsize': 9})):
            with self.subTest(module=module, wrapper=wrapper, shape=shape):
                select, clip, vk, dft2, classic, importer = self.exercise(
                    module, ('dfttestvk', *BACKENDS), wrapper)
                self.assertEqual(select(clip, **shape), 'vk')
                vk.assert_called_once_with(clip, **shape)
                importer.assert_not_called()
                dft2.assert_not_called()
                classic.assert_not_called()

    def test_vulkan_forwards_parameters_and_omits_none(self):
        params = dict(sigma=0, sigma2=3.5, sbsize=8, sosize=6, tbsize=5,
                      twin=0, zmean=False, slocation=[0.0, 4.0, 1.0, 15.0],
                      planes=[0, 2], num_streams=4, device_index=0)
        for module in MODULES:
            with self.subTest(module=module):
                select, clip, vk, _, _, _ = self.exercise(module, ('dfttestvk',))
                select(clip, **params, ssystem=None, sbeta=None)
                vk.assert_called_once_with(clip, **params)

    def test_absent_vulkan_preserves_the_complete_window_policy(self):
        shapes = [({}, True), ({'sbsize': None, 'tbsize': None}, True)]
        shapes += [(dict(sbsize=16, tbsize=size), True) for size in (1, 3, 5, 7)]
        shapes += [(dict(sbsize=8, tbsize=3), False), (dict(sbsize=16, tbsize=9), False)]
        for module, present, (shape, cpu_shape) in itertools.product(
                MODULES, itertools.product((False, True), repeat=3), shapes):
            with self.subTest(module=module, present=present, shape=shape):
                available = [name for name, exists in zip(BACKENDS, present) if exists]
                select, clip, vk, dft2, classic, importer = self.exercise(module, available)
                backend = ('nvrtc' if present[0] else 'cpu' if present[1] else None) if cpu_shape else ('cufft' if present[2] else None)
                params = {key: value for key, value in shape.items() if value is not None}
                self.assertEqual(select(clip, **shape), 'dfttest2' if backend else 'classic')
                importer.assert_called_once_with('dfttest2')
                vk.assert_not_called()
                if backend:
                    dft2.assert_called_once_with(clip, backend=backend, **params)
                    classic.assert_not_called()
                else:
                    classic.assert_called_once_with(**params)
                    dft2.assert_not_called()

    def test_missing_dfttest2_wrapper_uses_classic(self):
        for module in MODULES:
            with self.subTest(module=module):
                select, clip, _, dft2, classic, _ = self.exercise(module, BACKENDS, wrapper=False)
                self.assertEqual(select(clip, sigma=5, planes=None), 'classic')
                classic.assert_called_once_with(sigma=5)
                dft2.assert_not_called()

    def test_vulkan_construction_and_frame_errors_propagate(self):
        for module, construction in itertools.product(MODULES, (True, False)):
            with self.subTest(module=module, construction=construction):
                select, clip, vk, dft2, classic, importer = self.exercise(module, ('dfttestvk', *BACKENDS))
                error = RuntimeError('Vulkan failure')
                if construction:
                    vk.side_effect = error
                else:
                    vk.return_value = SimpleNamespace(get_frame=Mock(side_effect=error))
                with self.assertRaises(RuntimeError) as caught:
                    result = select(clip)
                    if not construction:
                        result.get_frame(0)
                self.assertIs(caught.exception, error)
                importer.assert_not_called()
                dft2.assert_not_called()
                classic.assert_not_called()

    def test_all_collection_native_calls_pass_through_the_policy(self):
        registry = json.loads((ROOT / 'modules/collection.json').read_text(encoding='utf-8'))
        callers = set()
        for item in registry['components']:
            for relative in item['runtime_sha256']:
                if not relative.endswith('.py'):
                    continue
                path = ROOT / item['path'] / relative
                with warnings.catch_warnings():
                    warnings.simplefilter('ignore', SyntaxWarning)
                    tree = ast.parse(path.read_text(encoding='utf-8'))
                selectors = [node for node in tree.body if isinstance(node, ast.FunctionDef)
                             and node.name == SELECTOR]
                permitted = {id(node) for selector in selectors for node in ast.walk(selector)}
                for node in ast.walk(tree):
                    if not isinstance(node, ast.Call):
                        continue
                    if isinstance(node.func, ast.Attribute) and node.func.attr == 'DFTTest':
                        self.assertIn(id(node), permitted, f'{path}:{node.lineno} bypasses the backend policy')
                    elif isinstance(node.func, ast.Name) and node.func.id == SELECTOR:
                        callers.add(item['module'])
        self.assertEqual(callers, set(MODULES))


if __name__ == '__main__':
    unittest.main()
