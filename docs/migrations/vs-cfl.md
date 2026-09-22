# vs-cfl migration record

Status: published and verified.

## Aligned revisions

- Root upstream:
  `LumeCraft-Labs/vs-cfl@502791b86d286ecbf9779ec033fc93789ac5a6c2`
- Former fork:
  `RyougiKukoc/vs-cfl-vcs@84cd9ff81f160328deacf8879e3093329da45ac7`
- Fork merge base: `502791b86d286ecbf9779ec033fc93789ac5a6c2`
- Upstream import: `git subtree --squash` at `plugins/vs-cfl`

The fork is exactly six commits ahead of the root upstream, while the upstream
has no commits beyond the common baseline. Annotated tag `v1.0.2` resolves to
the fork head. Distribution version `1.0.2` is a valid public PEP 440 version.

## Source and packaging delta

The imported upstream already uses VapourSynth API4, including
`VapourSynthPluginInit2`, API4 maps, frames, nodes, formats, filter
dependencies, and video-filter callbacks. The fork's source delta guards the
OpenMP pragma when OpenMP is disabled. Its other changes add Meson options,
release-backed wheel packaging, Windows UCRT64 and conservative Linux build
helpers, and functional smoke tests for `core.cfl.KACFL`. No source or plugin
patch from `vs-wheels` is included.

## Verified-fork workflow and monorepo adaptations

The Windows build, explicit payload load, wheel build/install, source install,
Linux manylinux build, GLIBC check, filter smoke, and release-payload smoke
commands are copied directly from the former fork's verified
`.github/workflows/build.yml`.

Only these integration details differ:

- Root workflow name: `Package - vs-cfl`.
- Working directories, Docker mount, artifacts, and payload paths point to
  `plugins/vs-cfl`.
- Release tag: `vs-cfl-v1.0.2`; the build hook resolves prebuilt assets from
  `AliceTeaParty/vapoursynth-api4-wheels`.
- VCS documentation uses `#subdirectory=plugins/vs-cfl`.
- Publication is restricted to Windows and Linux x86_64 assets, validates the
  exact four-file inventory, and dispatches the Pages index workflow.

## Published result

- Release: `vs-cfl-v1.0.2`
- Index: `https://aliceteaparty.github.io/vapoursynth-api4-wheels/simple/`
- Windows and Linux: Pages-only binary wheel installs autoloaded
  `core.cfl.KACFL`, rendered frames 0, 3, and 11 with identical hashes and
  PlaneStats, and returned the documented invalid-RGB error.
