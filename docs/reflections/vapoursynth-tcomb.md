# vapoursynth-tcomb reflection

Completed: 2026-09-22

## Provenance and release

- Imported root upstream
  `dubhatervapoursynth/vapoursynth-tcomb@29318d2b9b5e2f266202294498533805f48b194f`
  as a squashed subtree.
- Squashed the seven fork commits through
  `RyougiKukoc/vapoursynth-tcomb-api4@a50361812ac00f4695d7b939ac215d160d67cd20`
  into one plugin patch commit.
- Fork tag `v4.2` equals its branch head; `4.2` is a valid public PEP 440
  version.
- Published `vapoursynth-tcomb==4.2` as `vapoursynth-tcomb-v4.2` with exactly
  two platform wheels and two native package zips.

## Verification

- Branch run `35746134587`, tag run `35746527531`, and Pages run
  `35746833602` passed.
- Windows WinPython first removed `vapoursynth-tcomb==4.1`, then downloaded
  the `win_amd64` wheel from the Pages-only index with `--only-binary=:all:`.
- `vpy:generic` removed its existing package and downloaded the
  `manylinux_2_27_x86_64` wheel through the same Pages-only binary path.
- Both environments autoloaded `core.tcomb`, rendered a 64x48 `YUV420P8`
  frame from a 12-frame clip, and returned identical PlaneStats:
  average `0.3764705882352941`, minimum `96.0`, and maximum `96.0`.

## Lessons for the next plugin

1. Do not add a force-build VCS smoke unless the fork already verified that
   path. TComb's fork verifies release-backed source installs, but its isolated
   build requirements omit VapourSynth, so an invented isolated force-build
   test fails before reaching the copied build logic.
2. `actions/setup-python` may pre-populate `PKG_CONFIG_PATH`. A build hook that
   discovers VapourSynth metadata must prepend its directory instead of only
   setting the variable when absent.
3. Preserve staged temporal-filter smoke semantics. TComb's package smoke
   exercises actual frame rendering and an invalid RGB input, while the
   installed-wheel smoke confirms autoload and deterministic PlaneStats.
4. Use the Pages index as the only index plus `--only-binary=:all:` and
   `--no-deps` for the final native-wheel provenance check when the allowed
   verification environments already contain the runtime dependency.
5. Keep a release-asset inventory assertion before publication. It proved the
   tag contained exactly one Windows wheel, one Linux wheel, and their two
   corresponding native zips.
