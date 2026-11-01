# Gate and Command Map

Use this reference for every build-tool pipeline run. Replace placeholders with repository-relative paths and retained evidence references. Run commands from `tools/intent-tool-pipeline/` with `..\..\.venv\Scripts\python.exe` on Windows.

## Table of Contents

- [Global rules](#global-rules)
- [State bookkeeping](#state-bookkeeping)
- [Semantic invocation boundary](#semantic-invocation-boundary)
- [Selected artifact submission and registration](#selected-artifact-submission-and-registration)
- [Selected four-round modification and threshold review](#selected-four-round-modification-and-threshold-review)
- [Run initialization and migration](#run-initialization-and-migration)
- [Stage command map](#stage-command-map)
- [Failure routing](#failure-routing)
- [Release sequence](#release-sequence)
- [Resume validation](#resume-validation)

## Global Rules

- Use `pipeline_ops.py --format json` when a result will be retained or parsed.
- Stop on exit code `1` or `2`; retain the command, JSON output, and diagnostic codes.
- Run `validate-run` before every advancement and after every Root-owned metadata edit.
- Run `validate-contract` for every new active contract version.
- Use only the fixed default `30_execution/test_results.json` to satisfy packaging and release gates, and require it to identify a retained immutable `30_execution/test_attempts/<attempt-id>/test_results.json` record.
- Use only the fixed default `50_release/package_inspection.json` to pass release.
- Reject any product-contract acceptance method that requires the current verifier report or a future final release-gate decision to produce that same pre-release verifier judgment.
- Archive by copying the old active artifact, not by moving it away; replace and validate the active path before changing its run-state reference.
- Never call an agent again after a bounce-back until the event records a changed input, decision, implementation, or evidence basis.
- Never invoke a governed semantic/read-only role without a retained role-boundary start baseline. Complete semantic-artifact assignments with finalize-semantic-return; complete read-only explorers and selected threshold process reviews with role-boundary finish.
- Never manually activate `problem_frame`, `product_contract`, or `verification_report`; use `finalize-semantic-return` with the matching start baseline.
- Run `prepare-verification` only after `package` and `inspect-package` pass, and bind its plan to the exact active contract, manifest, inspection, and archive paths and SHA-256 values.
- Before run initialization and every spawn, inventory retained agents and
  available task-lifetime capacity when the runtime exposes them. Treat a
  completed agent as reusable and still retained unless disposal is explicitly
  confirmed.
- Keep one agent per exact semantic role and use `followup_task` for later runs,
  revisions, retries, and repairs. A fresh same-role agent requires a recorded
  context-isolation reason and sufficient reserved capacity.
- Reserve required semantic roles before optional delegation. Never repurpose a
  fixed custom role, and do not initialize a run that cannot obtain all required
  roles within the current task or an explicitly arranged task handoff.
- Start a role boundary only after the selected agent is available. If spawn
  fails and protected run bytes later change, discard the unused invocation
  reference and create a new boundary baseline before invoking the role.

## State Bookkeeping

Use `update-state` for stage and gate status changes. It atomically increments the run-state artifact version and synchronizes the active self-reference.

Use `update-bounce-back` for bounce-back creation and resolution. The command owns event placement, ID assignment, open/resolved control fields, run-state version synchronization, candidate validation, and atomic replacement. Do not edit `bounce_back_events` directly.

Root may manually update only remaining Root-owned fields the control plane does
not expose: blockers, required approvals and the normalized build-request identity.
For a changed request, preserve prior bytes in `00_intake/history/`, increment its
version, retain original sources and recorded decisions, keep its consumed route,
and bind the new version/hash in `active_artifacts.build_request`. Treat request
and state replacement as one Root-owned operation with rollback on validation
failure. Never refresh hashes merely to bless unexplained drift; first resolve
the change and its authority. Subsequent contract adoption must cite the new identity.
Active semantic artifact references are owned by `finalize-semantic-return`
(legacy `persist-artifact`). For each allowed manual edit:

1. start from the latest validated state;
2. keep Root as the only writer;
3. increment `artifact.version` and `active_artifacts.run_state.version` together;
4. set a timezone-aware `artifact.updated_at`;
5. preserve prior events and records;
6. atomically replace the state file;
7. run `validate-run` immediately;
8. do not advance if validation fails.

`finalize-semantic-return` finishes the role boundary, archives a consumed semantic artifact before replacing it, enforces the next version, updates the active entry with hash/provenance, validates the whole run, and rolls all canonical/state bytes back on failure. Do not reproduce those steps manually. `role-boundary finish` plus `persist-artifact` remains available only for migration-compatible older orchestration.

## Semantic Invocation Boundary

For every governed semantic invocation, apply [invocation.md](invocation.md).
Name the current role-specific skill and adapter, original inputs, output identity
and authorized boundary. Custom role selection alone does not load this protocol.
Historical problem_framer calls must name [framing-adapter.md](framing-adapter.md).
These commands govern pipeline calls, not unrelated ordinary custom-agent work.

New runs record `control.intent_realization: "1.0"`; when A is applicable, use
`intent_realizer` in the compatibility `framing` stage / `problem_frame` slot.
Direct B omits that invocation and leaves the slot null. Unmarked historical
runs retain `problem_framer` when resuming their original workflow; never relabel
old artifact owners or hashes. The `problem_framer` registration is retired;
a fresh invocation is blocked pending explicitly authorized migration or
restoration. Do not substitute the successor under its recorded identity.
In the commands below use the owner selected by
the run, not a convenient available agent.

### Legacy semantic invocation

The following full-body return, read-only Realizer/Contractor and generic probe
allowances apply to legacy boundary control "1.0" and supported historical calls.
Selected "1.1" or "1.2" runs use the next section instead. Neither procedure is required
for unrelated ordinary role use.

Before invoking intent_realizer, product_contract_agent, independent_verifier, or a read-only explorer:

```powershell
..\..\.venv\Scripts\python.exe pipeline_ops.py --format json role-boundary start `
  --run-dir <run-dir> `
  --role <role> `
  --invocation-ref <unique-invocation-ref>
```

Retain `data.baseline_sha256` and invoke the role. For `intent_realizer`, `product_contract_agent`, or `independent_verifier`, save the complete returned body at a separate Root-held repository path, not the canonical active path, and finalize it in one call:

```powershell
..\..\.venv\Scripts\python.exe pipeline_ops.py --format json finalize-semantic-return `
  --run-dir <run-dir> `
  --artifact <problem_frame|product_contract|verification_report> `
  --role <role> `
  --invocation-ref <same-invocation-ref> `
  --baseline-sha256 <start-result-baseline-sha256> `
  --source <root-held-returned-body-path>
```

Require `ok: true`, then run `validate-run` immediately. The command validates the role/artifact ownership pair, returned body and version, archives an active prior version, atomically replaces canonical bytes, updates `active_artifacts`, and restores the exact prior artifact and state bytes if any step fails. Its immutable failure journal is diagnostic evidence, never an activated semantic result.

For a read-only `explorer`, which returns no semantic artifact to activate, finish the audit directly:

```powershell
..\..\.venv\Scripts\python.exe pipeline_ops.py --format json role-boundary finish `
  --run-dir <run-dir> `
  --role explorer `
  --invocation-ref <same-invocation-ref> `
  --baseline-sha256 <start-result-baseline-sha256>
```

`intent_realizer`, legacy `problem_framer`, `product_contract_agent`, and `explorer` have no allowed run writes. `independent_verifier` may write only `40_verification/probes/**`; a symlink or reparse-point escape is unauthorized. Any create, modify/overwrite, truncate, delete, or rename outside the role allowance produces `BOUNDARY_VIOLATION`, restores baseline `run_state.json` bytes if that file changed, and blocks artifact activation, gate PASS, and advancement. Resolve or contain the changed paths and use a new invocation reference; a later clean PASS becomes the latest role result.

## Selected artifact submission and registration

For control `1.2`, including the new-run default, these file/round rules also apply.
After start, give the specialist [assignment-entry.md](assignment-entry.md) and
the exact assignment identity. It loads mandatory procedures with
`load-role-assignment`; finalization also validates its result binding. Current
procedure drift blocks forward mutations; replacement assignment and retained
receipt recovery follow [the binding contract](../../../../tools/intent-tool-pipeline/docs/contracts/procedure-binding.md).

This section applies to runs with control.semantic_role_boundary: "1.1" or "1.2".
The user-authorized post-S7 override `ITP-20261101-DEFAULT12` (2026-11-01)
makes "1.2" the new-run default; "1.1" remains explicit and compatible.
New legacy runs require explicit `--control-revision 1.0`. Read the maintained
docs/contracts/agent-artifact-protocol.md and round-recovery-clarification.md;
the original semantic schemas, readiness judgments and quality gates remain.

Start only after the required exact role is available with effective selected
write permissions. A TOML edit or earlier agent does not prove reload. If the
runtime cannot write the assigned file, preserve the failure and wait for a
refreshed role context; a generic worker or Root transcription is not proof.

### Assign one complete artifact

The semantic keys remain problem_frame, product_contract and verification_report.
Start captures mandatory original/upstream/candidate inputs. A selected read-only
explorer uses the existing start/finish calls without --artifact and receives no
submission grant. Repeat --input-ref
for additional local files actually supplied; omission removes no mandatory input.

~~~powershell
..\..\.venv\Scripts\python.exe pipeline_ops.py --format json role-boundary start --run-dir <run-dir> --role <role> --invocation-ref <unique-invocation-ref> --artifact <artifact-key> --input-ref <additional-local-input-path>
~~~

Retain baseline_sha256, derived artifact version, round_number, exact inputs and
submission_path from data. Omit --input-ref if there is no additional input.
Give the role that assignment, its named skill/adapter and original sources.
It completes the semantic artifact only at the returned submission_path:

| Key | Assigned run-relative file |
| --- | --- |
| problem_frame | 30_execution/sub/<audit-id>/brief.md |
| product_contract | 30_execution/sub/<audit-id>/contract.yaml |
| verification_report | 30_execution/sub/<audit-id>/report.md |

The Verifier additionally uses only its assigned
40_verification/probes/<audit-id>/ directory. Other artifact roles have no probe
allowance. Canonical metadata retains the existing active path; do not substitute
the submission path. No sibling, descendant, alias, canonical/state or prior
output is writable.

### Register actual bytes and consume the registered artifact

Require a compact response with actual path, artifact ID/version, SHA-256,
invocation, status, inputs read, unresolved items and evidence references. Root
reads the file, checks the returned identity and finalizes those same bytes:

~~~powershell
..\..\.venv\Scripts\python.exe pipeline_ops.py --format json finalize-semantic-return --run-dir <run-dir> --artifact <artifact-key> --role <role> --invocation-ref <same-invocation-ref> --baseline-sha256 <start-result-baseline-sha256> --source <exact-start-result-submission-path> --expected-source-sha256 <actual-role-submission-sha256>
~~~

Require ok true, retain the receipt/canonical identity and run validate-run.
Root and downstream roles read the actual registered brief, contract or report
and original sources. A compact return or receipt is not semantic readiness.
Preserve BLOCKED/NOT_READY/UNVERIFIED; do not routinely repeat specialist
adjudication or transcribe/rewrite the body. Selected persist-artifact rejects.

Changed inputs require finishing/accounting for the old invocation and issuing a
new assignment. Corrected producer bytes require a fresh invocation. After reply
loss or interrupted finalization, reissue the same matching request for
journal/receipt recovery. PREPARED blocks unrelated writers. Historical replay
may return is_current false; never reactivate old bytes, strip control markers
or recover with an incompatible old writer.

## Run Initialization and Migration

Normal initialization selects control `1.2`; explicit `--control-revision 1.2`
has the same result. Use `--control-revision 1.0` only when a new legacy run is
requested; explicit `--control-revision 1.1` remains supported for its earlier protocol.
Selection is new-run only; never migrate an existing ledger or create a new run
to reset allowance for the same unfinished work. Follow the
[rollout procedure](../../../../tools/intent-tool-pipeline/docs/contracts/agent-rollout.md)
for procedure drift, freeze and compatible recovery.

Choose exactly one request mode before initialization:

- `NEW_PRODUCT`: `project.request_kind: NEW_PRODUCT`; omit `revision_of` and `delta_request`.
- Exact-baseline `REVISION`: `project.request_kind: REVISION`; provide `revision_of.run_id`, archive/contract/report references and SHA-256 values, plus `delta_request.scope_classification: BOUNDED`, `requested_changes`, `explicit_non_changes`, and `feedback_evidence`.

The revision initializer accepts only a completed same-target release whose verification report is `READY` with every current requirement `PASS` and whose active contract, report, manifest, inspection, and archive still match the candidate binding captured at verification PASS. Any broad, ambiguous, incompatible, incomplete, missing, or drifted baseline returns `FRESH_REQUIRED`, creates no run, and must be reframed as a new request rather than silently downgraded.

A revision produces one complete current `product_contract.yaml`, and a complete
current `problem_frame.md` when using A. The contract must add `revision_control.mode: DELTA`, copy the exact baseline identity, hash every unchanged requirement with its linked acceptance records, and map every requested change/non-change exactly once while covering every baseline and current requirement. Each map entry carries its disposition, baseline/current requirement references, source/test/documentation/packaging references, migration impact, and `ALL_APPLICABLE_REQUIREMENTS` reverification scope.

Preserve older handoffs and label their migration role `SUPERSEDED_CONTEXT` in prose. Cite them through an existing permitted `source_context.authority` value; `SUPERSEDED_CONTEXT` is not an authority enum. Existing runs remain read-compatible, but a run without the complete captured candidate binding is not revision-baseline eligible.

## Stage Command Map

Set this placeholder once:

```text
<run-dir> = workspace/build_runs/<project-id>
```

### Initialize and validate intake

Before running the initializer, apply the `NEW_PRODUCT` or exact-baseline `REVISION` branch above. For a revision, require successful baseline resolution and the returned `control.revision_baseline`; stop on `FRESH_REQUIRED` and confirm no run directory was created.

```powershell
..\..\.venv\Scripts\python.exe ..\..\.agents\skills\build-tool-pipeline\scripts\initialize_run.py `
  --request <build-request-path> `
  --format json

..\..\.venv\Scripts\python.exe pipeline_ops.py --format json validate-run `
  --run-dir <run-dir>
```

For A, if intake is semantically ready, pass it and enter framing with two separate calls:

```powershell
..\..\.venv\Scripts\python.exe pipeline_ops.py --format json update-state `
  --run-dir <run-dir> `
  --to-stage intake `
  --stage-status PASSED `
  --gate-status PASSED `
  --evidence-ref build-request@<version> `
  --rationale "The active request preserves the approved outcome, target, constraints, and handoff." `
  --next-action "Start intent realization."

..\..\.venv\Scripts\python.exe pipeline_ops.py --format json update-state `
  --run-dir <run-dir> `
  --to-stage framing `
  --stage-status IN_PROGRESS `
  --gate-status IN_PROGRESS `
  --rationale "Intent realization started from the active request." `
  --next-action "Produce and persist problem_frame.md."
```

### Pass framing and enter contract

This section applies to A only. For an already prepared run, validate its current
request, adopted brief, original source/delegation snapshots and readiness, then
use only the contract-entry call below. Do not repeat Realizer or mark A passed twice.

Audit and activate the complete current realization brief with
`finalize-semantic-return --artifact problem_frame --role intent_realizer`.
Use the original owner only for an unmarked historical run. Validate the run. Then:

```powershell
..\..\.venv\Scripts\python.exe pipeline_ops.py --format json update-state `
  --run-dir <run-dir> `
  --to-stage framing `
  --stage-status PASSED `
  --gate-status PASSED `
  --evidence-ref problem-frame@<version> `
  --evidence-ref intent_realizer:<invocation-ref> `
  --rationale "The framing artifact permits contract authoring without material guessing." `
  --next-action "Start product-contract authoring."

..\..\.venv\Scripts\python.exe pipeline_ops.py --format json update-state `
  --run-dir <run-dir> `
  --to-stage contract `
  --stage-status IN_PROGRESS `
  --gate-status IN_PROGRESS `
  --rationale "Contract authoring started from the active request and frame." `
  --next-action "Produce, validate, and persist product_contract.yaml."
```

### Pass contract and enter repository analysis

For direct B, initialize with existing request `handoff.next_stage: contract`,
then pass intake and enter contract with the following calls. The initializer
binds request bytes in the existing `active_artifacts.build_request.content_sha256`.
Absent/framing next_stage preserves the existing prepared route; no new schema
version, stage or status enum is introduced.

```powershell
..\..\.venv\Scripts\python.exe pipeline_ops.py --format json update-state `
  --run-dir <run-dir> --to-stage intake --stage-status PASSED --gate-status PASSED `
  --evidence-ref build-request@<version> `
  --rationale "Clear intent and existing authority support direct Root and Contractor intake." `
  --next-action "Start direct contract intake."

..\..\.venv\Scripts\python.exe pipeline_ops.py --format json update-state `
  --run-dir <run-dir> --to-stage contract --stage-status IN_PROGRESS --gate-status IN_PROGRESS `
  --rationale "Root and Contractor review the original intent and delegated boundaries." `
  --next-action "Return the complete current product contract."
```

Direct framing stays PENDING with no active frame; it is not a passed requirement.
Both routes now use the same commands below and all remaining gates. Every newly
bound request requires exact `build-request` version/hash in contract
`source_artifacts`, plus `problem-frame` version/hash only for prepared runs.
Declared local source snapshots in `source_context` are checked by path/hash.
Supply these identities before the Contractor invocation; Root must not patch
the returned semantic body to add missing source records.

Audit and activate the complete current contract with `finalize-semantic-return --artifact product_contract --role product_contract_agent` before validation. A revision contract must contain a complete, coverage-valid `revision_control`; a delta-only fragment is invalid.

```powershell
..\..\.venv\Scripts\python.exe pipeline_ops.py --format json validate-contract `
  --contract <run-dir>/20_contract/product_contract.yaml

..\..\.venv\Scripts\python.exe pipeline_ops.py --format json validate-run `
  --run-dir <run-dir>

..\..\.venv\Scripts\python.exe pipeline_ops.py --format json update-state `
  --run-dir <run-dir> `
  --to-stage contract `
  --stage-status PASSED `
  --gate-status PASSED `
  --evidence-ref product-contract@<version> `
  --evidence-ref product_contract_agent:<invocation-ref> `
  --evidence-ref contract-validation:<result-ref> `
  --rationale "The active contract is structurally valid and semantically ready." `
  --next-action "Inspect the target repository and define the implementation boundary."

..\..\.venv\Scripts\python.exe pipeline_ops.py --format json update-state `
  --run-dir <run-dir> `
  --to-stage repository_analysis `
  --stage-status IN_PROGRESS `
  --gate-status IN_PROGRESS `
  --rationale "Repository analysis started from the active contract." `
  --next-action "Record repository findings and implementation constraints."
```

### Pass repository analysis and enter implementation

Pass the repository gate with read-only analysis evidence, then enter implementation. Do not use an explorer result as implementation evidence.

### Test, package the candidate, and pass implementation

```powershell
..\..\.venv\Scripts\python.exe pipeline_ops.py --format json run-tests `
  --run-dir <run-dir> `
  --plan <test-plan-path> `
  --attempt-id <unique-test-attempt-id>
```

Require `ok: true` and `data.status: PASS`. Retain `data.attempt_path` and `data.attempt_sha256`; attempt IDs are immutable and cannot be reused. The fixed canonical result must identify those immutable attempt bytes. Pass implementation with product paths and `30_execution/test_results.json` as evidence, but keep `implementation` as the current stage while candidate packaging and inspection run. Enter verification as `IN_PROGRESS` only after the inspected candidate and harness evidence exist; `IN_PROGRESS` is the normal report-registration window and may initially have a null active verification report.

Run `package`, then `inspect-package`, using the fixed default release-manifest and package-inspection paths. Require both commands to return `ok: true` and the inspection to return `data.status: PASS`. These files and the archive are pre-verification candidate evidence; their existence does not move release from `PENDING` or authorize user-facing release claims.

```powershell
..\..\.venv\Scripts\python.exe pipeline_ops.py --format json package `
  --run-dir <run-dir> `
  --spec <package-spec-path>

..\..\.venv\Scripts\python.exe pipeline_ops.py --format json inspect-package `
  --run-dir <run-dir> `
  --manifest <run-dir>/50_release/release_manifest.json

..\..\.venv\Scripts\python.exe pipeline_ops.py --format json prepare-verification `
  --run-dir <run-dir> `
  --plan <exact-binding-verifier-plan> `
  --contract <run-dir>/20_contract/product_contract.yaml `
  --manifest <run-dir>/50_release/release_manifest.json `
  --inspection <run-dir>/50_release/package_inspection.json `
  --archive <candidate-archive-path> `
  --attempt-id <unique-verification-attempt-id>
```

The verification plan must bind each explicit path and its SHA-256, enforce the full scenario minimums, and run every command against one clean extraction with isolated per-command temp/output roots. By default the harness allocates its owned short namespace under the operating-system temp directory; use `--scratch-root` only for a bounded local/test policy. Require `ok: true`, `data.status: PASS`, `data.extraction_count: 1`, immutable attempt/summary evidence, `data.cleanup_status: PASS`, no undeclared-dependency or protected-mutation diagnostic, and `python_audit_status: PASS` for every recognized Python command. Missing or disabled Python audit activation fails closed. The harness reports `independent_verifier_judgment: NOT_PERFORMED`; its argv/environment/entrypoint/Python-audit controls prepare evidence but remain not the verifier's semantic judgment or an OS sandbox.

The harness must accept a null current verification report before verifier invocation. It still requires and protects every applicable upstream semantic and candidate input; direct B has no required frame. If an already active verification report exists for a later attempt, it remains a protected input; any malformed non-null entry or mutation fails closed. Never create a placeholder report to satisfy preparation.

Regenerate and reinspect after any attributable source, test-plan, contract approval binding, or package-specification change, then create a new harness attempt. `package` invalidates the prior inspection before atomically replacing package evidence.

### Produce the report, then set verification status

After implementation, candidate packaging, package inspection, and `prepare-verification` pass, enter verification as `IN_PROGRESS`:

```powershell
..\..\.venv\Scripts\python.exe pipeline_ops.py --format json update-state `
  --run-dir <run-dir> `
  --to-stage verification `
  --stage-status IN_PROGRESS `
  --gate-status IN_PROGRESS `
  --rationale "Independent verification started against the inspected candidate." `
  --next-action "Produce and register verification_report.md."
```

Then start the `independent_verifier` boundary and invoke `independent_verifier` as the exact custom role. Supply the immutable harness attempt and cleanup evidence, source identity, release manifest, archive hash, package inspection, contract, tests, documentation, and repair history. Legacy verification permits focused probes under `40_verification/probes/**`; selected verification permits them only in its assigned `40_verification/probes/<audit-id>/` directory. These supplement but never replace full applicable-requirement coverage. Selected invocation/finalization must also supply the artifact assignment and expected digest from the selected recipe above. Finalize the complete report with `finalize-semantic-return --artifact verification_report --role independent_verifier`, require PASS, and run `validate-run` while verification remains `IN_PROGRESS`.

Only after that validation passes, set the in-progress stage to the report-derived verification status: for `READY` with every applicable requirement `PASS`, mark verification `PASSED`; for `NOT_READY`, mark verification `FAILED`; for `UNVERIFIED`, mark verification `BLOCKED` and acquire evidence without consuming a repair attempt unless implementation or contract changes become necessary.

Verification `IN_PROGRESS` may await report registration. Never create a terminal verification `PASSED`, `FAILED`, or `BLOCKED` state while `active_artifacts.verification_report` is null or points to a missing file.

## Selected four-round modification and threshold review

Apply only to selected "1.1" or "1.2" runs; legacy control "1.0" retains the
following Failure Routing section. All current test, candidate, readiness,
independent-verification and completed-release gates still apply.

### Reserve before modification; complete after the fresh verdict

Initial terminal verification records latest_verification_result with count zero.
Reserve before subsequent subject modification through existing update-state,
with the exact latest report and attributable modification-event IDs:

~~~powershell
..\..\.venv\Scripts\python.exe pipeline_ops.py --format json update-state --run-dir <run-dir> --to-stage repair --stage-status IN_PROGRESS --gate-status IN_PROGRESS --failure-ref verification-report@<latest-version> --evidence-ref <BB-ID> --rationale "Reserve one round before subject changes." --next-action "Apply the grouped changes within this round."
~~~

Repeat --evidence-ref for several event IDs. repair.active_attempt counts rounds
started; rounds records source, requests, IN_PROGRESS and eventual result.
Initial iteration/verification, status updates and attributable evidence-only
recovery add no round. Group related defects, contract-plus-code changes,
earlier-stage visits and resumed work within the reserved round. This includes
prior PASS or incomplete-release changes; completed release stays immutable.

Resolve originating modification events through update-bounce-back with changed
basis; rerun affected tests, regenerate/reinspect the candidate and obtain a fresh
Verifier assignment bound to this round. A pre-reservation report cannot complete
it. The fresh terminal result completes the record without another count.
PASSED alone grants release authority. Exact start/result replay recovers the
recorded identity; conflicting source/request/result rejects. Never edit the count,
ceiling or ledger, or create a replacement run to reset unfinished work.

Evidence-only recovery requires an attributable resolved EVIDENCE_GAP event with
EVIDENCE_CHANGED and known unchanged contract/archive/source. Unknown identity,
drift and two null values are not equality. A later null-round report may become
the threshold basis only through authenticated pre-invocation state and a finite
decreasing report-version lineage back to the exhausted completed result.
Preserve that original result and use the exact latest recovery report for
review/approval, following docs/contracts/round-recovery-clarification.md.

### Stop at exhaustion and review the process

The initial allowance is four. An in-progress fourth round may finish; a fourth
PASS may advance through ordinary release gates. Further modification stops
before reserving round five. Investigate repeated root causes/non-progress early;
do not disguise subject changes as environment/evidence operations.

At exhaustion with no IN_PROGRESS round, use update-bounce-back create for
REPAIR_LIMIT_EXHAUSTED. Its origin identifies the exact latest independent_verifier
role, invocation_ref, result_artifact_ref and terminal result. Root supplies
retained round, candidate/report and original-intent references; the command
derives round_review_basis rather than accepting caller-chosen counters.

Invoke independent_verifier separately as a process reviewer using
verification-adapter.md, distinct from correction work and product verification:

~~~powershell
..\..\.venv\Scripts\python.exe pipeline_ops.py --format json role-boundary start --run-dir <run-dir> --role independent_verifier --invocation-ref <unique-process-review-invocation> --review-event <threshold-BB-ID> --input-ref <additional-retained-review-input>
~~~

--review-event is mutually exclusive with --artifact. Supply the exact returned
review_path, basis and input identities. The only durable output is
40_verification/probes/<audit-id>/round-review.json. Its precreated parent is not
a probe/ephemeral grant. There is no product-report assignment/version/receipt.
The reviewer returns actual path/hash, recommendation, allowance, unresolved
items and references; it cannot implement or authorize its recommendation.

Finish this audit directly, rather than finalizing a semantic report:

~~~powershell
..\..\.venv\Scripts\python.exe pipeline_ops.py --format json role-boundary finish --run-dir <run-dir> --role independent_verifier --invocation-ref <same-process-review-invocation> --baseline-sha256 <process-review-start-baseline-sha256>
~~~

Retain matching PASS before submitting a bounded recommendation for user
decision. STOP, defer or denial grants no additional allowance.

### Obtain and retain the actual user decision

Only BOUNDED_CONTINUATION with intent_impact UNCHANGED supports continuation.
The user approves the exact positive finite additional_rounds and proposed
changed approach. Preserve the actual response: silence, a Root paraphrase,
the recommendation or general approval of framework work is not approval.
An intent change requires its existing separate user decision.

Approval JSON contains schema_version "1.0",
artifact_type "iteration-continuation-approval", run_id, user_role "user", actual
response, decision "APPROVE", timezone-aware timestamp, review_path, review_sha256,
exact basis, additional_rounds, proposed_changed_approach and intent_impact
"UNCHANGED". Its timestamp follows completed review and precedes resolution.

The existing update-bounce-back resolve payload uses resolution_type USER_DECIDED,
resolved_by user and retry.allowed true with change_basis [DECISION_CHANGED].
Add continuation: review_path, review_sha256, review_invocation_ref,
boundary_evidence_ref, approval_path, approval_sha256, additional_rounds and
new_maximum_attempts. Cite approval_path in decision_refs and exact review/boundary
paths in evidence_refs. Supply the complete payload to the existing command:

~~~powershell
..\..\.venv\Scripts\python.exe pipeline_ops.py --format json update-bounce-back --run-dir <run-dir> --action resolve --payload <complete-threshold-resolution-json>
~~~

The command validates reviewer/audit/user evidence and exact current basis/subject,
then atomically resolves and adds the approved allowance. Missing, stale or
malformed authorization rejects. Exact duplicate resolution returns the original
outcome without another increment; conflicting resolution rejects. Preserve all
rounds and approvals. Every later exhaustion needs a new review and exact user
decision. No allowance waives requirement coverage, tests, candidate or release gates.

## Failure Routing

The reassessment and two-attempt procedures in this section describe legacy
control "1.0"; selected "1.1" uses the preceding round/review section.

Ordinary evidence gaps and delegated technical decisions stay in B. Contractor
corrects contract meaning; Verifier owns verdict/revalidation. Only unsupported
material intent/preference/authority choices return to A/user, scoped to the
affected issue, with stable work preserved. Record source, individual/cumulative
impact, decision authority and changed basis in existing bounce-back references.

### Reassess a prior PASS before completed release

If new evidence or intent challenges a passed verdict, first preserve its report
and candidate identity in the event's referenced evidence. Create an OPEN
bounce-back using `update-bounce-back` with the exact `verification-report@<version>`
in `affected_refs`, verification in `affected_stages`, and retry role
`independent_verifier` / `prior_invocation_ref` matching that report. The existing
origin fields are `role`, `invocation_ref`, `result_artifact_ref`, `result`.
Classify the actual issue; do not invent a new event enum.

```powershell
..\..\.venv\Scripts\python.exe pipeline_ops.py --format json update-state `
  --run-dir <run-dir> --to-stage verification `
  --stage-status IN_PROGRESS --gate-status IN_PROGRESS `
  --failure-ref verification-report@<version> --evidence-ref <new-basis-ref> `
  --rationale "Recorded new basis requires independent reassessment." `
  --next-action "Obtain a fresh verifier judgment before any affected completion."
```

This works from verification PASSED or release IN_PROGRESS only when the previous
candidate binding exists; completed release cannot reopen. Release becomes PENDING.
The prior verification identity is retained as review basis and cannot authorize
release while verification is IN_PROGRESS. It also prevents candidate/contract
replacement from bypassing repair. Evidence-only reassessment resolves the event
with `resolution_type: EVIDENCE_ADDED`, `retry.change_basis: [EVIDENCE_CHANGED]`
and requires a fresh audited Verifier return. A new PASS replaces the old identity.
If code/contract changes are required, finalize the eligible NOT_READY/UNVERIFIED
verdict, mark FAILED/BLOCKED and enter repair through the existing sequence below.
That transition clears the old binding and increments the existing counter.
At two attempts, further repair remains rejected. No same-input verdict reuse.

### Repair an eligible failure

For an implementation defect or contract contradiction:

1. finalize the verifier report through `finalize-semantic-return`;
2. mark verification `FAILED` or `BLOCKED` with report evidence;
3. create an open bounce-back with retry disabled through `update-bounce-back --action create`;
4. enter repair with `--failure-ref verification-report@<version>`;
5. repair only the named defect or contradiction;
6. rerun the affected test plan with a new immutable attempt ID, regenerate and reinspect the candidate package, then run a new exact-binding verification-harness attempt;
7. resolve the event through `update-bounce-back --action resolve` with changed-artifact/evidence references and a non-empty allowed change basis;
8. pass repair and return to verification with current source and archive identities.

Entering repair must use:

```powershell
..\..\.venv\Scripts\python.exe pipeline_ops.py --format json update-state `
  --run-dir <run-dir> `
  --to-stage repair `
  --stage-status IN_PROGRESS `
  --gate-status IN_PROGRESS `
  --failure-ref verification-report@<version> `
  --rationale "Verification returned an eligible evidence-backed failure." `
  --next-action "Perform bounded repair attempt <n> and rerun attributable tests."
```

Never use repair to seek a different answer from unchanged inputs. Missing candidate package evidence alone is acquired before verification and does not consume an attempt. A semantic contract revision is a contract repair and does consume an attempt even if product hashes are unchanged. Never reduce `repair.active_attempt`; the enforced maximum is `2`.

## Release Sequence

After verification passes and the exact default-path tests, harness attempt, and candidate package evidence it judged are still current:

1. enter `release` as `IN_PROGRESS`;
2. require the automatic active verification-report reconciliation to match the hash captured when verification passed, then confirm the active source, immutable test attempt, contract approval binding, manifest, archive, inspection, and harness hashes match the verifier inputs;
3. require inspection and harness status `PASS`, cleanup status `PASS`, and verify the archive hash without rebuilding the archive;
4. run `validate-run`;
5. pass release with the exact `candidate_binding`, manifest, archive hash, inspection, harness attempt and cleanup, verifier report, and immutable/canonical test results as evidence;
6. write `50_release/completion_report.md` using `completion-report.md`;
7. report delivery as awaiting user approval unless approval is already recorded.

Do not pass release after a `PENDING` or failed inspection, harness attempt, or cleanup. If any material input changed after verification, do not rebuild inside release; return to tests, candidate packaging, inspection, `prepare-verification`, and independent verification first.

## Resume Validation

On every resume, run `validate-run` before invoking an agent or changing state. For `REVISION`, this re-resolves the exact baseline and rejects drift in the target, archive, active contract, active verification report, manifest, inspection, captured candidate binding, or unchanged requirement bundles. Stop on `FRESH_REQUIRED` or `REVISION_BASELINE_DRIFT`; never update stored hashes to bless changed bytes and never silently fall back to `NEW_PRODUCT`.

Read-compatible legacy runs keep their existing files and semantics. They may resume through the migration-compatible `role-boundary finish` plus `persist-artifact` path, but only runs with a fully captured exact verified-candidate binding are eligible as future revision baselines.
