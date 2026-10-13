# Maintaining the wheel collection

User installation and package selection are described in [README.md](README.md).
Exact wheel versions, runtime versions and source identities are recorded in
[VERSIONS.md](VERSIONS.md). Packaging metadata remains authoritative for builds;
update the version record whenever that metadata changes.

## Native plugin layout

Our independently maintained native plugins share this structure:

```text
plugins/vapoursynth-<name>/
  README.md          central integration / package documentation
  source.json        reviewed upstream repository, commit and source version
  native/            pinned upstream git submodule
  pyproject.toml     central wheel metadata, when wheel packaging exists
  hatch_build.py     central build hook, when wheel packaging exists
  tools/            central packaging and verification tools, when present
```

KrigBilateral Vulkan has central wheel packaging. DFTTestVK currently has a
source registration only; moving its source to `native/` does not publish a
wheel or change the pinned source revision. Central integration files belong
beside `native/`; native implementation changes belong in the upstream repository.

Initialize source checkouts with:

```console
git clone --recurse-submodules https://github.com/AliceTeaParty/vapoursynth-api4-wheels.git
```

For an existing checkout using the current layout:

```console
git submodule sync --recursive
git submodule update --init --recursive
```

### Migrating the old DFTTestVK checkout

If DFTTestVK was already initialized directly at
`plugins/vapoursynth-dfttestvk`, deinitialize that old path **before pulling
or switching to this layout**. Its upstream README would otherwise conflict
with the new central README and Git would refuse the checkout.

Save any local source changes first. The deinitialization command deliberately
omits `--force`, so Git refuses to remove a modified source checkout:

```console
git submodule deinit -- plugins/vapoursynth-dfttestvk
git pull --ff-only
git submodule sync --recursive
git submodule update --init --recursive
```

When reviewing a branch, use `git switch <branch>` in place of the pull.
The final initialization reuses the registered source at its new `native/`
path. New clones need only the recursive clone command above.

### Updating native sources

After reviewing an upstream change, update the gitlink and `source.json` commit
together. Update the source version and dependency header pins as needed.
For a packaged plugin, also update its wheel metadata and Release tag mapping.
Record the new values in VERSIONS.md and run the package's checks before release.
Run `python -m unittest discover -s tests -p test_plugin_submodules.py -v` to
check the registered source paths, URLs and gitlink pins without a native build.

## Upstream ports and Python modules

Other native projects under `plugins/<name>` retain their upstream source
layout through `git subtree`. Their API4 and packaging changes are maintained
in this repository. Each project's `.github/workflows/package-<name>.yml`
defines its build, validation and release procedure.

Python modules are maintained under `modules/`. `rksfunc` and `rkstool` retain
upstream source authority and versions; CI builds reviewed fixed-commit
checkouts. The 12 Collection components are centrally maintained subtrees,
and the entry package pins their exact wheel versions. See
[modules/README.md](modules/README.md) for preview/publication workflows and
[modules/COLLECTION.md](modules/COLLECTION.md) for provenance, module updates
and resolver/upgrade validation.

## Publication and index

Build and validate artifacts with the package's existing workflow before
publication. A configured wheel version does not prove that the asset has
been released. Release-backed source installation should consume the matching
tested payload; check the plugin package guide for fallback build controls.

`scripts/generate_index.py` creates the GitHub Pages package index from
published GitHub Release wheel assets. Module publication uses the separate
manual publish workflows described in the module guide. vs-mlrt entry and
component/model packages have separate version sequences and exact internal pins.

The wheel-version quality check compares packaging metadata and variant Release
tags with VERSIONS.md, and confirms exact pins between centrally maintained
packages. Run it with:

```console
python -m unittest discover -s tests -p test_wheel_versions.py -v
```
