# vs-mlrt split release and uninstall implementation plan

Status: implementation is in progress. Publication is not enabled yet.

Implementation update (2026-09-23): the component projects, entry dependency
graphs, unified Linux/Windows layout, CMake RUNPATH contract, ELF
normalization, wheel closure verifier, release assembler, and `rm_vsmlrt` are
implemented. Local Windows and Linux split-wheel installs passed cu121 TRT and
cu129 TRT/RTX engine-build and frame-inference tests. `rm_vsmlrt` passed a real
Linux cu129 complete-uninstall test. All six remote Windows/Linux build jobs
also passed. The first `publish=false` release-finalizer run
(`35866774669`) exposed one release-assembly defect: Windows and Linux had
independently built same-name `py3-none-any` entry wheels, and the finalizer
had selected a canonical copy only for the generic build. The assembler
correctly rejected the differing `vs_mlrt_cu121-16.2.3-py3-none-any.whl`
files instead of silently choosing one. The remaining gates are a corrected
finalizer run, atomic draft release upload, published digest verification, and
Pages-index consumer installs. A second `publish=false` run (`35871122166`)
proved the four platform-independent selections worked, then exposed the same
ownership requirement for the generic native `vs-ncnn` and `vs-ov` wheels
rebuilt by each CUDA variant. Publication remains disabled until all remote
gates pass. The corrected `publish=false` run (`35874217261`) then assembled
and uploaded the complete verified wheelhouse successfully. The first
`publish=true` run (`35877751333`) uploaded all 34 wheels plus the inventory to
a draft release, but its post-upload check used GitHub's
`/releases/tags/<tag>` REST endpoint. That endpoint returns 404 for drafts, so
the workflow stopped without publishing. Draft and published release assets
must instead be queried through `gh release view --json assets`; the existing
draft remained private until all 34 remote digests were verified. That audit
passed, `vs-mlrt-v16.2.3` was published on 2026-09-23, and Pages index run
`35881526259` deployed the three entry projects successfully from `main`.
The first published-index consumer run (`35883332207`) passed install,
layout, complete uninstall, and reinstall for all three Windows entries. All
three Linux installs also resolved successfully, but the workflow invoked the
Windows-only verifier and therefore looked for `.dll` files on Linux. The
consumer workflow must select `smoke_linux_vcs_install.py` on Linux before the
final gate is repeated.

## 1. Scope and fixed baseline

This plan replaces the old model in which `generic`, `cu121`, and `cu129`
were self-contained payload tags. The new model publishes small, composable
wheel distributions and keeps three user-facing entry distributions:

- `vs-mlrt-generic`
- `vs-mlrt-cu121`
- `vs-mlrt-cu129`

All distributions in one release train use the same version, initially
`16.2.3`, and all internal dependencies use exact `==16.2.3` pins. CUDA
compatibility remains in the distribution name and not in the version.

The source baseline recorded by the imported fork is upstream
`AmusementClub/vs-mlrt` tag `v16.2.test1`, commit
`9e4d0c9dbbcaa28275772d30520330e69a58307c`. The current fork workflows build
the API4 plugins from the source under `plugins/vs-mlrt`; they do not copy
plugin changes from `vs-wheels`.

The runtime reduction below was validated against the 81 bundled ONNX models.
Those models collapse to 14 executable operator/input groups. All 14 groups
successfully built TensorRT engines with the retained cu121 and cu129 files.

## 2. Installation ownership rules

All native component wheels install unique files under one directory:

```text
site-packages/
  vapoursynth/plugins/vsmlrt/
    manifest.vs
    models/
    vsmlrt-cuda/
    vsncnn.dll|so
    vsov.dll|so
    vstrt.dll|so
    vstrt_rtx.dll|so
    OpenVINO support libraries
```

The directory layout is identical on Windows and Linux:

