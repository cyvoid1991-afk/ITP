# Agent-owned artifact control protocol

## Decision and applicability

**Use the existing semantic artifacts, state transaction, gates and repair counter
for selected specialist submissions and Root-owned post-verification rounds.**

Design identity: `ITP-20261029-ARTIFACT-S1`, protocol revision 1.0.
S7 status annotation: `ITP-20261101-ARTIFACT-S7`, 2026-11-01. The selected
interfaces are implemented and the [new-run operating procedure](agent-rollout.md)
is published. The user-authorized post-S7 override `ITP-20261101-DEFAULT12`
(2026-11-01) makes `1.2` with [procedure binding](procedure-binding.md) the
new-run initializer default; explicit `1.1` remains compatible and new legacy
`1.0` requires explicit selection. Existing runs retain their actual selectors.
The original S1 status was implementation contract, not implemented or activated;
that describes the design checkpoint, not current operation. The D1-D7 decisions
and staged proof obligations below retain that design context. Models, reasoning,
role independence and delegation boundaries are unchanged. S7 grants no migration,
release or additional-round permission; preserve all historical evidence.

This document implements decisions D1-D7 from the [implementation companion](../../workspace/framework_development/agent-artifact-implementation-plan.md), subordinate to the [revision intent](../../workspace/framework_development/agent-artifact-revision-plan.md). The user's subsequent S1 decision resolves the plans' open D6 authority item: **independent review, followed by user approval**, before additional rounds. No other intent change is introduced.

## D1: one selector, unchanged semantic schemas

The table below is the preserved **S1 design checkpoint**, including its original
default. The current new-run default is `1.2` under `ITP-20261101-DEFAULT12`;
the table does not instruct callers to initialize new runs as `1.0`.

| Interface | Selected behavior | Compatibility |
| --- | --- | --- |
| `control.semantic_role_boundary` | Exact string `1.1` selects this entire protocol | Existing `1.0` retains existing behavior; historical uncontrolled state retains its supported behavior |
| Run-state schema | Keep `schema_version: "1.1"` | No semantic artifact schema change |
| `control.intent_realization` | Require existing `1.0` for selected runs, including Direct B | Do not relabel retired roles or change this marker's meaning |
| Initializer | Add `--control-revision {1.0,1.1}`, default `1.0`; Python `initialize(..., control_revision="1.0")` | New-run selection only; no in-place upgrade/default change |
| Unsupported combinations | Reject null/unknown revision, missing required selected fields, selected metadata under legacy control, or unsupported owner selection | No guessing from files, field presence, or a requested maximum |

Current interface annotation (`ITP-20261101-DEFAULT12`, 2026-11-01): the initializer
accepts `--control-revision {1.0,1.1,1.2}`, default `1.2`; Python
`initialize(..., control_revision="1.2")` has the same default. `1.2` inherits this `1.1` protocol and adds
the registry-owned binding contract. Baselines/receipts retain their actual
selected revision; the `1.1` examples below are not instructions to relabel `1.2`.

Keep the current legacy `CONTROL_REVISION` meaning for intent realization; introduce a separately named supported boundary-revision set. A second independent artifact/round selector would create unsupported half-configurations and is not needed.

The old validator explicitly rejects boundary control other than `1.0`, whereas an unknown optional field or a larger `1.x` schema minor would be ignored. This provides rejection by old validated readers/state transitions. It does **not** retrofit every old low-level writer: old boundary finish does not validate control revision. Never operate a selected run with an old checkout; rollback must retain a compatible reader/recovery implementation.

All updated run-mutating entry points must check supported control and unfinished registration transactions before side effects. Recovery and diagnostic reads are the explicit exceptions. An unsupported selected run must not receive new test, package, boundary or state outputs from an updated command.

## D2: assignment, inputs and exact write scope

Extend `role-boundary start` with `--artifact KEY` and repeatable `--input-ref FILE`; corresponding Python keyword arguments are `artifact_key=None` and `input_refs=()`. Selected artifact-producing invocations require one of the three existing semantic keys. Derive the next version from active state; do not add a caller-owned version counter.

Reuse the existing 24-character audit ID derived from role and invocation. A collision with different full identities is rejected. Root/control creates the parent before taking the snapshot and returns the assigned path:

| Artifact key | Exact run-relative submission |
| --- | --- |
| `problem_frame` | `30_execution/sub/<audit-id>/brief.md` |
| `product_contract` | `30_execution/sub/<audit-id>/contract.yaml` |
| `verification_report` | `30_execution/sub/<audit-id>/report.md` |

