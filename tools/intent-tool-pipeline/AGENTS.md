# AGENTS.md

Current operating rules for the optional Intent-to-Tool Pipeline, tool development,
realistic demos, and pipeline framework maintenance. Read [repository rules](../../AGENTS.md) first.
The runtime/project root for all unqualified paths here is `tools/intent-tool-pipeline/`.
This workflow is not the default for Nexus_AI research or experiments. Keep
pipeline activities in their assigned directories; the closest nested
`AGENTS.md` adds workspace-specific rules.

## Repository Routing

| Work type | Authoritative location |
| --- | --- |
| Tool source, tests, documentation | `codex_workspace/<tool_name>/` |
| Supplied intent packages | `intent_deliver/` |
| Tool demos and usage findings | `demo_workspace/` |
| Disposable probes and integration fixtures | `test_workspace/` |
| Framework implementation and policy | Tool root, `pipeline_control/`, `tests/`; shared `.agents/` and `.codex/` at repository root |
| Framework state and retained evidence | `workspace/` |
| Verified release archives | `deliverables/` |

Generated output, demo copies, and scratch fixtures are not canonical product
source. Promote reusable changes into the product tree and verify them there
before release. Preserve historical `workspace/handoffs/` provenance; new intent
inputs belong in `intent_deliver/`.

### Build Tool Pipeline Routing

- Use `$intent-tool-pipeline` as the combined entry point; A and B remain independently callable. Read its optional-workflows reference before offering documentation rework.

- Use `$build-tool-pipeline` for approved new or behaviorally revised local tools
  under `codex_workspace/` needing staged delivery, a product contract, tests,
  independent verification, and release packaging.
- Use `$intent-realization` for Workflow A when converged intent needs realized
  conditions and delegation. Workflow B starts with Root + Contractor from a
  prepared handoff or sufficiently clear direct intake; do not repeat A automatically.
- Do not route framework maintenance, demo-only work, scratch testing, simple
  isolated fixes, generic analysis, status work, or standalone documentation edits without a new verified release request
  into the pipeline.
- Use `$minor-tool-revision` for a qualified bounded change or local patch/full
  package of an existing tool at its declared authoritative source. New ITP
  products still default to `codex_workspace/`. Independently assembled local
  deliveries use repository-root `deliverables/`; governed releases retain the
  tool-local location and gates. A local delivery cannot bypass an unfinished
  or failed governed operation or become an eligible baseline.
- At governed A/B intake and resume, read the
  [Root authority rules](docs/governance/Root_Autonomy_Instruction_v0.3.md),
  [delegation and delta procedure](docs/governance/Root_Delegation_and_Delta_Procedure_v0.3.md),
  relevant lightweight fields of the
  [delegation contract](docs/governance/Task_Delegation_Contract_Template_v0.3.md), and the
  applicable Skill. These record existing authority, not new user authority.
- Root owns run state, product source, and release. Preserve semantic ownership
  and never bypass a failed deterministic gate.

## Common Operating Rules

- Inspect existing files before editing; preserve unrelated user work.
- Use small, reversible changes with explicit runnable inputs and outputs.
  Avoid unnecessary dependencies, abstractions, and configuration layers.
- Resolve exact paths before deletion; do not clean up outside approved scope.
- Keep retained framework evidence separate from disposable probes and demos.

### Module Responsibility and Boundaries

Choose cohesive modules around independently changing responsibilities. Separate
computation, validation, orchestration, rendering, and persistence when a module
combines three or more independently changing concerns. Keep small scripts
cohesive and a thin stable facade where useful;
do not split files solely to satisfy a line-count target.

### Windows Name and Path-Length Budget

- Before creating generated paths (including runs, sessions, worktrees, temporary
  output, and artifacts), resolve and measure them. Default limits: directory
  segment <=32 characters, leaf filename <=64, absolute parent path <180.
  Reserve suffix headroom and honor stricter application limits.
- Use short recognizable names; when uniqueness is needed, use one stable stem
  plus a 6-10 character digest. Preserve full meanings in metadata, not repeated
  path segments. Preserve user-facing names and compatibility paths unless a
  rename is approved.
- If over budget, shorten generated identifiers or use `test_workspace/t/<id>`
  before execution. Give pytest and similar tools an explicit short, unique
  temporary/base directory on Windows.
- Before packaging or extraction, preflight the longest member path against the
  destination, including application-added nesting; shorten the destination if needed.

## Subagent Delegation

Root Codex owns top-level delegation. Delegate bounded independent work when it
materially improves speed or quality; Root owns integration and final validation.

- During authorized coding work, Root may spawn built-in `worker` agents for
  implementation, fixes, and tests without further confirmation. Explicitly
  choose `gpt-6.1-sol` or `gpt-6.1-terra` and `medium` or `high` reasoning.
  Other worker settings require user authorization; custom-role settings are separate.
- When model overrides require partial/no history, use `fork_turns="none"` and
  supply context, inputs, expected outputs, and exclusive file ownership. Tell
  workers they share the codebase and must preserve others' edits.
