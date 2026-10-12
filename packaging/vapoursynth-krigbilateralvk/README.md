# vapoursynth-krigbilateralvk wheels

The central wheel wrapper for [KrigBilateral Vulkan](https://github.com/RyougiKukoc/vapoursynth-krigbilateralvk). The plugin source is the git submodule at `plugins/vapoursynth-krigbilateralvk`; `source.json` records the exact upstream commit. Packaging and release workflows are maintained in `AliceTeaParty/vapoursynth-api4-wheels`.

## Install

Windows and Linux x86_64 wheels are published on the central index:

```console
python -m pip install --extra-index-url https://aliceteaparty.github.io/vapoursynth-api4-wheels/simple/ "vapoursynth-krigbilateralvk==0.2.1+alice.1"
```

Use the same Python environment as VapourSynth. The wheel requires VapourSynth R81 (`>=81,<82`) because the plugin's core GPU interface targets that SDK. A Vulkan 1.4 device/driver is needed for rendering; FP16 input additionally requires shaderFloat16. Linux wheels use the `manylinux_2_28_x86_64` runtime floor. macOS and ARM packages are not published.

The wheel installs `vapoursynth/plugins/krigbilateralvk/krigbilateralvk.dll` or `.so`, its autoload manifest and license files. It does not provide or overwrite VapourSynth's Python package initializer. No compiler is needed for an index wheel install.

```python
import vapoursynth as vs

output = vs.core.krigvk.KrigBilateral(source)
# For a resident GPU chain:
gpu_output = vs.core.krigvk.KrigBilateralGPU(vs.core.std.GPUUpload(source))
```

Input is constant-format progressive YUV420 with positive even dimensions and left chroma placement. Output is YUV444 at the same size/type/depth; luma is preserved. Integer depths 8..16 and standard signed-chroma FP16/FP32 are supported. The `reference` option was removed upstream. See the [plugin README](https://github.com/RyougiKukoc/vapoursynth-krigbilateralvk#readme) for API, diagnostics and numerical limits.

## Source installation

This explicit named VCS form uses a matching central Release package by default:

```console
python -m pip install "vapoursynth-krigbilateralvk @ git+https://github.com/AliceTeaParty/vapoursynth-api4-wheels.git#subdirectory=packaging/vapoursynth-krigbilateralvk"
```

Version `0.2.1+alice.1` maps to central tag `vapoursynth-krigbilateralvk-v0.2.1+alice.1`. Assets are `krigbilateralvk-windows-x86_64.zip` and `krigbilateralvk-linux-x86_64.zip`. If the matching platform asset is unavailable, the backend compiles the pinned submodule with CMake and a C++20 compiler. `KRIGVK_FORCE_BUILD=1` explicitly selects that native build. No automatic platform substitution occurs.

For a local checkout:

```console
git clone --recurse-submodules https://github.com/AliceTeaParty/vapoursynth-api4-wheels.git
cd vapoursynth-api4-wheels/packaging/vapoursynth-krigbilateralvk
python -m pip install .
```

`KRIGVK_PREBUILT_URL` selects a local package zip or HTTPS URL for packaging tests; incorrect platform/source/version/hashes are rejected. `KRIGVK_VAPOURSYNTH_INCLUDE` and `KRIGVK_VULKAN_HEADERS` may select explicit include directories for source builds. CMake, Ninja and the R81 SDK are installed into the PEP 517 build environment; a C++ compiler and Git must be available for the native fallback. Set `CXX` if compiler discovery is ambiguous.

## Maintenance

Update the central submodule gitlink and `source.json` together after reviewing an upstream commit. The native implementation stays owned by the upstream repository. Bump the central wheel version, release tag mapping and the central version table when publishing changed source. The wrapper exports a small source snapshot into sdists so source archives can build without a sibling checkout.

The package workflow creates Windows/Linux wheels and payload zips. Windows registration checks run in hosted CI, and actual Vulkan rendering is verified locally before publication. Linux package validation runs with Vulkan-capable Mesa software execution; it is not an AMD/Intel/NVIDIA Linux hardware benchmark. Only tested artifacts should be published, followed by the index workflow.

The source and plugin are LGPL-3.0-or-later; the wheel/payload include the license and referenced GPLv3 terms.