Preflight the actual absolute parent (<180 characters), directory segments (<=32) and filename (<=64); reject before allocation if over budget. Use a shorter new-run ID rather than silently moving durable evidence into scratch. Existing canonical paths do not change.

The existing hash-bound baseline retains role, invocation, run path, original state backup and snapshot. Add `control_revision: "1.1"` and:

```json
{
  "submission": {
    "artifact_key": "product_contract",
    "artifact_id": "product-contract",
    "artifact_version": 1,
    "path": "30_execution/sub/<audit-id>/contract.yaml",
    "inputs": [],
    "round_number": null
  }
}
```

Each present input is `{path, content_sha256}` plus `artifact_id, version` for semantic artifacts. Paths are normalized project-relative paths. Mandatory missing verification evidence uses `{path, availability: "MISSING"}`; it cannot be represented as a valid digest. Present entries have `availability: "PRESENT"`. `round_number` is the current in-progress round number or null; it is linkage, not a counter.

Mandatory inputs are collected from existing state and fixed evidence interfaces, not omitted by leaving `--input-ref` empty:

- Realizer: active request and its locally bound original-intent/source-context files.
- Contractor: those request inputs and the registered brief on prepared A-to-B; no synthetic brief on Direct B.
- Verifier: active contract, its bound request/brief sources, current candidate manifest/inspection/archive and harness attempt/cleanup references. Capture what is actually supplied, not the previous verification-PASS candidate. Explicit missing/unusable evidence permits an attributable UNVERIFIED report, never a passing gate.
- `--input-ref` adds other local files supplied to the role. Non-local context remains attributed in the semantic artifact and cannot be claimed as locally hash-verified.

Reconcile the assignment with active input versions and file hashes at admission. Appearance/disappearance/change of a declared input invalidates the assignment: finish/account for the old invocation and issue a new one. Actual downstream reading remains a role duty and requires live evidence; input hashes alone do not prove reading.

Add `allowed_durable_files` to the serialized boundary path policy, empty by default for legacy baselines. Exact-file matching is separate from existing prefix-based directory roots. A directory, descendant, symlink/reparse point, hard-link alias or alternate spelling that resolves to a protected file is not an allowed submission. Check both before and after execution. Protect canonical files, state, prior submissions and histories. Do not place submissions beneath the audit-excluded `semantic_finalize` tree.

For selected Verifier invocations, retain probes under the assigned `40_verification/probes/<audit-id>/` only. Generic/legacy policy stays unchanged. Runtime permissions and role instructions must also support these writes; this post-execution audit is not an OS sandbox.

## D3: admission and recoverable receipts

Extend `finalize-semantic-return` with `--expected-source-sha256 SHA256` / `expected_source_sha256=None`. It is mandatory on selected runs and must match the captured bytes used for validation and canonical writing. Legacy calls preserve existing behavior; if a digest is explicitly supplied it must be checked. The supplied source must equal the exact assignment, and role/run/invocation/artifact/version/input/round bindings must agree.

Preserve current body validation, ownership, version sequence, source prerequisites, boundary PASS, history and rollback. Reject selected `persist-artifact` before mutation with an instruction to use finalization; it cannot bypass assignment, digest or receipt checks.

Add `control.semantic_registrations`, initially `{}`, keyed by audit ID. Store an immutable receipt atomically in the same state update as the active reference:

| Receipt field | Value |
| --- | --- |
| `artifact_key`, `artifact_ref`, `path`, `content_sha256` | Registered canonical identity |
| `producer_role`, `submission_path`, `source_invocation_ref` | Original producer and assigned source |
| `baseline_sha256`, `boundary_evidence_ref` | Exact assignment and invocation audit |
| `registered_at`, `run_state_version` | Commit timestamp and resulting state version |
| `round_number` | Bound in-progress round, or null |

Existing active-reference `semantic_owner` and `persistence_owner: root_codex` keep their meanings. The receipt is control provenance, not another product artifact. It refers to the hash-bound input baseline; do not duplicate complete semantic bodies in state or hash the containing state into its own receipt.

### Transaction and interruption table

Reuse the existing finalizer. Its current in-memory exception rollback is insufficient after process termination, so add a bounded write-ahead record at `30_execution/semantic_finalize/tx/<audit-id>.json`. Before any canonical/history mutation, atomically store the request identity, exact prior state/artifact bytes (base64, nullable artifact), prior digests, intended state bytes/digest, submitted digest, history action and status `PREPARED`. Record version and run identity; validate backups against recorded hashes before use.

