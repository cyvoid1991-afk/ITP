---
name: independent-verification
description: Verify or reverify an implementation or delivered artifact against an approved contract, classify requirement-level evidence as satisfied, failed, or insufficient, prepare repair requests without modifying the delivery, define revalidation scope, and determine release readiness.
---

# Independent Verification

## Repository integration

For pipeline work, first read [the tool rules](../../../tools/intent-tool-pipeline/AGENTS.md).
The pipeline project root is `tools/intent-tool-pipeline/`, not the Nexus_AI root.
Paths such as `docs/`, `codex_workspace/`, `workspace/`, `intent_deliver/`,
`test_workspace/` and `deliverables/` in this workflow are relative to that tool root.
Shared `.agents/` and `.codex/` paths are relative to the Nexus_AI root.
Run workflow command examples from the tool directory; use the root virtual environment.
General research or standalone role use does not start Workflow A/B.


Use this workflow for general verification against an approved acceptance baseline.
For a governed build-tool-pipeline assignment, also read [the verification adapter](../build-tool-pipeline/references/verification-adapter.md).
That adapter owns candidate inputs, evidence paths, report format and status values.
Its absence blocks governed verification; ordinary assignments do not require it.

## Required Inputs

Preferred inputs are:

1. Approved contract or acceptance baseline
2. Delivered implementation or artifact
3. Available tests and test results
4. Relevant documentation and configuration
5. Execution environment or observable outputs, when runtime verification is applicable
6. Prior verification report, when performing revalidation

Proceed with partial evidence when useful verification remains possible.

If a missing input prevents a reliable judgment for a requirement, mark that requirement as insufficiently verified rather than inferring success or failure.

---

## Expected Outputs

Produce, as applicable:

- requirement-level verification conclusions,
- attributable evidence for each conclusion,
- evidence limitations,
- uncovered requirements or missing proof,
- primary defect classification for unresolved items,
- repair request content when repair is required,
- revalidation scope after repair,
- release-readiness judgment when requested or required by the workflow.

Use project-specific status names only when another governing procedure defines them.

Otherwise preserve the logical distinction among:

- satisfied,
- failed,
- insufficient evidence.

---

## Verification Workflow

### Step 1. Establish the Baseline

Identify the approved contract and the acceptance obligations to be verified.

Do not silently replace, relax, or reinterpret the baseline.

If the contract is contradictory, materially ambiguous, or not objectively verifiable as written, record a contract defect and isolate the affected requirement.

### Step 2. Build the Verification Set

Enumerate the contract obligations that require verification.

Do not omit an objectively verifiable contract obligation merely because it is not labeled material or high-priority.

Explicitly flag requirements whose acceptance depends materially on semantic, inferential, or LLM judgment rather than deterministic verification.

### Step 3. Define Sufficient Evidence

For each requirement, determine what evidence would actually establish compliance or failure.

Match the evidence to the obligation:

- runtime behavior for runtime requirements,
- generated artifacts for artifact requirements,
- test logic and results for behavior covered by tests,
- source or configuration tracing when implementation structure is relevant,
- documentation for documentation obligations.

Do not use a test name, completion report, or implementer summary as proof by itself.

### Step 4. Collect the Strongest Available Evidence

Prefer evidence in this general order when it is relevant to the requirement:

1. direct execution and observed behavior,
2. reproducible artifact or interface observation,
3. inspectable requirement-relevant tests with actual results,
4. source or configuration tracing,
5. static inspection without behavioral confirmation,
6. documentation of intended behavior,
7. unexecuted test descriptions or implementer claims.

This is not a universal ranking. Evidence strength depends on what the requirement requires.

### Step 5. Validate the Evidence

Before using evidence, check that:

- it is attributable to the requirement,
- the setup is applicable,
- the observed result is reproducible or inspectable where practical,
- the test assertion actually proves the claimed behavior,
- the evidence is not stale, indirect, or invalidated by a changed implementation,
- any environment limitation is recorded.

Do not infer correctness solely because no failure was observed.

### Step 6. Issue the Requirement Judgment

Classify each requirement as:

- **Satisfied** — evidence demonstrates the requirement.
- **Failed** — evidence demonstrates contradiction with the requirement.
- **Insufficient evidence** — available evidence cannot reliably establish either satisfaction or failure.

State the evidence basis and any important limitation.

### Step 7. Classify Unresolved Problems

Use one primary classification:

