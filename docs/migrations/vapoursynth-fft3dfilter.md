# vapoursynth-fft3dfilter migration record

Status: prepared for CI; not yet published or consumer-verified.

## Aligned revisions

- Root upstream:
  `VFR-maniac/VapourSynth-FFT3DFilter@b023e21954423f29fdefcb54a6b0540deb3bdac4`
- Direct fork chain: `myrsloik/VapourSynth-FFT3DFilter`
- Former fork:
  `RyougiKukoc/VapourSynth-FFT3DFilter-vcs@a1753a132175a2678fe914348280a1052da30dea`
- Fork merge base: `b023e21954423f29fdefcb54a6b0540deb3bdac4`
- Upstream import: squashed subtree at `plugins/vapoursynth-fft3dfilter`

The root-upstream `master` still equals the exact common baseline. The fork is
116 commits ahead of that baseline, including 113 source/history commits
through the API4 port and three release-packaging commits. Annotated tag
`R2.1` resolves to fork head. Distribution version `2.1` is a valid public
PEP 440 version.

## Source-level API4 port

The port replaces the bundled API3 headers and plugin interface with
`VapourSynth4.h`, `VSHelper4.h`, and `VapourSynthPluginInit2`. API4 map, node,
frame, format, dependency, and video-filter interfaces span `Plugin.cpp`,
`FFT3DFilter.cpp`, `FFT3DFilter.h`, `FFT3DFilterTransform.cpp`, and
`fft3dfilter_c.cpp`. The remaining fork changes contain the long-lived filter
maintenance, Meson/MSVC projects, Release-backed wheel packaging, and smoke
tools. No plugin source or patch from `vs-wheels` is included.

## Monorepo adaptations

- Package: `vapoursynth-fft3dfilter==2.1`
- Workflow: `Package - vapoursynth-fft3dfilter`
- Release tag: `vapoursynth-fft3dfilter-v2.1`
- Windows and Linux x86_64 only; macOS and ARM are rejected by the build hook
- Release-backed installs use this repository and trigger the Pages index

The Windows UCRT64, manylinux/FFTW build, explicit payload load, installed
wheel autoload, deterministic frame smoke, and isolated native fallback
commands are copied from the fork's verified `build-msys2.yml`. Only monorepo
working paths, package-specific artifact/tag handling, and Release/Pages
publication are adapted.
