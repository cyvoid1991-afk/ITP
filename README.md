# ITP — Intent-to-Tool Pipeline

**ITP supports local tool development through intent preparation, contracts,
implementation, deterministic checks, independent verification and release.**
This public seed is candidate **0.3.0-rc.1**, assembled from explicitly inventoried
Nexus_AI working-tree source. Repository: [cyvoid1991-afk/ITP](https://github.com/cyvoid1991-afk/ITP).
Read the [source identity](SOURCE_IDENTITY.md) and `DISTRIBUTION_NOTICE.md`.

## Current source and original seed

`main` includes post-seed source maintenance recorded in [history](CHANGELOG.md),
including the 2026-11-04 worker-policy synchronization. The preserved root
manifest and provenance describe the original `0.3.0-rc.1` snapshot, not later
source changes. The seed integrity check is expected to report those changes
on current `main`; do not rewrite the old metadata to conceal the difference.
For current-source use, keep `main`, review its history and follow environment
setup and applicable tests below without claiming original-seed integrity.

## Fresh installation

Extract `intent-tool-pipeline-0.3.0-rc.1.zip` into a new, short path, such as
`C:\itp`. The ZIP has no enclosing directory. Do not extract over an existing
installation, and retain the nested `tools/intent-tool-pipeline/` plus root
`.agents/` and `.codex/` directories. On Windows, preflight the destination plus
the longest archive member: generated parent paths must remain below 180
characters, directory segments at most 32 characters and filenames at most 64.
Use an archive utility that preserves dot-prefixed directories.

Alternatively, clone the public repository into a new short directory:

```powershell
git clone https://github.com/cyvoid1991-afk/ITP.git C:\itp
Set-Location C:\itp
git checkout --detach c80f332f41348870ac133954d3284511709fbbdc
```

The checkout command selects the original seed for the integrity procedure.
Omit it when intentionally using current `main` as described above.

The bundled `.gitattributes` disables text conversion so Git preserves manifest
and procedure bytes even when `core.autocrlf=true`. GitHub's generated source
ZIP wraps the tree in a repository-named folder; change into that folder before
running commands. The custom release seed ZIP described above has no wrapper.
For every method, run the integrity check below before setup or caches.

Run integrity verification **before** creating an environment, opening Python
entry points that create caches, editing files or running tests. From the new
extraction root, with Python 3.11 available:

```powershell
python tools/intent-tool-pipeline/verify_bundle.py
```

Expected result: `PASS: all bundle files match; no unexpected files`.
This compares the root manifest with the fresh extraction; it is not a signature
or independent proof that the publisher is trusted. The component's nested
manifest is preserved historical import evidence, not the current seed manifest.

## Pipeline quick start

Create the repository-root environment with **Python 3.11 or newer** and install
the pinned runtime/development dependencies (`PyYAML==6.0.3`, `pytest==9.1.0`):

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r tools/intent-tool-pipeline/requirements-dev.txt
.\.venv\Scripts\python.exe tools/intent-tool-pipeline/pipeline_ops.py --help
.\.venv\Scripts\python.exe .agents/skills/build-tool-pipeline/scripts/initialize_run.py --help
.\.venv\Scripts\python.exe -m pytest tools/intent-tool-pipeline/tests -q --basetemp=.tmp/itp
```

On POSIX, use `python3.11 -m venv .venv` and `.venv/bin/python` for subsequent
commands. Keep the declared environment; report missing dependencies rather
than switching silently. These are installation checks to run, not historical
evidence of success. Integrity verification expects a fresh tree and will report
environments/caches created afterward; use a second untouched extraction for
another integrity check.

## Roles and usage

Open a fresh Codex session **at this repository root**. Read [root rules](AGENTS.md),
[tool rules](tools/intent-tool-pipeline/AGENTS.md), the
[getting-started guide](tools/intent-tool-pipeline/docs/getting-started.md),
[workflow selection](tools/intent-tool-pipeline/docs/workflows.md), and the
selected skill. Project skills live in `.agents/skills/`; project role definitions
and defaults live in `.codex/agents/` and `.codex/config.toml`. Do not copy them
into a personal agent directory as an installation step. See the
[role loading guide](.codex/agents/README.md).

Check that the fresh session actually exposes the required exact roles and
effective instructions. Static TOML checks and CLI loading do not prove live
discovery, model access, boundary enforcement or dispatch. Missing roles/model
access or stale loaded instructions block affected governed work; refresh the
session and resolve them. Do not substitute a generic agent and claim the named
role ran. Actual hosted Codex/model availability is a client prerequisite.

Trigger the workflow in that Codex session:

```text
Use $intent-tool-pipeline to prepare and deliver <the tool you want>.
```

For clear direct implementation intake, use `$build-tool-pipeline` with Direct B.
For intent preparation only, use `$intent-realization` and request stopping before
Workflow B. Include inputs, outputs, constraints and authority boundaries. More
examples are in the [trigger guide](tools/intent-tool-pipeline/BUILD_TOOL_PIPELINE_TRIGGER.md).
Simple fixes and general analysis do not automatically require the full workflow.

New governed runs default to **control `1.2`**, including workflow-owned procedure
binding. Explicit `1.1` remains compatible. A new legacy run requires the explicit
initializer option `--control-revision 1.0`; see the initializer `--help` and
[rollout/recovery procedure](tools/intent-tool-pipeline/docs/contracts/agent-rollout.md).
The public version `0.3.0-rc.1` is a bundle identity, not control revision `1.2`.
The seed contains no live runs and performs **no automatic existing-run migration**.
Retain compatible prior installations and historical selectors/receipts when
handling an existing run; migration needs separate authorization and evidence.

The CLI defaults to `tools/intent-tool-pipeline/` regardless of the caller's
working directory. Product source belongs in its `codex_workspace/<tool_name>/`,
supplied intent in `intent_deliver/`, run state in `workspace/build_runs/` and
governed release archives in `deliverables/`. Read the selected skill and exact
invocation adapter before calling an artifact role; Root owns registration and
canonical state, and Verifier independence remains required.

## Rebuild and fresh-install checks

An unchanged extracted seed can reproduce the ZIP, including original provenance:

```powershell
.\.venv\Scripts\python.exe tools/intent-tool-pipeline/packaging/public/build.py --output .tmp/itp-public.zip
.\.venv\Scripts\python.exe -m pytest tools/intent-tool-pipeline/tests/test_public_seed.py -q --basetemp=.tmp/public
```

Extract the rebuilt ZIP into another fresh short directory, verify it before
environment/caches, then repeat environment setup, both CLI help commands and
the full test suite above. Compare ZIP SHA-256 with the original to confirm
byte-for-byte reproduction. Generated provenance binds the input snapshot;
editing shipped source requires a newly reviewed public snapshot rather than
reusing the old provenance.

**Trade-off:** the seed ships procedures and tests while omitting private
workspace evidence. Some retained historical links intentionally point to absent
source-only targets; `DOCUMENT_REFERENCES.json` makes those
omissions visible. They are not available evidence or active runtime dependencies.
See [publication policy](tools/intent-tool-pipeline/docs/distribution.md).
No license has been selected; this bundle grants no third-party redistribution
permission. No live agent or external service check is claimed by installation
documentation.
