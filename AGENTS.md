# ITP repository working instructions

**This repository owns the public ITP seed; its runtime project root is
`tools/intent-tool-pipeline/`.** Read the [tool README](tools/intent-tool-pipeline/README.md)
and [tool instructions](tools/intent-tool-pipeline/AGENTS.md) before use or changes.
Shared skills are in `.agents/skills/` and registered project roles are in
`.codex/agents/`; preserve their authority and independent-verifier boundaries.

## Work and ownership

| Work | Location |
| --- | --- |
| Framework runtime, procedures and tests | `tools/intent-tool-pipeline/` |
| New pipeline product source | Tool-local `codex_workspace/<tool_name>/` |
| Supplied intent | Tool-local `intent_deliver/` |
| Run evidence and framework records | Tool-local `workspace/` |
| Governed release archives | Tool-local `deliverables/` |
| Disposable reproducible work | Root `.tmp/` or tool-local `test_workspace/t/` |

Inspect the working tree and applicable local instructions first; preserve
unrelated changes. Prefer small reversible changes. Resolve absolute paths and
authorized scope before deletion or moving. Keep source and required evidence
out of disposable directories. Use the repository-root `.venv/`; follow the
[engineering guide](docs/engineering.md) for path budgets and package checks.

ITP is optional: framework maintenance, analysis and simple isolated fixes do
not automatically start A/B. Read the selected skill and bound adapter for
governed work. Do not bypass failed deterministic gates or migrate existing runs
automatically. New governed runs default to `1.2`; explicit `1.1` is compatible,
and new legacy `1.0` requires explicit selection.

## Delegation and evidence

Root owns decomposition, integration and final validation. Follow the
[delegation policy](.agents/delegation-policy.md) and exact role instructions.
Assign bounded scope and exclusive write ownership; tell agents they share a
workspace and must preserve others' changes. Do not concurrently write shared
state or artifacts. Keep semantic roles within their declared write boundaries
and preserve verifier independence.

Run relevant smoke checks and necessary automated tests for executable changes;
report failed/unperformed checks. Verify documented commands and paths. Use
English for repository reports, preserving source quotations/raw evidence in
their original language. Lead with conclusions and explain facts, interpretation,
impact, trade-offs and failure conditions when material.

Record material public packaging/policy changes in [root history](CHANGELOG.md)
and component changes in the tool history with date, revision, affected scope,
compatibility, actual verification and limitations. Preserve historical releases,
component manifests and original evidence; add corrections separately.
Read [source identity](SOURCE_IDENTITY.md) before making provenance claims.
