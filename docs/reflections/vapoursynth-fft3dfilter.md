# vapoursynth-fft3dfilter reflection

Completed: 2026-09-23

## Provenance and release

- Imported root upstream
  `VFR-maniac/VapourSynth-FFT3DFilter@b023e21954423f29fdefcb54a6b0540deb3bdac4`
  as a squashed subtree. The intermediate fork chain is
  `myrsloik/VapourSynth-FFT3DFilter`.
- Squashed the fork history through
  `RyougiKukoc/VapourSynth-FFT3DFilter-vcs@a1753a132175a2678fe914348280a1052da30dea`
  into one plugin patch commit.
- Fork tag `R2.1` resolves to that fork head. Distribution version `2.1` is a
  valid public PEP 440 version.
- Published `vapoursynth-fft3dfilter==2.1` as
  `vapoursynth-fft3dfilter-v2.1` with exactly two platform wheels and two
  native package zips.

## Preserved build and monorepo changes

- The Windows UCRT64/MSYS2 build, R77 SDK preparation, artifact and manifest
  smoke, Linux manylinux2014 build, static FFTW3f build, release-zip checks,
  installed-wheel smoke, and forced isolated fallback were copied from the
  fork's verified `build-msys2.yml`.
- Monorepo-only changes are the `plugins/vapoursynth-fft3dfilter` working
  paths, package-specific artifacts and tag, default Release repository
  `AliceTeaParty/vapoursynth-api4-wheels`, exact asset inventory assertion,
  and Pages-index dispatch.
- The checked-in source marker binds VCS installs to
  `vapoursynth-fft3dfilter-v2.1`; legacy `R{version}` and `v{version}` guesses
  are only fallbacks for older source archives without a marker.

## Verification

- Branch run `35751827125`, tag run `35752217114`, and Pages run
  `35752527322` passed.
- Release assets are
  `fft3dfilter-msys2-ucrt64.zip`, `fft3dfilter-linux-x86_64.zip`,
  `vapoursynth_fft3dfilter-2.1-py3-none-win_amd64.whl`, and
  `vapoursynth_fft3dfilter-2.1-py3-none-manylinux_2_27_x86_64.whl`.
- WinPython removed `vapoursynth-fft3dfilter==2`, downloaded the `win_amd64`
  wheel from the Pages-only index with `--only-binary=:all:` and `--no-deps`,
  autoloaded `core.fft3dfilter`, rendered a 64x32 frame, and returned
  PlaneStats minimum `95`, maximum `96`, and average
  `0.3738568474264706`.
- `vpy:generic` removed its existing `2.1` package, downloaded the
  `manylinux_2_27_x86_64` wheel through the same Pages-only binary path, and
  autoloaded the manifest. It rendered frames 0, 3, and 11 from a 12-frame
  64x48 `YUV420P8` clip, returned PlaneStats minimum `95`, maximum `96`, and
  average `0.37418555964052286`, and rejected `bt=6` with the documented
  error.

## Lessons for the next plugin

1. Preserve subtree merge topology. Concurrent migrations repeatedly update
   README and PACKAGES at the same insertion point, so fetch and merge the
   latest `origin/main`, keep every plugin row, and never rebase the subtree
   history.
2. Audit Release selection as one unit: build-hook repository default,
   checked-in tag marker, project URLs, README commands, workflow tag filter,
   and exact asset names must all identify the monorepo package release.
3. Static native dependencies need an explicit portability decision.
   FFT3DFilter builds FFTW3f with `--disable-shared --enable-static
   --enable-float --enable-threads --with-pic`, preventing a separate runtime
   library from being omitted from the Linux wheel.
4. Run the platform-specific smoke entry point copied from the fork.
   `smoke_installed_wheel.py` is the Windows smoke, while Linux uses
   `smoke_linux_package.py --installed-wheel`; substituting the Windows script
   on Linux produces a false missing-DLL failure even when the `.so` wheel is
   installed correctly.
5. For final provenance, make Pages the only index, require binary wheels,
   pass `--no-deps` in the pre-provisioned verification environments, and
   uninstall the existing distribution before installing the published one.
