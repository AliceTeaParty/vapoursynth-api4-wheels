# vs-collection-rk

This entry package installs the pinned script components maintained as
individual subtrees in the central wheels repository. Runtime import names
remain CSMOD, havsfunc, mvsfunc, vsTAAmbk and the other original module names.
Python 3.12 or newer is required.

Install from the central index after a manual publication:

    python -m pip install --extra-index-url https://aliceteaparty.github.io/vapoursynth-api4-wheels/simple/ vs-collection-rk==0.4.5+alice.1

DFTTest calls in havsfunc, muvsfunc and fvsfunc prefer DFTTestVK when its
plugin is present, then use the existing DFTTest2 and classic DFTTest policy.
Native plugins remain user-managed. See [../COLLECTION.md](../COLLECTION.md#dfttest-backend-selection)
for the backend policy and complete call-site inventory.

## Migrating from the monolithic Collection package

Version 0.4.3+alice.1 supports a normal upgrade from both the old monolithic
distribution and the split 0.4.0–0.4.2 distributions, including installations
whose component files were deleted during an earlier upgrade:

    python -m pip install --upgrade --extra-index-url https://aliceteaparty.github.io/vapoursynth-api4-wheels/simple/ vs-collection-rk==0.4.5+alice.1

The old split 0.4.0–0.4.2 releases wrote scripts to paths also owned by the
monolith. Its uninstall could delete newly installed component files while
`pip check` still passed. Version 0.4.2 added a repair command but did not make
normal upgrades safe. Version 0.4.3 moves every component to a private runtime
directory and bumps every component version, so an ordinary upgrade installs
complete files even when old component metadata remains. The public import
names and script source code are preserved. No repair command is needed for
this upgrade.

For later accidental file damage, check and restore damaged components:

    python -m vs_collection_rk check
    python -m vs_collection_rk repair --extra-index-url https://aliceteaparty.github.io/vapoursynth-api4-wheels/simple/

The repair checks installed runtime files against RECORD and reinstalls only
damaged components at the entry's exact pins, using the same Python interpreter
and `--force-reinstall --no-deps`. For offline repair, use
`repair --no-index --find-links /path/to/collection-wheels`.

After installing your runtime dependencies, execute every component and package
child import with `python -m vs_collection_rk check --imports`. This also checks
that mvsfunc exposes Depth and BM3D, so an empty namespace package cannot pass.
An import failure with healthy files reports its traceback; file repair cannot
install missing user-managed runtime libraries or native plugins.

The entry package owns only vs_collection_rk metadata. Each component owns its
module/package under `_vs_collection_rk_runtime` and its own plain `.pth` file
which adds that directory to Python's module search path. These paths are not
owned by the old monolith or the public-layout component wheels. Uninstalling
one component removes only its script and path file; other components retain
their own path files. The `.pth` files contain a directory name and execute no
Python code. No component adds external runtime
dependencies; install the VapourSynth libraries and native plugins required
by your scripts separately. The entry's exact component requirements ensure
that installing this package installs the entire curated set.

The public metadata helpers bundled_scripts(), find_script() and load_registry()
remain available. __version__ comes from the installed distribution metadata.
Provenance is recorded in each component's provenance.toml and in VERSIONS.md
at the repository root. The former private _sources copies are replaced by
component metadata; source is maintained in modules/<component>/.
