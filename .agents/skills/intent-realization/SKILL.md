---
name: intent-realization
description: Run Workflow A with Root to realize supplied converged intent, discover missing conditions, and prepare a source-linked brief and delegation handoff for Contractor. Use for upstream preparation or scoped material intent returns. Clear/simple requests may enter implementation directly. Not product-contract authoring, implementation, or verification.
---

# Intent Realization

## Repository integration

For pipeline work, first read [the tool rules](../../../tools/intent-tool-pipeline/AGENTS.md).
The pipeline project root is `tools/intent-tool-pipeline/`, not the Nexus_AI root.
Paths such as `docs/`, `codex_workspace/`, `workspace/`, `intent_deliver/`,
`test_workspace/` and `deliverables/` in this workflow are relative to that tool root.
Shared `.agents/` and `.codex/` paths are relative to the Nexus_AI root.
Run workflow command examples from the tool directory; use the root virtual environment.
General research or standalone role use does not start Workflow A/B.


This skill selects Workflow A; selecting the reusable intent_realizer role alone
does not select this workflow. Root must name this skill in every Workflow A
invocation and supply the input, output identity and delegated boundary below.
Read [the invocation binding](../build-tool-pipeline/references/invocation.md) for
governed calls. The role's ordinary use does not require this artifact adapter.

Use one or more supplied intents; a UX-only request is valid input. Do not require
a separately named engineering handoff. The user supplies the desired outcome;
they need not anticipate every technical condition required to achieve it.

## Workflow A entry and ownership

The user may refine intent interactively in external ChatGPT before handing it to
Root. Read the supplied content; never depend on access to an unprovided external
conversation. Keep source intent, explicit decisions and their provenance distinct
from Root interpretations, facts, proposals and unresolved choices.

Root reads the repository's `docs/governance/Root_Autonomy_Instruction_v0.3.md` and
`docs/governance/Root_Delegation_and_Delta_Procedure_v0.3.md`, prepares a minimal existing-authority
skeleton, directs evidence gathering and obtains material user decisions. Root
maintains the lightweight `docs/governance/Task_Delegation_Contract_Template_v0.3.md` boundary.
Realizer owns only the brief and realization readiness: flag an authority gap,
but do not grant Root authority, author a product contract or approve acceptance.
Do not require the user to fill a delegation table or predetermine every internal
implementation choice. Upstream interaction is intended work, not a failure metric.

Workflow B starts with Root + Contractor. It consumes a prepared handoff without
a mandatory new Realizer call. A sufficiently clear/simple request may start B
directly without this workflow or the full delegation template.

## Read for meaning and authority

Read the request and its authorized source material, not only a previous agent's
summary. Identify requested outcomes, explicit non-changes, existing obligations,
and who may decide unresolved matters. Distinguish user decisions, established
facts, baseline behavior, agent proposals, and unknowns. Document type alone does
not establish priority. Preserve an approved change over conflicting old behavior
only within its authorized scope.

## Discover what realization requires

Connect relevant inputs, actions, state transitions, outputs and failure paths.
Inspect how a plausible implementation could satisfy the wording yet violate the
purpose. Examine the dimensions that actually matter: units, numerical and
boundary assumptions, ordering, defaults, resource limits, persistence, user
interpretation, or compatibility. Do not turn every dimension into a requirement.

For each consequential gap, explain:

- the outcome or invariant at risk and the source that motivates it;
- a concrete failure or counterexample;
- the condition needed to prevent it;
- a supported policy or bounded alternatives, including remaining uncertainty;
- who resolves it and what later evidence would establish correctness.

For example, an FFT-based transient request may omit padding and crop semantics.
Discover the possible mismatch between the requested finite-record behavior and
the chosen numerical operation; establish conditions and validation rather than
asserting a universal padding multiplier. A familiar plot style does not authorize
copying another quantity's arithmetic. These are examples, not mandatory checks
for unrelated products.

## Resolve bounded gaps

