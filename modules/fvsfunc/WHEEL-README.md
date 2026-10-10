# fvsfunc wheel

This component starts from [VapourSynth-Scripts-Collection](https://github.com/RyougiKukoc/VapourSynth-Scripts-Collection/tree/14091484381778fe55102b58ac584e38f5e0fc6a) at 14091484381778fe55102b58ac584e38f5e0fc6a and includes reviewed local fixes. Its import name remains fvsfunc.

The upstream subtree baseline is [https://github.com/Irrational-Encoding-Wizardry/fvsfunc](https://github.com/Irrational-Encoding-Wizardry/fvsfunc) at 076dbde68227f6cca91304a447b2a02b0e95413e. The following local patch combines the recorded intermediate/gist changes, the Collection changes and packaging metadata. See provenance.toml for the complete chain and runtime file hashes.

Wheel distribution: fvsfunc==0.3.0.post2+alice.1. The wheel version is the central distribution's version; source version markers remain unchanged. Runtime dependencies remain user-managed, matching Collection 0.3.0. Install vs-collection-rk to obtain the entire pinned component set.

License observation: Not separately declared. Any upstream license files and source headers are retained. Packaging does not assign a new license to files without a separately declared license.

Local fixes: OverlayInter forwards opencl, device, eedi3_core, eedi3_args and qtgmc_args
to its default QTGMC route. Existing default interpolation and custom bobber
behavior are retained.