| Observed durable state | Required recovery |
| --- | --- |
| Preparation write never completed | No canonical mutation is permitted; restart preflight |
| Prior state still active, canonical/history partially changed | Restore exact prior canonical/state bytes; retain journal and consistent history; mark `ROLLED_BACK` |
| Intended state installed, canonical digest agrees | Re-run post-validation, confirm embedded receipt, mark `COMMITTED`; recover the original result |
| Intended state installed but post-validation fails | Restore prior bytes only when current state/target are recognized transaction states; retain failure evidence |
| State/target differs from both recognized prior and intended identities | Block as recovery conflict; never overwrite unrelated later work |
| Journal marked `COMMITTED` | Read immutable receipt; no canonical or state mutation on replay |

A `PREPARED` journal blocks unrelated writers. Internal recovery may read/validate it without being blocked by its own guard. Retain terminal journals and existing failure records; do not create a second generic persistence engine. A terminal `ROLLED_BACK` record is first read without restoring its old backups again. A reissued matching finalization requests a new attempt: revalidate the original assignment, current inputs and next artifact version; capture fresh current before-images and intended state; then atomically append the new `PREPARED` attempt while preserving the old outcome. Never reuse old before/after snapshots across attempts. Reject if intervening work invalidates the assignment. A conflicting digest/binding under the same invocation rejects. Fresh producer corrections require a new invocation. S2 must inject interruption while appending a second attempt and during its rollback, as well as during the first attempt.

Use the same finalization command for recovery; no new recovery command. Consult receipt/journal before ordinary live-input and next-version validation. A matching committed replay validates retained provenance and returns `replayed: true`, the original receipt, and `is_current` determined from current active identity. Historical replay may return `is_current: false`; it never reactivates old bytes and need not match today's inputs/latest-role index. Missing or altered retained provenance rejects recovery. Consumers separately validate the current active artifact before progressing.

Registration is admission, not semantic readiness. If a new blocked contract cannot coexist with the current PASSED contract gate, retain its rejected submission and bounce-back evidence while the previous active contract stays identifiable. Block affected work; do not falsely approve the replacement or weaken global readiness validation. A ready replacement can use the still-available next version in a fresh invocation within the same round.

## D4: one Root-owned round count

Initialize selected runs with existing `repair.active_attempt: 0`, `repair.maximum_attempts: 4`, `repair.last_failure_ref: null`, plus `repair.rounds: []` and `control.latest_verification_result: null`. Legacy initialization remains at two. `active_attempt` is the only authoritative count of **rounds started**; the ledger substantiates it.

Each ledger record contains `number`, `started_at`, `request_refs` (existing bounce-back IDs), `source_verification`, `status` (`IN_PROGRESS` or `COMPLETED`) and nullable `result_verification`. Numbers are consecutive; count equals ledger length; at most the last record is in progress. No independent completed/in-progress counters are added.

A terminal verification snapshot contains `report_ref`, `report_path`, `report_sha256`, `source_invocation_ref`, `boundary_evidence_ref`, `stage_status`, `recorded_at`, `candidate_binding` and `harness_attempt`. Use the existing candidate-binding field names for contract/manifest/inspection/archive identities. A present harness attempt uses `{path, content_sha256, cleanup_path, cleanup_sha256}`; unavailable data is explicitly null and explained in the report. Capture authoritative supplied identities from the report's audited input baseline, not newly changed files after the invocation. PASSED requires all existing complete evidence; FAILED/BLOCKED may retain an incomplete candidate, with known contract identity and null missing members.

Capture all three terminal states (`PASSED`, `FAILED`, `BLOCKED`) in `control.latest_verification_result`. Keep `control.verification_validation_identity` PASS-only and unchanged as release authority. Historical ledger identities resolve through retained semantic versions, baselines and immutable harness/manifest evidence; do not compare an old report with a legitimately overwritten current archive. No second archive copy is required solely for this ledger.

| Event through existing `update-state` | Atomic effect |
| --- | --- |
| First terminal verification | Record latest result; count stays zero |
| Enter `repair` after a result | Require exact latest report through existing `--failure-ref` and existing modification-event IDs through `--evidence-ref`; reserve one slot and append IN_PROGRESS record before modifications |
| Same round continues/resumes | Keep slot/number; ordinary repair status updates do not start another round |
| `repair` returns to verification | Existing changed-basis, contract, test/candidate and verification prerequisites remain; require in-progress record |
| Fresh terminal result | Atomically record new result and complete the matching round; no increment |
| Replayed start/result | Resolve matching recorded identity without mutation; conflicting source/request/result rejects |

The legacy flag name `--failure-ref` refers to the source Verifier report under selected policy, even if it passed. No new counter command is needed. Repeated status calls must not overwrite a terminal snapshot or consume another slot.

