# Python modules

Modules keep their source, version, dependencies and build backend in their
original repositories. This directory contains registrations, not source
mirrors or submodules. CI checks out a fixed commit in `modules/<id>/src/`
and writes the wheel to `modules/<id>/dist/`; both are ignored by Git.

| Module | Source |
| --- | --- |
| rksfunc | https://github.com/RyougiKukoc/rksfunc |
| rkstool | https://github.com/RyougiKukoc/rkstool |

VapourSynth-Scripts-Collection is not registered in this phase.

## Manual preview from the wheels repository

Run **Package - Python modules** in Actions and select a module. An empty
`source_ref` uses its registered default, currently `main`. Branches, tags
and full commit SHAs in the approved upstream repository can be previewed.
The resolver records the exact SHA before any upstream build code runs.

Optional `source_sha` and `expected_version` must match what is resolved.
If a branch moves between submission and resolution, use the recorded SHA
as `source_ref` when retrying. Select `all` only without source overrides.

The workflow builds the wheel once and checks that same wheel on Linux and
Windows with Python 3.12 and 3.13. It preserves upstream dependency and Python
version metadata, validates RECORD and resource hashes, and verifies installed
files outside the checkout. Runtime dependencies remain user-managed. These
checks do not claim a successful import or exercise external tools/GPU filters.
There are no dependency stubs, automatic runtime installations or rewritten
upstream metadata.

Existing upstreams do not declare `requires-python`, so Hatchling currently
emits `py2.py3-none-any` rather than `py3-none-any`. The pipeline preserves
that existing upstream metadata and accepts pure wheels containing the Python 3
tag. Validation covers Python 3.12 and 3.13; it does not establish Python 2 or
unlisted Python/platform support.

A preview creates Actions artifacts only, retained for 30 days:

- `module-source-plan`: independently resolved source/configuration records.
- `module-wheel-<id>`: one built wheel.
- `module-validation-<id>-<os>-<python>`: metadata, hash and installed-file results.

The build summary lists source SHA, wheel name and wheel SHA256. Expired
artifacts require a new preview of the same fixed upstream commit.

## Manual preview from the upstream repository

The upstream's **Sync wheel preview** workflow calls the reusable
`submit-module-update.yml`. The caller pins both the reusable workflow and
`tools_ref` to the same full central commit. It resolves the caller's selected
source to a commit and sends API v1 inputs to the central preview workflow.

Configure upstream secret `WHEELS_UPDATE_TOKEN` with a fine-grained credential
limited to this wheels repository and **Actions: write**, or a suitably scoped
GitHub App token. Add the actual credential actor/bot to the registration's
`requesters`; initially only `RyougiKukoc` is registered. Do not copy a broad
administrator token into third-party repositories. Actions write is still
repository-wide, not a credential restricted to this one workflow.

The default upstream `GITHUB_TOKEN` cannot trigger this repository. An API
receipt means the preview request was accepted, not built or published.
Without a notification credential, the central maintainer can run a preview
directly, or accept the PR route below.

The source workflow has only a manual trigger. Quality checks on code PRs use
local fixtures; they do not synchronize upstream modules or publish wheels.

## API v1

Endpoint:

```text
POST /repos/AliceTeaParty/vapoursynth-api4-wheels/actions/workflows/package-modules.yml/dispatches
```

The outer `ref` is the central default branch. The module source is separately
specified by `source_ref` and `source_sha`.

```json
{
  "ref": "main",
  "inputs": {
    "api_version": "1",
    "module": "rksfunc",
    "source_ref": "<full-upstream-commit-sha>",
    "source_sha": "<same-full-upstream-commit-sha>",
    "expected_version": "1.1.4",
    "request_id": "rksfunc-1.1.4-<sha>"
  }
}
```

Author requests select one registered module and include ref, SHA, version and
correlation id. No source repository, build command, download URL, destination
or publish switch can be supplied. Sources and requester identities come from
reviewed registrations. Self-reported source labels are not authentication.

## Manual publication

Run **Publish - Python module** on the central default branch, selecting:

1. The module.
2. A successful manual central preview run id.
3. The exact wheel SHA256 reviewed in that build's summary.

Publishing requires all four installed-file validations. The chosen central
run must use `package-modules.yml`, originate on the default branch, and have
a successful conclusion and registered actor. The publisher rechecks upstream
identity and metadata and requires the source commit to belong to upstream
default-branch history. Merge upstream packaging/source PRs first and then
rebuild; feature-branch previews cannot bypass that publication condition.

The publish job downloads the exact tested wheel and does not execute upstream
build hooks or import upstream packages. It creates
`module-<id>-v<project.version>` with the wheel and `source-manifest.json`,
assembling assets in a draft before exposing the Release. The tag targets the
central build configuration commit; the manifest links the separate upstream
source SHA, file hashes, build run and validation results.

There is no clobber or silent version rewrite. An already-published matching
wheel is an idempotent success; a conflicting wheel, source or registration
requires an upstream version bump. Publication is serialized per module.
A complete existing publication can request another index refresh without
replacing its assets.

After the explicit manual publication, the publish job sends the existing
`index` dispatch to refresh Pages. If only index deployment fails, rerun
**Index - GitHub Pages**. Module assets are automatically collected by the
existing shared `/simple/<normalized-distribution>/` index.

## Third-party registration and updates

Open a registration PR containing `modules/<id>/module.toml`, matching
`schema.json`. Review covers the fixed repository id, normalized distribution,
import package, project subdirectory, requester actors and required resources/
license files. Add the module to the choices in the two manual central workflows.
Do not vendor its source or centralize its packaging fixes.

API v1 supports a conventional pure Python package with `__init__.py`, static
project name/version/dependency/Python metadata, standard wheel files and a
PEP 517 backend. Native wheels, namespace-only packages, dynamic versions and
optional-dependency metadata need an explicitly reviewed extension.

Third-party owners need no central write credential to submit a version request:
copy `update-request.example.json` to
`modules/<id>/updates/<version>.json`, replace its values, and open a normal
GitHub contribution PR. After review and merge, a registered central maintainer
manually runs the preview with the matching module and `request` file path.
Merging the PR does not synchronize or publish automatically.

A future GitHub App/OIDC gateway can authenticate external repositories and
submit this same API v1 request. No external service is required for the
current manual/PR paths.

## Licenses and source authority

Keep license expressions and notices upstream. The central repository does
not assign one license to all modules. rksfunc includes the original
KrigBilateral LGPL-3.0-or-later shader and its LGPL/GPL license texts; those
notices do not relicense all Python source. See [../LICENSES.md](../LICENSES.md).
Runtime dependencies for rksfunc and rkstool intentionally remain empty.
