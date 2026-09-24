# vs-mlrt migration record

Status: API4 source builds and the split component-wheel architecture are
verified locally on Windows and Linux. Publication remains disabled until the
updated GitHub workflows pass; all old prereleases and release tags remain
removed.

## Alignment

- Original upstream common baseline: `AmusementClub/vs-mlrt@1f166ba`
- Fork generic head: `RyougiKukoc/vs-mlrt-api4@dec8064`
- Fork variant branches: `generic`, `cu121`, `cu129`
- Fork patch: 114 commits compressed into one subtree patch commit
- Source package version: `16.2.2`

The old variant branches supplied the verified native build recipes. The
combined repository now exposes three entry distributions backed by shared,
exact-version component wheels:

- `vs-mlrt-generic`
- `vs-mlrt-cu121`
- `vs-mlrt-cu129`

CUDA compatibility is therefore represented by package name, never by a
version suffix or a mutable branch ref in the user-facing install command.

## Split wheel implementation

The old monolithic/numbered-volume wheel experiment has been replaced by
semantic components. Entry wheels directly depend on generic, model, TRT,
builder, and plugin components and no longer depend on another entry wheel.
Component file ownership is disjoint within each entry closure.

Windows and Linux now use the same `vsmlrt-cuda/` support directory. Linux
`vstrt.so` and `vstrt_rtx.so` encode
`$ORIGIN:$ORIGIN/vsmlrt-cuda` in their CMake build/install RUNPATH; NVIDIA
prebuilt ELF files are normalized during packaging. The layout passed real
standard TRT and RTX engine builds and frame inference in `vpy:cu129` without
`LD_LIBRARY_PATH` or a system TensorRT fallback.

The cu129 closure no longer ships cudart, cuBLAS, cuDNN, cuFFT, nvBLAS, NVRTC,
NVVM, or NVJitLink. The retained libraries built every one of the 14 distinct
operator/input groups derived from the 81 bundled models. cu121 retains
cuBLAS/cuBLASLt and cuDNN 8 because TensorRT 8.6's plugin directly imports
them.

Every entry wheel provides `python -m rm_vsmlrt` and `rm_vsmlrt`. A real Linux
cu129 split installation test removed all 11 distributions, the shared plugin
directory, models, and an untracked generated engine while preserving an
unrelated plugin.

## API4 classification

The fork contains real API4 backend work in TRT, ORT, OpenVINO, NCNN, and
MIGX sources, plus extensive runtime payload verification. This migration does
not use `vsmlrt-api4-port` and does not copy any plugin changes from
`vs-wheels`.

## Native build evidence

The original complete-wheel layout passed all three main-branch workflows at
`d68dba1fa39cd39394f5b250f5d796a1bbc29ae5`:

- Windows generic: run `35765442197`
- Windows CUDA 12.1/12.9 matrix: run `35765442225`
- Linux generic/CUDA 12.1/CUDA 12.9 matrix: run `35765442370`

Those runs compiled the native backends, assembled payloads, built wheels, and
passed their staged install smoke. The cu121 tag runs `35771541586` (Windows)
and `35771541531` (Linux) again completed native compilation and packaging;
they failed only when uploading a monolithic wheel beyond GitHub's 2 GiB
single-asset limit.

Commit `bf4f35ffc89e4e8c185f1638af140b64a6270918` tried a compositional package
layout. Its latest runs give a precise handoff boundary:

- Windows generic run `35776373307` passed completely.
- Windows CUDA run `35776373267` compiled `vstrt`, `vstrt_rtx`, and custom
  `trtexec`, verified the helper executables, assembled, inspected, and
  compressed both CUDA payloads. It then failed in the staged install check
  because the source-install hook requested an unpublished asset and received
  HTTP 404.
- Linux run `35776373243` built and verified native payloads for generic,
  cu121, and cu129. The cu121 compositional wheel was successfully built at
  1,912,900,980 bytes and installed, then failed because the resulting
  manifest still listed only `vsncnn` and `vsov`. The cu129 native payload was
  also built and verified before its wheel job was cancelled by matrix failure.

This evidence proves that compilation and native artifact assembly work. The
remaining failures are distribution composition and publication semantics, not
source compilation failures. No compilation was performed in the local
WinPython or Docker consumer environments.

## Publication handoff

Platform workflows build and upload native split-wheel artifacts but never
modify a GitHub Release. Entry-only patch releases are built from the three
pure-Python entry projects after their metadata is verified, then published
manually with their dependencies pinned to the already published component
wheels. The Pages index is refreshed through its `repository_dispatch` event.

This avoids rebuilding or republishing native component wheels when only the
entry package metadata changes. Native platform builds remain available as
manual validation workflows when their payloads change.

Commit `4f3494ee8f8e69d33c30f820bd7d08de0201c0d0` validated the handoff guards:

- Windows generic run `35815812926` passed; both `TODO(publishing)` steps were
  skipped.
- Windows CUDA run `35815813121` again completed native compilation, custom
  `trtexec`, payload assembly, inspection, and packaging for cu121 and cu129.
  Both jobs stopped at the known staged-install 404, and all publication steps
  were skipped.
- Linux run `35815813204` passed generic completely and completed cu129 native
  build plus staged verification before the known wheel-manifest failure. Its
  cu121 matrix job was cancelled by fail-fast; run `35776373243` provides the
  successful cu121 native-build evidence for the same source and packaging
  implementation. All Linux publication and Pages steps were skipped.

No vs-mlrt GitHub Release or release tag exists after this validation.
