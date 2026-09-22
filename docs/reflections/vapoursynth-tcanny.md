# vapoursynth-tcanny reflection

Completed: 2026-09-22

## Provenance and release

- Imported root upstream
  `HomeOfVapourSynthEvolution/VapourSynth-TCanny@14ac2ceeb59afc7089974d0ae233fe8d0ea183c8`
  as a squashed subtree.
- Squashed the seven fork commits through
  `RyougiKukoc/VapourSynth-TCanny-vcs@8634f7c87af5ffbfddcb0b3eb07fd2b48c74a46c`
  into one plugin patch commit.
- Fork tag `v14.1` peels to the fork head; `14.1` is a valid public PEP 440
  version.
- Published `vapoursynth-tcanny==14.1` as `vapoursynth-tcanny-v14.1` with
  exactly two platform wheels and two native package zips.

## Verification

- Branch run `35748905073`, tag run `35749223699`, and Pages run
  `35749420867` passed.
- Windows WinPython first removed `vapoursynth-tcanny==14`, then downloaded
  the `win_amd64` wheel from the Pages-only index with
  `--only-binary=:all:`.
- `vpy:generic` removed its existing package and downloaded the
  `manylinux_2_27_x86_64` wheel through the same Pages-only binary path.
- Both environments autoloaded `core.tcanny`, rendered frames 0, 3, and 11
  from a 12-frame 64x48 `YUV420P8` clip, and produced frame hash
  `4c72a79f158e44c0219013805f4f658e35c1c2d7b6d4cd9500865612a8b53579`.
  PlaneStats average was `0.0625`, minimum `0.0`, and maximum `255.0`; both
  also rejected `t_h <= t_l` with the expected TCanny error.

## Lessons for the next plugin

1. Do not rebase a migration branch containing subtree merge topology. Git
   replays the subtree's squashed source commit at the repository root; merge
   the latest `origin/main` instead, resolve the shared status table, and keep
   the subtree merge intact.
2. A copied build hook may still default to the former fork even after its
   workflow uses the monorepo. Audit the hook's repository and tag defaults,
   project URLs, and installation documentation together. TCanny now defaults
   to `AliceTeaParty/vapoursynth-api4-wheels` and
   `vapoursynth-tcanny-v{version}` for its Linux release payload.
3. Preserve platform-specific verified inputs. TCanny Windows source builds
   checksum the upstream r14 archive, while Linux source builds reuse the
   package-specific monorepo release zip; both release wheels still come from
   the same tag and Pages index.
4. Test behavior, not only namespace loading. The smoke renders multiple
   frames, checks deterministic hashes and PlaneStats, and verifies the
   filter's invalid-threshold error path.
5. Keep final provenance checks strict: make the Pages index the only index,
   require binary wheels, use `--no-deps` in the pre-provisioned verification
   environments, and uninstall any existing distribution first.