- native VapourSynth plugins (`vsncnn`, `vsov`, `vstrt`, and `vstrt_rtx`),
  OpenVINO support libraries, TBB, hwloc, and `cache.json` live directly in
  `vapoursynth/plugins/vsmlrt/`;
- every standard TensorRT, TensorRT-RTX, cuBLAS, and cuDNN runtime library,
  every builder resource, `trtexec`, `trtexec-build.json`, and
  `tensorrt_rtx` lives in `vapoursynth/plugins/vsmlrt/vsmlrt-cuda/`.

Do not preserve the old Linux release layout that placed TensorRT/CUDA shared
libraries at the plugin root. Linux supports the Windows-style subdirectory
layout when the ELF search paths are written correctly:

```text
vstrt.so and vstrt_rtx.so:       $ORIGIN:$ORIGIN/vsmlrt-cuda
vsmlrt-cuda/lib*.so*:            $ORIGIN
vsmlrt-cuda/trtexec:             $ORIGIN:$ORIGIN/..
vsmlrt-cuda/tensorrt_rtx:        $ORIGIN:$ORIGIN/..
```

Users must not run `patchelf` or set `LD_LIBRARY_PATH`. For the two plugins
built by this repository, encode the final path at link/install time in
`vstrt/CMakeLists.txt`:

```cmake
set_target_properties(vstrt PROPERTIES
    BUILD_RPATH "$ORIGIN;$ORIGIN/vsmlrt-cuda"
    INSTALL_RPATH "$ORIGIN;$ORIGIN/vsmlrt-cuda"
)
set_target_properties(vstrt_rtx PROPERTIES
    BUILD_RPATH "$ORIGIN;$ORIGIN/vsmlrt-cuda"
    INSTALL_RPATH "$ORIGIN;$ORIGIN/vsmlrt-cuda"
)
```

The repository-built `trtexec` target should similarly receive an
`INSTALL_RPATH` of `$ORIGIN`. NVIDIA's precompiled TensorRT, TensorRT-RTX, and
cu121 dependency libraries cannot inherit this repository's CMake settings;
the packaging job must apply `$ORIGIN` to those staged ELF files before wheel
creation and then verify the resulting dynamic section. `tensorrt_rtx` is also
an NVIDIA precompiled executable, so the packaging job sets its RUNPATH. This
is release-time normalization, not an end-user installation step.

The same normalization must run `patchelf --clear-execstack` and verify
`--print-execstack` for every staged ELF. TensorRT 8.6's Linux builder resource
ships with `GNU_STACK` marked executable; hardened runtimes reject it with
`cannot enable executable stack` even though the library does not require an
executable stack.

This layout was verified in `vpy:cu129` after removing the image's installed
`vs-mlrt`. With unmodified `$ORIGIN` on `vstrt.so`, loading failed with
`libnvinfer.so.11: cannot open shared object file`. After adding
`$ORIGIN/vsmlrt-cuda`, `/proc/self/maps` showed `libnvinfer.so.11`,
`libnvinfer_plugin.so.11`, and `libtensorrt_rtx.so.1` loaded from the staged
subdirectory. Packaged `trtexec` and `tensorrt_rtx` then built DPIR engines,
and `vstrt` and `vstrt_rtx` both rendered a 16x16 frame.

The existing `vsmlrt.py` locations for `trtexec` and `tensorrt_rtx` already
target `vsmlrt-cuda/`; do not move those tools to the root and do not change
their relative-path contract.

Only an entry distribution may own these files at the top of
`site-packages` or the shared plugin manifest:

```text
vsmlrt.py
vsmlrt_dll_paths.py
vs_mlrt_dll_paths.pth
vapoursynth/plugins/vsmlrt/manifest.vs
rm_vsmlrt/
```

Component distributions must not install `manifest.vs`, the Python wrapper,
or the uninstall command. Component wheels must not contain overlapping
files. The three entry distributions are mutually exclusive; Python package
metadata cannot express conflicts, so their build/install smoke tests must
reject an environment containing another entry distribution.

