# Repository Delegation Policy

Read this policy before delegating repository work. It preserves the execution
limits formerly recorded in root [AGENTS.md](../AGENTS.md); moving them here
does not expand delegation authority or start a pipeline workflow.

## Built-in Workers

- During authorized coding work, built-in `worker` agents may handle
  implementation, fixes, and tests when the current runtime permits delegation.
- Explicitly select `gpt-6.1-sol` or `gpt-6-luna` with `low`, `medium`, or `high`
  reasoning. Other worker settings require user authorization; custom-role
  settings are treated separately.
- When model overrides require partial or no history, use `fork_turns="none"`
  and provide context, inputs, expected outputs, and exclusive file ownership.
  Explain that the workspace is shared and other changes must be preserved.
- Built-in workers and explorers follow the current runtime's delegation
  authority. This document does not override runtime restrictions.

## Role and Workflow Boundaries

- Before assigning a custom role, read its configuration under
  [.codex/agents/](../.codex/agents/) and its applicable task instructions.
  Preserve its read-only or isolated-probe write boundary and delegation limits.
- The current custom roles `product_intake_consultant`, `intent_realizer`,
  `product_contract_agent`, `independent_verifier`, `theoretical_analysis_agent`,
  and `collaborative_intent_shaping_agent`
  must not spawn subagents.
  Their role configurations retain those prohibitions.
- Reserve capacity for roles required by the selected workflow. Do not write
  concurrently to the same file, run state, or semantic artifact.
- Preserve verifier independence. Role selection alone does not invoke ITP;
  governed ITP assignments follow the
  [ITP instructions](../tools/intent-tool-pipeline/AGENTS.md).

## Task-scoped artifact output

Role selection never grants ambient write permission or selects a pipeline.
Preserve reusable semantic reasoning; bind procedure-specific paths, schemas,
commands and lifecycle rules outside it. The three artifact roles may author an
exact new noncanonical result only under their explicit task-procedure exception.
Ordinary Realizer/Contractor calls stay read-only; Verifier evidence stays isolated.
Parent-inherited runtime permissions are separate from this authorized write scope.
Root retains canonical registration and state ownership.

For ITP, use the selected/legacy branches in the
[invocation procedure](skills/build-tool-pipeline/references/invocation.md).
Revision `ITP-20261101-DEFAULT12` (2026-11-01), authorized by the user after S7,
makes control `1.2` the new-run default. Explicit `1.1` remains compatible;
legacy `1.0` requires explicit `--control-revision 1.0` for a new run. Follow the
[rollout procedure](../tools/intent-tool-pipeline/docs/contracts/agent-rollout.md)
for selection, procedure drift and compatible recovery. Check effective role
reload; do not claim permission support from static configuration. Existing runs
retain their selectors, evidence and round history.

## Configuration Defaults

[.codex/config.toml](../.codex/config.toml) supplies project defaults. Those
defaults neither replace the worker limits above nor guarantee a
runtime-enforced ceiling. Custom-role model and reasoning settings remain
in their role configurations.
