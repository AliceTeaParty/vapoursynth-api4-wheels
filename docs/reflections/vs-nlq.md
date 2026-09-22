# vs-nlq reflection

Completed: 2026-09-22

## Provenance and release

- Imported `quietvoid/vs-nlq@97cbb19a9883feb05e558a6fb4a2192b7c6d8005`
  with a squashed subtree.
- Squashed the two fork commits through
  `RyougiKukoc/vs-nlq@e9090bf2ae215a48997f59d8c0e9a6671478b11b`
  into one patch commit.
- Published package `vs-nlq==1.2.0` as `vs-nlq-v1.2.0`.
- Release assets contain exactly two wheels and two native package zips for
  Windows and Linux x86_64.

## Verification

- Both branch and tag runs passed the copied Windows/Linux build commands.
- Windows WinPython downloaded the wheel from the Pages index, upgraded the
  declared dependency from VapourSynth R73 to R80, exposed
  `core.vsnlq.MapNLQ`, and created a 64x32 `YUV420P12` node.
- `vpy:generic` downloaded the manylinux wheel from the Pages index. It rendered
  three 64x32 `YUV420P12` frames with the expected hash, preserved
  `DolbyVisionRPU`, reported zeroed PlaneStats, and produced the expected error
  for a floating-point EL clip.

## Lessons for the next plugin

1. GitHub Pages must be enabled with `build_type=workflow` before the first
   `actions/configure-pages` run. Merely committing the workflow is not enough.
2. Do not use `--no-deps` for the final consumer test. It can leave an old
   VapourSynth runtime in place even when package metadata correctly requires a
   newer release.
3. On Windows, `vapoursynth.__file__` may be a single
   `site-packages/vapoursynth.pyd`; in other environments it may be
   `site-packages/vapoursynth/__init__.py`. Installed-plugin tests must support
   both layouts when resolving `vapoursynth/plugins`.
4. Run Docker daemon readiness checks before Linux validation. A missing named
   pipe means Docker Desktop is stopped, not that the image is invalid.
5. GitHub Actions currently emits Node 20 deprecation notices for pinned major
   versions such as `actions/checkout@v4`. These are warnings under the current
   runner and did not affect artifacts, but should be revisited when the action
   majors are updated.
6. Keep a branch CI run before tagging. It caught monorepo path handling while
   the release job remained gated, so no broken Release was published.
