# TensorRT component release matrix

This document records the native CUDA contract enforced by the split wheel
implementation. The complete release and provenance plan is in
`docs/plans/vs-mlrt-release-and-uninstall.md` at the repository root.

## Runtime lines

| Entry | Plugins | SDKs | Required runtime families |
| --- | --- | --- | --- |
| `vs-mlrt-cu121` | `vsncnn`, `vsov`, `vstrt` | CUDA 12.1.1, TensorRT 8.6.1.6, cuDNN 8.9.7.29 | TensorRT core/plugin/parser, builder resource, cuBLAS/cuBLASLt, cuDNN inference, packaged `trtexec` |
| `vs-mlrt-cu129` | `vsncnn`, `vsov`, `vstrt`, `vstrt_rtx` | CUDA 12.9 build toolchain, TensorRT 11.1.0.106, TensorRT-RTX 1.5.0.114 | TensorRT core/plugin/parser, all standard builder resources, packaged `trtexec`, TensorRT-RTX runtime/parser/tool |

cu121 does not provide TensorRT-RTX. TensorRT 8.6's `nvinfer_plugin` directly
imports cuBLAS, cuBLASLt, and cuDNN, even when those tactic sources are
disabled. Those files are therefore runtime dependencies rather than optional
performance libraries.

The cu129 model matrix does not need cudart, cuBLAS, cuDNN, cuFFT, nvBLAS,
NVRTC, NVVM, or NVJitLink. Component and installed-layout verifiers reject
those families if they return to the cu129 closure.

## Builder resources

Standard TensorRT engine construction requires its builder resources:

- cu121 packages the single TensorRT 8.6 builder resource;
- cu129 `base` packages PTX and SM75/80/86/89;
- cu129 `modern` packages SM90/100/120.

`vs-trtexec-cu129` depends on both cu129 resource wheels so the entry package
can build engines for every supported architecture. TensorRT-RTX uses its own
builder executable and runtime; it does not depend on standard TensorRT
builder resources.

Builder resource files retain NVIDIA's fully versioned SDK filename because
TensorRT opens that exact name dynamically. Linux does not rename them from a
sentinel SONAME.

## Cross-platform layout

Both systems install CUDA/TensorRT support files below:

```text
vapoursynth/plugins/vsmlrt/vsmlrt-cuda/
```

Only `vstrt.dll|so` and `vstrt_rtx.dll|so` remain at the plugin root. Linux
uses these RUNPATH values:

```text
vstrt.so and vstrt_rtx.so:       $ORIGIN:$ORIGIN/vsmlrt-cuda
vsmlrt-cuda/lib*.so*:            $ORIGIN
vsmlrt-cuda/trtexec:             $ORIGIN:$ORIGIN/..
vsmlrt-cuda/tensorrt_rtx:        $ORIGIN:$ORIGIN/..
```

The plugin RUNPATH is encoded by CMake. NVIDIA prebuilt ELF files are
normalized during packaging. Missing `patchelf` fails the build; users never
set `LD_LIBRARY_PATH` or modify installed files.
Packaging also clears and verifies executable-stack flags because NVIDIA's
TensorRT 8.6 builder resource otherwise fails on hardened Linux runtimes.

## Verification gates

For every release:

1. Check Windows PE imports and Linux `DT_NEEDED` across the complete selected
   dependency closure.
2. Check every Linux SONAME and RUNPATH before wheel creation.
3. Verify component wheel RECORD ownership has no overlap.
4. Build a standard TensorRT engine with the packaged `trtexec` and render it
   through `vstrt`.
5. For cu129, build an RTX engine with packaged `tensorrt_rtx` and render it
   through `vstrt_rtx`.
6. Run without a system TensorRT installation or `LD_LIBRARY_PATH` fallback.

The dependency reduction was tested against all 81 bundled ONNX models,
grouped into 14 distinct operator/input signatures. All representative groups
built successfully on both runtime lines with the retained files.
