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

| Upstream | Package | Version | Platforms | Status |
| --- | --- | --- | --- | --- |
| [quietvoid/vs-nlq](https://github.com/quietvoid/vs-nlq) | `vs-nlq` | `1.2.0` | Windows/Linux x86_64 | Published and verified |
| [HomeOfVapourSynthEvolution/VapourSynth-NNEDI3CL](https://github.com/HomeOfVapourSynthEvolution/VapourSynth-NNEDI3CL) | `vapoursynth-nnedi3cl` | `8.1` | Windows/Linux x86_64 | Published and verified |
| [dubhatervapoursynth/vapoursynth-smoothuv](https://github.com/dubhatervapoursynth/vapoursynth-smoothuv) | `vapoursynth-smoothuv` | `3.1` | Windows/Linux x86_64 | Published and verified |
| [HomeOfVapourSynthEvolution/VapourSynth-DFTTest](https://github.com/HomeOfVapourSynthEvolution/VapourSynth-DFTTest) | `vapoursynth-dfttest` | `1.1` | Windows/Linux x86_64 | Published and verified |
| [Khanattila/KNLMeansCL](https://github.com/Khanattila/KNLMeansCL) | `vapoursynth-knlm` | `1.1.2` | Windows/Linux x86_64 | Published and verified |
| [HomeOfVapourSynthEvolution/VapourSynth-Retinex](https://github.com/HomeOfVapourSynthEvolution/VapourSynth-Retinex) | `vapoursynth-retinex` | `4.1` | Windows/Linux x86_64 | Published and verified |
| [dubhatervapoursynth/vapoursynth-tcomb](https://github.com/dubhatervapoursynth/vapoursynth-tcomb) | `vapoursynth-tcomb` | `4.2` | Windows/Linux x86_64 | Published and verified |
| [HomeOfVapourSynthEvolution/VapourSynth-TCanny](https://github.com/HomeOfVapourSynthEvolution/VapourSynth-TCanny) | `vapoursynth-tcanny` | `14.1` | Windows/Linux x86_64 | Migration in progress |

See [PACKAGES.md](PACKAGES.md) for the complete naming plan and version audit.

## Repository layout

- `plugins/<name>`: upstream subtree plus this project's squashed patch
- `.github/workflows/package-<name>.yml`: build, test, and release workflow
- `scripts/generate_index.py`: GitHub Release to PEP 503 index generator
- `docs/reflections/<name>.md`: lessons recorded after each verified migration

## Updating a subtree

Each plugin records its upstream repository and revision in its reflection
document. Updates must be pulled from the original upstream, never from the
former fork:

```console
git subtree pull --prefix plugins/vs-nlq \
  https://github.com/quietvoid/vs-nlq.git main --squash
```

Build logic must continue to come from the already verified fork workflow.
Only monorepo path handling and release/index publishing may be adapted.
