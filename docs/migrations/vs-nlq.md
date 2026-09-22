# vs-nlq migration record

Status: published and verified on Windows and Linux x86_64.

## Aligned revisions

- Original upstream: `quietvoid/vs-nlq@97cbb19a9883feb05e558a6fb4a2192b7c6d8005`
- Former fork: `RyougiKukoc/vs-nlq@e9090bf2ae215a48997f59d8c0e9a6671478b11b`
- Fork merge base: `97cbb19a9883feb05e558a6fb4a2192b7c6d8005`
- Upstream import: `git subtree --squash` at `plugins/vs-nlq`

The fork is exactly two commits and 15 changed files ahead of this upstream
revision. Those changes are applied here as one patch commit.

## Classification

This migration is packaging and compatibility glue, not a new source-level
API4 port. The imported upstream Rust source already uses the current
VapourSynth Rust bindings and contains none of the API3 C interface markers
(`VapourSynthPluginInit`, `createFilter`, `propGet*`, `VSFrameRef`, or
`VSNodeRef`). No code from `vs-wheels` or its packaged plugins is included.

Fork-derived files:

- Packaging: `hatch_build.py`, `pyproject.toml`
- Build helpers: `tools/ci_build_native.py`, `tools/ci_build_windows.py`,
  `tools/ci_prepare_windows.py`, `tools/package_plugin_zip.py`
- Runtime verification: `tools/smoke_installed_wheel.py`,
  `tools/smoke_load_artifact.py`, `tools/smoke_native_package.py`
- Dependency/version metadata: `Cargo.toml`, `Cargo.lock`
- Documentation and ignores: `README.md`, `VERIFICATION.md`, `.gitignore`
- Verified CI source: former fork `.github/workflows/ci.yml` and
  `.github/workflows/build-windows.yml`

## Monorepo adaptations

- Package and quality workflows run from `plugins/vs-nlq`.
- GitHub artifacts use paths rooted at `plugins/vs-nlq`.
- The release tag is `vs-nlq-v1.2.0` rather than `v1.2.0`.
- Prebuilt downloads target this repository and the package-specific tag.
- The macOS fallback job is omitted and unsupported platforms are rejected.
- Release publication triggers regeneration of the GitHub Pages package index.

The Windows and Linux build, artifact load, installed-wheel smoke, source
fallback smoke, GLIBC check, and Rust commands are copied from the verified
fork workflow. Only the path and publication adaptations above differ.

## Published result

- Release: `vs-nlq-v1.2.0`
- Index: `https://aliceteaparty.github.io/vapoursynth-api4-wheels/simple/`
- Windows: WinPython with VapourSynth R80, installed-wheel node smoke passed
- Linux: `vpy:generic` with VapourSynth R80, full three-frame native smoke passed