`vs-mlrt-cu121` and `vs-mlrt-cu129` must depend directly on the generic
components. They must not depend on `vs-mlrt-generic`, because that would give
two distributions ownership of `manifest.vs`, the wrapper, and the uninstall
command.

## 3. Final dependency trees

### 3.1 Generic

```text
vs-mlrt-generic
  == vs-mlrt-models
  == vs-ov
  == vs-ncnn
```

Its manifest contains exactly:

```text
[VapourSynth Manifest V1]
vsncnn
vsov
```

### 3.2 CUDA 12.1 / TensorRT 8.6

```text
vs-mlrt-cu121
  == vs-mlrt-models
  == vs-ov
  == vs-ncnn
  == vs-cublas-cu121
  == vs-cudnn-cu121
  == vs-tensorrt-core-cu121
       == vs-cublas-cu121
       == vs-cudnn-cu121
  == vs-tensorrt-builder-cu121
       == vs-tensorrt-core-cu121
  == vs-trtexec-cu121
       == vs-tensorrt-core-cu121
       == vs-tensorrt-builder-cu121
  == vs-trt-cu121
       == vs-tensorrt-core-cu121
```

Its manifest contains exactly:

```text
[VapourSynth Manifest V1]
vsncnn
vsov
vstrt
```

cuBLAS and cuDNN remain mandatory even when the corresponding tactic sources
are disabled. TensorRT 8.6's `nvinfer_plugin` directly imports them on Windows
and records them in ELF `DT_NEEDED` on Linux.

### 3.3 CUDA 12.9 / TensorRT 11.1 / TensorRT-RTX 1.5

```text
vs-mlrt-cu129
  == vs-mlrt-models
  == vs-ov
  == vs-ncnn
  == vs-tensorrt-core-cu129
  == vs-tensorrt-builder-cu129-base
       == vs-tensorrt-core-cu129
  == vs-tensorrt-builder-cu129-modern
       == vs-tensorrt-core-cu129
  == vs-trtexec-cu129
       == vs-tensorrt-core-cu129
       == vs-tensorrt-builder-cu129-base
       == vs-tensorrt-builder-cu129-modern
  == vs-trt-cu129
       == vs-tensorrt-core-cu129
  == vs-tensorrt-rtx-cu129
  == vs-trt-rtx-cu129
       == vs-tensorrt-rtx-cu129
```

Its manifest contains exactly:

```text
[VapourSynth Manifest V1]
vsncnn
vsov
vstrt
vstrt_rtx
```

TensorRT 11.1 and TensorRT-RTX 1.5 do not use the cu129 cuBLAS or cuDNN
payload for the bundled models. The standard TensorRT builder resources are
required by `trtexec`, but they are not a dependency of the TensorRT-RTX
builder.

## 4. Wheel contents

Names below are exact for the currently verified SDK versions. Linux wheels
must store a real file under the ELF SONAME required by `DT_NEEDED`; wheel ZIP
extraction must not rely on preserving symlinks.

Unless a table explicitly says otherwise, all CUDA/TensorRT files listed in
the cu121 and cu129 tables are installed under `vsmlrt/vsmlrt-cuda/`. The
`vstrt` and `vstrt_rtx` plugin files themselves remain at `vsmlrt/`.

### 4.1 Shared generic packages

| Distribution | Windows files | Linux files | Approximate unpacked size |
| --- | --- | --- | --- |
| `vs-mlrt-models` | `models/**/*.onnx` | same | 891.6 MiB |
| `vs-ncnn` | `vsncnn.dll` | `vsncnn.so` | 11.3 / 20.4 MiB |
| `vs-ov` | `vsov.dll`, `openvino.dll`, `openvino_c.dll`, `openvino_onnx_frontend.dll`, `openvino_auto_plugin.dll`, `openvino_auto_batch_plugin.dll`, `openvino_hetero_plugin.dll`, `openvino_intel_cpu_plugin.dll`, `openvino_intel_gpu_plugin.dll`, `openvino_intel_npu_plugin.dll`, `tbb12.dll`, `cache.json` | `vsov.so`, `libopenvino.so.2460`, `libopenvino_c.so.2460`, `libopenvino_onnx_frontend.so.2460`, OpenVINO device/auto/hetero plugins, `libtbb.so.12`, `libtbbmalloc.so.2`, `libtbbmalloc_proxy.so.2`, `libtbbbind_2_5.so.3`, `libhwloc.so.15` | 99.2 / 111.1 MiB |

