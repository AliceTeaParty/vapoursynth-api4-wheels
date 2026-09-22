# vs-cfl reflection

Completed: 2026-09-23

## Provenance and release

- Imported upstream `LumeCraft-Labs/vs-cfl@502791b86d286ecbf9779ec033fc93789ac5a6c2`
  as a squashed subtree.
- Squashed fork `RyougiKukoc/vs-cfl-vcs@84cd9ff81f160328deacf8879e3093329da45ac7`
  into one plugin patch commit. Annotated fork tag `v1.0.2` peels to that head.
- Published `vs-cfl==1.0.2` as `vs-cfl-v1.0.2` with exactly two platform
  wheels and two native package zips.

## Verification

- Branch run `35751502111`, tag run `35751842078`, and Pages run
  `35752149940` passed Windows UCRT64, Linux manylinux, release-payload,
  installed-wheel, prebuilt source-install, and native fallback gates.
- Windows WinPython first removed its existing `vs-cfl==1.0.2`, then downloaded
  the `win_amd64` wheel from the Pages-only index with
  `--only-binary=:all:` and `--no-deps`.
- Linux `vpy:generic` performed the same clean Pages-only installation and
  downloaded the `manylinux_2_27_x86_64` wheel.
- Both environments autoloaded `core.cfl.KACFL`, rendered frames 0, 3, and 11
  from a 12-frame 64x48 `YUV420P8` clip to `YUV444P8`, and produced hash
  `1f198fd0fc4ef4a4d6357b2de35fb9fb2b57df1087dad2fc10b9ce6e02a835b8`.
  PlaneStats average was `0.3764705882352941`, with minimum and maximum
  `96.0`; an RGB input returned `KACFL: input must be YUV color family`.

## Lessons for the next plugin

1. MSYS2 GCC 16 split OpenMP into the optional
   `mingw-w64-ucrt-x86_64-libgomp` package. Installing the GCC package alone
   can compile OpenMP objects but fail at link time with `cannot find -lgomp`.
2. Preserve the fork's OpenMP-enabled Windows build rather than disabling the
   feature to accommodate packaging drift. Explicitly install the split
   runtime package and keep staging its DLL closure in the release payload.
3. The conservative Linux build intentionally disables OpenMP, so its wheel
   does not bundle `libgomp.so.1`; the branch and tag jobs both enforce this
   runtime boundary and a GLIBC maximum of 2.17.
4. Final provenance checks should uninstall any existing distribution, use
   the Pages index as the only index, require binary wheels, and run the full
   deterministic filter smoke rather than stopping at namespace loading.
