# vapoursynth-krigbilateralvk wheels

The central wheel project for [KrigBilateral Vulkan](https://github.com/RyougiKukoc/vapoursynth-krigbilateralvk) lives at `plugins/vapoursynth-krigbilateralvk`. The original native source is its `native/` git submodule; `source.json` records the exact upstream commit. Wheel metadata, tools and release workflows are maintained in `AliceTeaParty/vapoursynth-api4-wheels` alongside the other plugin packages. The wheel retains the original upstream version without a local `+alice.x` label.

## Install

Windows and Linux x86_64 wheels are published on the central index:

```console
python -m pip install --extra-index-url https://aliceteaparty.github.io/vapoursynth-api4-wheels/simple/ "vapoursynth-krigbilateralvk==0.4.0"
```

Use the same Python environment as VapourSynth. The wheel requires VapourSynth R81 or newer (`>=81`) because the plugin's core GPU interface targets that SDK. A Vulkan 1.4 device/driver is needed for rendering; GPU FP16 conversions additionally depend on the core's device support. Linux wheels use the `manylinux_2_28_x86_64` runtime floor. macOS and ARM packages are not published.

The wheel installs `vapoursynth/plugins/krigbilateralvk/krigbilateralvk.dll` or `.so`, its autoload manifest and license files. It does not provide or overwrite VapourSynth's Python package initializer. No compiler is needed for an index wheel install.

```python
import vapoursynth as vs

output = vs.core.krigvk.KrigBilateral(source)
# For a resident GPU chain:
gpu_output = vs.core.krigvk.KrigBilateralGPU(vs.core.std.GPUUpload(source))
```

Input is constant-format progressive YUV420 with positive even dimensions and left chroma placement. Integer depths 8..16 and standard signed-chroma FP16/FP32 are supported. Core `resize.Point` handles range-aware conversion to FP32 working samples and final output conversion. It reads each frame's `_Range` (`0=limited`, `1=full`); untagged YUV follows resize's limited default, so full-range input must be tagged correctly.

Both entries accept `bits`, `sample_type` and `dither_type`. Output is YUV444 at the same size, with sample type/depth matching input by default. `bits=32` selects FP32; `bits=16, sample_type=vs.INTEGER` explicitly selects integer 16-bit even for floating input. Dither defaults to `none` (Python `None` is accepted), with `ordered`, `random` and `error_diffusion` also available. It applies only to integer output. At unchanged type/depth the original luma bytes are preserved; otherwise core resize converts original luma directly. Finite float headroom is retained until output conversion.

```python
floating = vs.core.krigvk.KrigBilateral(source, bits=32)
eight_bit = vs.core.krigvk.KrigBilateral(source, bits=8, dither_type="error_diffusion")
```

Version 0.4.0 removes `debug` and diagnostic output from both public entries. Calls passing `debug` fail, including `debug=0`. Current CPU/GPU performance measurements and their completion/transfer boundaries are recorded in the upstream validation report; old v0.2.0 timings do not describe the range-aware conversion path.

Both entries use the same GPU resize backend for none/ordered/random, avoiding entry-dependent conversion rounding. CPU-frame callers transfer at their interface; ordinary GPU chains stay resident. R81's GPU resize lacks error diffusion, so selecting it for integer output explicitly uses CPU resize and transfers to the requested output residency. The covariance and solver are unchanged, but corrected range handling can change integer results from v0.2.x. The `reference` option remains removed. See the [plugin README](https://github.com/RyougiKukoc/vapoursynth-krigbilateralvk#readme) for type inference, diagnostics and numerical limits.

## Source installation

This explicit named VCS form uses a matching central Release package by default:

```console
python -m pip install "vapoursynth-krigbilateralvk @ git+https://github.com/AliceTeaParty/vapoursynth-api4-wheels.git#subdirectory=plugins/vapoursynth-krigbilateralvk"
```

Version `0.4.0` maps to central tag `vapoursynth-krigbilateralvk-v0.4.0`. Assets are `krigbilateralvk-windows-x86_64.zip` and `krigbilateralvk-linux-x86_64.zip`. If the matching platform asset is unavailable, the backend compiles the pinned submodule with CMake and a C++20 compiler. `KRIGVK_FORCE_BUILD=1` explicitly selects that native build. No automatic platform substitution occurs.

For a local checkout:

```console
git clone --recurse-submodules https://github.com/AliceTeaParty/vapoursynth-api4-wheels.git
cd vapoursynth-api4-wheels/plugins/vapoursynth-krigbilateralvk
python -m pip install .
```

`KRIGVK_PREBUILT_URL` selects a local package zip or HTTPS URL for packaging tests; incorrect platform/source/version/hashes are rejected. `KRIGVK_VAPOURSYNTH_INCLUDE` and `KRIGVK_VULKAN_HEADERS` may select explicit include directories for source builds. CMake, Ninja and the R81 SDK are installed into the PEP 517 build environment; a C++ compiler and Git must be available for the native fallback. Set `CXX` if compiler discovery is ambiguous.

## Maintenance

Update the central submodule gitlink and `source.json` together after reviewing an upstream commit. The native implementation stays owned by the upstream repository. Bump the central wheel version, release tag mapping and the central version table when publishing changed source. The wrapper exports a small source snapshot into sdists so source archives can build without a sibling checkout.

The package workflow creates Windows/Linux wheels and payload zips. Windows registration checks run in hosted CI, and actual Vulkan rendering is verified locally. Linux package validation runs with Vulkan-capable Mesa software execution. Physical GPU validation also passed on Windows RTX 3090 Ti and Linux NVIDIA A100 with Vulkan 1.4: published-wheel rendering, signed FP16/FP32, nonuniform chroma, exact luma and CPU/GPU entry equality; Linux additionally passed release-payload source installation and a native source rebuild. See the upstream [validation report](https://github.com/RyougiKukoc/vapoursynth-krigbilateralvk/blob/main/docs/validation.md) for versions and scope. These checks are not a Linux original-GLSL bit-exact comparison or benchmark.

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