`cache.json`, TBB, and hwloc belong to `vs-ov`. They are copied from the
OpenVINO runtime, and Linux `libtbbbind_2_5` needs `libhwloc`.

### 4.2 cu121 packages

| Distribution | Windows files | Linux files | Approximate unpacked size |
| --- | --- | --- | --- |
| `vs-cublas-cu121` | `cublas64_12.dll`, `cublasLt64_12.dll` | `libcublas.so.12`, `libcublasLt.so.12` | 607.4 / 593.8 MiB |
| `vs-cudnn-cu121` | `cudnn64_8.dll`, `cudnn_ops_infer64_8.dll`, `cudnn_cnn_infer64_8.dll`, `cudnn_adv_infer64_8.dll` | `libcudnn.so.8`, `libcudnn_ops_infer.so.8`, `libcudnn_cnn_infer.so.8`, `libcudnn_adv_infer.so.8` | 761.0 / 757.5 MiB |
| `vs-tensorrt-core-cu121` | `nvinfer.dll`, `nvinfer_plugin.dll`, `nvinfer_lean.dll`, `nvinfer_dispatch.dll`, `nvinfer_vc_plugin.dll`, `nvonnxparser.dll` | corresponding SONAME files under TensorRT ABI 8 | 362.5 / 298.3 MiB |
| `vs-tensorrt-builder-cu121` | `nvinfer_builder_resource.dll` | `libnvinfer_builder_resource.so.8.6.1` | 974.0 / 956.8 MiB |
| `vs-trtexec-cu121` | `trtexec.exe`, `trtexec-build.json` | `trtexec`, `trtexec-build.json` | 0.8 / 1.4 MiB |
| `vs-trt-cu121` | `vstrt.dll` | `vstrt.so` | 0.5 / 2.2 MiB |

Do not publish these former cu121 payload files:

```text
cudart*, cufft*, cufftw*, nvblas*, nvrtc*, nvrtc-builtins*, nvvm*, nvJitLink*
```

### 4.3 cu129 packages

| Distribution | Windows files | Linux files | Approximate unpacked size |
| --- | --- | --- | --- |
| `vs-tensorrt-core-cu129` | `nvinfer_11.dll`, `nvinfer_plugin_11.dll`, `nvinfer_lean_11.dll`, `nvinfer_dispatch_11.dll`, `nvinfer_vc_plugin_11.dll`, `nvonnxparser_11.dll` | corresponding SONAME files under TensorRT ABI 11 | 494.8 / 807.8 MiB |
| `vs-tensorrt-builder-cu129-base` | builder resources for PTX, SM75, SM80, SM86, SM89 | same architecture resources with their full Linux SDK names | 1,374.9 / 1,369.3 MiB |
| `vs-tensorrt-builder-cu129-modern` | builder resources for SM90, SM100, SM120 | same architecture resources with their full Linux SDK names | 1,416.5 / 1,415.0 MiB |
| `vs-trtexec-cu129` | `trtexec.exe`, `trtexec-build.json` | `trtexec`, `trtexec-build.json` | 1.1 / 2.3 MiB |
| `vs-trt-cu129` | `vstrt.dll` | `vstrt.so` | 0.5 / 2.4 MiB |
| `vs-tensorrt-rtx-cu129` | `tensorrt_rtx_1_5.dll`, `tensorrt_onnxparser_rtx_1_5.dll`, `tensorrt_rtx.exe` | `libtensorrt_rtx.so.1`, `libtensorrt_onnxparser_rtx.so.1`, `tensorrt_rtx` | 200.3 / 205.5 MiB |
| `vs-trt-rtx-cu129` | `vstrt_rtx.dll` | `vstrt_rtx.so` | 0.5 / 2.5 MiB |

