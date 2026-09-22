# vapoursynth-tcanny migration record

Status: published and verified on Windows and Linux x86_64.

## Aligned revisions

- Original upstream:
  `HomeOfVapourSynthEvolution/VapourSynth-TCanny@14ac2ceeb59afc7089974d0ae233fe8d0ea183c8`
- Former fork:
  `RyougiKukoc/VapourSynth-TCanny-vcs@8634f7c87af5ffbfddcb0b3eb07fd2b48c74a46c`
- Fork merge base: `14ac2ceeb59afc7089974d0ae233fe8d0ea183c8`
- Upstream import: `git subtree --squash` at
  `plugins/vapoursynth-tcanny`

The GitHub fork network identifies HomeOfVapourSynthEvolution as both the
parent and root source. The fork is seven commits ahead of the exact imported
upstream head. Its annotated `v14.1` tag peels to the fork head, and `14.1` is
a valid public PEP 440 version.

## Source and packaging delta

The fork retains the upstream TCanny implementation and adds verified wheel
and Release packaging. Its `meson.build` adjustment targets the current
VapourSynth dependency, while `hatch_build.py` and the three `tools/ci_*`
scripts stage, package, and smoke test the native plugin. The Windows path
uses the checksum-pinned upstream r14 payload; Linux builds the API4 source in
manylinux and validates the resulting Release payload. No source or plugin
patch from `vs-wheels` is included.

## Monorepo adaptations

- Workflow: `Package - vapoursynth-tcanny`
- Release tag: `vapoursynth-tcanny-v14.1`
- VCS release smoke uses the monorepo `subdirectory` fragment.
- Only Windows and Linux x86_64 are accepted by the build hook and workflow.
- Publication dispatches the Pages index workflow.

All compilation and smoke commands come directly from the fork's verified
`.github/workflows/release.yml`. Changes are limited to monorepo working
directories and artifact paths, package-specific triggers and release
inventory, removal of the unsupported macOS job, and Pages dispatch.

## Published result

- Release: `vapoursynth-tcanny-v14.1`
- Index: `https://aliceteaparty.github.io/vapoursynth-api4-wheels/simple/`
- Windows and Linux: Pages-only binary wheel installs autoloaded
  `core.tcanny`, rendered the test clip, and returned identical frame hashes
  and PlaneStats.
