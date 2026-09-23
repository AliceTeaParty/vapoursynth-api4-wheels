# vapoursynth-dfttest2 migration record

Status: the three intended distributions are published and verified on
Windows and Linux x86_64. One mistakenly named intermediate Release is now a
draft and excluded from Pages; permanent deletion is pending explicit approval.

## Aligned revisions

- Root upstream: `AmusementClub/vs-dfttest2@65b4379eb1ac5da50be985ef843f17107fb398c5` (`v10`)
- Fork CPU head: `RyougiKukoc/vs-dfttest2-api4@5f19b151cf8d09bd43f4a0a67815569782d44bc7`
- Fork CUDA 12.1 head: `597cfdae67d2a636c600bc62cfe81bc929f2f1a9`
- Fork CUDA 12.9 head: `51cae090eea28cd3c479a003aaf82e61b31b24e2`
- Vectorclass dependency: `vectorclass/version2@a0a33986fb1fe8a5b7844e8a1b1f197ce19af35d`

The root upstream was imported as a squashed subtree. Fork changes through the
cu129 head were compressed into commit `5b96d5b4`; the three fork tags differ
only in the committed variant selector and a release-workflow correction. The
upstream vectorclass gitlink was replaced with an exact nested squash subtree,
so combined-repository checkouts do not depend on an invalid relative
submodule path.

## API4 classification

The CPU, NVRTC, and cuFFT/CUDA translation units export
`VapourSynthPluginInit2`, register against `VAPOURSYNTH_API_VERSION`, and use
the API4 node/frame interfaces. This is a source-level API4 port. No plugin
modification from `vs-wheels` was copied.

## Distribution mapping

- `vapoursynth-dfttest2-cpu==10.2`: Python helper plus CPU plugin
- `vapoursynth-dfttest2-cu121==10.2`: helper, CPU plugin, CUDA 12.1 NVRTC and cuFFT plugins, and runtime libraries
- `vapoursynth-dfttest2-cu129==10.2`: helper, CPU plugin, CUDA 12.9 NVRTC and cuFFT plugins, and runtime libraries

Each distribution is a complete wheel without another DFTTest2 distribution
as a dependency. They install the same helper and native paths, so one variant
must be uninstalled before another is installed.

## Preserved build flow

The fork's MSVC builds, micromamba CUDA package pins, manylinux2014 CPU build,
UBI8 CUDA builds, native contract/regression checks, explicit and autoload
smokes, source-install checks, package-wide GLIBC/GLIBCXX checks, and static
NVRTC packaging are retained. Monorepo-only changes select public distribution
names, use combined-repository paths and tags, verify exact four-asset Release
inventories, and dispatch the Pages index.

## Intended releases

- `https://github.com/AliceTeaParty/vapoursynth-api4-wheels/releases/tag/vapoursynth-dfttest2-cpu-v10.2`
- `https://github.com/AliceTeaParty/vapoursynth-api4-wheels/releases/tag/vapoursynth-dfttest2-cu121-v10.2`
- `https://github.com/AliceTeaParty/vapoursynth-api4-wheels/releases/tag/vapoursynth-dfttest2-cu129-v10.2`

The intermediate `vapoursynth-dfttest2-generic-v10.2` Release and tag were
created before the user corrected the intended CPU package name. The Release
was changed to a reversible draft, and Pages run `35814057724` proved the
generic project is no longer exposed. The draft and tag remain pending explicit
approval for destructive cleanup and are not part of the supported mapping.
