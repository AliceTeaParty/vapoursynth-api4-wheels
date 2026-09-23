# vapoursynth-bm3dcuda migration record

Status: three distributions published and verified on Windows and Linux x86_64.

## Aligned revisions

- Root upstream: `WolframRhodium/VapourSynth-BM3DCUDA@8c16009ce44b5e9b9fcf3288e1a7a922f9b4ccea`
- Fork CPU head: `RyougiKukoc/VapourSynth-BM3DCUDA-api4@aec7ff74957207e0b585da0de06e577be60e9e7b`
- Fork CUDA 12.1 head: `b9cc306430bfd0f73c5948d1a3b287fcdec84839`
- Fork CUDA 12.9 head: `ebc9488dc8e86d48d84ee5eabb7307b421bf7865`
- Upstream import: squashed subtree at `plugins/vapoursynth-bm3dcuda`

All three fork tags share one source tree and differ only in
`bm3dcuda_variant.txt`. The common fork changes were compressed into commit
`eef93f7`; monorepo distribution and publication work follows separately.
Version `2.16` is valid public PEP 440 metadata.

## API4 classification

The CPU and CUDA RTC translation units export `VapourSynthPluginInit2`, use
`VAPOURSYNTH_API_VERSION`, and register plugin version `2.16`. This is a real
source-level API4 port, not a wrapper around an API3 binary. No plugin changes
from `vs-wheels` were used.

## Distribution mapping

- `vapoursynth-bm3dcpu==2.16`: CPU plugin only
- `vapoursynth-bm3dcuda-cu121==2.16`: CPU plus CUDA 12.1 RTC plugin
- `vapoursynth-bm3dcuda-cu129==2.16`: CPU plus CUDA 12.9 RTC plugin

Each distribution is a complete wheel and has no dependency on another BM3D
distribution. The variants intentionally install the same native paths, so
users must uninstall one before switching to another.

## Preserved build and publication changes

The MSVC build, micromamba CUDA 12.1/12.9 environments, UBI8 static-NVRTC
Linux build, manylinux CPU build, artifact layout checks, GLIBC checks, source
install checks, and native fallback checks are copied from the fork workflows.
Monorepo changes are limited to working paths, public distribution selection,
release tags, exact four-asset inventories, repository URLs, and Pages dispatch.

Published tags are:

- `vapoursynth-bm3dcpu-v2.16`
- `vapoursynth-bm3dcuda-cu121-v2.16`
- `vapoursynth-bm3dcuda-cu129-v2.16`