Selected-policy routing must additionally allow verification PASSED, or incomplete release, to enter existing `repair` on a recorded authorized modification request. Preserve the actual verdict. Atomically invalidate release authority, set verification stage/gate IN_PROGRESS and incomplete release stage/gate PENDING. Completed releases stay immutable. The old FAILED/BLOCKED-only rule remains for legacy runs.

Contract/brief owner work can occur while `repair` remains current; no new backward stage graph is needed. Several items, combined contract/code changes and agent changes stay in the reserved round. Existing retry qualification must accept an attributable authorized change under an existing classification rather than inventing a failed defect; changed-basis evidence remains mandatory.

## D5: recovery boundary

| Situation | Treatment |
| --- | --- |
| Initial intent/contract discussion, first verification | No round |
| Post-verification implementation/contract modification or request | Start one round before subject modification |
| Interrupted work, tests, invocation, finalization reply loss | Resume the reserved round; no reset/refund |
| Missing evidence/environment recovery with unchanged contract and candidate | Existing uncounted recovery route and bounce-back rules |
| Evidence recovery shows subject changes are needed | Enter counted route before changing it |
| Contract/source/archive drift during claimed evidence-only recovery | Reject uncounted progression; do not retroactively hide the drift |
| Fourth result passes | Ordinary gates may advance |
| Further modification after the current allowance | Stop before reserving another slot; D6 applies |

Evidence-only recovery must demonstrate unchanged subject through existing contract/manifest source hashes and archive identity. Rebuilding metadata/evidence may change its own hashes while the subject stays identical. If a failed report had no usable subject identity, do not assert equality from two null values: recover attributable pre-existing identity first or escalate the uncertainty. Do not invent a general retry counter or automatically charge environment operations as repair.

No replacement run is an automatic fresh allowance for continuing the same unfinished work. Root must resume the original ledger; independently authorized new scope follows ordinary intake. Automated detection of unrelated arbitrary replacement directories is not promised by this trusted local protocol.

## D6: independent review followed by user approval

**User decision on 2026-10-29: "독립 검토 후 사용자 승인" (independent review, then user approval).** This resolves only continuation authority, not permission to change agreed intent.

At exhaustion, Root creates an existing `REPAIR_LIMIT_EXHAUSTED` bounce-back event before further modification. Eligibility requires `active_attempt == maximum_attempts`, no IN_PROGRESS round, and the exact latest terminal result equal to the last completed round's result. An in-progress fourth round can finish without threshold review. Reuse `update-bounce-back create/resolve`; add no stage/gate or permanent reviewer role. Invoke the existing `independent_verifier` separately as a process reviewer, distinct from the correction performer and from product-verification judgment. It cannot implement changes or approve its own recommendation.

Extend a selected threshold event with `round_review_basis`: `{round_number, source_report_ref, source_report_sha256, contract_ref, contract_sha256, maximum_attempts}`. Existing event origin identifies the triggering result. Root supplies retained round, candidate, report and original-intent references; no full-body reconstruction is required.

For this process review only, extend boundary start with `--review-event BB-ID` / `review_event_id=None`, mutually exclusive with `--artifact`. Require the independent_verifier role and a matching eligible threshold event. Bind that event's basis and input identities in baseline `round_review`, derive the same audit ID from role/invocation, and precreate its parent before snapshot. No product-report assignment, version reservation or semantic registration receipt is created. The only allowed durable output is `40_verification/probes/<audit-id>/round-review.json`; do not also grant its parent as an ephemeral write root. Finish the audit and retain PASS evidence before the recommendation is submitted for user approval. Other writes remain prohibited. This is process evidence, not a sixth canonical semantic artifact. It contains:

- `schema_version: "1.0"`, `artifact_type: "iteration-threshold-review"`, run ID, reviewer role/invocation and exact `basis` matching the event;
- `recommendation`: `STOP`, `REQUEST_USER_DECISION`, or `BOUNDED_CONTINUATION`;
- unresolved issues, observed progress, likely causes, proposed changed approach, intent impact and evidence references;
- `additional_rounds`: a positive finite integer only for bounded continuation, otherwise zero.

Only after an affirmative user response may Root resolve the threshold event with existing `resolution_type: USER_DECIDED`, attributed `resolved_by: user`, decision/evidence references and changed decision basis. Add `resolution.continuation` containing `{review_path, review_sha256, review_invocation_ref, boundary_evidence_ref, approval_path, approval_sha256, additional_rounds, new_maximum_attempts}`. Approval evidence retains the user's actual response, exact review/basis reference, explicit finite allowance and timestamp; a Root paraphrase or silence is not approval. This is attribution in the trusted local model, not cryptographic authentication of the human.

