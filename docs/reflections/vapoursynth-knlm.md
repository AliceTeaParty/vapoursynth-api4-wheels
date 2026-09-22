# vapoursynth-knlm reflection

Completed: 2026-09-22

## Provenance and release

- Imported root upstream `Khanattila/KNLMeansCL@c4af339` as a squashed
  subtree, rather than importing an intermediate fork.
- Squashed fork `9e18210991a516981e4118bc646ca520865bc5b0` into
  one patch commit.
- Published `vapoursynth-knlm==1.1.2` as `vapoursynth-knlm-v1.1.2`.

## Verification

- CI passed Windows UCRT64, CentOS 7 manylinux, runtime closure, RPATH/GLIBC,
  prebuilt source install, and native fallback checks.
- WinPython installed from Pages and executed OpenCL frames 0, 2, and 4 with
  matching hashes on the available GPU.
- `vpy:generic` installed from Pages, loaded the namespace, rejected `h=0`, and
  reported the expected lack of an OpenCL platform instead of failing load.

## Lessons for the next plugin

1. Follow the fork network to its root source, but import the exact common
   baseline used by the verified fork. Importing a later divergent upstream
   commit would mix unverified behavior into the patch.
2. API3-like property names inside retained AviSynth headers are not evidence
   that the VapourSynth implementation is API3. Scope source scans to the
   actual VapourSynth translation units.
3. Native dependency closure matters independently of plugin loading. Verify
   bundled loader/runtime libraries, `$ORIGIN`, and GLIBC symbols in CI.
4. An OpenCL smoke can legitimately skip frame execution in a generic Linux
   container, but it must still prove namespace loading and deterministic error
   behavior. Hardware execution remains required where a device is available.
