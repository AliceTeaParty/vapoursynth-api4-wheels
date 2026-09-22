# vapoursynth-nnedi3cl reflection

Completed: 2026-09-22

## Provenance and release

- Imported original upstream `eb2a810c0b7dfdd3ad908a1bdc07d6daab64eb57`
  as a squashed subtree.
- Squashed the fork through `1c22f3ed54f18a237dcd2fa7ba73d24c817ce050`
  into one plugin patch commit.
- Published `vapoursynth-nnedi3cl==8.1` as
  `vapoursynth-nnedi3cl-v8.1` with two wheels and two native package zips.

## Verification

- Branch and tag workflows passed Windows UCRT64, Linux manylinux, Release
  payload, installed-wheel, local-payload source install, and isolated native
  fallback jobs.
- WinPython downloaded the wheel from Pages and rendered frames 0, 3, and 11
  on an NVIDIA GeForce RTX 3090 Ti. All hashes matched and the invalid field
  case returned the expected error.
- `vpy:generic` downloaded the Linux wheel from Pages, autoloaded the namespace
  and callable, and returned the expected invalid-input error. GPU frame
  rendering is intentionally not required in the generic container.

## Lessons for the next plugin

1. When a Docker workflow changes its source/output mount from repository root
   to a plugin subtree, every host-side `mkdir` must move to that same subtree.
   The first run built valid Linux assets but failed only at the final copy
   because `/out/release-assets-linux` had not been created in the mounted
   plugin `dist` directory.
2. Audit both the latest tag and branch head. Here `v8.1` points to `ddc6c01`,
   while `1c22f3e` adds a build-dependency compatibility fix without changing
   the distribution version.
3. Preserve platform-specific validation expectations. Windows can exercise
   real OpenCL hardware; `vpy:generic` should validate loading and errors
   without pretending a GPU device exists.
4. Keep the original manual MSVC workflow as subtree provenance, but publish
   through the fork's designated primary MSYS2/UCRT64 workflow only.
5. A source fallback passing does not prove the release-payload path. Both jobs
   are needed because their dependency and artifact flows are different.

## Scope update

`vapoursynth-tivtc` and `vapoursynth-bifrost` were removed from the user's
current fork list during this migration and are no longer planned packages.