Use authorized documentation, code inspection and bounded analysis to support a
proposal. Respect the runtime read/write boundary; ask Root to execute probes if
the role is read-only. A proposed default needs applicability, result/resource
impact, override/failure behavior and evidence appropriate to its risk.

Resolve ordinary choices within delegated authority and record the basis. Do not
escalate every default. Do not invent user preferences, acceptable error, physical
boundary conditions, or a new scope to avoid asking. Root first checks existing
intent and authorization, then obtains only the material missing decision.

When the remaining question needs a new objective or open-ended model research,
return the exact unresolved decision and useful work already completed. Missing
implementation guidance alone is not a reason to reject the intake.

## Return a realization brief, not a contract

Keep a complete but concise current brief with intent, behavior flow, preserved
meaning, derived conditions, relevant defaults, assumptions, unresolved questions,
and evidence needs. Give consequential proposals local identifiers under Decisions
so subsequent contract decisions can cite or reject them. Each proposal must name
its basis, status/authority and a failure it addresses. Do not create a parallel
REQ/ACC catalog or prescribe internal structure without a behavioral reason.

The product-contract agent independently compares the brief to original intent,
challenges unnecessary constraints and unsafe assumptions, and owns binding
requirements plus checkable acceptance. Its readiness judgment is not compelled
by this brief's PASS. On a bounce-back, revise only on a changed basis, preserve
resolved decisions, and return the complete current body.

Contract-ready means the contract author can evaluate proposed obligations and
acceptance without materially guessing the intended outcome or identified
realization conditions. Resolve consequential gaps or explicitly assign them to
safe downstream discretion without concealing a material decision. This is
readiness for critical contract authoring, not an approved contract or a claim
that implementation can start. The contract author may still reject proposals,
identify further gaps, or return BLOCKED. Formatting completeness and an
impressive plan do not demonstrate feasibility or implementation correctness.

## Prepare a consumable handoff

Return the complete owner-authored brief with original sources and explicit user
decisions, realized conditions/evidence, visible assumptions, open decisions and
delegated downstream choices. Root binds it to the task delegation boundary and
applicable source versions using existing run records, not a duplicate contract.
The handoff index must identify the brief return/invocation, stored version/hash,
source intent and delegation version, held scope and safe independent work.
Put source, decision, invocation and external-index references in Input Reviewed,
Decisions and Handoff Readiness. Root records post-persistence byte hashes in
`active_artifacts` or a separate existing handoff index; never embed an artifact's
own final-byte hash in that artifact or edit an adopted brief to insert it. Actual
source/delegation snapshots may live in the run's `00_intake/` directory.

Before declaring readiness, test whether a Contractor with no original chat can
identify the contract to write, material unresolved choices, delegated/reserved
areas and the source basis for later drift checks. Missing source meaning that
forces a material guess blocks affected readiness. Non-blocking assumptions and
delegated technical choices remain permissible. Root persists the adopted brief
unchanged; binding the handoff is not a new user approval or a Realizer override.

On a B return, use the precise issue, evidence and changed basis supplied by Root.
Preserve resolved intent and revise only affected reasoning, returning a complete
current brief when it changes. Ordinary context, technical and contract-expression
issues stay under Root/Contractor in B; only unsupported material intent/preference/
loss/authority needs upstream/user decision. Update affected sources and delegation
through Root; downstream contract and verification judgments belong to their owners.

## Governed run adapter

For `1.2` runs, including the new-run initializer default, load the workflow-owned assignment
through [assignment-entry.md](../build-tool-pipeline/references/assignment-entry.md).
Apply the selected `1.1` file/compact transport below, adding exactly one
procedure-binding JSON comment containing the loader's `required_result_binding`.
Read the bound original procedures and inputs. Reusable semantic judgment and
ordinary behavior remain unchanged. The user-authorized post-S7 override
`ITP-20261101-DEFAULT12` (2026-11-01) makes new runs default to `1.2`;
new legacy `1.0` requires explicit selection and `1.1` remains an explicit compatible route.
Follow the
[rollout procedure](../../../tools/intent-tool-pipeline/docs/contracts/agent-rollout.md).

