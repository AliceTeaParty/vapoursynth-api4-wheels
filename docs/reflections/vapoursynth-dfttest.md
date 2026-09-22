# vapoursynth-dfttest reflection

Completed: 2026-09-22

## Provenance and release

- Imported upstream `bc5e0186a7f309556f20a8e9502f2238e39179b8`
  as a squashed subtree.
- Squashed fork `e11c7ea2564843b531f0ec366a6219b293ae7948` into
  one patch commit.
- Published `vapoursynth-dfttest==1.1` as `vapoursynth-dfttest-v1.1`.

## Verification

- Branch and tag workflows passed Windows UCRT64, Linux manylinux, explicit
  payload loading, prebuilt source installs, and isolated Linux fallback.
- WinPython and `vpy:generic` installed wheels from Pages and rendered frames
  0, 3, and 11. Frame hashes and all three plane statistics matched exactly.

## Lessons for the next plugin

1. When the fork tag equals its branch head, record that explicitly; it removes
   ambiguity over which commit the combined release represents.
2. SIMD variants (SSE2, AVX2, AVX512) belong to the source-port diff even when
   the public API entry point lives in one C++ file. Include all such files in
   the source-level migration record.
3. Cross-platform deterministic frame hashes plus plane statistics provide
   stronger behavior evidence than namespace/load tests alone.
4. A package requiring Python 3.13 remains installable in the Python 3.14
   WinPython environment because its wheel is `py3-none-<platform>` and the
   declared lower bound is satisfied.
