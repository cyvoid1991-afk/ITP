---
name: author-product-contract
description: Create, finalize, or revise a behavioral and acceptance contract from stable product intent, determine whether context is contract-ready, preserve implementation discretion, map requirements to acceptance evidence, and expose assumptions, contradictions, or blockers without implementing or verifying the product.
---

# Product Contract Authoring

## Repository integration

For pipeline work, first read [the tool rules](../../../tools/intent-tool-pipeline/AGENTS.md).
The pipeline project root is `tools/intent-tool-pipeline/`, not the Nexus_AI root.
Paths such as `docs/`, `codex_workspace/`, `workspace/`, `intent_deliver/`,
`test_workspace/` and `deliverables/` in this workflow are relative to that tool root.
Shared `.agents/` and `.codex/` paths are relative to the Nexus_AI root.
Run workflow command examples from the tool directory; use the root virtual environment.
General research or standalone role use does not start Workflow A/B.


Use this workflow for general contract authoring. For a governed build-tool-pipeline
assignment, also read [the contract adapter](../build-tool-pipeline/references/contract-adapter.md).
That adapter owns repository schemas, source identities, statuses and exact revision
rules. Its absence blocks governed finalization; ordinary assignments do not load it.

If a project-specific contract schema or procedure exists, follow it where it is more specific than this generic workflow.

## Required Inputs

Use the available contract-relevant context, preferably:

1. approved product intent and decisions,
2. scope and non-scope,
3. constraints affecting behavior, feasibility, compatibility, risk, or acceptance,
4. relevant user, operator, interface, or system behavior,
5. existing behavior and compatibility expectations when revising a product,
6. the prior contract or baseline when revising,
7. known assumptions, unresolved issues, contradictions, or blockers.

Proceed with partial context when useful work remains possible.

Do not replace a missing product decision with an invented requirement. If the missing information would force a material guess, preserve it as unresolved or blocked.

---

## Expected Outputs

Produce, as applicable:

- a self-contained behavioral and acceptance contract,
- scope and non-scope,
- required behavior and relevant constraints,
- acceptance conditions or evidence expectations,
- assumptions, unresolved issues, contradictions, and blockers,
- change notes for revisions,
- contract readiness.

Use project-specific identifiers, schemas, or artifact formats only when another governing procedure defines them.

---

## Contract Authoring Workflow

### Step 1. Establish the Baseline

Identify the approved intent, decisions, constraints, and prior contract material that are authoritative.

Separate them from proposals, implementation ideas, discussion history, and unapproved assumptions.

If authoritative inputs conflict, record the contradiction unless an approved decision resolves it.

When given an intent realization brief, independently compare consequential
conditions and defaults against the original authorized sources. The brief's
readiness does not establish correctness or approval. Consider a concrete behavior
that would pass its proposed checks yet violate the purpose. Accept, reject or
defer consequential proposals with source-linked reasons in the contract's
existing decisions/assumptions/blockers. Do not invent objections to fill a quota.

The realizer proposes conditions needed for faithful implementation; the contract
author owns binding obligations and acceptance. Return newly discovered technical
gaps to Root with their effect and needed decision. Root can resolve bounded
evidence/implementation choices or request a material user choice. Avoid both
uncritical transcription and a second open-ended design exercise.

### Step 2. Classify Open Context

Classify contract-relevant context only when needed:

- **Approved decision** — authoritative product intent.
- **Assumption** — a narrow provisional premise that permits progress without materially changing intended behavior.
- **Unresolved issue** — open but not yet blocking.
- **Blocker** — would force a material guess.
- **Contradiction** — authoritative obligations that cannot all hold as written.
- **Implementation discretion** — a reversible internal choice that need not become a contract obligation.

These are control categories, not mandatory document headings.

### Step 3. Define Scope and Non-Scope

State what the contract covers and explicitly exclude likely sources of downstream scope assumption.

Do not expand scope merely to make the contract appear complete.

### Step 4. Define Observable Behavior

For each contract-relevant behavior, examine only the dimensions that matter:

- trigger or input,
- output or observable effect,
- interface behavior,
- state change or persistent side effect,
- failure or invalid-input behavior,
- edge condition,
- constraint or compatibility obligation.

Do not create empty obligations to fill the checklist.

Describe user or operator flows only to the level needed for implementation and verification to agree on observable behavior.

### Step 5. Construct Requirements and Preserve Implementation Discretion

Convert approved behavior into clear obligations.

Split compound requirements when doing so materially improves interpretation, acceptance mapping, or change traceability.

Distinguish required, optional, deferred, and excluded behavior when useful. Separate functional, non-functional, and documentation obligations only when the distinction affects implementation or acceptance.