The existing resolve operation validates reviewer ownership/boundary, bound review, user decision evidence, positive allowance, unchanged basis and that the threshold event was not already used. Unchanged basis includes current contract/candidate/source-hash reconciliation against the triggering result and review inputs, not merely matching numeric/report fields. Unknown subject identity must be resolved before approving continued modification. Atomically resolve the event and set `maximum_attempts` to the previous ceiling plus approved allowance. Validate the ceiling as four plus all valid resolved continuation increments; these are allowances, not another round count. Keep all prior rounds. Duplicate identical resolution returns the original outcome, never adds twice. Different, missing, stale or unsupported authorization rejects.

The reviewer must recommend bounded continuation and the user must approve the specific allowance and approach; Root may not infer a larger allowance. A change to intent returns to the user under existing intent rules before implementation and cannot be hidden in a threshold approval. At each later exhaustion, repeat independent review and explicit user approval. Denial/defer/STOP leaves the ceiling unchanged. Approval does not waive quality, candidate-binding or release gates.

## D7: staged deployment and rollback

1. S2 implements assignment/finalization/receipt controls on isolated selected fixtures. Keep normal initializer default at legacy and global roles unchanged.
2. S3 implements full round and user-approved continuation rules. Until this exists, S2 fixtures are not operational new-policy product runs; runtime feature incompleteness must be explicit.
3. S4 aligns the three specialist configurations/adapters conditionally and proves effective role discovery/reload. Keep unbound roles' current behavior and configured models/reasoning.
4. S5 runs actual custom-role Direct B, A-to-B and exact-baseline scenarios; generic workers do not prove specialist write support.
5. S6 resolves changed-path failures, distribution closure and required missing coverage. S7 publishes explicit selection only after review; default remains legacy unless separately changed by an authorized revision.

Rollback disables new selected admissions, retains compatible reading/recovery for existing selected records, and preserves all markers, receipts and round history. Do not strip revision markers or run old low-level writers against selected state. Resolve an interrupted transaction with the compatible recovery implementation before rollback. Existing runs/releases are never silently migrated.

S7 operating annotation: this staged sequence is complete within the recorded
activation scope; use [rollout and recovery](agent-rollout.md) for current commands
and limits. Retain the complete compatible installation before procedure-byte
updates. Recover interrupted work against original project/run paths, then obtain
fresh owner assignments and bindings before forward use; never edit old bindings,
hashes or receipts to make updated procedures appear current.

## Exact implementation delta and review boundaries

| Source/interface | Bounded delta | Stage / proof |
| --- | --- | --- |
| `validation.py`, initializer | Supported boundary revisions; strict selector/metadata; initial maps and limit | S2 selector/receipt validation, S3 full round validation; legacy/unknown-policy tests |
| `boundary.py`, `cli.py` | Assignment/input capture, exact-file policy, selected probe path; start arguments; mutually exclusive process-review event mode | S2 artifact path tests; S3 review-file scope, no product-report activation |
| `artifacts.py`, `cli.py` | Expected digest; embedded receipts; write-ahead recovery; selected persist rejection | S2 captured-byte identity, rollback, process interruption, current/historical replay |
| `state.py`, `validation.py` | Terminal snapshot, round ledger, narrow PASS/incomplete-release repair route, replay | S3 grouping, zero initial count, fourth pass, contract revisit, interrupted round |
| `state.py` bounce-back interfaces | Threshold basis, review/approval validation and atomic finite allowance | S3 missing/forged/stale/replayed approval rejection, authorized bounded continuation |
| Existing run-mutator preflights | Supported-policy/pending-transaction guard before writes | S2 dependency needed for recovery integrity; cover test runner, package/inspection and harness entry points where existing validation does not suffice |
| Role/adapters/governance | Conditional artifact ownership, compact references, reviewer/user routing | S4; actual runtime write support in S5 |
| Docs/inventory | Selected operating instructions and required distributed dependencies | S6-S7; preserve existing package exclusions |

The additional preflight call sites may require small changes in `test_runner.py`, `packaging.py` and `verifier_harness.py`. This is an explicit source-map extension to prevent writes during incomplete registration, not redesign of tests, packaging or the harness. Prefer existing validators/call paths; add no redundant policy engine.

Preserve stage/gate IDs and quality meanings; semantic contract/report headings and requirement coverage; independent verifier verdicts; test/harness/manifest/inspection formats; exact-baseline eligibility and historical evidence. Review each slice against parent A01-A26; existing two-attempt/generic/legacy tests remain. Failure injection, live roles and distribution tests are implementation obligations, not evidence already obtained by this S1 design.
