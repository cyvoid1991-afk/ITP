# Repository integration and migration

For selected controls 1.1/1.2, use the
[new-run operating and rollback procedure](contracts/agent-rollout.md).
The user-authorized post-S7 override `ITP-20261101-DEFAULT12` (2026-11-01)
makes new-run initialization default to `1.2`. Retain explicit compatible `1.1`;
use explicit `--control-revision 1.0` only when a new legacy run is requested.
This is no authorization to migrate existing runs or rewrite their selectors,
bindings, receipts, hashes or round history. Retain a compatible installation
before procedure-byte updates or operational rollback; recover interrupted work
against original project/run paths, then obtain fresh owner bindings before
forward use. S7 grants no release, baseline promotion or additional rounds.

**Nexus_AI keeps shared Codex discovery at the repository root and the optional
pipeline runtime under `tools/intent-tool-pipeline/`.** The original 0.2.0 flat
seed layout is historical distribution evidence, not the current runtime map.

| Original extracted path | Current location |
| --- | --- |
| `.agents/`, `.codex/` | Repository root `.agents/`, `.codex/` |
| `pipeline_ops.py`, `pipeline_control/`, `tests/` | `tools/intent-tool-pipeline/` |
| `codex_workspace/`, `workspace/`, `intent_deliver/`, `deliverables/` | Under the tool directory |
| Original seed `AGENTS.md` and README | Tool policy and documentation; new root documents define repository scope |

The CLI and root skill initializer default to the tool runtime root. Explicit
`--project-root` overrides remain supported. Use the repository-root `.venv`;
see [setup](getting-started.md). Moving discovery files improves repository-wide
availability, but commands, Markdown links and package lists must preserve the
distinction between repository and runtime roots.

When incorporating an existing product, review authoritative source, tests,
documentation, license, dependencies and revision history before placing it in
tool-local `codex_workspace/<tool_name>/`. Preserve user data and generated
results in their assigned locations. Review conflicting repository instructions
and agent definitions before governed execution; do not overwrite another
repository's configuration with an extracted bundle.

Initialized run paths, state keys and artifact identities are not cosmetic
documentation paths. Do not rename or silently revalidate them. Historical
completed runs and release archives remain evidence. A `REVISION` requires the
build skill's exact eligible baseline; incomplete evidence means `FRESH_REQUIRED`.
Preserve the original manifest and import map; they do not attest the relocated
tree. Alternate-agent adapters have not been verified.
