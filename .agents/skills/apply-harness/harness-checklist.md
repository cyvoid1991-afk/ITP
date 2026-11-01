# Harness Checklist

Revision: 2.3.1

A proportionate quality baseline for tasks and agentic workflows. These controls define required outcomes, not a mandatory implementation framework. Use with `SKILL.md`, or as a standalone control reference.

## Application rules

- **Activation:** Follow SKILL.md selection rules. Only Light may activate automatically; Standard and workflow construction controls require an explicit user request. This checklist does not independently activate them.
- **Inheritance:** Standard includes every Light control. Keep H1-H17 identifiers stable.
- **Reuse first:** Recognize existing tools, tests, schemas, hooks, and workflow controls when they actually cover the requirement. Add only necessary gaps; avoid duplicate verification infrastructure.
- **Proportionate coverage:** Apply controls according to task relevance and consequence. Explain exclusions. A missing capability or failed check is a gap, not a reason to declare a relevant control inapplicable.
- **No silent weakening:** User revisions override profile defaults, not higher-priority instructions, organizational restrictions, or required approvals. Record deviations and remaining limitations.
- **Real enforcement:** Use mechanical checks for mechanically decidable conditions. Distinguish instructions from implemented enforcement; never claim unavailable permissions or gates are active.
- **Protected criteria:** Do not obtain a pass by weakening tests, tolerances, acceptance criteria, references, or validation. Record separately authorized contract changes before re-verifying.
- **Evidence integrity:** Bind evidence to the claim and current artifact or input version. Agent narratives, another agent's success report, and stale results are insufficient by themselves.
- **Minimal overhead:** Reuse existing task records and formats. Preserve observable actions, evidence links, and concise decision rationale; do not require private reasoning transcripts or unnecessary artifacts.
- **Continuity:** Reuse [work-guidance.md](work-guidance.md) to keep current work state discoverable and evidence applicable across resumptions and procedure boundaries. This supports H1-H7; it adds no profile or automatic Standard activation. A checkpoint guides work but is not proof of correctness or permission to advance.
- **Workflow construction:** Only when explicitly activated under SKILL.md, apply [workflow-procedure.md](workflow-procedure.md) to the requested workflow and affected handoff boundaries. Automatic Light does not require this procedure. Its contracts and records operationalize H1-H7 and overlap H10-H12 without activating every Standard control. Preserve H1-H17. Review-only requests identify gaps; design-only requests specify checks without claiming execution.

## Completion gate

Identify the mandatory acceptance criteria and checks, execute available checks, inspect their actual results, and map evidence back to the requirements. Passing tests alone does not establish task completion. Use evidence-based review where mechanical checking is not applicable; disclose assumptions and uncertainty.

**PASS:** All mandatory criteria in the declared scope have supporting verification evidence. **FAIL:** A mandatory criterion was checked and failed. **BLOCKED:** Required verification, input, or authorization is unavailable. Preserve partial results without presenting them as an overall pass. Unrun checks remain **NOT_RUN**.

## Light Harness

| ID | Control | Objective |
| --- | --- | --- |
| H1 | Input Contract | Validate required inputs, schema, constraints, and basic semantic validity. |
| H2 | Execution Boundary | Constrain files, tools, actions, permissions, and scope; preserve secrets and data boundaries. |
| H3 | Deterministic Checks | Mechanically verify conditions that can be evaluated with tests, assertions, schemas, or numerical checks. |
| H4 | Evidence | Require inspectable evidence directly supporting completion and correctness claims. |
| H5 | Traceability | Connect requirements, actions or implementation, verification, evidence, and decisions. |
| H6 | Failure Handling | Detect, classify, and expose failures, unavailable checks, and unresolved conditions. |
| H7 | Output Contract | Define outputs, artifact locations, acceptance criteria, and completion status. |

## Standard Harness

Includes every Light control, plus:

| ID | Control | Objective |
| --- | --- | --- |
| H8 | Semantic Validation | Check domain meaning, units, ranges, assumptions, consistency, and invariants. |
| H9 | Regression Protection | Check affected existing behavior against valid tests or references; expose missing baselines. |
| H10 | Reproducibility | Preserve inputs, versions, configuration, and procedures needed to repeat checks; disclose nondeterminism. |
| H11 | Provenance | Identify the origin and version of inputs, references, dependencies, and generated artifacts. |
| H12 | Explicit State Transition | Track workflow states and prevent advancement unsupported by required checks. |
| H13 | Repair and Escalation Policy | Define failure-specific recovery, bounded retries, stopping, and escalation. |
| H14 | Scope and Resource Budget | Bound changes, dependencies, retries, execution resources, and external side effects. |
| H15 | Independent Verification | Use a separate verification path for consequential claims; do not derive the reference solely from the producer's result. |
| H16 | Human Gate | Obtain required approval before protected or high-impact changes; escalate material unresolved ambiguity. |
| H17 | Harness Self-Check | Test relevant rejection and failure paths, including missing evidence and false success. |
