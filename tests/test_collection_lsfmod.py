"""Run real std expressions to regress LSFmod's integer/float thresholds."""
from __future__ import annotations
import ast
import importlib.util
import math
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


def load_functions(relative, names, core, vs):
    path = ROOT / 'modules' / relative
    tree = ast.parse(path.read_text(encoding='utf-8'))
    nodes = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in names]
    compiled = ast.Module(body=[ast.ImportFrom(module='__future__',
                          names=[ast.alias(name='annotations')], level=0), *nodes], type_ignores=[])
    import functools
    env = dict(core=core, vs=vs, math=math, functools=functools, partial=functools.partial,
               _dfttest_preferring_dfttestvk=lambda clip, **kwargs: clip)
    ast.fix_missing_locations(compiled)
    exec(compile(compiled, str(path), 'exec'), env)
    return env


@unittest.skipUnless(importlib.util.find_spec('vapoursynth'), 'Requires native VapourSynth std filters')
class LSFmodThresholdTests(unittest.TestCase):
    def test_dfttest_preblur_matches_havsfunc_for_integer_and_float_input(self):
        import vapoursynth as vs
        core = vs.core
        muf = load_functions('muvsfunc/muvsfunc.py', {'haf_LSFmod','haf_Clamp','haf_cround','scale'}, core, vs)
        haf = load_functions('havsfunc/havsfunc.py', {'LSFmod','mt_clamp','cround','scale'}, core, vs)
        for fmt, color in ((vs.GRAY8,96),(vs.GRAY16,24672),(vs.GRAYS,0.375)):
            for preblur in (-1,3):
                with self.subTest(format=fmt,preblur=preblur):
                    clip = core.std.BlankClip(width=32,height=24,length=3,format=fmt,color=[color])
                    params = dict(preblur=preblur,Smode=1,Smethod=1,ss_x=1,ss_y=1,
                                  Lmode=1,soft=0,soothe=False,secure=True,edgemaskHQ=False)
                    actual = muf['haf_LSFmod'](clip,**params)
                    expected = haf['LSFmod'](clip,**params)
                    for n in (0,1,2):
                        self.assertEqual(bytes(actual.get_frame(n)[0]),bytes(expected.get_frame(n)[0]))


if __name__ == '__main__':
    unittest.main()
