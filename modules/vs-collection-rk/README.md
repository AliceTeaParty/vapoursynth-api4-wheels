# vs-collection-rk

This entry package installs the pinned script components maintained as
individual subtrees in the central wheels repository. Runtime import names
remain CSMOD, havsfunc, mvsfunc, vsTAAmbk and the other original module names.
Python 3.12 or newer is required.

Install from the central index after a manual publication:

    python -m pip install --extra-index-url https://aliceteaparty.github.io/vapoursynth-api4-wheels/simple/ vs-collection-rk==0.4.2+alice.1

## Migrating from the monolithic Collection package

Uninstall the old monolithic distribution first, then install the component
entry package. A plain in-place upgrade can install component dependencies
before removing the old distribution, whose RECORD still owns the same files.

    python -m pip uninstall vs-collection-rk
    python -m pip install --force-reinstall --extra-index-url https://aliceteaparty.github.io/vapoursynth-api4-wheels/simple/ vs-collection-rk==0.4.2+alice.1

If you already upgraded in place, pip may report success and `pip check` may
pass even though the old monolith's uninstall deleted newly installed component
files. This affects all 12 components, including mvsfunc. Repeating a normal
install does not restore them because their distribution metadata still exists.
With entry version 0.4.2+alice.1 or newer, check and restore damaged components:

    python -m vs_collection_rk check
    python -m vs_collection_rk repair --extra-index-url https://aliceteaparty.github.io/vapoursynth-api4-wheels/simple/

The repair checks installed runtime files against RECORD and reinstalls only
damaged components at the entry's exact pins, using the same Python interpreter
and `--force-reinstall --no-deps`. For offline repair, use
`repair --no-index --find-links /path/to/collection-wheels`.
For entry versions without the repair command, the force-reinstall command above
restores the entire component set after the old monolith has been removed.

After installing your runtime dependencies, execute every component and package
child import with `python -m vs_collection_rk check --imports`. This also checks
that mvsfunc exposes Depth and BM3D, so an empty namespace package cannot pass.
An import failure with healthy files reports its traceback; file repair cannot
install missing user-managed runtime libraries or native plugins.

The entry package owns only vs_collection_rk metadata. Each component owns its
original runtime module/package. No component adds external runtime
dependencies; install the VapourSynth libraries and native plugins required
by your scripts separately. The entry's exact component requirements ensure
that installing this package installs the entire curated set.

The public metadata helpers bundled_scripts(), find_script() and load_registry()
remain available. __version__ comes from the installed distribution metadata.
Provenance is recorded in each component's provenance.toml and in VERSIONS.md
at the repository root. The former private _sources copies are replaced by
component metadata; source is maintained in modules/<component>/.
