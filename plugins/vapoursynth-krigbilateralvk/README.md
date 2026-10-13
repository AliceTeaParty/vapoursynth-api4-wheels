# vapoursynth-krigbilateralvk wheels

The central wheel project for [KrigBilateral Vulkan](https://github.com/RyougiKukoc/vapoursynth-krigbilateralvk) lives at `plugins/vapoursynth-krigbilateralvk`. The original native source is its `native/` git submodule; `source.json` records the exact upstream commit. Wheel metadata, tools and release workflows are maintained in `AliceTeaParty/vapoursynth-api4-wheels` alongside the other plugin packages. The wheel retains the original upstream version without a local `+alice.x` label.

## Install

Windows and Linux x86_64 wheels are published on the central index:

```console
python -m pip install --extra-index-url https://aliceteaparty.github.io/vapoursynth-api4-wheels/simple/ "vapoursynth-krigbilateralvk==0.4.1"
```

Use the same Python environment as VapourSynth. The wheel requires VapourSynth R81 or newer (`>=81`) because the plugin's core GPU interface targets that SDK. A Vulkan 1.4 device/driver is needed for rendering; GPU FP16 conversions additionally depend on the core's device support. Linux wheels use the `manylinux_2_28_x86_64` runtime floor. macOS and ARM packages are not published.

The wheel installs `vapoursynth/plugins/krigbilateralvk/krigbilateralvk.dll` or `.so`, its autoload manifest and license files. It does not provide or overwrite VapourSynth's Python package initializer. No compiler is needed for an index wheel install.

```python
import vapoursynth as vs

output = vs.core.krigvk.KrigBilateral(source)
# For a resident GPU chain:
gpu_output = vs.core.krigvk.KrigBilateralGPU(vs.core.std.GPUUpload(source))
```

Input is constant-format progressive YUV420 with positive even dimensions and left chroma placement. Integer depths 8..16 and signed-chroma FP16/FP32 are supported. Version 0.4.0 fuses input normalization and output quantization into the original three Krig kernels, removing boundary resize nodes and full-frame FP32 conversion buffers. Each frame's `_Range` is retained (`0=limited`, `1=full`); untagged YUV defaults to limited, so tag full-range input correctly. Legacy `_ColorRange` setters work through the core alias. See the upstream [conversion contract and range table](https://github.com/RyougiKukoc/vapoursynth-krigbilateralvk/blob/main/docs/range-depth.md).

Both entries accept `bits` and `sample_type`. Integer input defaults to **integer16 output**; float input retains its float depth. `bits=32` selects FP32; `bits=16, sample_type=vs.INTEGER` explicitly selects integer16 for float input. Integer output below 16 bits emits one VapourSynth warning at construction: no dither is applied and banding may occur. Processing continues. Version 0.4.1 removes `dither_type` from both entries; passing it fails. Apply core resize to 16-bit or FP32 output when dithering is required.

At unchanged type/depth the original Y plane is shared exactly. Otherwise the final Krig kernel converts original Y directly. Finite float headroom is retained until integer quantization, which rounds to nearest with ties to even and clips to storage range. CPU and GPU entries use identical conversion arithmetic; CPU-frame output adds upload/download, while the resident entry stays on the GPU.

```python
floating = vs.core.krigvk.KrigBilateral(source, bits=32)
sixteen_bit = vs.core.krigvk.KrigBilateral(source)
eight_bit = vs.core.resize.Point(sixteen_bit, format=vs.YUV444P8, dither_type="error_diffusion")
# No dither, with a warning:
eight_bit_no_dither = vs.core.krigvk.KrigBilateral(source, bits=8)
```

Version 0.4.0 removes `debug` and all diagnostic output branches; calls passing `debug` fail, including `debug=0`. The `reference` option remains removed. The covariance and solver are unchanged. Windows RTX 3090 Ti and Linux A100 each pass 730 range/depth checks, 41 contracts and the 32-configuration / 256-frame original-GLSL matrix against an independent resize-based oracle. Mesa also passes the full range/depth, contract and original-GLSL suites; the integer chroma adaptation boundary prevents contraction into its range affine. Eight real 1080p frames match across 99,532,800 output samples. Matched source measurements improve CPU16 from 112.67 to 189.29 fps and resident GPU16 from 122.29 to 220.73 fps. The [validation report](https://github.com/RyougiKukoc/vapoursynth-krigbilateralvk/blob/main/docs/validation.md) records measured binary hashes and differing timing boundaries; these source measurements identify their binaries separately from hosted release artifacts.

## Source installation

This explicit named VCS form uses a matching central Release package by default:

```console
python -m pip install "vapoursynth-krigbilateralvk @ git+https://github.com/AliceTeaParty/vapoursynth-api4-wheels.git#subdirectory=plugins/vapoursynth-krigbilateralvk"
```

Version `0.4.1` maps to central tag `vapoursynth-krigbilateralvk-v0.4.1`. Assets are `krigbilateralvk-windows-x86_64.zip` and `krigbilateralvk-linux-x86_64.zip`. If the matching platform asset is unavailable, the backend compiles the pinned submodule with CMake and a C++20 compiler. `KRIGVK_FORCE_BUILD=1` explicitly selects that native build. No automatic platform substitution occurs.

For a local checkout:

```console
git clone --recurse-submodules https://github.com/AliceTeaParty/vapoursynth-api4-wheels.git
cd vapoursynth-api4-wheels/plugins/vapoursynth-krigbilateralvk
python -m pip install .
```

`KRIGVK_PREBUILT_URL` selects a local package zip or HTTPS URL for packaging tests; incorrect platform/source/version/hashes are rejected. `KRIGVK_VAPOURSYNTH_INCLUDE` and `KRIGVK_VULKAN_HEADERS` may select explicit include directories for source builds. CMake, Ninja and the R81 SDK are installed into the PEP 517 build environment; a C++ compiler and Git must be available for the native fallback. Set `CXX` if compiler discovery is ambiguous.

## Maintenance

Update the central submodule gitlink and `source.json` together after reviewing an upstream commit. The native implementation stays owned by the upstream repository. Bump the central wheel version, release tag mapping and the central version table when publishing changed source. The wrapper exports a small source snapshot into sdists so source archives can build without a sibling checkout.

The package workflow creates Windows/Linux wheels and payload zips. Windows registration checks run in hosted CI, and actual Vulkan rendering is verified locally. Linux package validation runs with Vulkan-capable Mesa software execution. Physical GPU validation also passed on Windows RTX 3090 Ti and Linux NVIDIA A100 with Vulkan 1.4: published-wheel rendering, signed FP16/FP32, nonuniform chroma, exact luma and CPU/GPU entry equality; Linux additionally passed release-payload source installation and a native source rebuild. See the upstream [validation report](https://github.com/RyougiKukoc/vapoursynth-krigbilateralvk/blob/main/docs/validation.md) for versions and scope. The versioned source validation also includes the original-GLSL matrix on Linux; no Linux throughput or cross-device speed claim is made.

Physical GPU tests can run locally over SSH using an isolated mamba environment; registering the host as a GitHub runner is optional. Keep machine addresses, account paths and device identifiers in local evidence. Normal hosted CI remains responsible for compilation, package loading and software Vulkan checks. Only tested artifacts should be published, followed by the index workflow.

The separate `Validate - KrigBilateral physical GPU` workflow can be dispatched
on a Linux NVIDIA GPU runner. Its `runner_labels` input is a JSON array: use
the label of a configured GitHub-hosted GPU larger runner, or the default
`["self-hosted","linux","x64","nvidia-vulkan-1.4"]` for a matching self-hosted
runner. The selected release must match this checkout's registered source and
package version. The runner needs Docker, NVIDIA Container Toolkit with the
`nvidia` runtime configured, and an NVIDIA Linux driver exposing Vulkan 1.4.
The job's 20-minute timeout bounds execution time.

This hardware job restricts the loader to an injected NVIDIA ICD, explicitly
selects a usable physical Vulkan 1.4 device, and verifies the active device's
identity before requesting frames. It tests both the released wheel and its
payload source-install loopback, including integer, signed FP16/FP32 and
nonuniform chroma. The artifact contains device/driver information, Vulkan
inventory, native hashes and rendering results. A software device or an older
Vulkan hardware device causes failure.

Standard `ubuntu-latest` runners provide the existing software Vulkan checks.
GitHub's hosted GPU larger runners use a Tesla T4, require a Team or Enterprise
organization plan, and are billed separately even for public repositories.
Their actual driver/API support must satisfy the hardware check. See
[runner specifications](https://docs.github.com/en/actions/reference/runners/larger-runners)
and [pricing](https://docs.github.com/en/billing/reference/actions-runner-pricing).
Self-hosted Linux GPU machines can run the same workflow.

For a runner with an existing mamba/Python environment, set
`environment_prefix` to its absolute prefix. This runs the released plugin
directly in that environment. It needs Python 3.12+, R81, Hatchling, Packaging,
the GitHub CLI, Vulkan tools, a Vulkan 1.4 loader and access to the host NVIDIA
ICD/libraries. An empty prefix uses the Docker path described above.
`device_index` can select a specific Vulkan device on a shared server;
otherwise the hardware check selects automatically. The chosen device is
verified by identity and recorded in the results.

The source and plugin are LGPL-3.0-or-later; the wheel/payload include the license and referenced GPLv3 terms.
