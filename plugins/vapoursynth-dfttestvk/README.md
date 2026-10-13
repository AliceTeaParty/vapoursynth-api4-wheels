# vapoursynth-dfttestvk wheels

[DFTTestVK](https://github.com/RyougiKukoc/vapoursynth-dfttestvk#readme) provides
spatial/temporal frequency-domain denoising on VapourSynth's Vulkan device.

## Install

Windows and Linux x86_64 wheels install the plugin and its autoload manifest:

```console
python -m pip install --extra-index-url https://aliceteaparty.github.io/vapoursynth-api4-wheels/simple/ "vapoursynth-dfttestvk==0.1.0"
```

Use the same Python environment as your scripts. Requirements are Python 3.12+,
VapourSynth R81 or newer (`>=81`, with no upper version cap), and a Vulkan 1.4
device/driver. FP16 input also requires `shaderFloat16`. Linux wheels require
glibc 2.28+. macOS and ARM native wheels are not published. Exact versions and
source revisions are recorded in [VERSIONS.md](../../VERSIONS.md).

```python
import vapoursynth as vs

output = vs.core.dfttestvk.DFTTest(source, sigma=8, tbsize=3)
gpu_output = vs.core.dfttestvk.DFTTestGPU(vs.core.std.GPUUpload(source), sigma=8, tbsize=3)
output = vs.core.std.GPUDownload(gpu_output)
```

Input must have constant format and dimensions. Gray, YUV and RGB with 8–16-bit
integer or 16/32-bit float storage are supported. The default block size is 16,
with spatial overlap 12 and three temporal frames. Selected unprocessed planes
and frame properties are preserved. Temporal processing can reuse spatial FFTs;
see the upstream guide for cache controls, parameters and numerical limits.

## Source installation

The named VCS install uses the matching central Release payload by default:

```console
python -m pip install "vapoursynth-dfttestvk @ git+https://github.com/AliceTeaParty/vapoursynth-api4-wheels.git#subdirectory=plugins/vapoursynth-dfttestvk"
```

Version `0.1.0` maps to `vapoursynth-dfttestvk-v0.1.0`. Payloads are
`dfttestvk-windows-x86_64.zip` and `dfttestvk-linux-x86_64.zip`. If the matching
asset is unavailable, the build hook compiles the registered native source.
`DFTTESTVK_FORCE_BUILD=1` selects native compilation; it requires Git, a C++20
compiler and matching SDK headers. The isolated build environment provides
CMake, Ninja and VapourSynth. `CXX`, `DFTTESTVK_VAPOURSYNTH_INCLUDE` and
`DFTTESTVK_VULKAN_HEADERS` can select explicit compiler/header paths.

`DFTTESTVK_PREBUILT_URL` selects a local payload zip or an HTTPS URL for
packaging checks. The hook rejects mismatched version, platform, source commit
and file hashes. Sdists include a standalone source snapshot.

## Maintenance

The upstream implementation remains in the `native/` git submodule;
`source.json` records the reviewed source and header pins. Central wheel
metadata, packaging tools and release workflows live beside it. The central
wheel version equals the original upstream version, just as for KrigBilateral
Vulkan, rksfunc and rkstool. See [DEVELOPMENT.md](../../DEVELOPMENT.md) for source
updates and checkout migration.

The package workflow builds Windows and Linux wheels, checks package layout
and Linux ABI requirements, tests installed-path loading, and verifies a
payload-backed source-install loopback. Linux renders through Mesa Vulkan and
compares the packaged plugin against the upstream independent NumPy oracle.
These checks verify packaging and runtime behavior; hardware execution is
checked separately with `tools/smoke_installed.py --exercise --require-hardware`.

The GPL-3.0-or-later license and third-party notices are included in the wheel
and payload. See [LICENSE](LICENSE) and [THIRD_PARTY.md](THIRD_PARTY.md).
