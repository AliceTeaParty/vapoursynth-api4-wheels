# vapoursynth-nnedi3cl migration record

Status: implementation in progress; publication and consumer verification are
pending.

## Aligned revisions

- Original upstream:
  `HomeOfVapourSynthEvolution/VapourSynth-NNEDI3CL@eb2a810c0b7dfdd3ad908a1bdc07d6daab64eb57`
- Former fork:
  `RyougiKukoc/VapourSynth-NNEDI3CL-api4@1c22f3ed54f18a237dcd2fa7ba73d24c817ce050`
- Fork merge base: `eb2a810c0b7dfdd3ad908a1bdc07d6daab64eb57`
- Upstream import: `git subtree --squash` at
  `plugins/vapoursynth-nnedi3cl`

The fork is 22 commits ahead of the original upstream. Its `v8.1` tag points
to `ddc6c01cefbebbdbe68c929b374bc11553b5183e`; the imported fork head adds
`1c22f3e`, which only allows current VapourSynth build dependencies. The
audited distribution version remains the valid PEP 440 version `8.1`.

## Source-level API4 port

`NNEDI3CL/NNEDI3CL.cpp` is the sole plugin source migration target. The fork
replaces the API3 entry point and registration functions with
`VapourSynthPluginInit2`, `configPlugin`, and `registerFunction`; replaces old
map, node, frame, filter, and format interfaces with API4 equivalents; and
later fixes the MinGW filter-creation lifetime crash. The remaining changed
files are build, packaging, runtime verification, and documentation.

No source or plugin patch from `vs-wheels` is included.

## Monorepo adaptations

- Package workflow: `Package - vapoursynth-nnedi3cl`
- Release tag: `vapoursynth-nnedi3cl-v8.1`
- Prebuilt assets resolve from this repository and package-specific tag.
- Only Windows and Linux x86_64 are accepted by the build hook.
- Release publication triggers regeneration of the Pages package index.

All Windows UCRT64, Linux manylinux, installed-wheel, release-zip, and forced
source fallback commands come from the former fork's verified
`.github/workflows/build-msys2.yml`; only monorepo paths and publication are
adapted.
