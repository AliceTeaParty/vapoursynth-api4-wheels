# vs-mlrt

VapourSynth API4 ML runtime plugins and the `vsmlrt.py` wrapper for Windows
and Linux x86_64.

## Install

Install exactly one entry package from the repository index:

```text
pip install --extra-index-url https://aliceteaparty.github.io/vapoursynth-api4-wheels/simple/ vs-mlrt-generic
pip install --extra-index-url https://aliceteaparty.github.io/vapoursynth-api4-wheels/simple/ vs-mlrt-cu121
pip install --extra-index-url https://aliceteaparty.github.io/vapoursynth-api4-wheels/simple/ vs-mlrt-cu129
```

Requirements are Python 3.12+, VapourSynth R75+, and Windows or Linux x86_64.
The CUDA entries additionally need a compatible NVIDIA driver. Do not install
more than one entry package in an environment.

The public Python API remains:

```python
import vsmlrt

out = vsmlrt.DPIR(clip, strength=5.0, backend=vsmlrt.Backend.TRT(fp16=True))
```

The `16.2.3` entry packages depend on the tested `16.2.2` component wheels.
This entry-only release is aligned with upstream `AmusementClub/vs-mlrt` tag `v16.2.test1`, commit
`9e4d0c9dbbcaa28275772d30520330e69a58307c`.

## Package Composition

Entry wheels own `vsmlrt.py`, the manifest, and the complete uninstall
command. Exact-version component dependencies own native files and models.

```text
vs-mlrt-generic
  -> vs-mlrt-models, vs-ov, vs-ncnn

vs-mlrt-cu121
  -> generic components
  -> vs-cublas-cu121, vs-cudnn-cu121
  -> vs-tensorrt-core-cu121, vs-tensorrt-builder-cu121
  -> vs-trtexec-cu121, vs-trt-cu121

vs-mlrt-cu129
  -> generic components
  -> vs-tensorrt-core-cu129
  -> vs-tensorrt-builder-cu129-base
  -> vs-tensorrt-builder-cu129-modern
  -> vs-trtexec-cu129, vs-trt-cu129
  -> vs-tensorrt-rtx-cu129, vs-trt-rtx-cu129
```

The cu129 builder wheels split resources by GPU architecture. They are real
independent wheels, not byte volumes, and every release asset remains below
GitHub's 2 GiB limit.

TensorRT 8.6's plugin directly imports cuBLAS, cuBLASLt, and cuDNN 8, so cu121
must ship them even with external tactics disabled. TensorRT 11.1 and
TensorRT-RTX 1.5 do not need the old cu129 CUDA/cuDNN payload for the 81
bundled models. The cu129 closure therefore excludes cudart, cuBLAS, cuDNN,
cuFFT, nvBLAS, NVRTC, NVVM, and NVJitLink.

## Installed Layout

Windows and Linux use the same layout:

```text
site-packages/
  vsmlrt.py
  vsmlrt_dll_paths.py
  vs_mlrt_dll_paths.pth
  rm_vsmlrt/
  vapoursynth/plugins/vsmlrt/
    manifest.vs
    models/
    cache.json
    OpenVINO and TBB libraries
    vsncnn.dll|so
    vsov.dll|so
    vstrt.dll|so
    vstrt_rtx.dll|so
    vsmlrt-cuda/
      TensorRT and TensorRT-RTX libraries
      TensorRT builder resources
      cu121 cuBLAS and cuDNN libraries
      trtexec[.exe]
      trtexec-build.json
      tensorrt_rtx[.exe]
```

On Linux, `vstrt.so` and `vstrt_rtx.so` are linked with
`RUNPATH=$ORIGIN:$ORIGIN/vsmlrt-cuda`. Libraries in the subdirectory use
`$ORIGIN`, while helpers use `$ORIGIN:$ORIGIN/..`. The wheel works without
`LD_LIBRARY_PATH`, system TensorRT libraries, or end-user patching.
Repository-built ELF files receive their final RUNPATH in CMake. Packaging
normalizes NVIDIA prebuilt ELF files before wheel creation and rejects a build
when `patchelf` is unavailable. It also clears and verifies executable-stack
flags; this is required for TensorRT 8.6's builder resource on hardened Linux
runtimes.

`vsmlrt.py` resolves builders from `vsmlrt-cuda/`. It first honors
`VSMLRT_TRTEXEC_PATH` or `VSMLRT_TENSORRT_RTX_PATH`, then uses the packaged
tool, then falls back to host `PATH`.

## Uninstall

Pip does not recursively remove dependencies when an entry package is
uninstalled. Use the command shipped by every entry wheel:

```text
python -m rm_vsmlrt --yes
# or
rm_vsmlrt --yes
```

It uninstalls the reviewed current and legacy distributions, removes metadata
and wrapper files, and deletes the shared payload including generated engines
and caches. It does not uninstall VapourSynth or remove unrelated plugins.
Run `python -m rm_vsmlrt --dry-run` to inspect the exact actions.

## Backend Scope

Published backends are:

- `generic`: NCNN/Vulkan and OpenVINO;
- `cu121`: generic backends plus standard TensorRT 8.6;
- `cu129`: generic backends plus standard TensorRT 11.1 and TensorRT-RTX 1.5.

ORT and MIGraphX sources remain in the tree but are not released because they
do not have the same hardware-backed validation coverage.

## Build and Release

There is no root CMake project. Build the backend being changed, for example:

```text
cmake -S vstrt -B vstrt/build -G Ninja -D CMAKE_BUILD_TYPE=Release
cmake --build vstrt/build --verbose
cmake --install vstrt/build --prefix vstrt/install
```

`tools/build_component_wheels.py` takes a canonical staged `vsmlrt/`
directory and model archive, builds the selected entry's full wheel closure,
then runs `tools/verify_component_wheels.py`. The verifier enforces the 2 GiB
limit, exact closure, non-overlapping RECORD ownership, manifests, and the
cu129 exclusion list.

Release workflows compile native code using the fork's verified build steps,
normalize the canonical stage, and call the shared component builder.
Publication remains disabled until both platform workflows pass clean staged
install checks. One `vs-mlrt-v<version>` GitHub Release will hold the complete
Windows/Linux wheel set; the Pages workflow turns those assets into the PEP
503 index.

The authoritative package inventory, binary provenance, release order,
validation gates, and uninstall design are documented in
[`../../docs/plans/vs-mlrt-release-and-uninstall.md`](../../docs/plans/vs-mlrt-release-and-uninstall.md).

## Validation Evidence

The dependency reduction was tested against all 81 bundled ONNX models,
collapsed into 14 distinct operator/input groups. Every group built an engine
with the retained cu121 and cu129 files.

Split cu129 wheel closures were built and installed on Windows and Linux. On
an RTX 3090 Ti, packaged `trtexec` and `tensorrt_rtx` built DPIR engines and
both `vstrt` and `vstrt_rtx` rendered frames. Linux loaded `libnvinfer`,
`libnvinfer_plugin`, and `libtensorrt_rtx` from `vsmlrt-cuda/` without a
system TensorRT fallback.

`rm_vsmlrt` was exercised against an installed Linux cu129 closure: it removed
all 11 distributions, the shared payload, and an untracked generated engine,
while preserving an unrelated plugin.

Run the packaging regression suite with:

```text
python -m unittest discover -s tools -p "test_*.py"
```
