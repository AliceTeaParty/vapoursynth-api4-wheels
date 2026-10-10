# havsfunc wheel

This component starts from [VapourSynth-Scripts-Collection](https://github.com/RyougiKukoc/VapourSynth-Scripts-Collection/tree/14091484381778fe55102b58ac584e38f5e0fc6a) at 14091484381778fe55102b58ac584e38f5e0fc6a and includes reviewed local fixes. Its import name remains havsfunc.

The upstream subtree baseline is [https://github.com/HomeOfVapourSynthEvolution/havsfunc](https://github.com/HomeOfVapourSynthEvolution/havsfunc) at 7f0a9a7a37b60a05b9f408024d203e511e544a61. The following local patch combines the recorded intermediate/gist changes, the Collection changes and packaging metadata. See provenance.toml for the complete chain and runtime file hashes.

Wheel distribution: havsfunc==33.post2+alice.1. The wheel version is the central distribution's version; source version markers remain unchanged. Runtime dependencies remain user-managed, matching Collection 0.3.0. Install vs-collection-rk to obtain the entire pinned component set.

License observation: Unlicense. Any upstream license files and source headers are retained. Packaging does not assign a new license to files without a separately declared license.

Local fixes: EEDI3 uses CPU by default; opencl=True selects Vulkan with OpenCL-only fallback.
Backend/device/eedi3_args controls are available through santiag, EEDI3zig,
QTGMC and the credits helpers, including lazy frame-error fallback.
