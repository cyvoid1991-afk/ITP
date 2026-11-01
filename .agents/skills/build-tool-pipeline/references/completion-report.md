# Completion Report Format

Create one concise report for a delivered, blocked, or cancelled run. Store a delivered run's report at `50_release/completion_report.md`. This report is user-facing release evidence; it does not replace any of the five semantic coordination artifacts.

## Required Headings

Use these headings in order:

```markdown
# Tool Pipeline Completion Report

## Outcome

## Request and Scope

## Delivered Artifacts

## Gate Results

## Agent Invocations

## Decisions and Escalations

## Repair History

## Verification Evidence

## Release Evidence

## Deviations and Limitations

## Continuity

## User Approval
```

## Content Rules

### Outcome

Use exactly one run outcome:

- `DELIVERED_AWAITING_USER_APPROVAL`
- `DELIVERED_APPROVED`
- `BLOCKED`
- `CANCELLED`

Do not use a delivered outcome unless the release stage and gate passed. Do not use `DELIVERED_APPROVED` unless explicit user approval is recorded.

### Request and Scope

Name the run, active request version, contract version, target path, requested deliverables, included scope, and exclusions. State `NEW_PRODUCT` or `REVISION`. For a revision, report the exact baseline run/archive/contract/report references and SHA-256 values, `BOUNDED` scope classification, requested changes, explicit non-changes, feedback evidence, and whether baseline revalidation remained current. Never describe `SUPERSEDED_CONTEXT` as a `source_context.authority` value.

State prepared A → B or direct B, the intake rationale and consumed source/delegation
versions and hashes. Direct B need not instantiate the full delegation template.

### Delivered Artifacts

List the product source, documentation, tests, examples, complete current frame and contract, build-run artifacts, and release archive. Use repository-relative paths and identify anything requested but not delivered. For a revision, identify `revision_control` and retained semantic history; do not present a delta fragment as the current frame or contract.

The frame is applicable only to the prepared path. Direct B lists no frame and
reports the unused framing stage/gate as PENDING with the bound route rationale.
Do not fabricate a skipped/PASS state or Realizer invocation.

### Gate Results

Report every fixed stage, status, and primary evidence reference. Include each deterministic test attempt ID, immutable attempt path/SHA-256, canonical result path, package/inspection result, and verification-harness attempt status. Preserve failed, blocked, pending, and skipped states; never flatten them into success.

### Agent Invocations

List the exact role, invocation reference, role-boundary baseline/result, input artifact versions, returned result, and `finalize-semantic-return` persisted output version for `intent_realizer`, `product_contract_agent`, and `independent_verifier`. Preserve the recorded legacy role in unmarked historical runs. Include a read-only explorer only when it materially contributed evidence. A harness attempt is deterministic evidence, not an agent invocation.

List only roles actually invoked. Separate upstream A preparation from B activity,
including repeated formatting/intake turns. Prepared handoff reuse is not a new invocation.

### Decisions and Escalations

List user decisions, `AGENT_DECIDED` implementation choices, unresolved blockers, required approvals, waivers, and repair-limit escalation. Explain why each material user interruption was necessary.

Include consequential realization conditions/defaults and whether the contractor
accepted, rejected or deferred them, with brief reasons and original intent/evidence
references. Summarize Root's answers to bounce-backs and their changed basis. Do
not conflate an agent proposal with user approval. These sections serve humans and
AI readers; keep identifiers/paths attributable without adding a telemetry system.

Report consequential individual and cumulative intent differences, who had authority
to choose, and the owner review that accepted the actual saved version. Explain
scoped upstream returns and preserve unresolved user-reserved choices. If assessing
workflow improvement, include preparation conversation/documentation costs and late
rework; fewer questions alone are not evidence of better quality.

### Repair History

Report attempt count out of `2`, failure references, root-cause classifications, changed bases, repaired files or contract versions, new immutable test and harness attempt IDs, retest results, and revalidation scope. Write `None` when no repair occurred.

### Verification Evidence

Report the verifier's overall result, requirement totals, all-applicable-requirement scope, deterministic test-plan result and canonical/immutable paths, and exact candidate identity. Report the verification-harness plan/attempt/summary paths and hashes, exact contract/manifest/inspection/archive binding, extraction count, command totals, cleanup path/status and retained-scratch flag, and its explicit `independent_verifier_judgment: NOT_PERFORMED`. Then list any additional verifier-owned probe locations separately. A harness PASS never substitutes for the independent report.

### Release Evidence

For a delivered run, report the archive path, manifest path, archive SHA-256, entry count, single root, required-role coverage, prohibited-entry counts, inspection status, and staging cleanup result. Include the exact release candidate binding captured at verification PASS: contract, manifest, inspection, archive, and verification-report references/paths and SHA-256 values, plus the immutable test and harness attempts judged by the verifier. Confirm that release did not rebuild the archive.

For a blocked or cancelled run, state that no release authorization exists and identify any partial release output that must not be used.

### Deviations and Limitations

Distinguish approved deviations, deferred requirements, known limitations, and unverified claims. State that the verification harness isolates a clean extracted-package working directory plus per-command temp roots and scrubbed Python/PIP environment but is not an OS sandbox. Report cleanup failures or retained scratch explicitly. Write `None` only when no other deviation, deferral, limitation, or unverified claim exists; do not erase the harness isolation limitation.

### Continuity

State the exact `run_state.json` path, its active version, the current stage, the next allowed action, and the safe resume condition. For a revision, include the recorded exact baseline and latest drift-revalidation result; any future mismatch requires `FRESH_REQUIRED` handling rather than a silent baseline refresh. A delivered run may say no further pipeline action is permitted until user feedback or approval.

### User Approval

Record `PENDING`, `APPROVED`, `REJECTED`, or `DEFERRED`, plus the decision source when known. Never infer approval from silence or from successful verification.
