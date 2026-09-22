# vs-mlrt migration record

Status: source and distribution split prepared; native payload publication is
pending dedicated CUDA/generic CI verification.

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

## Remaining work

The payload workflows are large and CUDA-specific. They must be adapted and
verified on Windows/Linux before publishing the three package releases and
their Pages entries. No local compilation is performed in this worktree.
