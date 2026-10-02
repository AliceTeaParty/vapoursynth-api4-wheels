# vs-collection-rk maintenance

The central repository maintains these scripts as individual Git subtrees.
The migration preserves Collection 0.3.0 at commit
14091484381778fe55102b58ac584e38f5e0fc6a. Each component has an unmodified
canonical upstream import followed by one local patch combining all gist/fork
and Collection modifications with wheel packaging.

## Installed packages

The entry distribution is `vs-collection-rk==0.4.0+alice.1`. Its dependencies pin
the 12 component wheels exactly. Runtime imports remain `CSMOD`, `havsfunc`,
`mvsfunc`, `vsTAAmbk` and the other original names. Components install the
original single .py files or packages; the entry owns only `vs_collection_rk`.

Component versions with an existing valid upstream marker use a post release:
havsfunc 33.post1, mvsfunc 11.post1, nnedi3-resample 2.post1 and
nnedi3-rpow2 1.1.0.post1. Other initial component versions are 0.3.0.post1,
identifying the Collection snapshot. Source version constants are preserved
byte-for-byte. The exact pins prevent a newer upstream distribution from
silently replacing the curated implementation when installing the entry.

External runtime dependencies remain user-managed, as in the actual
Collection 0.3.0 pyproject.toml. Its old README's matplotlib dependency note
was stale. This migration adds only the explicitly requested component
dependencies to the entry. rksfunc/rkstool are not added to this collection,
and their original repositories and dependency policies are unchanged.

## Installation and old-package migration

After an explicit manual publication:

```shell
python -m pip install --extra-index-url https://aliceteaparty.github.io/vapoursynth-api4-wheels/simple/ vs-collection-rk==0.4.0+alice.1
```

If the old monolithic vs-collection-rk distribution is installed, remove it
before installing the split entry:

```shell
python -m pip uninstall vs-collection-rk
python -m pip install --force-reinstall --extra-index-url https://aliceteaparty.github.io/vapoursynth-api4-wheels/simple/ vs-collection-rk==0.4.0+alice.1
```

A plain in-place upgrade is unsafe because pip can install the new component
dependencies before uninstalling the old entry; the old RECORD still owns
the same script paths and can delete those newly installed files. CI verifies
fresh installation and the documented uninstall-then-install migration.

The metadata helpers `bundled_scripts()`, `find_script()` and
`load_registry()` remain available. The former private `_sources` copies
are replaced by each component's installed dist-info/extra_metadata provenance
record and the maintained source trees here.

## Source history

[../VERSIONS.md](../VERSIONS.md) contains separate plugin and module tables.
The module table records canonical URL/revision, intermediate snapshot,
subtree import commit and the one combined patch commit.

- `modules/collection.json` describes current wheel versions and runtime hashes.
- `modules/collection-history.json` freezes the original migration audit.
- Each component's `provenance.toml` records the intermediate and Collection
  commits and its runtime hashes.
- HAvsFunc's real baseline is HomeOfVapourSynthEvolution/havsfunc at
  7f0a9a7a37b60a05b9f408024d203e511e544a61, followed by the user's gist at
  4e0d21258869283ce04568dda0173e4c8b890668 and the final Collection snapshot.
- nnedi3_rpow2's canonical gist baseline is
  68ec4bdff1e51a3832b163198ed7ea00e1c1ab46. The two later fork commits and
  Collection changes belong in its local patch, not in the canonical revision.

CI inspects the recorded Git import/patch objects and compares the original
migration patch with the immutable Collection snapshot. Later reviewed upstream
updates can change current runtime hashes without erasing that migration proof.

## Updating a component

1. Fetch and review the chosen commit from the component's canonical URL.
2. Merge with `git subtree pull --prefix=modules/<id> <url> <commit> --squash`.
   Resolve any conflicts while preserving the local API and packaging changes.
3. Bump that component's wheel version. Update its current upstream revision
   and runtime hashes in provenance.toml and collection.json.
4. Update the entry's exact requirement and installed _registry.json, bump the
   entry version, and add/update the module version record in VERSIONS.md.
   Preserve collection-history.json and its original import/patch anchors.
5. Run source-history tests and the complete wheel-set preview before publishing.

The upstream layout is retained beneath each subtree, including upstream
documentation and license files. Wheel file selection includes only the
runtime payload, metadata and available license/provenance material.

## CI and manual publication

**Package - vs-collection-rk** builds all component wheels and the entry from
one central commit. It then tests those same artifacts on Windows and Linux
with Python 3.12 and 3.13. It also verifies an offline pip install of only the
entry requirement, proving that all 12 component dependencies are resolved.

**Publish - vs-collection-rk** accepts a successful manual preview run on main
and the reviewed entry version. It checks source plans against that exact
central Git commit, the complete wheel set and all four validation records.
It stages every wheel and collection-manifest.json in one draft release,
checks hashes, then publishes the group and requests the existing Pages index
refresh. There is no automatic release from a push or PR.

Quality checks call the same packaging workflow, but the publisher rejects
PR and non-default-branch runs. Native plugin and external-module workflows
continue to use their existing paths.

For local verification:

```shell
python -m pip install -r scripts/requirements-modules.txt hatchling==1.32.4
python -m unittest discover -s tests -p test_collection.py -v
python scripts/build_collection.py plan
python scripts/build_collection.py build
python scripts/build_collection.py validate --install
```

Source plans read committed Git objects, so commit reviewed source/packaging
changes before generating a plan. Build output goes to ignored dist/collection.
