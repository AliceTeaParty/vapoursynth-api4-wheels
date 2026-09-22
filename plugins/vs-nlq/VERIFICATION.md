# Verification Notes

## Linux v1.2.0 packaging

- The Linux Release payload is `vs-nlq/libvs_nlq.so` plus `manifest.vs` and
  `LICENSE`. Cargo's ELF output uses the `libvs_nlq` manifest entry.
- The package is built with Rust 1.88 in `manylinux2014_x86_64`. Its own
  highest GLIBC requirement is 2.14, but its published wheel uses
  `manylinux_2_27_x86_64` because VapourSynth R79 has that end-to-end runtime
  floor.
- Python 3.13 with VapourSynth R79 explicitly loaded the release `.so` with
  autoload disabled. The installed wheel also manifest-autoloaded it. A static
  64x32 case with the embedded profile-7 RPU renders frames 0, 1, and 2 as
  `YUV420P12`, each with SHA-256
  `001642a98efb58316259e09c7b2c632fbb6cedc18a19a2a32acf0b9bc196808c`.
  `DolbyVisionRPU` is preserved and PlaneStats min/max/average are all 0.0.
- The documented invalid case is a floating-point EL clip. Rendering raises
  `Floating point formats are not supported`.
- The local force-build gate used an ordinary isolated PEP 517 install with
  `VS_NLQ_FORCE_BUILD=1` and an unrelated `PKG_CONFIG_PATH`. This Rust plugin's
  bindings bundle the API4 headers and dynamically resolve the plugin API, so
  no VapourSynth pkg-config metadata is required for its source build.

## API3 comparison

The repository has no API3 scanner hits. The only known API3 baseline is a
historical Windows binary/release, while this iteration's Linux environment
contains only VapourSynth R79. No compatible R73/API3 Linux binary or runtime
is available, so a paired API3/API4 behavior comparison was not run.

## Unsupported platforms

This combined wheel repository supports only Windows and Linux x86_64. The
former fork's macOS fallback job is intentionally not carried into the package
workflow, and the build hook rejects macOS and ARM instead of implying support.