For Workflow A use the exact `intent_realizer` role. The existing
`framing` stage, `problem_frame` key, `problem-frame` ID and
`10_framing/problem_frame.md` path are compatibility names for this brief, not a
request to call `problem_framer`. Root owns persistence and run-state transitions.
Use the exact headings/metadata in the Required brief format below; place
condition/decision records within those headings. Root may initialize the existing
run for A and stop after its audited framing handoff. B later resumes that run at Root +
Contractor intake; no second realization is required. No extra artifact or schema
is needed. The build-pipeline gate-map supplies boundary/finalize commands.

For a revision, use the exact resolved verified baseline named by Root as immutable
context. Return a complete current brief carrying requested changes, explicit
non-changes, accumulated source deltas, compatibility/migration and whole-product
regression needs. An ineligible baseline or broad/incompatible/ambiguous delta
requires `FRESH_REQUIRED`; never silently substitute or refresh it.

Record material bounce-backs and Root answers through the existing pipeline
mechanism. Clarification is not automatically a repair attempt; preserve the
control plane's repair-entry rules: legacy control keeps two attempts; selected
control "1.1" uses the four-round ledger and separately reviewed, explicitly
user-approved finite continuation described in the build-pipeline gate-map. Keep agent-to-agent
answers attributable and understandable without hidden chat history.

### Invocation inputs and return ownership

- Primary input: the exact current `build_request.yaml` named by Root.
- Supporting inputs: authorized sources referenced by that request and additional
  evidence explicitly named by Root, including current responses to bounce-backs.
  Use relevant sources directly; do not reconstruct hidden conversation context.
- Required output: one complete current problem_frame.md in the compatibility
  format below. Legacy governed use returns the full body to Root. Only an
  control.semantic_role_boundary: "1.1" or "1.2" run writes
  the body at the exact role-boundary start submission_path. The reusable role's
  ordinary procedure remains unchanged.
- Selected writing permits only that exact file, with no siblings, probes,
  canonical writes or run-state changes. Root retains registration/activation
  ownership and executes any needed probe; the Realizer does not implement.
- Root supplies the run ID and canonical path. Selected start derives the next
  artifact version and binds mandatory/additional --input-ref identities; use
  those exact values and read the original sources and actual registered inputs.
  Legacy calls retain Root-supplied version/path. Do not invent identities.
- For selected output, return actual path, artifact ID/version, final SHA-256,
  invocation, readiness, inputs read, unresolved decisions and evidence references.
  Root finalizes those same bytes with --expected-source-sha256 and consumes the
  registered brief. Do not return the body for transcription or claim activation.
  Keep full-body return for legacy governed use, including BLOCKED output.

### Required brief format

Return these headings exactly once and in this order:

1. `# Problem Frame`
2. `## Contract Metadata`
3. `## Completion Status`
4. `## Input Reviewed`
5. `## Active Problem`
6. `## Objective and User Need`
7. `## Target UX Flow`
8. `## Scope`
9. `## Non-Scope`
10. `## Inputs and Outputs`
11. `## Failure Behavior`
12. `## Constraints`
13. `## Assumptions`
14. `## Decisions`
15. `## Open Issues and Blockers`
16. `## Validation Needs`
17. `## Handoff Readiness`

The old heading names are persistence compatibility. Target UX Flow may describe
an operator/API flow; no GUI or separate UX handoff is required. Use concise
not-applicable explanations where appropriate, never invented obligations.

Metadata must use Markdown bullet lines with backtick-delimited values exactly
as shown below (plain unbulleted labels are not parsed by the current adapter).
Keep the labels unbolded:

- Schema version: `1.0`
- Artifact ID: `problem-frame`
- Version: `<positive integer assigned by Root>`
- Lifecycle status: `ACTIVE`
- Owner role: `intent_realizer`
- Run ID: `<run ID named by Root>`
- Canonical path: `<exact path named by Root>`