Do not create `vs-cuda-runtime-cu129`, `vs-cudnn-cu129`, or
`vs-cuda-compiler-cu129`. Do not publish these former payload files:

```text
cudart*, cublas*, cudnn*, cufft*, cufftw*, nvblas*, nvrtc*,
nvrtc-builtins*, nvvm*, nvJitLink*
```

## 5. Binary provenance derived from the fork CI

The implementation must retain these sources and version pins unless a
separate upgrade is deliberately validated. A downloaded SDK supplies runtime
libraries; `vsncnn`, `vsov`, `vstrt`, and `vstrt_rtx` themselves are compiled
from this repository's API4 source.

| Output family | Windows source | Linux source |
| --- | --- | --- |
| VapourSynth headers | `vapoursynth/vapoursynth` tag R77 | tag R79 |
| `vsncnn` | local source; ncnn SDK from `AmusementClub/ncnn` release `250919-1038-g86efe80`, asset `ncnn-gpu-x64-windows.zip`; ONNX v1.19.0 built statically | local source; Tencent ncnn release `20250503`, Ubuntu 24.04 archive; ONNX commit `b86cc54efce19530fb953e4b21f57e6b3888534c` and protobuf v3.21.12 built statically |
| `vsov` and OpenVINO runtime | local source; `AmusementClub/openvino` release `2020.2-15171-g4655dd6ce3-2058-g5833781ddb`, asset `openvino-gpu-win64.zip`; protobuf commit `f0dc78d7e6e331b8c6bb2d5283e06aa26883ca7c`; ONNX commit `b8baa8446686496da4cc8fda09f2b6fe65c2a02c` | local source; official OpenVINO 2024.6.0.17404 Ubuntu 24.04 toolkit archive; ONNX/protobuf pins above |
| Models | all assets from `AmusementClub/vs-mlrt` releases `model-20211209`, `model-20220923`, and `contrib-models` | same platform-independent wheel |
| cu121 cuBLAS | NVIDIA CUDA redistrib manifest `redistrib_12.1.1.json`, component `libcublas` | NVIDIA CUDA 12.1.1 local toolkit installer |
| cu121 cuDNN | NVIDIA cuDNN `8.9.7.29_cuda12` Windows redistributable | corresponding Linux x86_64 tar.xz |
| TensorRT 8.6 runtime and builder | NVIDIA TensorRT 8.6.1.6 Windows CUDA 12.0 SDK ZIP | NVIDIA TensorRT 8.6.1.6 Linux x86_64 CUDA 12.0 tarball |
| TensorRT 11 runtime and builder | NVIDIA TensorRT Enterprise 11.1.0.106 Windows CUDA 12.9 SDK ZIP | corresponding Linux CUDA 12.9 tar.zst |
| `vstrt` | local API4 source, compiled against the selected TensorRT SDK with `USE_NVINFER_PLUGIN=ON` | same |
| `trtexec` | NVIDIA/TensorRT OSS tag `v8.6.1` or `v11.1`, nlohmann/json v3.11.3, then this fork's `tools/build_custom_trtexec.py` and local patches | same source and local builder |
| TensorRT-RTX runtime/parser/tool | NVIDIA TensorRT-RTX 1.5.0.114 Windows CUDA 12.9 SDK ZIP | corresponding Linux CUDA 12.9 tar.zst |
| `vstrt_rtx` | local API4 source compiled against TensorRT-RTX 1.5.0.114 | same |

