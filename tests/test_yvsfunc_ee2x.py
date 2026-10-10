"""Regression checks for the independent NNEDI3 guide in ee2x.

Load the unchanged runtime definitions without requiring native plugins in
packaging CI. Tagged frames make the two filter paths observably distinct.
"""
from __future__ import annotations

import ast
from pathlib import Path
from types import SimpleNamespace
import unittest


class TaggedFrame:
    def __init__(self, tag="source", width=64, height=32):
        self.tag, self.width, self.height = tag, width, height


def load_runtime():
    path = Path(__file__).parents[1] / "modules/yvsfunc/yvsfunc/resample.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    definitions = [node for node in tree.body
                   if isinstance(node, (ast.FunctionDef, ast.ClassDef))
                   and node.name in {"ResClip", "interpolate", "ee2x", "_resolve_eedi3"}]
    module = ast.Module(body=[ast.ImportFrom(module="__future__", names=[ast.alias(name="annotations")], level=0),
                             *definitions], type_ignores=[])
    ast.fix_missing_locations(module)
    def transpose(frame):
        return TaggedFrame(frame.tag, frame.height, frame.width)
    environment = {"vs": SimpleNamespace(VideoNode=TaggedFrame),
                   "core": SimpleNamespace(std=SimpleNamespace(Transpose=transpose))}
    exec(compile(module, str(path), "exec"), environment)
    return environment


class EE2xTests(unittest.TestCase):
    def setUp(self):
        self.runtime = load_runtime()
        self.calls = []

    def nnedi3(self, frame, *, field, dh):
        self.calls.append(("NN", frame.tag, None, field, dh))
        return TaggedFrame(f"NN({frame.tag})", frame.width, frame.height * 2)

    def eedi3(self, frame, *, field, dh, vcheck, sclip):
        self.calls.append(("EE", frame.tag, sclip.tag, field, dh))
        self.assertEqual(vcheck, 3)
        return TaggedFrame(f"EE({frame.tag})", frame.width, frame.height * 2)

    def test_second_pass_uses_independent_nnedi3_guide(self):
        ee, nn = self.runtime["ee2x"](TaggedFrame(), nnedi3=self.nnedi3,
                                      eedi3=self.eedi3, with_nn=True)
        self.assertEqual(nn.clip.tag, "NN(NN(source))")
        self.assertEqual(ee.clip.tag, "EE(EE(source))")
        self.assertEqual([call[2] for call in self.calls if call[0] == "EE"],
                         ["NN(source)", "NN(NN(source))"])
        self.assertEqual((ee.clip.width, ee.clip.height), (128, 64))
        self.assertEqual((nn.clip.width, nn.clip.height), (128, 64))

    def test_default_output_is_eedi3_path(self):
        result = self.runtime["ee2x"](TaggedFrame(), nnedi3=self.nnedi3, eedi3=self.eedi3)
        self.assertIsInstance(result, self.runtime["ResClip"])
        self.assertEqual(result.clip.tag, "EE(EE(source))")

    def test_cropped_resclip_keeps_output_geometry_and_input(self):
        source = self.runtime["ResClip"](TaggedFrame(), sx=0.25, sy=0.125, sw=63.75, sh=31.75)
        ee, nn = self.runtime["ee2x"](source, nnedi3=self.nnedi3,
                                      eedi3=self.eedi3, with_nn=True)
        self.assertEqual((source.sx, source.sy, source.sw, source.sh), (0.25, 0.125, 63.75, 31.75))
        for output in (ee, nn):
            self.assertEqual((output.sx, output.sy, output.sw, output.sh), (0.0, -0.25, 127.5, 63.5))
        self.assertEqual(nn.clip.tag, "NN(NN(source))")
        self.assertEqual(ee.clip.tag, "EE(EE(source))")


if __name__ == "__main__":
    unittest.main()