- **Implementation defect** — delivered behavior or artifact contradicts a valid contract requirement.
- **Test or evidence defect** — tests or evidence are missing, invalid, misleading, stale, or insufficient to establish the requirement.
- **Environment limitation** — verification is blocked by unavailable access, dependencies, permissions, files, services, tools, or execution conditions.
- **Contract defect** — the contract is contradictory, materially ambiguous, infeasible to evaluate as written, or lacks an objective acceptance basis where one is required.

Do not classify a contract defect as an implementation failure.

If multiple causes exist, identify the primary cause and note materially relevant secondary causes.

### Step 8. Prepare the Repair Request

When an implementation repair or evidence repair is required, specify:

- affected contract requirement,
- observed evidence,
- failure or insufficiency condition,
- expected compliant behavior or required evidence,
- related requirements likely to be affected.

Describe the required outcome without prescribing unnecessary implementation details.

Do not apply the repair while acting as verifier.

### Step 9. Define Revalidation Scope

After repair, revalidate:

1. the failed or insufficient requirement,
2. requirements materially affected by the repair,
3. prior conclusions whose evidence may have been invalidated.

Preserve prior conclusions only when the repair could not reasonably invalidate their supporting evidence.

Do not assume a local repair has no adjacent effect.

### Step 10. Apply the Requested Acceptance or Release Judgment

When acceptance or release readiness is requested, apply the governing scope.
A delivery is not release-ready when any of the following applies:

- an acceptance-relevant contract requirement has failed,
- a required acceptance condition remains insufficiently verified without an explicitly acceptable limitation,
- an unresolved contract defect prevents reliable acceptance judgment.

Environment limitations do not automatically equal product failure, but they may block release judgment when required acceptance evidence cannot be obtained.

If partial verification is acceptable under the governing contract or process, state the accepted limitation explicitly.

### Step 11. Produce the Verification Report

Organize the report around traceability.

Recommended generic fields are:

| Requirement | Evidence | Conclusion | Limitation / Defect | Follow-up |
|---|---|---|---|---|

Add repair and revalidation sections only when needed.

Do not impose a fixed repository-specific schema unless another procedure requires one.

---

## Evidence Policy

Use the strongest evidence that is practical and relevant.

Prefer direct execution when runtime behavior matters and execution is available.

Use static inspection when it is sufficient for the requirement or runtime execution is unavailable.

Treat documentation as primary evidence only for obligations that concern documentation itself or when the contract explicitly makes it authoritative.

Treat implementer summaries as context, not proof.

If evidence is conflicting, do not silently choose the preferred source. Identify the conflict and determine which evidence is authoritative under the contract.

If no source is authoritative enough to resolve the conflict, classify the result according to the underlying cause.

---

## Semantic or Inferential Verification

When deterministic verification is not practical and the requirement depends on interpretation, semantics, or qualitative judgment:

1. state that the conclusion depends on semantic or inferential evaluation,
2. define the acceptance criterion as concretely as the contract allows,
3. cite the evidence used,
4. state meaningful uncertainty or alternate interpretations,
5. avoid presenting the result as deterministic proof.

Use this flag to expose evidence quality, not to exempt the requirement from verification.

---

## Failure Handling

If the approved contract is unavailable:

- verification may proceed only for clearly attributable obligations available from another approved source,
- otherwise report the baseline as missing and avoid full acceptance judgment.

If execution is unavailable:

- use the strongest valid static or artifact evidence,
- record the runtime limitation,
- do not represent static inference as executed behavior.

If tests are unavailable or inadequate:

- inspect other evidence where useful,
- classify missing proof as a test or evidence defect when appropriate,
- do not fail the product solely because a test is absent unless the contract requires that test or evidence artifact.

If the environment prevents required acceptance verification:

- classify the limitation separately,
- state whether the limitation blocks release judgment.

---

## Final Validation Checklist

Before finalizing, confirm that:

- the approved contract remained the baseline,
- every required verification item was addressed or explicitly left insufficient,
- each conclusion has attributable evidence,
- passing tests were checked for actual requirement coverage,
- failure and insufficient evidence were not conflated,
- implementation, evidence, environment, and contract causes were distinguished,
- semantic or inferential judgments were identified when material,
- no repair was performed while acting as verifier,
- revalidation scope was defined when repair occurred,
- release readiness follows from the verified acceptance state,
- the report is concise, traceable, and free of repeated rules.

Remove catalog-like phrasing and consolidate overlapping rules before finalizing.

## Revision History

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
