# vapoursynth-retinex migration record

Status: published and verified on Windows and Linux x86_64.

- Upstream: `HomeOfVapourSynthEvolution/VapourSynth-Retinex@6bfbdd429159c85075dc4b08e0ac4e706470916b`
- Fork: `RyougiKukoc/VapourSynth-Retinex-api4@b33f9a3a2fe4671699235224165053d127cdeb94`
- Fork is two commits ahead; `v4.1` equals fork head; version `4.1` is PEP 440.
- Imported as squashed subtree at `plugins/vapoursynth-retinex`.

The source port spans `source/VSPlugin.cpp`, filter implementations, and API
headers under `include/`. It uses pure API4 registration, maps, frames, nodes,
formats, and dependencies. No `vs-wheels` plugin patch is included.

Workflow `Package - vapoursynth-retinex` copies the fork's verified build and
smoke commands. Only monorepo paths, Windows/Linux-only enforcement, package
tag `vapoursynth-retinex-v4.1`, and Pages dispatch are adapted.

Published result: `vapoursynth-retinex-v4.1`; Windows and Linux R80 online
installs produced identical frame hashes and PlaneStats.