Replace vague qualitative criteria with observable or objectively assessable conditions.

Do not turn architecture, algorithms, libraries, frameworks, internal data structures, or other reversible design choices into contract requirements unless observable behavior, feasibility, compatibility, risk, or acceptance depends on them.

### Step 6. Define the Acceptance Basis

For every required contract obligation, define enough information for later verification to determine satisfaction.

Map, when relevant:

1. the requirement,
2. the observable acceptance condition,
3. suitable evidence or verification method,
4. any known limitation or interpretation dependency.

Do not require a specific testing framework or internal implementation method unless the contract itself depends on it.

When deterministic acceptance is impractical, define the semantic or inferential judgment criterion as concretely as the approved intent allows. If reliable acceptance would still require material guessing, record the limitation or blocker instead of manufacturing precision.

### Step 7. Check Existing Behavior and Compatibility

When revising an existing product, identify established behavior, approved compatibility expectations, and interface dependencies affected by the change.

Surface conflicts rather than silently breaking compatibility.

Treat existing behavior as authoritative only when supported by the approved baseline or supplied context.

### Step 8. Resolve or Expose Ambiguity

Resolve ambiguity only when the supplied context supports a clear interpretation.

Otherwise:

- use a narrow visible assumption when non-blocking,
- preserve an unresolved issue when useful work can continue,
- mark a blocker when implementation or verification would require a material guess,
- record a contradiction when authoritative obligations conflict.

Do not escalate reversible implementation discretion merely to eliminate developer choice.

### Step 9. Apply Change Control

When revising an approved contract:

1. identify the changed requirement or behavior,
2. distinguish the new decision from the prior baseline,
3. record material effects on scope, compatibility, assumptions, dependencies, or acceptance,
4. preserve unaffected obligations unless the change logically invalidates them.

Do not silently rewrite unchanged requirements.

### Step 10. Judge Readiness and Produce the Contract

Use these generic readiness states unless another procedure overrides them:

- **Contract-ready** — implementation and verification can proceed without material guessing.
- **Conditionally ready** — they can proceed with explicit non-blocking assumptions or limited unresolved items.
- **Materially blocked** — unresolved context would force a material guess about behavior, scope, compatibility, risk, or acceptance.

Do not present a materially blocked contract as final.

Use the least complex output structure that preserves traceability. A generic contract may contain:

- baseline or purpose,
- scope and non-scope,
- behavioral requirements,
- constraints and compatibility obligations,
- acceptance basis,
- assumptions or unresolved issues,
- blockers or contradictions,
- change notes when applicable,
- readiness state.

This is a default structure, not a mandatory schema.

---

## Failure Handling

If product intent is still fundamentally unstable, stop contract finalization, identify what remains at the problem-framing layer, and preserve any already-stable contract sections.

If context is missing but non-blocking, proceed with a narrow explicit assumption or unresolved issue.

If missing context would force a material guess, block the affected part rather than inventing the decision.

If authoritative inputs contradict each other, record the contradiction and affected obligations instead of choosing a preferred interpretation without authority.

If an objective acceptance basis cannot be defined, state the limitation and use the narrowest supported judgment criterion; if that remains unreliable, treat acceptance as blocked.

If a required project-specific schema, identifier policy, or artifact rule is unavailable, produce the generic contract content that remains valid and state the missing procedural dependency.

---

## Final Validation Checklist

Before finalizing, confirm that:

- approved product intent remains intact,
- scope and relevant non-scope are explicit,
- observable behavior precedes unnecessary implementation detail,
- requirements can be interpreted consistently by implementation and verification,
- subjective criteria have an objective or explicitly bounded judgment basis,
- assumptions are not presented as approved requirements,
- contradictions and blockers remain visible,
- implementation discretion is not unnecessarily constrained,
- every required obligation has an acceptance basis or an explicit blocker,
- relevant existing behavior and compatibility were considered,
- contract changes are explicit and unaffected obligations are preserved,
- readiness matches the remaining uncertainty,
- the contract is self-contained, concise, and non-redundant.

Before finalizing, consolidate repeated rules and catalog-like phrasing.

## Revision History

### 2026-09-13 — TW-20260913

- Trigger: sequential two-workflow transition request.
- Difference: prepared/direct B intake, original/cumulative source comparison,
  consumed identities and selective returns; Contractor retains sole contract judgment.
- Components: this skill and product-contract agent runtime guidance.
- Compatibility: complete contract schema and exact-revision checks are retained;
  no mandatory A or full delegation template for direct requests.
- Completed validation and limitations: `workspace/framework_development/two_workflow_review.md`.

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
