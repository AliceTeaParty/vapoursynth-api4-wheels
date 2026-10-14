"""Preserve RGVS calls and provide the documented zsmooth equivalents."""
from __future__ import annotations
import ast
import json
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock
import warnings

ROOT = Path(__file__).resolve().parents[1]
PATHS = ('havsfunc/havsfunc.py', 'csmod/CSMOD.py', 'muvsfunc/muvsfunc.py',
         'fvsfunc/fvsfunc.py', 'sdering-fix/sdering_fix.py', 'vstaambk/vsTAAmbk.py')


def load_proxy(relative, core):
    path = ROOT / 'modules' / relative
    with warnings.catch_warnings():
        warnings.simplefilter('ignore', SyntaxWarning)
        tree = ast.parse(path.read_text(encoding='utf-8'))
    node = next(n for n in tree.body if isinstance(n, (ast.ClassDef,ast.FunctionDef))
                and n.name in ('_CoreProxy','_get_rgvs_namespace'))
    compiled = ast.Module(body=[ast.ImportFrom(module='__future__',
                          names=[ast.alias(name='annotations')], level=0), node], type_ignores=[])
    env = {'vs': SimpleNamespace(core=core)}
    ast.fix_missing_locations(compiled)
    exec(compile(compiled, str(path), 'exec'), env)
    if '_CoreProxy' in env:
        return env['_CoreProxy']()
    return SimpleNamespace(rgvs=env['_get_rgvs_namespace'](),std=getattr(core,'std',None))


class RGVSCompatibilityTests(unittest.TestCase):
    def test_priority_and_native_argument_forwarding_for_all_filters(self):
        for path in PATHS:
            for present in (True, False):
                with self.subTest(path=path, rgvs=present):
                    rgvs = SimpleNamespace(**{name: Mock(return_value='rgvs') for name in ('RemoveGrain','Repair','VerticalCleaner')})
                    zsmooth = SimpleNamespace(**{name: Mock(return_value='zsmooth') for name in ('RemoveGrain','Repair','VerticalCleaner')})
                    core = SimpleNamespace(zsmooth=zsmooth, std=object())
                    if present:
                        core.rgvs = rgvs
                    proxy = load_proxy(path, core)
                    clip, reference = object(), object()
                    for name, args, mode in (('RemoveGrain',(clip,),[11,0]),
                                             ('Repair',(clip,reference),[13,0]),
                                             ('VerticalCleaner',(clip,),[1,0])):
                        result = getattr(proxy.rgvs, name)(*args, mode=mode)
                        chosen, other = (rgvs,zsmooth) if present else (zsmooth,rgvs)
                        self.assertEqual(result, 'rgvs' if present else 'zsmooth')
                        getattr(chosen,name).assert_called_once_with(*args, mode=mode)
                        getattr(other,name).assert_not_called()
                    self.assertIs(proxy.std, core.std)

    def test_missing_plugins_and_selected_filter_errors_remain_visible(self):
        for path in PATHS:
            with self.subTest(path=path):
                with self.assertRaises(AttributeError):
                    load_proxy(path, SimpleNamespace()).rgvs
                native = Mock(side_effect=RuntimeError('selected RGVS failure'))
                fallback = Mock()
                proxy = load_proxy(path, SimpleNamespace(rgvs=SimpleNamespace(Repair=native),
                                   zsmooth=SimpleNamespace(Repair=fallback)))
                with self.assertRaisesRegex(RuntimeError, 'selected RGVS failure'):
                    proxy.rgvs.Repair(object(), object(), mode=1)
                fallback.assert_not_called()

    def test_every_collection_rgvs_access_uses_a_core_proxy(self):
        registry = json.loads((ROOT/'modules/collection.json').read_text(encoding='utf-8'))
        users = set()
        for item in registry['components']:
            for relative in item['runtime_sha256']:
                if not relative.endswith('.py'):
                    continue
                path = ROOT/item['path']/relative
                with warnings.catch_warnings():
                    warnings.simplefilter('ignore', SyntaxWarning)
                    tree = ast.parse(path.read_text(encoding='utf-8'))
                for node in ast.walk(tree):
                    if isinstance(node,ast.Attribute) and node.attr == 'rgvs':
                        users.add(item['module'])
                        if item['module']=='vstaambk':
                            helper = next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='_get_rgvs_namespace')
                            self.assertIn(node,list(ast.walk(helper)),f'{path}:{node.lineno} bypasses the namespace selector')
                            continue
                        self.assertIsInstance(node.value,ast.Name, f'{path}:{node.lineno} bypasses the proxy')
                        self.assertEqual(node.value.id,'core', f'{path}:{node.lineno} bypasses the proxy')
                        self.assertTrue(any(isinstance(n,ast.ClassDef) and n.name=='_CoreProxy' for n in tree.body))
        self.assertEqual(users, {'havsfunc','csmod','muvsfunc','fvsfunc','sdering-fix','vstaambk'})


if __name__ == '__main__':
    unittest.main()