The current CUDA workflows download additional CUDA and cuDNN families because
they still assemble the old monolithic payload. Those downloads are build
inputs or legacy staging behavior, not authority to include them in the new
cu129 wheels. Packaging allowlists, rather than broad `*.dll`/`*.so*` copies,
must implement the tables in section 4.

Every downloaded archive or CUDA redistrib component must have a recorded URL,
version, and SHA-256 in a generated provenance JSON. CUDA redistrib entries
already expose SHA-256 through NVIDIA's manifest; add explicit pinned digests
for the TensorRT, TensorRT-RTX, cuDNN, ncnn, OpenVINO, and model assets.

## 6. Release and index plan

This repository publishes a PyPI-compatible PEP 503 index through GitHub
Pages. It is not an upload to `pypi.org`: most native component wheels exceed
PyPI's normal per-file size limit. The user-facing install remains:

```text
pip install --index-url https://aliceteaparty.github.io/vapoursynth-api4-wheels/simple/ vs-mlrt-generic
pip install --index-url https://aliceteaparty.github.io/vapoursynth-api4-wheels/simple/ vs-mlrt-cu121
pip install --index-url https://aliceteaparty.github.io/vapoursynth-api4-wheels/simple/ vs-mlrt-cu129
```

Use one atomic release-train tag, `vs-mlrt-v<version>`, containing all Windows,
Linux, and platform-independent wheels. Create it as a draft, upload every
wheel and provenance file, verify remote SHA-256 values, and publish only when
the complete dependency closure is present. Publishing the release triggers
`.github/workflows/index-pages.yml`, which regenerates the PEP 503 index.

The three native build workflows are manual producers. They must use
`workflow_dispatch` only: a merge to `main` or creation of the release tag
must not rebuild roughly 10 GiB of already verified artifacts. The lightweight
contract workflow runs on relevant pull requests before merge. Finalizer-only
tools and tests do not trigger native builds.

The `github-pages` environment allows deployments only from `main`, so the
index workflow must not deploy directly from a `release` event (whose ref is
the release tag). Every publisher sends `repository_dispatch(index)` only
after release assets are verified and published; that event runs the index
workflow from the default branch and satisfies the environment policy.

Platform-independent wheels are release-train assets with exactly one owner,
even though each platform job builds a copy for its local installation smoke
test. Independent Windows and Linux builds of a `py3-none-any` wheel are not
assumed byte-identical or logically identical: checkout newline normalization
alone can change the packaged Python sources. The finalizer must explicitly
select the verified Linux copies of `vs-mlrt-models`, `vs-mlrt-generic`,
`vs-mlrt-cu121`, and `vs-mlrt-cu129` as the four authoritative shared wheels.
It must still validate every original artifact against all six component
inventories. A same-name wheel conflict without an explicitly selected
authoritative shared copy is a hard failure; filename-order or first-seen
deduplication is forbidden.

`vs-ncnn` and `vs-ov` are shared by all three dependency closures but remain
platform-specific native wheels. The finalizer must select the Windows generic
build and Linux generic build as their authoritative copies for the respective
platform. CUDA variant builds may rebuild these wheels for their isolated
installation smoke tests, but those duplicate outputs are evidence checked by
their inventories, not additional release assets.

Build and verify in this order:

1. `vs-mlrt-models`, `vs-ov`, and `vs-ncnn`.
2. cu121 leaf runtime wheels, TensorRT core, builder, `trtexec`, and `vstrt`.
3. cu129 TensorRT core, both builder shards, `trtexec`, and `vstrt`.
4. cu129 TensorRT-RTX runtime/tool and `vstrt_rtx`.
5. Build the three entry wheels last from the exact component versions.
6. Install each entry wheel from a local wheelhouse with dependency resolution
   and no preinstalled vs-mlrt distributions.
7. Upload all wheels to the draft release, compare local and remote digests,
   publish the release, and wait for the Pages deployment.
8. Repeat clean installs from the published Pages index on Windows and Linux.

Required gates include:

