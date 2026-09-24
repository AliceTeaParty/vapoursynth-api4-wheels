# VapourSynth API4 Wheels

This repository publishes Windows and Linux x86_64 wheels for maintained
VapourSynth API4 ports. Original upstream projects are imported with
`git subtree`; the API4 and packaging work is kept as a separate, squashed
commit for each plugin.

Only Windows and Linux x86_64 are supported. macOS and ARM wheels are not
published.

## Install

The package index is hosted on GitHub Pages:

```console
python -m pip install \
  --extra-index-url https://aliceteaparty.github.io/vapoursynth-api4-wheels/simple/ \
  vs-nlq
```

Packages still need their normal Python dependencies from PyPI, which is why
the project index is supplied with `--extra-index-url`.

## Packages

| Upstream | Package |
| --- | --- |
| [quietvoid/vs-nlq](https://github.com/quietvoid/vs-nlq) | `vs-nlq` |
| [HomeOfVapourSynthEvolution/VapourSynth-NNEDI3CL](https://github.com/HomeOfVapourSynthEvolution/VapourSynth-NNEDI3CL) | `vapoursynth-nnedi3cl` |
| [dubhatervapoursynth/vapoursynth-smoothuv](https://github.com/dubhatervapoursynth/vapoursynth-smoothuv) | `vapoursynth-smoothuv` |
| [HomeOfVapourSynthEvolution/VapourSynth-DFTTest](https://github.com/HomeOfVapourSynthEvolution/VapourSynth-DFTTest) | `vapoursynth-dfttest` |
| [Khanattila/KNLMeansCL](https://github.com/Khanattila/KNLMeansCL) | `vapoursynth-knlm` |
| [HomeOfVapourSynthEvolution/VapourSynth-Retinex](https://github.com/HomeOfVapourSynthEvolution/VapourSynth-Retinex) | `vapoursynth-retinex` |
| [WolframRhodium/VapourSynth-BM3DCUDA](https://github.com/WolframRhodium/VapourSynth-BM3DCUDA) | `vapoursynth-bm3dcpu` |
| [WolframRhodium/VapourSynth-BM3DCUDA](https://github.com/WolframRhodium/VapourSynth-BM3DCUDA) | `vapoursynth-bm3dcuda-cu121` |
| [WolframRhodium/VapourSynth-BM3DCUDA](https://github.com/WolframRhodium/VapourSynth-BM3DCUDA) | `vapoursynth-bm3dcuda-cu129` |
| [AmusementClub/vs-dfttest2](https://github.com/AmusementClub/vs-dfttest2) | `vapoursynth-dfttest2-cpu` |
| [AmusementClub/vs-dfttest2](https://github.com/AmusementClub/vs-dfttest2) | `vapoursynth-dfttest2-cu121` |
| [AmusementClub/vs-dfttest2](https://github.com/AmusementClub/vs-dfttest2) | `vapoursynth-dfttest2-cu129` |
| [AmusementClub/vs-mlrt](https://github.com/AmusementClub/vs-mlrt) | `vs-mlrt-generic` |
| [AmusementClub/vs-mlrt](https://github.com/AmusementClub/vs-mlrt) | `vs-mlrt-cu121` |
| [AmusementClub/vs-mlrt](https://github.com/AmusementClub/vs-mlrt) | `vs-mlrt-cu129` |
| [dubhatervapoursynth/vapoursynth-tcomb](https://github.com/dubhatervapoursynth/vapoursynth-tcomb) | `vapoursynth-tcomb` |
| [VFR-maniac/VapourSynth-FFT3DFilter](https://github.com/VFR-maniac/VapourSynth-FFT3DFilter) | `vapoursynth-fft3dfilter` |
| [LumeCraft-Labs/vs-cfl](https://github.com/LumeCraft-Labs/vs-cfl) | `vs-cfl` |
| [HomeOfVapourSynthEvolution/VapourSynth-TCanny](https://github.com/HomeOfVapourSynthEvolution/VapourSynth-TCanny) | `vapoursynth-tcanny` |
| [vapoursynth/vs-miscfilters-obsolete](https://github.com/vapoursynth/vs-miscfilters-obsolete) | `vapoursynth-misc` |

## vs-mlrt

Install exactly one vs-mlrt entry package from this index. `generic` provides
NCNN/Vulkan and OpenVINO; the CUDA variants add their respective TensorRT
runtime. The CUDA variants require a compatible NVIDIA driver.

```console
python -m pip install --extra-index-url \
  https://aliceteaparty.github.io/vapoursynth-api4-wheels/simple/ \
  vs-mlrt-generic
```

Replace `vs-mlrt-generic` with `vs-mlrt-cu121` or `vs-mlrt-cu129` as needed.
Do not install more than one entry package in the same environment.

To remove a vs-mlrt installation and its installed component wheels, run:

```console
python -m rm_vsmlrt_helper
```

The helper prints the exact `python -m pip uninstall -y ...` command for the
reviewed installed vs-mlrt distributions. Review and run that command; the
helper does not invoke pip or delete files itself.

## Repository layout

- `plugins/<name>`: upstream subtree plus this project's squashed patch
- `.github/workflows/package-<name>.yml`: build, test, and release workflow
- `scripts/generate_index.py`: GitHub Release to PEP 503 index generator
- `docs/reflections/<name>.md`: lessons recorded after each verified migration

## Licenses

This repository is a collection of independently licensed upstream projects,
not a single relicensed work. Each plugin retains its upstream license in its
own directory. See [LICENSES.md](LICENSES.md) for the upstream audit, license
mapping, and third-party notices.
