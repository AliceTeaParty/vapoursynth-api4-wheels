# vapoursynth-knlm migration record

Status: published and verified on Windows and Linux x86_64.

## Aligned revisions

- Root upstream: `Khanattila/KNLMeansCL@c4af339b1d7b41268b3c5015627e68434bc139c7`
- Direct fork chain: `AmusementClub/KNLMeansCL` via `pinterf/KNLMeansCL`
- Fork: `RyougiKukoc/VapourSynth-KNLMeansCL-api4@9e18210991a516981e4118bc646ca520865bc5b0`
- Upstream import: squashed subtree at `plugins/vapoursynth-knlm`

The current root-upstream master has one later commit not included in the
verified fork. The subtree therefore uses the exact common baseline `c4af339`;
the fork is 11 commits ahead of that baseline. Tag `v1.1.2` equals fork head,
and `1.1.2` is valid PEP 440.

## API4 classification

`KNLMeansCL/NLMVapoursynth.cpp` and `.h` contain the source-level API4 port;
vendored API3 headers are removed. Other changes implement Meson, packaging,
runtime closure, and smoke tests. No `vs-wheels` plugin patch is included.

## Monorepo adaptations

- Workflow: `Package - vapoursynth-knlm`
- Release tag: `vapoursynth-knlm-v1.1.2`
- Windows/Linux x86_64 only; Pages index dispatch after release

Build and verification commands are copied from the fork's `build.yaml`; only
monorepo paths and publication are adapted.

## Published result

- Release: `vapoursynth-knlm-v1.1.2`
- Windows: R80 and RTX 3090 Ti OpenCL frame smoke passed
- Linux: R80 load/error smoke passed; generic container reported no OpenCL platform
