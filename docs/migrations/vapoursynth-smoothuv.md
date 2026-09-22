# vapoursynth-smoothuv migration record

Status: implementation in progress; publication and consumer verification are
pending.

## Aligned revisions

- Original upstream:
  `dubhatervapoursynth/vapoursynth-smoothuv@30a2851b4573802b7684fd20ec2cec05ab49925f`
- Former fork:
  `RyougiKukoc/vapoursynth-smoothuv-api4@1b3d3e66f5ec1cb168db0fa65c580b64408480e2`
- Fork merge base: `30a2851b4573802b7684fd20ec2cec05ab49925f`
- Upstream import: `git subtree --squash` at `plugins/vapoursynth-smoothuv`

The fork is 10 commits ahead. Its `v3.1` tag points to `bb31b088`; fork head
`1b3d3e6` only relaxes current VapourSynth build dependencies. The audited PEP
440 version remains `3.1`.

## Source-level API4 port

`src/SmoothUV.cpp` is the plugin source migration target. It uses
`VapourSynthPluginInit2`, `createVideoFilter`, API4 node/frame types, embedded
video formats, map accessors, and filter dependencies. Other changed files add
Meson, wheel packaging, release assets, and verification. No source or plugin
patch from `vs-wheels` is included.

## Monorepo adaptations

- Workflow: `Package - vapoursynth-smoothuv`
- Release tag: `vapoursynth-smoothuv-v3.1`
- VCS fallback uses the monorepo `subdirectory` fragment.
- Only Windows and Linux x86_64 are accepted by the build hook.
- Publication triggers the Pages index workflow.

All compilation and smoke commands come directly from the fork's verified
`.github/workflows/build-windows.yml`; only paths and publication are adapted.
