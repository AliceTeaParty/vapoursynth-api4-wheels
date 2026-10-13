# VapourSynth API4 Wheels

Prebuilt VapourSynth plugins and Python script modules, installable with pip.
This collection includes our own projects and maintained API4 ports of upstream
plugins, plus a curated set of modified script modules.

Native plugin wheels support **Windows and Linux x86_64**. macOS and ARM native
wheels are not published. Python modules use platform-independent wheels;
the plugins and external programs they call still have their own requirements.

## Install

1. Find a package in the lists below and copy its exact wheel version from
   [VERSIONS.md](VERSIONS.md#wheel-versions).
2. Use the same Python environment as your VapourSynth scripts. Replace
   `PACKAGE` and `VERSION` in this command with that package name and version:

   ```console
   python -m pip install --extra-index-url https://aliceteaparty.github.io/vapoursynth-api4-wheels/simple/ "PACKAGE==VERSION"
   ```

The [package index](https://aliceteaparty.github.io/vapoursynth-api4-wheels/simple/)
contains published wheels; normal Python dependencies come from PyPI. Native
wheels install the plugin and its autoload manifest, so you do not need to copy
DLLs or compile the plugin yourself. Restart an existing Python or editor session
after installation.

Our modified upstream projects use the version suffix **`+alice.x`**.
KrigBilateral Vulkan, DFTTestVK, `rksfunc` and `rkstool` retain their original
upstream versions. Keep the complete version when pinning a package: pip
compares both indexes and can otherwise choose a different same-name package.
All exact versions, source revisions and runtime compatibility details are
recorded in [VERSIONS.md](VERSIONS.md).

If an earlier KrigBilateral installation carries an `+alice.x` suffix,
reinstall the version from VERSIONS.md with `--force-reinstall`; pip treats the
old local label as newer than the same original version.

## Our projects

- [KrigBilateral Vulkan](plugins/vapoursynth-krigbilateralvk/README.md) — `vapoursynth-krigbilateralvk`: Luma-guided chroma reconstruction on a Vulkan GPU. Integer 8..16-bit and FP16/FP32 YUV420 input becomes YUV444, with range-aware output depth and dither control. Luma is preserved at unchanged depth/type. Includes CPU-clip and GPU-resident entry points. See [runtime requirements](VERSIONS.md#runtime-compatibility).
- [DFTTestVK](plugins/vapoursynth-dfttestvk/README.md) — `vapoursynth-dfttestvk`: Frequency-domain spatial/temporal denoising on a Vulkan GPU. Includes CPU-clip and GPU-resident entry points, with spatial FFT caching for temporal processing. See [runtime requirements](VERSIONS.md#runtime-compatibility).
- [rksfunc](https://github.com/RyougiKukoc/rksfunc#readme) — `rksfunc`: VapourSynth script helpers, including a bundled KrigBilateral shader. Install the Python modules and native plugins required by your script separately. The bundled shader is distinct from the native Vulkan plugin above.
- [rkstool](https://github.com/RyougiKukoc/rkstool/wiki) — `rkstool`: Helpers for encoding, muxing and media-processing workflows. External tools such as ffmpeg, mkvmerge and qaac must be installed separately when used.
- [Script Collection](modules/vs-collection-rk/README.md) — `vs-collection-rk`: Installs all 12 modified script modules listed below as one matched set. Import them by their original module names. Required runtime plugins and libraries remain user-managed. See the package guide for upgrades and installed-file checks.

## Maintained upstream plugins

These packages contain our API4 and packaging changes to upstream projects.
The links lead to the plugin documentation; choose the package by its workload
and hardware requirements.

- [NLQ](plugins/vs-nlq/README.md) — `vs-nlq`: Dolby Vision nonlinear quantization processing. Expects a 16-bit mapped base layer and 10-bit enhancement layer; produces 12-bit output.
- [NNEDI3CL](plugins/vapoursynth-nnedi3cl/README.md) — `vapoursynth-nnedi3cl`: Neural interpolation for resizing and anti-aliasing. Requires an OpenCL device and driver.
- [SmoothUV](plugins/vapoursynth-smoothuv) — `vapoursynth-smoothuv`: Chroma smoothing and denoising. Accepts constant-format 8-bit YUV; convert higher bit depths before using it.
- [DFTTest](plugins/vapoursynth-dfttest/README.md) — `vapoursynth-dfttest`: Frequency-domain spatial/temporal denoising on the CPU. A CPU option with the original DFTTest parameter interface.
- [KNLMeansCL](plugins/vapoursynth-knlm/README.md) — `vapoursynth-knlm`: Non-local means denoising. Requires an OpenCL device and driver.
- [Retinex](plugins/vapoursynth-retinex/README.md) — `vapoursynth-retinex`: Contrast and dynamic-range enhancement. MSRCP needs 8–16-bit Gray, YUV444 or RGB; MSRCR needs RGB. Convert subsampled YUV first.
- [BM3DCUDA / CPU](plugins/vapoursynth-bm3dcuda/README.md) — `vapoursynth-bm3dcpu`, `vapoursynth-bm3dcuda-cu121`, `vapoursynth-bm3dcuda-cu129`: BM3D denoising on CPU or NVIDIA GPU. CPU backend needs AVX2. CUDA wheels include `core.bm3dcpu` and `core.bm3dcuda_rtc`; `core.bm3dcuda` is not included. Install one variant.
- [DFTTest2](plugins/vapoursynth-dfttest2/README.md) — `vapoursynth-dfttest2-cpu`, `vapoursynth-dfttest2-cu121`, `vapoursynth-dfttest2-cu129`: Frequency-domain denoising with CPU and CUDA backends. CPU wheel needs no NVIDIA GPU. CUDA wheels include CPU, NVRTC and cuFFT backends. Install one variant.
- [vs-mlrt](plugins/vs-mlrt/README.md) — `vs-mlrt-generic`, `vs-mlrt-cu121`, `vs-mlrt-cu129`: Neural video processing with NCNN, OpenVINO and TensorRT. Install one entry package; it selects matching models and runtimes. See variant selection below.
- [TComb](plugins/vapoursynth-tcomb) — `vapoursynth-tcomb`: Temporal dot-crawl and rainbow reduction. Needs constant-format 8-bit Gray or YUV. Gray input requires luma-only mode.
- [FFT3DFilter](plugins/vapoursynth-fft3dfilter/README.md) — `vapoursynth-fft3dfilter`: Frequency-domain denoising, sharpening and dehaloing. Runs on the CPU; temporal settings determine how neighboring frames are used.
- [Chroma-from-Luma](plugins/vs-cfl/README.md) — `vs-cfl`: Luma-guided chroma reconstruction. Integer YUV420/YUV422 input becomes YUV444; chroma placement affects reconstruction.
- [TCanny](plugins/vapoursynth-tcanny/README.md) — `vapoursynth-tcanny`: Canny edge detection and masks. Supports 8–16-bit integers and FP32. `mode=0` gives a thresholded edge mask; `mode=1` gives gradient magnitude.
- [Misc filters](plugins/vapoursynth-misc/README.md) — `vapoursynth-misc`: Legacy utility filters, including SCDetect, AverageFrames and Hysteresis. Provides API4 ports for scripts that still use the `misc` namespace.

### Choosing CPU and GPU variants

For BM3D and DFTTest2, choose the `cpu` package for CPU processing or a `cu121` /
`cu129` package for an NVIDIA GPU. The CUDA suffix selects the bundled runtime
line. You need a compatible NVIDIA driver; a separate CUDA Toolkit is not
required to use the wheel. See [runtime compatibility](VERSIONS.md#runtime-compatibility)
for the runtime versions.

For vs-mlrt:

- `vs-mlrt-generic`: NCNN/Vulkan and OpenVINO.
- `vs-mlrt-cu121`: The common backends above plus standard TensorRT on the `cu121` runtime line.
- `vs-mlrt-cu129`: The common backends above plus standard TensorRT and TensorRT-RTX on the `cu129` runtime line.

Install **one variant of each project** per environment; variants own the same
plugin or Python API paths. To switch, uninstall the current variant first.
For vs-mlrt, `python -m rm_vsmlrt_helper` prints the uninstall command for the
installed entry and component packages; review and run that command before
installing another entry. Install the entry package rather than selecting
individual backend wheels.

If an older installation contains `bm3dcuda-cpu`, uninstall that withdrawn
package before installing any of the current BM3D packages.

## Maintained upstream script modules

Install `vs-collection-rk` for the complete set, or install the component
packages individually. These modified modules retain their familiar import
names. Install the native plugins and Python libraries your scripts use
separately; the Collection does not supply every filter they can call.

- [csmod](modules/csmod/WHEEL-README.md): Contra-sharpening helpers. Import as `CSMOD`.
- [fvsfunc](modules/fvsfunc/README.md): Filtering, resizing and interlaced-overlay helpers; `OverlayInter` can use QTGMC. Import as `fvsfunc`.
- [getfnative](modules/getfnative/README.md): Estimate native fractional resolution in upscaled/cropped sources; base-dimension parity affects the result. Import as `getfnative`.
- [havsfunc](modules/havsfunc/README.md): QTGMC and other filtering / anti-aliasing helpers; required plugins depend on the chosen function. Import as `havsfunc`.
- [kagefunc](modules/kagefunc/README.md): Common filtering, masking and grain helpers. Import as `kagefunc`.
- [muvsfunc](modules/muvsfunc/README.md): Filtering and numerical-processing helpers; optional functions can require additional libraries. Import as `muvsfunc`.
- [mvsfunc](modules/mvsfunc/README.md): Depth/color conversion and denoising helpers, including BM3D. Import as `mvsfunc`.
- [nnedi3-resample](modules/nnedi3-resample/README.md): NNEDI3-based resizing; requires the backend plugins selected by your script. Import as `nnedi3_resample`.
- [nnedi3-rpow2](modules/nnedi3-rpow2/WHEEL-README.md): Power-of-two NNEDI3 enlargement. Import as `nnedi3_rpow2`.
- [sdering-fix](modules/sdering-fix/WHEEL-README.md): Deringing helpers. Import as `sdering_fix`.
- [vstaambk](modules/vstaambk/README.md): Anti-aliasing helpers. Import as `vsTAAmbk`.
- [yvsfunc](modules/yvsfunc/README.md): Resampling, denoising, frame and preview helpers. Import as `yvsfunc`.

The maintained EEDI3 routes in HAvsFunc, vsTAAmbk and yvsfunc use the CPU by
default. Their `opencl=True` option selects Vulkan with an OpenCL fallback.
See the [backend guide](modules/COLLECTION.md#eedi3-controls) for plugin
requirements and device controls.

## About this collection

The distribution model was inspired by
[vs-wheels](https://github.com/Jaded-Encoding-Thaumaturgy/vs-wheels).
This project maintains its own ports and packages, offers separate CUDA runtime
variants, and aims to keep existing `vsmlrt.py` workflows familiar. When an
upstream project provides a suitable API4 package, we will review migration
and retirement of the corresponding package here.

For source layout, builds and update workflows, see [DEVELOPMENT.md](DEVELOPMENT.md).
Each project retains its own license; see [LICENSES.md](LICENSES.md) for sources
and third-party notices.
