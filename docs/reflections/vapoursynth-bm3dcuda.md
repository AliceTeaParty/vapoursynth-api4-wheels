# vapoursynth-bm3dcuda reflection

Completed: 2026-09-23

## Provenance and release

- Imported root upstream
  `WolframRhodium/VapourSynth-BM3DCUDA@8c16009ce44b5e9b9fcf3288e1a7a922f9b4ccea`
  as a squashed subtree.
- Squashed the fork through CPU head
  `aec7ff74957207e0b585da0de06e577be60e9e7b` into one patch commit. CUDA tags
  `b9cc306430bfd0f73c5948d1a3b287fcdec84839` and
  `ebc9488dc8e86d48d84ee5eabb7307b421bf7865` differ only by their variant marker.
- Published three independent version `2.16` distributions and Releases:
  `vapoursynth-bm3dcpu`, `vapoursynth-bm3dcuda-cu121`, and
  `vapoursynth-bm3dcuda-cu129`.
- Release URLs:
  `https://github.com/AliceTeaParty/vapoursynth-api4-wheels/releases/tag/vapoursynth-bm3dcpu-v2.16`,
  `https://github.com/AliceTeaParty/vapoursynth-api4-wheels/releases/tag/vapoursynth-bm3dcuda-cu121-v2.16`,
  and
  `https://github.com/AliceTeaParty/vapoursynth-api4-wheels/releases/tag/vapoursynth-bm3dcuda-cu129-v2.16`.
- Each Release contains exactly two native zips and two platform wheels. CUDA
  wheel sizes are about 19/25 MB for cu121 and 39/49 MB for cu129 on
  Windows/Linux, well below GitHub's asset limit.

## Verification

- CPU branch run `35807654038`, CPU tag run `35808000334`, and Pages run
  `35808094871` passed.
- CUDA branch run `35808440374`, cu121 tag run `35808696742`, cu121 Pages run
  `35808881888`, cu129 tag run `35809140725`, and cu129 Pages run
  `35809309088` passed.
- WinPython installed every distribution from the Pages-only index after
  removing all former BM3D names. CPU, cu121, and cu129 returned version
  `2.16`; CPU frame execution passed for all three. Both CUDA wheels loaded
  `core.bm3dcuda_rtc` and rendered a 16x16 frame on GPU 0 with PlaneStats
  average `0.49999997578561306`.
- `vpy:generic` installed the CPU wheel from Pages and rendered frames 0, 3,
  and 11 with stable hashes plus the expected negative-radius error.
- `vpy:cu129` installed both cu121 and cu129 wheels separately from Pages.
  Each rendered CPU and CUDA RTC frames 0, 3, and 11 on an RTX 3090 Ti; both
  CUDA lines produced the expected hashes and reported driver API `13040`.

## Lessons for the next plugin

1. A multi-variant source tree can keep each wheel independently uninstallable
   by changing only its static distribution name during CI. No dependency or
   payload split is needed when every complete wheel fits the host limit.
2. Publish the CPU Release first when a verified Windows CUDA workflow merges
   a separately built CPU zip into the CUDA wheel. Branch CUDA CI cannot pass
   until that immutable CPU asset exists in the combined repository.
3. Preserve smoke-test semantics. `smoke_bm3dcpu_linux.py` without
   `--expect-rtc` deliberately rejects a CUDA file; it is a CPU-only test, not
   a generic way to exercise just the CPU namespace inside a CUDA wheel.
4. A no-GPU CI runner should verify CUDA wheel layout, GLIBC ceiling, native
   dependency closure, and source payload selection. Actual RTC loading and
   frame execution belongs in the allowed GPU consumer environments.
5. Shell quoting inside a single-quoted `docker ... bash -lc` body must remain
   byte-for-byte compatible with the verified fork. A Python one-liner using
   unescaped single quotes can fail before the container even starts.
