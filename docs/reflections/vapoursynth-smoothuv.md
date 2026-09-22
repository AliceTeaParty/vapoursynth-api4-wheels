# vapoursynth-smoothuv reflection

Completed: 2026-09-22

## Provenance and release

- Imported upstream `30a2851b4573802b7684fd20ec2cec05ab49925f` as
  a squashed subtree.
- Squashed the fork through `1b3d3e66f5ec1cb168db0fa65c580b64408480e2`
  into one patch commit.
- Published `vapoursynth-smoothuv==3.1` as
  `vapoursynth-smoothuv-v3.1` with Windows/Linux wheels and package zips.

## Verification

- Branch and tag workflows passed Windows UCRT64, Linux manylinux, Release
  payload, installed-wheel, prebuilt source install, and named VCS force-build
  paths.
- WinPython and `vpy:generic` both downloaded their platform wheels from Pages.
  Both loaded `RainbowSmooth.py` and `core.smoothuv`, rendered frames 0, 3, and
  11 with identical hashes, and rejected the invalid input as expected.

## Lessons for the next plugin

1. Monorepo VCS installs require
   `#subdirectory=plugins/<package>` after the commit SHA. This must be tested,
   not merely documented; the fork's named VCS force-build job provides that
   coverage.
2. A package may contain both a native plugin and a top-level Python helper.
   Consumer smoke must verify both (`core.smoothuv` and `RainbowSmooth.py`).
3. Fork tags may omit a later build-only compatibility commit while keeping the
   same distribution version. Import the audited branch head and record the tag
   discrepancy rather than inventing a new package version.
4. Small wheels still need platform tags because they contain a native plugin;
   the presence of a pure Python helper does not make the distribution pure.
