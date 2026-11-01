# Framework State and Evidence Rules

`workspace/` is reserved for framework-controlled state, decisions, and
evidence. It is not a general tool-development or scratch directory.

- `framework_development/` stores roadmap, phase plans, decisions, and phase notes.
- `build_runs/` stores pipeline run state and gate evidence.
- `artifacts/` stores attributable review requests, verification evidence, and
  short-lived packaging staging data.
- `handoffs/` is historical provenance; do not add new runtime handoffs unless
  a current framework contract explicitly requires them.

Preserve records that are referenced by an active plan, contract, skill, test,
or accepted release decision. Put disposable probes in `test_workspace/` and
remove temporary artifact/staging directories after their result is promoted
to a durable report.

Do not edit product source from this workspace. `run_state.json` and semantic
artifacts have a single writer at a time, and deterministic gate failures must
not be bypassed.
