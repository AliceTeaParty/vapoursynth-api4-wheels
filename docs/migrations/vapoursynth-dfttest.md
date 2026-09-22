# vapoursynth-dfttest migration record

Status: published and verified on Windows and Linux x86_64.

## Aligned revisions

- Upstream: `HomeOfVapourSynthEvolution/VapourSynth-DFTTest@bc5e0186a7f309556f20a8e9502f2238e39179b8`
- Fork: `RyougiKukoc/VapourSynth-DFTTest-api4@e11c7ea2564843b531f0ec366a6219b293ae7948`
- Fork merge base: `bc5e0186a7f309556f20a8e9502f2238e39179b8`
- Upstream import: squashed subtree at `plugins/vapoursynth-dfttest`

The fork is three commits ahead and its `v1.1` tag equals the imported head.
The audited PEP 440 version is `1.1`.

## Source-level API4 port

`DFTTest/DFTTest.cpp`, its header, and SSE2/AVX2/AVX512 implementation files
form the API4 migration. The fork uses `VapourSynthPluginInit2`, API4 map,
frame, node, format, dependency, and video-filter interfaces. No source or
plugin patch from `vs-wheels` is included.

## Monorepo adaptations

- Workflow: `Package - vapoursynth-dfttest`
- Release tag: `vapoursynth-dfttest-v1.1`
- Only Windows/Linux x86_64 are accepted.
- Publication triggers the Pages index.

All build and smoke commands come from the fork's verified
`.github/workflows/build-and-release.yml`; only paths and publication differ.

## Published result

- Release: `vapoursynth-dfttest-v1.1`
- Windows/Linux: R80 online wheel installs rendered identical deterministic frames
