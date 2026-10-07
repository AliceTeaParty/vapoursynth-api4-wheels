# VapourSynth API4 Wheels

This repository publishes Windows and Linux x86_64 wheels for maintained
VapourSynth API4 ports. Original upstream projects are imported with
`git subtree`; the API4 and packaging work is kept as a separate, squashed
commit for each plugin.

Native plugin wheels support Windows and Linux x86_64. macOS and ARM native
plugin wheels are not published.

Python modules are maintained separately under `modules/`. rksfunc and rkstool
keep source authority in their original repositories and use fixed-commit CI
checkouts. The 12 components of `vs-collection-rk` are central-owned subtrees;
each preserves its canonical upstream baseline and one combined Collection
patch. The entry package installs their exact wheel versions together.
See [modules/README.md](modules/README.md), [Collection maintenance](modules/COLLECTION.md)
and the separate module table in [VERSIONS.md](VERSIONS.md). Builds and
publication use separate manual workflows.

## Relationship to vs-wheels

This repository was inspired by Jaded-Encoding-Thaumaturgy's
[vs-wheels](https://github.com/Jaded-Encoding-Thaumaturgy/vs-wheels). After
maintaining API4 forks and builds for a long time, we adopted its idea of
organizing prebuilt plugins as a dedicated wheel repository and package index.
The two repositories are independent; vs-wheels is the inspiration for this
repository's distribution model, not the upstream of the plugin ports hosted
here.

This repository is also not intended to permanently replace official upstream
packages. If a plugin's upstream project gains API4 support and provides its
own pip-installable package, we will review the overlap. In most cases, we
expect to deprecate the corresponding package here and eventually remove it
once a reasonable migration path exists.

Where the repositories package the same plugins, they serve somewhat different
compatibility goals. vs-wheels generally tracks the current CUDA toolchain -- at
the time of writing, its BM3DCUDA and DFTTest2 CUDA workflows default to CUDA
13.4, and its vs-mlrt TensorRT packages use the CUDA 13 line -- which targets
systems with sufficiently recent NVIDIA drivers. This repository instead
publishes separate `cu121` and `cu129` builds for BM3DCUDA, DFTTest2, and
vs-mlrt. Those two CUDA lines were chosen for their substantial existing user
base, so users can select a build compatible with the drivers already deployed
on their systems.

For vs-mlrt in particular, this repository also aims to preserve the public
behavior and workflow of upstream's `vsmlrt.py`. We make the compatibility
changes needed for API4, packaged runtimes, and the wheel layout, while trying
to avoid forcing large changes on existing user scripts.

## Install

The package index is hosted on GitHub Pages:

```console
python -m pip install \
  --extra-index-url https://aliceteaparty.github.io/vapoursynth-api4-wheels/simple/ \
  "vs-nlq==1.2.0+alice.1"
```

Packages still need their normal Python dependencies from PyPI, which is why
the project index is supplied with `--extra-index-url`.

All centrally maintained wheels use the PEP 440 local label `+alice.1`.
Use the exact versions below when installing with `--extra-index-url`: pip
compares candidates across both indexes and does not prioritize this index.
For example, `2.16+alice.1` is still older than `2.17`; the suffix alone does
not prevent installing a different same-name PyPI package.

```console
python -m pip install --force-reinstall --extra-index-url https://aliceteaparty.github.io/vapoursynth-api4-wheels/simple/ "vapoursynth-bm3dcpu==2.16+alice.1"
```

The temporary `bm3dcuda-cpu` rename has been withdrawn. If you installed that
package, run `python -m pip uninstall -y bm3dcuda-cpu` before the commands
above, because both distributions own the same plugin files.

## Packages

| Upstream | Package |
| --- | --- |
| [quietvoid/vs-nlq](https://github.com/quietvoid/vs-nlq) | `vs-nlq` |
| [HomeOfVapourSynthEvolution/VapourSynth-NNEDI3CL](https://github.com/HomeOfVapourSynthEvolution/VapourSynth-NNEDI3CL) | `vapoursynth-nnedi3cl` |
| [dubhatervapoursynth/vapoursynth-smoothuv](https://github.com/dubhatervapoursynth/vapoursynth-smoothuv) | `vapoursynth-smoothuv` |
| [HomeOfVapourSynthEvolution/VapourSynth-DFTTest](https://github.com/HomeOfVapourSynthEvolution/VapourSynth-DFTTest) | `vapoursynth-dfttest` |
| [Khanattila/KNLMeansCL](https://github.com/Khanattila/KNLMeansCL) | `vapoursynth-knlm` |
| [HomeOfVapourSynthEvolution/VapourSynth-Retinex](https://github.com/HomeOfVapourSynthEvolution/VapourSynth-Retinex) | `vapoursynth-retinex` |
| [WolframRhodium/VapourSynth-BM3DCUDA](https://github.com/WolframRhodium/VapourSynth-BM3DCUDA) | `vapoursynth-bm3dcpu` /<br> `vapoursynth-bm3dcuda-cu121` /<br> `vapoursynth-bm3dcuda-cu129` |
| [AmusementClub/vs-dfttest2](https://github.com/AmusementClub/vs-dfttest2) | `vapoursynth-dfttest2-cpu` /<br> `vapoursynth-dfttest2-cu121` /<br> `vapoursynth-dfttest2-cu129` |
| [AmusementClub/vs-mlrt](https://github.com/AmusementClub/vs-mlrt) | `vs-mlrt-generic` /<br> `vs-mlrt-cu121` /<br> `vs-mlrt-cu129` (Entry packages) |
| [dubhatervapoursynth/vapoursynth-tcomb](https://github.com/dubhatervapoursynth/vapoursynth-tcomb) | `vapoursynth-tcomb` |
| [VFR-maniac/VapourSynth-FFT3DFilter](https://github.com/VFR-maniac/VapourSynth-FFT3DFilter) | `vapoursynth-fft3dfilter` |
| [LumeCraft-Labs/vs-cfl](https://github.com/LumeCraft-Labs/vs-cfl) | `vs-cfl` |
| [HomeOfVapourSynthEvolution/VapourSynth-TCanny](https://github.com/HomeOfVapourSynthEvolution/VapourSynth-TCanny) | `vapoursynth-tcanny` |
| [vapoursynth/vs-miscfilters-obsolete](https://github.com/vapoursynth/vs-miscfilters-obsolete) | `vapoursynth-misc` |

## Wheel versions

These are the versions configured for the next manual release, not a claim
that all assets are already published. rksfunc and rkstool retain their
upstream versions; all other distributions carry our local build label.

| Distribution | Version |
| --- | --- |
| `csmod` | `0.3.0.post1+alice.1` |
| `fvsfunc` | `0.3.0.post1+alice.1` |
| `getfnative` | `0.3.0.post1+alice.1` |
| `havsfunc` | `33.post1+alice.1` |
| `kagefunc` | `0.3.0.post1+alice.1` |
| `muvsfunc` | `0.3.0.post1+alice.1` |
| `mvsfunc` | `11.post1+alice.1` |
| `nnedi3-resample` | `2.post1+alice.1` |
| `nnedi3-rpow2` | `1.1.0.post1+alice.1` |
| `sdering-fix` | `0.3.0.post1+alice.1` |
| `vapoursynth-bm3dcpu` | `2.16+alice.1` |
| `vapoursynth-bm3dcuda-cu121` | `2.16+alice.1` |
| `vapoursynth-bm3dcuda-cu129` | `2.16+alice.1` |
| `vapoursynth-dfttest` | `1.1+alice.1` |
| `vapoursynth-dfttest2-cpu` | `10.2+alice.1` |
| `vapoursynth-dfttest2-cu121` | `10.2+alice.1` |
| `vapoursynth-dfttest2-cu129` | `10.2+alice.1` |
| `vapoursynth-fft3dfilter` | `2.1+alice.1` |
| `vapoursynth-knlm` | `1.1.2+alice.1` |
| `vapoursynth-misc` | `2.1+alice.1` |
| `vapoursynth-nnedi3cl` | `8.1+alice.1` |
| `vapoursynth-retinex` | `4.1+alice.1` |
| `vapoursynth-smoothuv` | `3.1+alice.1` |
| `vapoursynth-tcanny` | `14.1+alice.1` |
| `vapoursynth-tcomb` | `4.2+alice.1` |
| `vs-cfl` | `1.0.2+alice.1` |
| `vs-collection-rk` | `0.4.0+alice.1` |
| `vs-cublas-cu121` | `16.2.2+alice.1` |
| `vs-cudnn-cu121` | `16.2.2+alice.1` |
| `vs-mlrt` | `16.2.2+alice.1` |
| `vs-mlrt-cu121` | `16.2.6+alice.1` |
| `vs-mlrt-cu129` | `16.2.6+alice.1` |
| `vs-mlrt-generic` | `16.2.6+alice.1` |
| `vs-mlrt-models` | `16.2.2+alice.1` |
| `vs-ncnn` | `16.2.2+alice.1` |
| `vs-nlq` | `1.2.0+alice.1` |
| `vs-ov` | `16.2.2+alice.1` |
| `vs-tensorrt-builder-cu121` | `16.2.2+alice.1` |
| `vs-tensorrt-builder-cu129-base` | `16.2.2+alice.1` |
| `vs-tensorrt-builder-cu129-modern` | `16.2.2+alice.1` |
| `vs-tensorrt-core-cu121` | `16.2.2+alice.1` |
| `vs-tensorrt-core-cu129` | `16.2.2+alice.1` |
| `vs-tensorrt-rtx-cu129` | `16.2.2+alice.1` |
| `vs-trt-cu121` | `16.2.2+alice.1` |
| `vs-trt-cu129` | `16.2.2+alice.1` |
| `vs-trt-rtx-cu129` | `16.2.2+alice.1` |
| `vs-trtexec-cu121` | `16.2.2+alice.1` |
| `vs-trtexec-cu129` | `16.2.2+alice.1` |
| `vstaambk` | `0.3.0.post1+alice.1` |
| `yvsfunc` | `0.3.0.post1+alice.1` |
| `rksfunc` | `1.1.5` (upstream) |
| `rkstool` | `1.1.3` (upstream) |

vs-mlrt entry packages and their component/model packages have separate
version sequences. Every internal requirement pins the exact version in
this table, including `+alice.1`. The legacy `vs-mlrt` source package is
listed for completeness; new installs use one of the three entry packages.

## Choosing a variant

The `cu121` and `cu129` suffixes identify the CUDA runtime line bundled in the
wheel. Installing a prebuilt wheel does not require a matching CUDA Toolkit,
but the CUDA packages do require an NVIDIA GPU and a driver compatible with
the selected runtime. Install only one variant of a project in an environment;
the variants place plugins at the same paths.

### BM3DCUDA

- `vapoursynth-bm3dcpu` is for CPU-only systems or users who only need the
  `core.bm3dcpu` backend. It requires an AVX2-capable CPU.
- `vapoursynth-bm3dcuda-cu121` is for NVIDIA users on the older CUDA 12.1
  runtime line. It installs both `core.bm3dcpu` and the `core.bm3dcuda_rtc` backend (`core.bm3dcuda` is not included).
- `vapoursynth-bm3dcuda-cu129` installs the same two backends for systems whose
  NVIDIA driver supports CUDA 12.9.

### DFTTest2

- `vapoursynth-dfttest2-cpu` installs only the CPU backend and does not require
  NVIDIA hardware.
- `vapoursynth-dfttest2-cu121` installs the CPU, NVRTC, and cuFFT backends
  with the CUDA 12.1 runtime libraries.
- `vapoursynth-dfttest2-cu129` installs the same backends with the CUDA 12.9
  runtime libraries and requires a driver that supports that runtime.

### vs-mlrt

`vs-mlrt-generic`, `vs-mlrt-cu121`, and `vs-mlrt-cu129` are the three
user-facing **entry packages**. Choose and install exactly one; pip then pulls
in the matching, version-pinned component wheels. The entry wheel owns the
Python API, autoload manifest, and uninstall helper; its dependencies own the
models and native backends. Every entry resolves to the models, NCNN/Vulkan,
and OpenVINO components. The choice is:

- `vs-mlrt-generic` for NCNN/Vulkan and OpenVINO only. It does not install a
  TensorRT backend and is recommended for those who do not have an NVIDIA GPU.
- `vs-mlrt-cu121` for the common backends plus standard TensorRT 8.6 on the
  CUDA 12.1 runtime line.
- `vs-mlrt-cu129` for the common backends plus standard TensorRT 11.1 and
  TensorRT-RTX 1.5 on the CUDA 12.9 runtime line.

The component split is an implementation detail; users should install an entry
package rather than selecting these dependencies individually. Its condensed
dependency tree is:

```text
vs-mlrt-generic [entry]
`-- common components
    |-- vs-mlrt-models
    |-- vs-ncnn
    `-- vs-ov

vs-mlrt-cu121 [entry]
|-- common components above
`-- TensorRT 8.6 / CUDA 12.1 components
    |-- vs-cublas-cu121 + vs-cudnn-cu121
    |-- vs-tensorrt-core-cu121 + vs-tensorrt-builder-cu121
    `-- vs-trtexec-cu121 + vs-trt-cu121

vs-mlrt-cu129 [entry]
|-- common components above
|-- TensorRT 11.1 / CUDA 12.9 components
|   |-- vs-tensorrt-core-cu129
|   |-- vs-tensorrt-builder-cu129-base + vs-tensorrt-builder-cu129-modern
|   `-- vs-trtexec-cu129 + vs-trt-cu129
`-- TensorRT-RTX 1.5 components
    `-- vs-tensorrt-rtx-cu129 + vs-trt-rtx-cu129
```

For example:

```console
python -m pip install --extra-index-url \
  https://aliceteaparty.github.io/vapoursynth-api4-wheels/simple/ \
  "vs-mlrt-generic==16.2.6+alice.1"
```

To remove a vs-mlrt installation and its installed component wheels, run:

```console
python -m rm_vsmlrt_helper
```

The helper prints the exact `python -m pip uninstall -y ...` command for the
reviewed installed vs-mlrt distributions. Review and run that command; the
helper does not invoke pip or delete files itself.

## Repository layout

- `plugins/<name>`: upstream subtree plus this project's squashed patch
- `modules/<name>/module.toml`: upstream module registration; temporary source
  and wheel directories are ignored by Git
- `modules/collection.json`: current Collection component and entry versions
- `modules/collection-history.json`: initial canonical imports and combined patches
- `VERSIONS.md`: separate native-plugin and Python-module version records
- `.github/workflows/package-modules.yml`: manual shared module preview builds
- `.github/workflows/publish-modules.yml`: manual publication of a verified wheel
- `.github/workflows/package-<name>.yml`: build, test, and release workflow
- `scripts/generate_index.py`: GitHub Release to PEP 503 index generator

## Licenses

This repository is a collection of independently licensed upstream projects,
not a single relicensed work. Each plugin retains its upstream license in its
own directory. See [LICENSES.md](LICENSES.md) for the upstream audit, license
mapping, and third-party notices.
