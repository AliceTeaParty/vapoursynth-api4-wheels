# Linux and Windows component parity audit

Status: the split wheel layout has platform parity.

Both platforms install native VapourSynth plugins and generic support files at
`vapoursynth/plugins/vsmlrt/`. All TensorRT, TensorRT-RTX, builder, and cu121
CUDA dependency files install at `vapoursynth/plugins/vsmlrt/vsmlrt-cuda/`.

Linux originally kept shared libraries at the plugin root because `vstrt.so`
used `RUNPATH=$ORIGIN`. Moving them without changing RUNPATH failed with
`libnvinfer.so.11: cannot open shared object file`. The final contract is:

```text
vstrt.so and vstrt_rtx.so:       $ORIGIN:$ORIGIN/vsmlrt-cuda
vsmlrt-cuda/lib*.so*:            $ORIGIN
vsmlrt-cuda/trtexec:             $ORIGIN:$ORIGIN/..
vsmlrt-cuda/tensorrt_rtx:        $ORIGIN:$ORIGIN/..
```

With that contract, `vpy:cu129` loaded `libnvinfer.so.11`,
`libnvinfer_plugin.so.11`, and `libtensorrt_rtx.so.1` from the package
subdirectory, built standard and RTX engines, and rendered frames without
`LD_LIBRARY_PATH` or system TensorRT libraries.

The Linux cu121 audit additionally found NVIDIA's TensorRT 8.6 builder
resource requesting an executable stack. Packaging now applies
`patchelf --clear-execstack` to every staged ELF and verifies the result. The
corrected split cu121 closure built an engine and rendered a frame in the GPU
container.

Component-wheel verification enforces:

- no overlapping files in any entry dependency closure;
- no CUDA/TensorRT support library outside `vsmlrt-cuda/`;
- cu121 includes its cuBLAS and cuDNN hard dependencies;
- cu129 excludes the removed CUDA runtime/compiler families;
- platform-correct wheel tags and the GitHub 2 GiB asset limit;
- exact manifests for generic, cu121, and cu129.
