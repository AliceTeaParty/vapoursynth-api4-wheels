# vapoursynth-misc migration record

Status: branch validation pending.

## Aligned revisions

- Root upstream:
  `vapoursynth/vs-miscfilters-obsolete@07e0589a381f7deb3bf533bb459a94482bccc5c7`
- Former fork head:
  `RyougiKukoc/vs-miscfilters-obsolete-vcs@5a4d62723ed91fde5934126ab2ba279e0b05baf5`
- Fork merge base: `07e0589a381f7deb3bf533bb459a94482bccc5c7`
- Upstream import: `git subtree --squash` at `plugins/vapoursynth-misc`

The fork is ten commits ahead of the exact imported upstream head. Its latest
`v2.1` tag resolves to `11bbd892593ab01067001fd47d301f0c3bcd6b18`;
the subsequent head commit only allows a VapourSynth R80 runtime and retains
the audited `2.1` distribution version, which is a valid public PEP 440
version.

## Source-level API4 port

`src/miscfilters.cpp` contains the API4 migration and uses
`VapourSynthPluginInit2`, API4 maps, frames, nodes, dependencies, and filter
creation. The remaining fork changes add Meson adjustments, the release-backed
wheel backend, Windows/Linux packaging helpers, and smoke tests. No source or
plugin patch from `vs-wheels` is included.

## Monorepo adaptations

- Workflow: `Package - vapoursynth-misc`
- Release tag: `vapoursynth-misc-v2.1`
- VCS fallback uses the monorepo `subdirectory` fragment.
- The build backend and workflow support only Windows and Linux x86_64.
- Package metadata and default prebuilt downloads point at this repository.
- Publication triggers the Pages index workflow.

All compilation and smoke commands come directly from the fork's verified
`.github/workflows/build-msys2.yml`; only monorepo paths, platform scope,
package-specific tag/release handling, and Pages dispatch are adapted.
