# License and Third-Party Notices

This repository aggregates independently licensed VapourSynth plugins. It is
not offered under one repository-wide license. The applicable license for a
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

## Embedded third-party code

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