Completion Status is PASS, PASS_WITH_ASSUMPTIONS or BLOCKED with a brief rationale.
PASS means contract authoring needs no material guess about intent or identified
realization conditions. PASS_WITH_ASSUMPTIONS carries only visible non-blocking
assumptions or delegated choices. BLOCKED names the missing decision and next
resolver. Neither readiness state asserts a verified implementation or approval.

Finish with a compact Root return: status, inputs reviewed, unresolved decisions
and next action. Under selected "1.1", identify the actual assigned file,
artifact ID/version, invocation, final SHA-256 and evidence references; for legacy
use, retain the complete body followed by its intended output path and summary.
Keep all semantic readiness meanings and exact brief headings unchanged.

## Revision history

2026-09-13 — TW-20260913-P2: user-requested two-workflow transition moves this
procedure to A, adds self-contained handoff and scoped returns, and leaves simple
B entry optional. Realizer authorship/readiness, Root persistence, source authority,
legacy names, exact revision baseline and formal repair rules remain unchanged.
Completed trials/checks and limitations are recorded in
`workspace/framework_development/two_workflow_review.md`. The earlier 2026-09-09
revision reference `intent_realization_revision.md` is currently deleted in the
user's working tree; this revision does not recreate or rewrite that history.

2026-09-13 — IR-20260913-PROC: user requested moving procedural content out of
intent_realizer instructions while retaining its semantic role and the current
fixed skill/workflow binding. Moved invocation rules, complete brief headings,
metadata syntax, completion-status encoding and Root return format into this
skill; existing A/B, revision and decision-record procedures remain authoritative
here without duplicate runtime instructions. The agent retains judgment,
readiness meaning, authority boundaries, read-only/no-delegation restrictions
and mandatory skill loading. Components: intent_realizer.toml, this skill and
agent policy regression tests. Compatibility: no artifact schema, role identity,
model, sandbox, run-state, gate or other custom-agent changes; no migration.
Verification: repository .venv targeted regression passed (79 tests); full
framework regression (`python -m pytest tests`) passed (221 tests, 3 Windows-symlink
privilege skips, one expected duplicate-ZIP-member fixture warning). UTF-8 skill
quick_validate and scoped git diff --check passed. Source comparison confirmed
unchanged Role and purpose/Judgment/contract-boundary text, verbatim migration of
the output-format block and no edits to the other three custom agents.
Limitation: no new live semantic-agent trial has been performed; deterministic
checks establish configuration and format compatibility, not LLM behavior.

### 2026-09-17 — SS-20260917: reusable semantic roles and explicit workflow binding

- Trigger: user-approved separation of custom-agent semantics from A/B procedures.
- Difference: role definitions retain independent judgment and common runtime
  boundaries; skills and named adapters bind repository-specific execution rules.
  Generic role use no longer requires pipeline artifacts. Governed invocations
  must still load their adapters and pass the existing gates.
- Components: four role definitions, A/B and generic role skills, invocation and
  role adapter references, repository guidance and policy regression tests.
- Compatibility: role IDs, model/effort/sandbox settings, schemas, run ownership,
  exact revision checks, repair limits and control-plane code are unchanged.
  Existing child sessions must not be assumed to reload changed instructions.
- Verification: repository .venv targeted suite 63 passed; full suite 230 passed,
  3 Windows-symlink privilege skips and one expected duplicate-ZIP fixture warning;
  all six skill validators, CLI help and integration diff checks passed. Four
  native ordinary-role trials and A/direct-B/verifier artifact finalization ran.
  Missing-procedure and blocked-frame gate checks refused unsupported progression.
- Limitations: finite synthetic trials, not a new real-product delivery or a
  universal guarantee of model behavior. Legacy/prepared/revision control coverage
  is deterministic; no new full native delivery was run for each such combination.
- Authoritative rule mapping, results and evidence: see
  `workspace/framework_development/ss_review.md`.
