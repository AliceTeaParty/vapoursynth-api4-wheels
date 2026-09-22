# vapoursynth-retinex reflection

Completed: 2026-09-22

- Imported upstream `6bfbdd429159c85075dc4b08e0ac4e706470916b` as
  a squashed subtree and fork `b33f9a3a2fe4671699235224165053d127cdeb94`
  as one patch commit.
- Published `vapoursynth-retinex==4.1` as `vapoursynth-retinex-v4.1`.
- Branch/tag CI passed Windows UCRT64, manylinux, payload, prebuilt source, and
  force-build paths.
- WinPython and `vpy:generic` installed from Pages and produced the same
  `YUV444P8` frame hash and PlaneStats.

Lessons:

1. Multi-filter plugins may spread API4 edits across the registration file,
   filter implementations, and shared headers; migration records must name the
   whole source surface.
2. Keep platform-support documentation synchronized with the build hook. A
   native fallback on supported platforms does not imply macOS/ARM support.
3. A single deterministic output frame plus exact PlaneStats can be sufficient
   when the fork's smoke intentionally exercises the full registered filter
   path and both platforms agree.
