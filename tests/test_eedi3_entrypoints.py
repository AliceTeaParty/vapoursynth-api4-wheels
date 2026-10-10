"""Backend controls must survive high-level wrapper boundaries."""
from __future__ import annotations
import ast
from pathlib import Path
from types import SimpleNamespace
import unittest

ROOT = Path(__file__).parents[1]

class ObservedQTGMC(Exception):
    pass

class Clip:
    width = 128
    height = 64

def definitions(path, names, env):
    tree = ast.parse((ROOT / path).read_text(encoding='utf-8'))
    nodes = [n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.ClassDef)) and n.name in names]
    module = ast.Module(body=[ast.ImportFrom(module='__future__', names=[ast.alias(name='annotations')], level=0), *nodes], type_ignores=[])
    ast.fix_missing_locations(module)
    exec(compile(module, str(ROOT / path), 'exec'), env)
    return env


class EntryPointTests(unittest.TestCase):
    def test_credits_helpers_forward_backend_and_qtgmc_controls(self):
        calls = []
        def qtgmc(clip, **kwargs):
            calls.append(kwargs)
            raise ObservedQTGMC()
        names = ['dec_txt60mc', 'ivtc_txt30mc', 'ivtc_txt60mc']
        env = definitions('modules/havsfunc/havsfunc.py', names,
                          dict(vs=SimpleNamespace(VideoNode=Clip), QTGMC=qtgmc))
        for name in names:
            with self.subTest(entry=name), self.assertRaises(ObservedQTGMC):
                env[name](Clip(), frame_ref=0, tff=True, opencl=True, device=0,
                          eedi3_core='eedi3vk2', eedi3_args={'num_streams': 4},
                          qtgmc_args={'EdiMode': 'EEDI3'})
            self.assertTrue(calls[-1]['opencl'])
            self.assertEqual(calls[-1]['eedi3_core'], 'eedi3vk2')
            self.assertEqual(calls[-1]['eedi3_args'], {'num_streams': 4})
            self.assertEqual(calls[-1]['EdiMode'], 'EEDI3')

    def test_overlayinter_forwards_backend_and_qtgmc_controls(self):
        calls = []
        def qtgmc(clip, **kwargs):
            calls.append(kwargs)
            raise ObservedQTGMC()
        haf = SimpleNamespace(QTGMC=qtgmc)
        core = SimpleNamespace(std=SimpleNamespace(CropRel=lambda clip, *args: clip))
        env = definitions('modules/fvsfunc/fvsfunc.py', {'OverlayInter'}, dict(core=core))
        from unittest.mock import patch
        with patch.dict('sys.modules', havsfunc=haf), self.assertRaises(ObservedQTGMC):
            env['OverlayInter'](Clip(), pattern=0, tff=True, opencl=True, device=0,
                                eedi3_core='vszipcl', eedi3_args={'hp': True},
                                qtgmc_args={'EdiMode': 'EEDI3'})
        self.assertTrue(calls[0]['opencl'])
        self.assertEqual(calls[0]['eedi3_core'], 'vszipcl')
        self.assertEqual(calls[0]['eedi3_args'], {'hp': True})
        self.assertEqual(calls[0]['EdiMode'], 'EEDI3')

    def test_taambk_preserves_native_options_and_frame_layout(self):
        class Parent:
            def __init__(self, *args, **kwargs):
                pass
        class Dispatcher:
            _allowed = {'eedi3vk2': {'hp', 'vcheck', 'num_streams', 'field', 'dh'}}
            def __init__(self, preferred, device, *, opencl):
                self.preferred, self.device, self.opencl = preferred, device, opencl
        env = definitions('modules/vstaambk/vsTAAmbk.py', {'AAEedi3'},
                          dict(AAParent=Parent, _EEDI3Dispatcher=Dispatcher))
        obj = env['AAEedi3'](Clip(), opencl=True, opencl_device=-1, eedi3_core='eedi3vk2',
                             num_streams=4, hp=True, eedi3_args={'vcheck': 3, 'field': 0, 'dh': False})
        self.assertTrue(obj.eedi3.opencl)
        self.assertEqual(obj.eedi3.preferred, 'eedi3vk2')
        self.assertEqual(obj.eedi3_args['num_streams'], 4)
        self.assertTrue(obj.eedi3_args['hp'])
        self.assertEqual(obj.eedi3_args['vcheck'], 3)
        self.assertNotIn('field', obj.eedi3_args)
        self.assertNotIn('dh', obj.eedi3_args)

    def test_yvsfunc_legacy_cl_factory_uses_gpu_policy(self):
        class Dispatcher:
            def __init__(self, preferred, device, kwargs, *, opencl):
                self.preferred, self.opencl, self.kwargs = preferred, opencl, kwargs
        env = definitions('modules/yvsfunc/yvsfunc/resample.py', {'get_eedi3', 'get_eedi3cl'},
                          dict(_EEDI3Dispatcher=Dispatcher))
        default = env['get_eedi3']()
        gpu = env['get_eedi3cl'](num_streams=4)
        self.assertFalse(default.opencl)
        self.assertTrue(gpu.opencl)
        self.assertIsNone(gpu.preferred)
        self.assertEqual(gpu.kwargs['num_streams'], 4)

    def test_yvsfunc_backend_arguments_are_resolved_or_rejected_explicitly(self):
        calls = []
        token = object()
        def factory(**kwargs):
            calls.append(kwargs)
            return token
        env = definitions('modules/yvsfunc/yvsfunc/resample.py', {'_resolve_eedi3'}, dict(get_eedi3=factory))
        resolve = env['_resolve_eedi3']
        self.assertIsNone(resolve(None, False, None, None, None))
        self.assertIs(resolve(None, True, None, 0, {'num_streams': 4}), token)
        self.assertEqual(calls[0], dict(opencl=True, eedi3_core=None, device=0, num_streams=4))
        with self.assertRaises(ValueError):
            resolve(token, True, None, 0, None)


if __name__ == '__main__':
    unittest.main()
