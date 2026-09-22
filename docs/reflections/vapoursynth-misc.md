# vapoursynth-misc reflection

Completed: 2026-09-23

## Provenance and release

- Imported root upstream
  `vapoursynth/vs-miscfilters-obsolete@07e0589a381f7deb3bf533bb459a94482bccc5c7`
  as a squashed subtree.
- Squashed the ten fork commits through
  `RyougiKukoc/vs-miscfilters-obsolete-vcs@5a4d62723ed91fde5934126ab2ba279e0b05baf5`
  into one plugin patch commit.
- Fork tag `v2.1` resolves to
  `11bbd892593ab01067001fd47d301f0c3bcd6b18`; the later fork head retains the
  audited public PEP 440 version `2.1` while allowing a VapourSynth R80
  runtime.
- Published `vapoursynth-misc==2.1` as `vapoursynth-misc-v2.1` with exactly
  two platform wheels and two native package zips.

## Verification

- Branch run `35751144887`, tag run `35751604957`, and Pages run
  `35751917299` passed.
- Windows WinPython removed `vapoursynth-misc==2.0.post1`, then downloaded
  the `win_amd64` wheel from the Pages-only index with
  `--only-binary=:all:`.
- `vpy:generic` removed its existing package and downloaded the
  `manylinux_2_27_x86_64` wheel through the same Pages-only binary path.
- Both VapourSynth R80 environments autoloaded `core.misc`. `AverageFrames`
  rendered the middle frame of a five-frame 64x32 `YUV420P8` clip with
  PlaneStats average `96/255`, minimum `96`, and maximum `96`; `SCDetect`
  produced zero previous/next scene-change flags on the static clip; and
  `Hysteresis` rendered a 32x16 `GRAY8` frame.

## Lessons for the next plugin

1. Do not rebase a migration branch containing subtree merge topology. Git
   replays the subtree's squashed source commit at the repository root; merge
   or fast-forward the latest `origin/main` and preserve the subtree merge.
2. A root-level `.gitignore` in an imported upstream can collide during a
   rebase even though `git subtree` originally placed it under the plugin
   prefix. This is another signal to stop and retain the merge topology.
3. Audit the custom backend independently from the workflow. Its default
   repository, package-specific tag, project URLs, and documented index all
   need to point at the monorepo even when CI supplies explicit local assets.
4. Keep branch and tag gates equally strong. Misc validated both Release-
   backed wheels and forced native fallback on Windows and Linux before the
   tag job published the exact four-asset inventory.
5. For final consumer tests, make Pages the only index, require binary wheels,
   use `--no-deps` in the provisioned environments, and uninstall any existing
   distribution first. PlaneStats averages are normalized to `[0, 1]`, so an
   8-bit sample value of 96 is asserted as `96/255`, not `0.375`.
