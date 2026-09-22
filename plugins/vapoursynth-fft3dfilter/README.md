# VapourSynth FFT3DFilter

FFT3DFilter provides the frequency-domain denoising and sharpening filter
`core.fft3dfilter.FFT3DFilter`. The plugin is an API4 CPU filter built on
single-precision FFTW3. It has no accelerated backend.

## Install

Windows x86_64 and Linux x86_64 users can install the package from the project
index:

```powershell
pip install --extra-index-url https://aliceteaparty.github.io/vapoursynth-api4-wheels/simple/ vapoursynth-fft3dfilter
```

Version `2.1` is paired with Release tag
`vapoursynth-fft3dfilter-v2.1`. The checked-in Release marker selects one of
these platform-specific payloads:

```text
vapoursynth-fft3dfilter-v2.1/fft3dfilter-msys2-ucrt64.zip  Windows x86_64
vapoursynth-fft3dfilter-v2.1/fft3dfilter-linux-x86_64.zip  Linux x86_64
```

The installed package places the matching native module and manifest under:

```text
site-packages/vapoursynth/plugins/fft3dfilter/
  fft3dfilter.dll       # Windows
  fft3dfilter.so        # Linux
  manifest.vs
```

The Linux Release zip has the same top-level `fft3dfilter/` directory and
contains `fft3dfilter.so` plus the manifest. Its FFTW3f dependency is linked
statically, so the Release payload has no separate FFTW runtime library to
copy. The published Linux wheel is tagged `manylinux_2_27_x86_64`, matching the
VapourSynth R79 Linux runtime floor even though the plugin is built in a glibc
2.17 environment.

## Local fallback

The Release payload is an optimization. On supported platforms, the build hook
performs a native Meson build when the asset is unavailable or when
`FFT3DFILTER_FORCE_BUILD=1` is set:

```powershell
$env:FFT3DFILTER_FORCE_BUILD = "1"
pip install "vapoursynth-fft3dfilter @ git+https://github.com/AliceTeaParty/vapoursynth-api4-wheels.git#subdirectory=plugins/vapoursynth-fft3dfilter"
```

On Linux, the isolated PEP 517 build installs `VapourSynth>=79` as a build
dependency and prepends its `vapoursynth/pkgconfig` directory to an existing
`PKG_CONFIG_PATH`. Install a C++17 compiler, Meson, Ninja, pkg-config, and the
FFTW3f development package first; for Debian/Ubuntu this is `libfftw3-dev`.
The local fallback links the compatible system FFTW3f runtime. Windows retains
its existing MSYS2/UCRT64 fallback. macOS and ARM are not supported.

For a local or test Release payload, set `FFT3DFILTER_PREBUILT_URL` to a zip
with the matching native suffix. A Linux build never accepts a DLL, and a
Windows build never accepts a Linux `.so` payload.

## Verification

The Linux Release smoke disables autoload, explicitly calls `LoadPlugin` on
`fft3dfilter.so`, renders a deterministic 64x48 YUV420P8 case at frames 0, 3,
and 11, records SHA-256 frame data and PlaneStats, and verifies the documented
`bt=6` error. The installed-wheel smoke separately proves manifest autoload.
The CI also forces an ordinary isolated source build with an intentionally
unrelated `PKG_CONFIG_PATH` to verify the native fallback's VapourSynth SDK
discovery.

An API3 baseline binary is not present in this repository or the validation
environment, so no API3/API4 output-equivalence claim is made. The source scan
contains no API3 markers; this packaging work does not alter filter behavior.

## Local build

Meson remains available for native builds:

```powershell
meson setup build
meson compile -C build
```

Filter parameters and examples are documented in
[doc/fft3dfilter.md](doc/fft3dfilter.md).

## License

The upstream source and bundled `LICENSE` file are GPL v2.
