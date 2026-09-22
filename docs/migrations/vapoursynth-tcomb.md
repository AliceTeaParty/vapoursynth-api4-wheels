# vapoursynth-tcomb migration record

Status: published and verified on Windows and Linux x86_64.

## Aligned revisions

- Original upstream:
  `dubhatervapoursynth/vapoursynth-tcomb@29318d2b9b5e2f266202294498533805f48b194f`
- Former fork:
  `RyougiKukoc/vapoursynth-tcomb-api4@a50361812ac00f4695d7b939ac215d160d67cd20`
- Fork merge base: `29318d2b9b5e2f266202294498533805f48b194f`
- Upstream import: `git subtree --squash` at `plugins/vapoursynth-tcomb`

The fork is seven commits ahead. Its `v4.2` tag equals the imported head, and
the audited version `4.2` is a valid public PEP 440 version.

## Source-level API4 port

`src/tcomb.c` is the plugin source migration target. It uses
`VapourSynthPluginInit2`, API4 map, frame, node, embedded video-format,
dependency, and video-filter interfaces. The remaining fork changes add the
Meson and wheel/release packaging plus verification tools. No source or plugin
patch from `vs-wheels` is included.

## Monorepo adaptations

- Workflow: `Package - vapoursynth-tcomb`
- Release tag: `vapoursynth-tcomb-v4.2`
- VCS fallback uses the monorepo `subdirectory` fragment.
- Only Windows and Linux x86_64 are accepted by the build hook.
- Publication triggers the Pages index workflow.

All compilation and smoke commands come directly from the fork's verified
`.github/workflows/build-windows.yml`; only monorepo paths, package-specific
tag/release handling, and Pages dispatch are adapted.

## Published result

- Release: `vapoursynth-tcomb-v4.2`
- Index: `https://aliceteaparty.github.io/vapoursynth-api4-wheels/simple/`
- Windows and Linux: Pages-only binary wheel installs autoloaded `core.tcomb`
  and produced identical output dimensions and PlaneStats.