- Preserve workflow write restrictions and reserve capacity for required roles.
  Do not parallelize writes to `run_state.json`, a semantic artifact, or the same
  product-tree paths. Root owns decomposition, conflict avoidance, and synthesis.
- The custom semantic roles `intent_realizer`, `collaborative_intent_shaping_agent`,
  `product_contract_agent`, and `independent_verifier` must not spawn agents.
  Built-in workers and
  explorers retain the execution environment's current delegation authority.
- Project fallback settings live in repository-root `.codex/config.toml`; defaults are not a
  runtime-enforced ceiling or a replacement for the worker limits above.

### Reusable Semantic Roles and Workflow Binding

- `collaborative_intent_shaping_agent` and `problem-framing` are available for
  general problem and intent framing; selecting either does not start Workflow A/B.
- `problem_framer` and `collaborative_intent_framing_agent` are retired.
  Preserve historical owner identities and hashes. If an unmarked historical run
  needs a fresh `problem_framer` invocation, report that missing-role dependency
  as blocked pending an explicitly authorized migration or restoration; do not
  substitute the successor under the retired identity.
- Selecting a role does not start Workflow A/B. For ordinary use, Root supplies
  the task, authorized sources, judgment scope, and return format. Preserve
  read-only roles, verifier independence, and the prohibition on further delegation.
- For every governed A/B or historical-run invocation/resume, load and bind the
  required Skill and role adapter through the
  [invocation procedure](../../.agents/skills/build-tool-pipeline/references/invocation.md).
  Missing procedural dependencies do not permit fallback to ordinary mode.
- For control revision `1.1` or `1.2`, the three artifact roles
  write only their assigned noncanonical submission under the bound procedure.
  Ordinary semantic reasoning stays reusable; pipeline commands and schemas stay
  in adapters. Legacy calls retain their original complete-body transport.
  Root registers unchanged bytes and consumers read actual registered artifacts.
  Verify effective role reload before using the conditional write procedure.
- Selected control `1.2` inherits those ownership and round rules and
  additionally use the workflow-owned [procedure binding](docs/contracts/procedure-binding.md).
  The child loads the exact assignment and mandatory original procedures;
  supported commands enforce binding at admission and forward use. Ordinary
  role semantics and earlier receipts remain unchanged.
- S7 (`ITP-20261101-ARTIFACT-S7`, 2026-11-01) publishes the
  [selected new-run operating procedure](docs/contracts/agent-rollout.md).
  The user-authorized post-S7 override `ITP-20261101-DEFAULT12` (2026-11-01)
  makes `1.2` the new-run initializer default; `1.1` remains an explicit
  compatible route and new legacy `1.0` requires explicit selection.
  Existing runs retain their recorded selectors, receipts and round history.
  Models, reasoning, role independence and delegation boundaries are unchanged.
  Retain a compatible installation before procedure updates or rollback; changed
  procedure bytes require fresh assignments before forward use, never edits to
  historical bindings. S7 grants no migration, release or additional rounds.
- General role outputs become active pipeline artifacts or approvals only after
  the owner, source, boundary, finalization, and gate checks. Verifier evidence
  writes require a task-specific isolated directory or an explicitly bound exact
  result file under its runtime boundary; otherwise the role is read-only.

## Revision Recording Policy

- Every new tool and material tool/framework revision needs an authoritative
  history entry in the same change. Start with the initial delivered baseline;
  record behavior, interface, schema, workflow, policy, compatibility, and release
  changes. Typo-only corrections need no entry.
- Tool history stays in `codex_workspace/<tool_name>/` (CHANGELOG, REVISION_HISTORY,
  or a labeled README section). Component history stays in its maintained
  documentation; cross-cutting framework records belong under
  `workspace/framework_development/`.
- Repository operating-policy history belongs in
  [root history](../../CHANGELOG.md); pipeline component history belongs in
  [tool history](CHANGELOG.md), not this file.
- Include date and revision ID, trigger, behavioral difference, affected components,
  compatibility/migration impact, actual verification, and limitations. Finish
  provisional entries before reporting completion; never claim unperformed checks.
- Released history is append-only. Correct past claims through a labeled correction
  or superseding entry. History is not current policy or required startup reading.

## Verification

Before completion, run/smoke-test changed executable code and relevant automated
tests, check expected paths, and compare documentation with actual commands and
layout. Report incomplete checks. Use the repository virtual environment for
framework checks when available: `../../.venv/Scripts/python.exe` from the tool directory
on Windows. The CLI defaults to this tool project root from any working directory;
explicit `--project-root` overrides remain supported.
Do not silently substitute another environment because a dependency is missing.

## On-Demand References

| When needed | Read |
| --- | --- |
| Framework file locations, load order, evidence, or historical path mapping | [Current framework inventory](docs/current-framework.md) |
| Repository overview and usage orientation | [README](README.md) |
| Prior repository policy changes or compatibility investigation | [Pipeline history](CHANGELOG.md) and [repository history](../../CHANGELOG.md) |

Follow the selected Skill and adapter for detailed workflow commands, role outputs,
and schemas. Read history for provenance, not as additional runtime instructions.
