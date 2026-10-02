# License and Third-Party Notices

This repository aggregates independently maintained VapourSynth plugins and
Python modules. It is not offered under one repository-wide license.
The applicable license for a
plugin is the license file in that plugin directory; its source and binary
packages include the declared license file. This document records the audited
upstream source and license for each subtree.

| Plugin directory | Upstream | License |
| --- | --- | --- |
| `plugins/vs-nlq` | [quietvoid/vs-nlq](https://github.com/quietvoid/vs-nlq) | GPL-3.0 |
| `plugins/vapoursynth-nnedi3cl` | [HomeOfVapourSynthEvolution/VapourSynth-NNEDI3CL](https://github.com/HomeOfVapourSynthEvolution/VapourSynth-NNEDI3CL) | GPL-2.0-or-later |
| `plugins/vapoursynth-smoothuv` | [dubhatervapoursynth/vapoursynth-smoothuv](https://github.com/dubhatervapoursynth/vapoursynth-smoothuv) | GPL-2.0-or-later |
| `plugins/vapoursynth-dfttest` | [HomeOfVapourSynthEvolution/VapourSynth-DFTTest](https://github.com/HomeOfVapourSynthEvolution/VapourSynth-DFTTest) | GPL-3.0 |
| `plugins/vapoursynth-knlm` | [Khanattila/KNLMeansCL](https://github.com/Khanattila/KNLMeansCL) | GPL-3.0-only |
| `plugins/vapoursynth-retinex` | [HomeOfVapourSynthEvolution/VapourSynth-Retinex](https://github.com/HomeOfVapourSynthEvolution/VapourSynth-Retinex) | GPL-3.0-or-later |
| `plugins/vapoursynth-bm3dcuda` | [WolframRhodium/VapourSynth-BM3DCUDA](https://github.com/WolframRhodium/VapourSynth-BM3DCUDA) | GPL-2.0-only |
| `plugins/vapoursynth-dfttest2` | [AmusementClub/vs-dfttest2](https://github.com/AmusementClub/vs-dfttest2) | GPL-3.0 |
| `plugins/vs-mlrt` | [AmusementClub/vs-mlrt](https://github.com/AmusementClub/vs-mlrt) | GPL-3.0-or-later |
| `plugins/vapoursynth-tcomb` | [dubhatervapoursynth/vapoursynth-tcomb](https://github.com/dubhatervapoursynth/vapoursynth-tcomb) | GPL-2.0-or-later |
| `plugins/vapoursynth-fft3dfilter` | [VFR-maniac/VapourSynth-FFT3DFilter](https://github.com/VFR-maniac/VapourSynth-FFT3DFilter) | GPL-2.0-only |
| `plugins/vs-cfl` | [LumeCraft-Labs/vs-cfl](https://github.com/LumeCraft-Labs/vs-cfl) | MIT |
| `plugins/vapoursynth-tcanny` | [HomeOfVapourSynthEvolution/VapourSynth-TCanny](https://github.com/HomeOfVapourSynthEvolution/VapourSynth-TCanny) | GPL-3.0 |
| `plugins/vapoursynth-misc` | [vapoursynth/vs-miscfilters-obsolete](https://github.com/vapoursynth/vs-miscfilters-obsolete) | LGPL-2.1 |

## Python modules

Module source is checked out from the registered upstream during CI; it is not
vendored or relicensed by this repository. The upstream owners have authorized
this module packaging integration. Neither rksfunc nor rkstool currently
declares a project-wide license for its Python code; hosting here does not
introduce a blanket grant for that source. Refer to the original repositories
for applicable notices and permission for other uses.

| Registration | Upstream | Third-party notices |
| --- | --- | --- |
| `modules/rksfunc` | [RyougiKukoc/rksfunc](https://github.com/RyougiKukoc/rksfunc) | `rksfunc/KrigBilateral.glsl`: original attribution to Shiandow, LGPL-3.0-or-later; upstream includes LGPL/GPL texts and `LICENSES.md` in the sdist and wheel |
| `modules/rkstool` | [RyougiKukoc/rkstool](https://github.com/RyougiKukoc/rkstool) | No project-wide license is introduced by the wheel registration |

KrigBilateral's original shader header is preserved. Its referenced source is
[the igv gist](https://gist.github.com/igv/a015fc885d5c22e6891820ad89555637).
The shader-specific LGPL notice does not describe the entire rksfunc project.
The central build checks that the shader and upstream license materials are
present in the wheel; it does not copy a central license over upstream files.

## Collection component sources

The `vs-collection-rk` entry depends on independently packaged component
wheels. Their canonical upstream source trees, source headers and any license
files are retained in `modules/<component>/`. This packaging does not relicense
the collection as one work. See [VERSIONS.md](VERSIONS.md) and each
`provenance.toml` for the complete upstream, gist/fork and Collection chain.

| Component | Retained upstream license material |
| --- | --- |
| havsfunc | Canonical upstream `LICENSE`: Unlicense, recovered from the specified original repository commit |
| getfnative | Canonical upstream `LICENSE`: GNU LGPL version 2.1 text |
| kagefunc | Canonical upstream `LICENSE`: MIT |
| yvsfunc | Canonical upstream `COPYING`: WTFPL version 2 |
| sdering-fix, csmod, nnedi3-resample, nnedi3-rpow2, mvsfunc, muvsfunc, fvsfunc, vstaambk | Original source headers and provenance retained; no separate repository-wide license is assigned here |

Each component wheel includes its available license files and its provenance
record. The entry package owns only its metadata package and dependency pins.

## Embedded plugin third-party code

`vapoursynth-dfttest`, `vapoursynth-dfttest2`, and `vapoursynth-tcanny`
include Agner Fog Vector Class Library sources under Apache-2.0. The original
license files remain in their respective `VCL2` or `vectorclass` directories.

SmoothUV's imported upstream did not include a license file. Its README states
that it is GNU GPL like the Avisynth source. The referenced
[AviSynth-SmoothUV2](https://github.com/Asd-g/AviSynth-SmoothUV2) LICENSE
identifies that source as GPL-2.0-or-later; `plugins/vapoursynth-smoothuv/COPYING`
records this provenance.

The vs-mlrt release packages may additionally contain separately distributed
NVIDIA, Intel OpenVINO, oneTBB, NCNN, and model payloads. Their applicable
vendor terms are not replaced by the GPL license for vs-mlrt source. Release
assembly must retain each vendor's required notices and redistribution terms.
