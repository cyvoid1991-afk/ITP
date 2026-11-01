# Getting started

**Install from a fresh short extraction, verify integrity first, then create the
root Python environment.** The complete PowerShell and POSIX setup, CLI, test,
role-loading and rebuilding commands are in the [public README](../../../README.md).
Read [root rules](../../../AGENTS.md) and [tool rules](../AGENTS.md) before use.

The runtime project root is `tools/intent-tool-pipeline/`; shared skills and
project role configuration remain at the repository root. Use Python 3.11+ and
the root `.venv/` with this tool's `requirements-dev.txt`. CLI defaults are
independent of the current working directory; explicit `--project-root` wins.
Run skill examples from this tool directory. Read [workflow selection](workflows.md),
the selected skill and its invocation adapter before governed work.

New governed runs default to `1.2` under `ITP-20261101-DEFAULT12`; explicit `1.1`
remains compatible and new legacy `1.0` requires `--control-revision 1.0`.
Read [operating/recovery instructions](contracts/agent-rollout.md). This public
candidate includes no existing runs and performs no automatic migration.

Open a fresh Codex session at the repository root and verify exact live role
discovery, effective instructions and model access. Configuration presence and
CLI tests do not prove live dispatch. Missing dependencies/roles or stale
instructions block affected governed work without ordinary-agent substitution.
Run state belongs in `workspace/build_runs/`, product source in
`codex_workspace/<tool_name>/` and governed archives in `deliverables/`.

The root manifest verifies this public seed before environments/caches are
created. The nested component manifest is retained original 0.2.0 evidence.
Read [source identity](../../../SOURCE_IDENTITY.md) and the
[publication boundary](distribution.md) for exact provenance and absent historical
references. Integrity verification, test results and live operation are distinct.
