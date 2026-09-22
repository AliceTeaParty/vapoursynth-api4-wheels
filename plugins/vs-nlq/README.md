BL is expected to be mapped to 16 bits.  
EL is 10 bits.  

Output is 12 bits.

Usage:
```
core.vsnlq.MapNLQ(blClip: vs.VideoNode, elClip: vs.VideoNode[, rpu: str])
```

The `rpu` param is an optional path to a RPU binary file.

Install:
```
pip install --extra-index-url https://aliceteaparty.github.io/vapoursynth-api4-wheels/simple/ vs-nlq
```

Tagged releases publish Windows and Linux x86_64 package zips plus direct-install
wheels. The VCS build hook reuses the matching Release zip on Windows or Linux
x86_64. Linux wheels are tagged `manylinux_2_27_x86_64` to match VapourSynth
R79's runtime baseline. macOS, ARM, and other platforms are unsupported. Set
`VS_NLQ_FORCE_BUILD=1` to bypass a matching Release asset on a supported
platform.
