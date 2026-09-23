# vapoursynth-dfttest2 reflection

Completed: 2026-09-23

## Provenance and packaging

- Imported `AmusementClub/vs-dfttest2@65b4379eb1ac5da50be985ef843f17107fb398c5`
  as the root upstream subtree and squashed the API4 fork through
  `51cae090eea28cd3c479a003aaf82e61b31b24e2` into one patch.
- Replaced the inherited vectorclass gitlink with nested subtree
  `vectorclass/version2@a0a33986fb1fe8a5b7844e8a1b1f197ce19af35d`.
- Audited `10.2` as valid public PEP 440 metadata and published complete,
  independently uninstallable CPU, cu121, and cu129 distributions.

## Verification

- Initial branch run `35810368542` passed all three Windows builds, all three
  Linux native builds, and all three Linux wheel/ABI validation jobs.
- CUDA 12.1 tag run `35811413727` and Pages run `35811804306` passed.
- CUDA 12.9 tag run `35812096892` and Pages run `35812516379` passed.
- After the package name correction, branch run `35812810480`, CPU tag run
  `35813219926`, and Pages run `35813630833` passed.
- WinPython installed all three intended names from the Pages-only index.
  CPU rendered a 64x32 frame with PlaneStats average `0.3764705882352941`.
  Both CUDA variants passed native and GPU regression workers.
- `vpy:generic` installed `vapoursynth-dfttest2-cpu==10.2` from Pages, loaded
  the installed helper, rendered frames 0, 3, and 11 with stable hashes, and
  returned the expected unsupported-format error.
- `vpy:cu129` installed cu121 and cu129 separately from Pages. For each wheel,
  CPU, NVRTC, and cuFFT rendered frames 0, 3, and 11; NVRTC and cuFFT hashes
  matched for every tested frame. The helper resolved from site-packages.

## Lessons for the next plugin

1. A gitlink inside an imported upstream subtree remains a gitlink. If its
   `.gitmodules` path is relative to the former repository root, replace it
   with an exact nested subtree before adapting checkout workflows.
2. Distribution naming must follow backend semantics and the user's naming
   decision, not an unconfirmed planning-table placeholder. Here `cpu` is more
   precise than `generic` because the package contains a dedicated CPU backend.
3. Installed-environment tests and pre-install isolation tests have different
   contracts. The `isolation_on` regression intentionally expects its sentinel
   plugin to win; it is valid before installation but conflicts with an already
   autoloaded consumer wheel. Use native+GPU workers for installed validation.
4. CUDA wheel size can substantially exceed its native zip because the wheel
   contains both plugins, the Python helper, and runtime libraries. Check each
   final wheel, not only the native archive, against hosting limits.
5. Run GPU consumer smoke from outside the source checkout so `import dfttest2`
   proves the helper came from the installed wheel rather than the working tree.

## Cleanup result

The unsupported `vapoursynth-dfttest2-generic-v10.2` Release was changed to a
draft and its Pages entry was removed by successful index run `35814057724`.
After explicit approval, the draft and its remote/local tags were permanently
deleted. Only the intended CPU, cu121, and cu129 names remain public.