- every individual release asset is below 2 GiB;
- wheel RECORD entries own no overlapping files except directories;
- only entry wheels contain wrapper files, `manifest.vs`, and `rm_vsmlrt`;
- Windows PE imports and Linux ELF `DT_NEEDED` resolve within the selected
  dependency closure, except the NVIDIA driver and normal system libraries;
- Linux files have the required SONAME name and `$ORIGIN` RUNPATH;
- no Linux wheel ELF requests an executable stack;
- Windows and Linux wheels produce the same `vsmlrt-cuda/` ownership layout;
- Linux `vstrt.so` and `vstrt_rtx.so` load their runtime libraries from
  `vsmlrt-cuda/` without `LD_LIBRARY_PATH` or a system TensorRT installation;
- all 81 bundled models are represented by the 14 TensorRT build groups;
- cu121 and cu129 `trtexec` build an engine using packaged files in an
  environment that cannot fall back to a system CUDA/TensorRT installation;
- cu129 `tensorrt_rtx` builds an engine and `vstrt_rtx` renders it;
- `vstrt` renders a freshly built engine for both CUDA lines;
- the installed manifest exactly matches the selected entry package;
- published-index installs produce the same file hashes as staged installs.

## 7. `rm_vsmlrt` design

### 7.1 Naming and ownership

Each of the three mutually exclusive entry wheels ships the same Python
package:

```text
rm_vsmlrt/
  __init__.py
  __main__.py
  cli.py
```

and installs both `rm_vsmlrt.cmd` and an extensionless POSIX shell wrapper in
the scripts directory. Each wrapper runs the module in the foreground with
the environment's Python interpreter.

Supported invocations are:

```text
python -m rm_vsmlrt
rm_vsmlrt
```

The module and command wrappers use the same underscore spelling: `rm_vsmlrt`.

### 7.2 Why deletion alone is insufficient

Deleting only `vapoursynth/plugins/vsmlrt` and `vsmlrt.py` leaves every wheel's
`.dist-info` metadata installed. Pip would continue to report the components
as satisfied and could skip them on a later reinstall. Complete removal must:

1. uninstall every known vs-mlrt distribution through the running Python's
   `python -m pip`;
2. remove untracked/generated files left in the shared plugin directory;
3. remove legacy wrapper files left by old VCS or monolithic installs.

### 7.3 Exact uninstall allowlist

The command operates on a fixed, normalized distribution-name allowlist. It
must include the new packages:

```text
vs-mlrt-generic
vs-mlrt-cu121
vs-mlrt-cu129
vs-mlrt-models
vs-ov
vs-ncnn
vs-cublas-cu121
vs-cudnn-cu121
vs-tensorrt-core-cu121
vs-tensorrt-builder-cu121
vs-trtexec-cu121
vs-trt-cu121
vs-tensorrt-core-cu129
vs-tensorrt-builder-cu129-base
vs-tensorrt-builder-cu129-modern
vs-trtexec-cu129
vs-trt-cu129
vs-tensorrt-rtx-cu129
vs-trt-rtx-cu129
```

It must also remove known superseded distributions from this repository and
the fork:

```text
vs-mlrt
vs-mlrt-payload-generic
vs-mlrt-payload-cu121
vs-mlrt-payload-cu129
vs-mlrt-cu129-payload-2
vs-mlrt-cu129-payload-3
```

Do not uninstall packages discovered merely because their name contains
`mlrt`; only names in the reviewed allowlist are eligible.

### 7.4 Execution sequence

1. Resolve the interpreter, site-packages directories, installed allowlisted
   distributions, and the actual `vapoursynth` package directory.
2. Refuse paths outside the resolved site-packages roots. Do not follow a
   symlink or junction that escapes those roots.
3. Print the distributions and filesystem targets. Interactive use requires
   confirmation; CI uses `--yes`. `--dry-run` performs no mutation.
4. Run `sys.executable -m pip uninstall -y` for installed component and legacy
   distributions, then uninstall all entry distributions, including the one
   that supplied the command.
