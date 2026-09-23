# Package naming and version audit

Package names deliberately omit `-api4` and `-vcs`. CUDA variants name the
runtime compatibility in the distribution name instead of encoding it in the
version or selecting it through a Git tag.

Audited versions are recorded only after their corresponding wheels have been
published and verified. Pending rows have not completed that process.

| Former fork repository | Published package name | Audited version |
| --- | --- | --- |
| `RyougiKukoc/vs-nlq` | `vs-nlq` | `1.2.0` |
| `RyougiKukoc/VapourSynth-NNEDI3CL-api4` | `vapoursynth-nnedi3cl` | `8.1` |
| `RyougiKukoc/vapoursynth-smoothuv-api4` | `vapoursynth-smoothuv` | `3.1` |
| `RyougiKukoc/VapourSynth-DFTTest-api4` | `vapoursynth-dfttest` | `1.1` |
| `RyougiKukoc/VapourSynth-KNLMeansCL-api4` | `vapoursynth-knlm` | `1.1.2` |
| `RyougiKukoc/VapourSynth-Retinex-api4` | `vapoursynth-retinex` | `4.1` |
| `RyougiKukoc/vapoursynth-tcomb-api4` | `vapoursynth-tcomb` | `4.2` |
| `RyougiKukoc/VapourSynth-TCanny-vcs` | `vapoursynth-tcanny` | `14.1` |
| `RyougiKukoc/vs-miscfilters-obsolete-vcs` | `vapoursynth-misc` | `2.1` |
| `RyougiKukoc/VapourSynth-FFT3DFilter-vcs` | `vapoursynth-fft3dfilter` | `2.1` |
| `RyougiKukoc/vs-cfl-vcs` | `vs-cfl` | `1.0.2` |
| `RyougiKukoc/VapourSynth-BM3DCUDA-api4` (`cpu`) | `vapoursynth-bm3dcpu` | `2.16` |
| `RyougiKukoc/VapourSynth-BM3DCUDA-api4` (`cu121`) | `vapoursynth-bm3dcuda-cu121` | `2.16` |
| `RyougiKukoc/VapourSynth-BM3DCUDA-api4` (`cu129`) | `vapoursynth-bm3dcuda-cu129` | `2.16` |
| `RyougiKukoc/vs-dfttest2-api4` (`cpu`) | `vapoursynth-dfttest2-cpu` | `10.2` |
| `RyougiKukoc/vs-dfttest2-api4` (`cu121`) | `vapoursynth-dfttest2-cu121` | `10.2` |
| `RyougiKukoc/vs-dfttest2-api4` (`cu129`) | `vapoursynth-dfttest2-cu129` | `10.2` |
| `RyougiKukoc/vs-mlrt-api4` (`generic`) | `vs-mlrt-generic` | `16.2.2` |
| `RyougiKukoc/vs-mlrt-api4` (`cu121`) | `vs-mlrt-cu121` | `16.2.2` |
| `RyougiKukoc/vs-mlrt-api4` (`cu129`) | `vs-mlrt-cu129` | `16.2.2` |

## Version rules

- Versions must be valid public PEP 440 versions.
- CUDA compatibility belongs in the package name, not the version.
- A package release tag is `<package>-v<version>`, for example
  `vs-nlq-v1.2.0`.
- Rebuilding unchanged source uses a PEP 440 post release rather than silently
  replacing an existing wheel.

## Workflow names

- Package workflow: `Package - <package>`
- Quality workflow: `Quality - <package>`
- Index workflow: `Index - GitHub Pages`
- Build jobs: `Build - Windows x86_64` and `Build - Linux x86_64`
- Runtime verification jobs: `Test - <platform>`
- Release job: `Publish - GitHub Release`
