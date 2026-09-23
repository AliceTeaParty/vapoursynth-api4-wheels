# vs-mlrt migration record

Status: API4 source and native payload builds are verified. Publication is an
explicit handoff TODO; all vs-mlrt prereleases and release tags were removed.

## Alignment

- Original upstream common baseline: `AmusementClub/vs-mlrt@1f166ba`
- Fork generic head: `RyougiKukoc/vs-mlrt-api4@dec8064`
- Fork variant branches: `generic`, `cu121`, `cu129`
- Fork patch: 114 commits compressed into one subtree patch commit
- Source package version: `16.2.2`

The three variant branches share the same source and differ only in
`packaging/payload-tag.txt` plus the selected release payload. The combined
repository exposes them as three distribution names:

- `vs-mlrt-generic`
- `vs-mlrt-cu121`
- `vs-mlrt-cu129`

CUDA compatibility is therefore represented by package name, never by a
version suffix or a mutable branch ref in the user-facing install command.

## API4 classification

The fork contains real API4 backend work in TRT, ORT, OpenVINO, NCNN, and
MIGX sources, plus extensive runtime payload verification. This migration does
not use `vsmlrt-api4-port` and does not copy any plugin changes from
`vs-wheels`.

## Native build evidence

The original complete-wheel layout passed all three main-branch workflows at
`d68dba1fa39cd39394f5b250f5d796a1bbc29ae5`:

- Windows generic: run `35765442197`
- Windows CUDA 12.1/12.9 matrix: run `35765442225`
- Linux generic/CUDA 12.1/CUDA 12.9 matrix: run `35765442370`

Those runs compiled the native backends, assembled payloads, built wheels, and
passed their staged install smoke. The cu121 tag runs `35771541586` (Windows)
and `35771541531` (Linux) again completed native compilation and packaging;
they failed only when uploading a monolithic wheel beyond GitHub's 2 GiB
single-asset limit.

Commit `bf4f35ffc89e4e8c185f1638af140b64a6270918` tried a compositional package
layout. Its latest runs give a precise handoff boundary:

- Windows generic run `35776373307` passed completely.
- Windows CUDA run `35776373267` compiled `vstrt`, `vstrt_rtx`, and custom
  `trtexec`, verified the helper executables, assembled, inspected, and
  compressed both CUDA payloads. It then failed in the staged install check
  because the source-install hook requested an unpublished asset and received
  HTTP 404.
- Linux run `35776373243` built and verified native payloads for generic,
  cu121, and cu129. The cu121 compositional wheel was successfully built at
  1,912,900,980 bytes and installed, then failed because the resulting
  manifest still listed only `vsncnn` and `vsov`. The cu129 native payload was
  also built and verified before its wheel job was cancelled by matrix failure.

This evidence proves that compilation and native artifact assembly work. The
remaining failures are distribution composition and publication semantics, not
source compilation failures. No compilation was performed in the local
WinPython or Docker consumer environments.

## Publication handoff

Publication is intentionally disabled and visibly labeled
`TODO(publishing)` in:

- `.github/workflows/package-vs-mlrt-windows-generic.yml`
- `.github/workflows/package-vs-mlrt-windows-cuda.yml`
- `.github/workflows/package-vs-mlrt-linux.yml`

The disabled blocks cover GitHub Release upload, published-digest checks, and
Pages dispatch. Native build, staged payload verification, wheel experiments,
and Actions artifact upload remain enabled for the next agent.

The next publication implementation must choose a user-facing install and
uninstall model, keep every Release asset below 2 GiB, repair the CUDA overlay
manifest/install behavior, publish all three distribution names, and repeat
Pages-only WinPython and Linux GPU consumer tests.

Commit `4f3494ee8f8e69d33c30f820bd7d08de0201c0d0` validated the handoff guards:

- Windows generic run `35815812926` passed; both `TODO(publishing)` steps were
  skipped.
- Windows CUDA run `35815813121` again completed native compilation, custom
  `trtexec`, payload assembly, inspection, and packaging for cu121 and cu129.
  Both jobs stopped at the known staged-install 404, and all publication steps
  were skipped.
- Linux run `35815813204` passed generic completely and completed cu129 native
  build plus staged verification before the known wheel-manifest failure. Its
  cu121 matrix job was cancelled by fail-fast; run `35776373243` provides the
  successful cu121 native-build evidence for the same source and packaging
  implementation. All Linux publication and Pages steps were skipped.

No vs-mlrt GitHub Release or release tag exists after this validation.
