---
name: problem-framing
description: Structure ambiguous, under-specified, or unstable problems into decision-usable framings using explicit assumptions, option comparison, validation planning, convergence, and handoff. Use for repeatable problem-framing work; do not use for implementation, product-contract authoring, or independent verification.
---

# Problem Framing Workflow

## Repository integration

For pipeline work, first read [the tool rules](../../../tools/intent-tool-pipeline/AGENTS.md).
The pipeline project root is `tools/intent-tool-pipeline/`, not the Nexus_AI root.
Paths such as `docs/`, `codex_workspace/`, `workspace/`, `intent_deliver/`,
`test_workspace/` and `deliverables/` in this workflow are relative to that tool root.
Shared `.agents/` and `.codex/` paths are relative to the Nexus_AI root.
Run workflow command examples from the tool directory; use the root virtual environment.
General research or standalone role use does not start Workflow A/B.


Use this skill when a problem requires a structured framing process beyond ordinary discussion.
Root may use it directly or as the procedure for the `collaborative_intent_shaping_agent` role;
invoking a particular agent is not required. Selecting this skill does not start
intent-realization or build-tool-pipeline. General framing work requires no
pipeline run state, fixed artifact format, or pipeline gates.

Only when resuming an unmarked historical build run whose recorded owner is
`problem_framer`, also
read [the legacy framing adapter](../build-tool-pipeline/references/framing-adapter.md).
The `problem_framer` registration is retired. A fresh invocation of that recorded
owner is blocked pending an explicitly authorized migration or restoration;
do not relabel historical artifacts or substitute the successor under that identity.
Only that adapter requires the repository artifact format and exact revision rules.
New Workflow A runs use intent-realization; ordinary discussion uses neither adapter.

This skill stays within problem framing; it does not grant implementation,
contract ownership, or independent verification authority.

## 1. Establish the Active Framing

Identify, as far as the available context supports:

- active problem;
- objective or decision to be made;
- intended deliverable;
- scope and explicit non-scope;
- material constraints;
- evaluation criteria;
- current main decision.

Do not reconstruct information that is already sufficiently established.

If the user changes the objective, update the active framing before continuing.

## 2. Structure the Reasoning State

When relevant, distinguish:

- established facts;
- user-provided assumptions;
- inferred or proposed assumptions;
- approximations;
- hypotheses;
- unresolved issues;
- blockers.

Classify unresolved issues as:

- **blocking** when reliable framing or recommendation would otherwise require a material guess;
- **non-blocking** when useful progress can continue with an explicit assumption or later validation.

Do not create categories merely for formatting. Use them only when they improve reasoning or traceability.

## 3. Resolve Ambiguity Efficiently

Ask a clarifying question only when the missing information would materially change one or more of:

- the real problem;
- scope;
- evaluation criteria;
- dominant assumptions;
- preferred direction;
- ability to converge.

Otherwise:

1. make the narrowest useful assumption;
2. state it explicitly;
3. continue the analysis;
4. identify validation if confidence materially depends on it.

Do not repeatedly reopen broad clarification once the relevant uncertainty has been bounded.

## 4. Evaluate Candidate Directions

Generate alternatives only when materially distinct directions exist.

Compare candidates against the current:

- objective;
- constraints;
- assumptions;
- tradeoffs;
- failure conditions;
- validation needs;
- decision value.

Prefer the smallest set of alternatives necessary to expose the real decision.

Do not preserve an earlier direction merely because work has already been invested in it.

When one direction becomes sufficiently preferred, state why and move toward convergence instead of continuing ideation.

## 5. Evaluate Simplifications

When proposing or reviewing a simplification, determine:

1. what is being simplified;
2. why the simplification is useful;
3. what information or behavior is lost;
4. under what conditions the simplification remains acceptable;
5. under what conditions it may fail.

Do not reject approximation merely because it is imperfect. Judge whether the lost fidelity matters to the active decision.

## 6. Evaluate Models, Theories, or Formulations

When a model, theory, abstraction, or formulation materially affects the decision, identify:

- what it preserves;
- what it abstracts or ignores;
- where it may fail;
- what validation would materially increase confidence.

Separate model inadequacy from uncertainty in inputs or evidence.

## 7. Control Side Branches and Drift

When an adjacent issue appears, determine whether it:

- clarifies the framing;
- changes a material assumption or tradeoff;
- affects feasibility or validation;
- directly advances the current decision.

If not, defer it.

If discussion begins solving a different problem or over-refining a secondary issue:

1. isolate the branch;
2. restate the active problem and main decision;
3. preserve any relevant conclusion from the branch;
4. return to the main reasoning path.

An explicit user redirection is a new objective, not drift.

## 8. Converge

When enough information is available:

- identify the preferred direction or current decision;
- state the decisive rationale;
- retain only material alternatives or objections;
- identify remaining assumptions and validation needs;
- stop broad ideation.

If convergence is not yet justified, state the specific unresolved decision or blocker instead of manufacturing certainty.

## 9. Consolidate the Framing

Create a structured consolidation or handoff when:

- the user requests one;
- the discussion has materially converged;
- the reasoning state needs preservation;
- another stage or agent requires reusable input.

Include only what is needed to reconstruct the active reasoning state.

When relevant, distinguish:

- settled points;
- provisional points;
- assumptions;
- unresolved issues;
- blockers;
- validation needs;
- next decision or action.

Do not turn every intermediate response into a formal artifact.

## 10. Handoff Readiness

Treat the framing as handoff-ready only when another agent or user can continue without materially reconstructing or guessing the reasoning state.

Check that:

- the active problem is clear;
- objective and relevant scope are explicit;
- material constraints and evaluation criteria are known;
- important assumptions are visible;
- unresolved blockers are identified;
- material tradeoffs are sufficiently represented;
- validation needs are stated where required;
- the next action is clear.

Do not present the framing as handoff-ready when:

- the real problem remains materially ambiguous;
- dominant evaluation criteria are unknown;
- a recommendation depends on hidden or unstable assumptions;
- unresolved blockers require the next stage to guess intended behavior or scope.

## 11. Output Guidance

Use ordinary consultative discussion by default.

Use tables or explicit structure when they materially improve:

- comparison;
- assumption visibility;
- tradeoff review;
- decision traceability;
- handoff usability.

Avoid rigid templates when they do not improve the task.

Do not produce a full report by default.

## 12. Final Check

Before completing framing work, check that:

- the response addresses the active problem;
- material assumptions and uncertainty are visible;
- prior context has not been treated as evidence of correctness;
- viable alternatives were considered when they materially affect the decision;
- approximation and failure risks are stated where relevant;
- validation needs are visible;
- unresolved issues have not been disguised by polished wording;
- the discussion has either converged or clearly identifies what prevents convergence;
- any claimed tool, source, calculation, or validation step was actually used.

Remove repeated rules or catalog-like wording when a shorter formulation preserves the same reasoning state.

## Revision History

### AGENT-20261011-CIS — 2026-10-11

- Route ordinary role-assisted framing to `collaborative_intent_shaping_agent`
  after the user-authorized consolidation and retirement of both old roles.
- Preserve historical owner names, adapter schemas and hashes; fresh retired-role
  invocation is blocked pending authorized migration or restoration.
- Verification is recorded in the repository agent-registration history.

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
