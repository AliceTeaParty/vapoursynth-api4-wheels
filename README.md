# nnedi3_resample

A VapourSynth script for easy resizing using nnedi3/znedi3/nnedi3cl with center alignment and correct chroma placement.

It can do scaling, color space conversion, etc.

## Requirements

- [znedi3](https://github.com/sekrit-twc/znedi3) / [nnedi3](https://github.com/dubhater/vapoursynth-nnedi3) / [nnedi3cl](https://github.com/HomeOfVapourSynthEvolution/VapourSynth-NNEDI3CL)
- [fmtconv](https://github.com/EleonoreMizo/fmtconv)
- [mvsfunc](https://github.com/HomeOfVapourSynthEvolution/mvsfunc)

## Installation

For Windows users, put nnedi3_resample.py into
- VapourSynth installed for all users: `<python folder>\Lib\site-packages`
- VapourSynth installed for current user: `%AppData%\Python\Python<version>\site-packages`

## Note

1. Internally, nnedi3_resample always processes in 16-bit integer. The output format can be specified by `csp` with Format id (default is the same as input).
2. To speed up the processing, it is recommended to input 16-bit clip to avoid internal depth conversions.

## Example

Double the width and height of a clip.

Optional mode='nnedi3cl' to force using NNEDI3CL plugin.

```python
import vapoursynth as vs
from vapoursynth import core
from nnedi3_resample import nnedi3_resample

clip = XXXSource()
clip = nnedi3_resample(clip, clip.width * 2, clip.height * 2, mode='nnedi3cl')

clip.set_output()
```

## ChangeLog

1. Add new option `mode`, default value is None, which will automatically choose the available plugin (from top to bottom priority):
    - `znedi3`, faster CPU implementation
    - `nnedi3`, original CPU implementation
    - `nnedi3cl`, OpenCL implementation, with a new option `device` to specify the desired device (refer to )
2. Change how to import core because `get_core` is deprecated.
3. Remove `YCOCG` and `COMPAT`, deprecated in VapourSynth API4.