5. Delete the remaining shared directory
   `vapoursynth/plugins/vsmlrt/`. This intentionally removes generated
   `.engine`, `.cache`, and `.lock` files as part of a complete uninstall.
6. Remove only these reviewed legacy top-level paths when present:
   `vsmlrt.py`, `vsmlrt_dll_paths.py`, `vs_mlrt_dll_paths.pth`, and their
   matching `__pycache__` entries.
7. Rescan `importlib.metadata` and the filesystem. A nonempty allowlisted
   distribution set or remaining reviewed path is an error.

The Windows command is a batch wrapper rather than a generated `.exe` console
launcher; POSIX and Git Bash use the extensionless shell wrapper. Windows runs
all component uninstalls and payload cleanup in the foreground, then starts a
silent helper only for removal of the running wrapper and its owning entry
wheel after the foreground Python process exits. This avoids `cmd.exe` rereading
a deleted batch file. Both wrappers invoke `python -m rm_vsmlrt` in the
foreground, so the shell does not return to its prompt until all user-visible
uninstall and cleanup work has completed.

Recommended options and exit behavior:

```text
--dry-run       show exact pip and filesystem actions
--yes           skip the interactive confirmation
--keep-engines  preserve generated *.engine/*.cache files outside the plugin
                directory only; never preserve a partial plugin directory
--verbose       show subprocess output and resolved paths
```

- Exit 0: all allowlisted distributions and reviewed files are absent.
- Exit 1: pip uninstall or filesystem cleanup failed.
- Exit 2: unsafe path, invalid arguments, or user declined confirmation.

The tool must never edit global PATH, delete the parent `vapoursynth/plugins`
directory, uninstall VapourSynth itself, or remove unrelated plugins.

### 7.5 Uninstall verification

Test the command from each entry wheel on Windows and Linux:

1. Install from a clean local wheelhouse and confirm every expected component
   distribution is present.
2. Generate at least one TensorRT engine/cache for CUDA entries.
3. Run `python -m rm_vsmlrt --yes`; verify metadata, wrapper files, plugin
   directory, engines, and caches are absent.
4. Reinstall the same entry normally and run a smoke inference. This proves no
   stale `.dist-info` prevented dependency restoration.
5. Repeat through `rm_vsmlrt`/`rm_vsmlrt.exe` to exercise the Windows launcher
   handoff.
6. Place an unrelated plugin beside `vsmlrt` and prove its hash is unchanged.
7. Exercise `--dry-run`, declined confirmation, a read-only file, a path
   escape symlink/junction, and a partially installed legacy package set.

## 8. Implementation work breakdown

1. Replace broad runtime-copy rules with explicit per-distribution allowlists.
2. Change the Linux `vstrt` and `vstrt_rtx` CMake `BUILD_RPATH` and
   `INSTALL_RPATH` to include `$ORIGIN/vsmlrt-cuda`; set the repository-built
   `trtexec` install RPATH to `$ORIGIN`.
3. Keep release-time `patchelf` normalization only for NVIDIA prebuilt ELF
   files and verify every final RUNPATH before wheel creation.
4. Add one build project and wheel hook per component in section 4.
5. Change all entry `pyproject.toml` files to direct, exact component
   dependencies and remove entry-to-entry dependencies.
6. Add shared entry-wheel content for the wrapper, manifest generator, and
   `rm_vsmlrt` package, without yet enabling publication.
7. Extend Windows PE, Linux ELF, RECORD-overlap, model-matrix, and uninstall
   tests.
8. Produce all wheels as Actions artifacts and pass clean local wheelhouse
   installs on both systems.
9. Enable draft release assembly and remote digest verification.
10. Enable release publication and Pages dispatch only after the published
   index consumer tests pass.

Do not reuse the old monolithic payload volumes as dependencies of the new
wheels. They are evidence and test fixtures only; the final release must be
assembled from the component wheel outputs described here.
