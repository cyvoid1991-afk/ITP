# Intent-to-Tool Pipeline

**Support local tool development from intent preparation through contracts, implementation, independent verification, and release.**
This is an optional Nexus_AI tool; it does not apply automatically to research, experiments, or general analysis.
Workflow A prepares intent; Workflow B implements prepared intent or a sufficiently clear request.

## Execution Locations

| Component | Location |
| --- | --- |
| Shared repository policy and configuration | [Root AGENTS.md](../../AGENTS.md), [skills](../../.agents/skills/intent-tool-pipeline/SKILL.md), [Codex configuration](../../.codex/config.toml) |
| Pipeline policy and runtime project root | [This directory](AGENTS.md): `tools/intent-tool-pipeline/` |
| Python environment | Repository-root `.venv/` |
| Authoritative tool source | `codex_workspace/<tool_name>/` |
| Intent inputs, run evidence, and releases | `intent_deliver/`, `workspace/build_runs/`, `deliverables/` |

The CLI uses this tool directory as its default project root, regardless of the caller's working directory.
An explicit `--project-root <path>` takes precedence. Run skill examples from this directory.

## Getting Started

Prepare a Python 3.11+ `.venv` at the repository root and install the tool's `requirements-dev.txt` dependencies.
See the [root quick start](../../README.md). The PowerShell commands below run from the **tool directory** after the initial directory change:

```powershell
Set-Location tools/intent-tool-pipeline
../../.venv/Scripts/python.exe pipeline_ops.py -h
../../.venv/Scripts/python.exe -m pytest tests -q --basetemp=../../.tmp/itp
../../.venv/Scripts/python.exe ../../.agents/skills/build-tool-pipeline/scripts/initialize_run.py -h
```

Omit `Set-Location` if already in the tool directory.
On POSIX, use `../../.venv/bin/python`.
Before execution, read the [tool instructions](AGENTS.md), [getting-started guide](docs/getting-started.md),
[workflow selection guide](docs/workflows.md), and the selected skill and adapter.

**Key trade-off:** use A/B for delivery that needs staged evidence and independent verification.
Automatically applying it to simple fixes or general research can introduce more procedure than the request warrants; follow the routing criteria.
Missing required roles or dependencies, failed control gates, and ineligible baselines block progress.

For governed new runs, follow the [selected new-run operating procedure](docs/contracts/agent-rollout.md)
and its user-authorized post-S7 override (`ITP-20261101-DEFAULT12`, 2026-11-01).
Omitting `--control-revision` now selects `1.2` for procedure-bound specialist
submissions. Explicit `1.1` remains compatible; use `--control-revision 1.0`
only when a new legacy run is requested. Existing runs retain their
selectors, receipts and round history. Models and role boundaries are unchanged;
activation grants no migration, release or additional-round permission.

For small compatible revisions, the [minor revision skill](../../.agents/skills/minor-tool-revision/SKILL.md)
also supports local patch and full packages with source tests, package checks,
hash-bound delivery records and future intake linkage. The [local delivery contract](../../.agents/skills/minor-tool-revision/references/local-delivery.md)
defines `minor_delivery.py` commands. These packages remain cumulative local
deltas, not pipeline-verified releases or eligible baselines.

## Maintenance and Provenance

See the [current framework](docs/current-framework.md), [maintenance guide](docs/maintenance.md),
and [migration guide](docs/migration.md).
`SOURCE_MANIFEST.json` and the [provenance map](docs/source-import.json) are evidence for the original 0.2.0 distribution.
Do not treat them as current verification of the restructured working tree or update them merely to force a pass.
Preserve [released history](CHANGELOG.md); new bundles use a repository layout containing root configuration and `tools/intent-tool-pipeline/`.
No license has been selected, and this document does not grant permission to redistribute third-party material.
