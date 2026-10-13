# DFTTestVK integration

[DFTTestVK](https://github.com/RyougiKukoc/vapoursynth-dfttestvk#readme) provides
spatial/temporal frequency-domain denoising on VapourSynth's Vulkan device.
It exposes `core.dfttestvk.DFTTest` for CPU clips and `DFTTestGPU` for
GPU-resident graphs. CUDA is not required.

This repository currently registers its source only. **There is no central
DFTTestVK wheel or package workflow yet.** Follow the upstream README for
building and explicitly loading the plugin. Runtime compatibility and the
pinned source version are recorded in [VERSIONS.md](../../VERSIONS.md).

## Source management

The upstream source is the `native/` git submodule. `source.json` records its
reviewed commit and header dependency pin, following the same source-management
layout as KrigBilateral Vulkan. Central integration documentation and future
wheel packaging live beside `native/`; implementation changes stay upstream.
See [DEVELOPMENT.md](../../DEVELOPMENT.md) for checkout and update instructions.

The source retains its GPLv3 license and third-party notices in
[`native/LICENSE`](https://github.com/RyougiKukoc/vapoursynth-dfttestvk/blob/f4760440ff5e360e773a4ebe0bb23f89de801a93/LICENSE)
and [`native/THIRD_PARTY.md`](https://github.com/RyougiKukoc/vapoursynth-dfttestvk/blob/f4760440ff5e360e773a4ebe0bb23f89de801a93/THIRD_PARTY.md).
