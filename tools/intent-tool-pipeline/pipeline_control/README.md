# Deterministic Pipeline Control Plane

## Purpose

New runs default to control `1.2`, requiring workflow-owned procedure assignments;
explicit `--control-revision 1.2` has the same result. `load-role-assignment` is read-only and
returns mandatory procedure bodies, bound inputs, exact outputs and result
binding. Registration/forward mutations reject missing, mismatched or stale
binding; matching historical receipt replay retains its original procedure bytes.
See [the binding contract](../docs/contracts/procedure-binding.md) and
[assignment entry](../../../.agents/skills/build-tool-pipeline/references/assignment-entry.md).
The user-authorized post-S7 override `ITP-20261101-DEFAULT12` (2026-11-01)
sets that new-run default; explicit compatible `1.1` remains and new legacy
`1.0` requires explicit selection. Existing runs retain their recorded control.
S7 (`ITP-20261101-ARTIFACT-S7`, 2026-11-01) publishes the
[operating and recovery procedure](../docs/contracts/agent-rollout.md).

This package implements the deterministic control plane of the Codex-native product-delivery framework. It moves artifact structure checks, semantic-role mutation audits, Root-controlled artifact activation, contract traceability, run-state transitions, test execution, deterministic ZIP creation, and archive inspection out of LLM reasoning.

The utility does not invoke an LLM, select an agent, make semantic product decisions, or replace independent verification. Root remains the orchestration and release owner.

## Selected submission and round controls

The [S1 control protocol](../docs/contracts/agent-artifact-protocol.md) defines
the selected submission/round interface; `1.2` adds procedure binding.
The protocol's original staged status describes S1 design provenance.
Use the [operating procedure](../docs/contracts/agent-rollout.md) for selection,
assignment, recovery and rollback, including the post-S7 default override.

Initializer `--control-revision 1.1` explicitly selects exact
assignments and recoverable registration. The initializer default is `1.2`;
`--control-revision 1.0` explicitly selects legacy new-run behavior.
`role-boundary start --artifact KEY --input-ref FILE` binds the derived next
version, mandatory inputs and optional additional local inputs. Use the returned
`submission_path` exactly; only that file and the selected Verifier's invocation
probe directory are permitted. `--input-ref` may be repeated or omitted; it
does not replace mandatory inputs.

Call existing `finalize-semantic-return` with the assignment's role, invocation,
baseline, source path and mandatory `--expected-source-sha256`. It compares
captured bytes with the expected identity, audits the write, validates input
currency and body, then registers a receipt with the canonical reference.
Selected `persist-artifact` is rejected. Legacy finalization remains supported;
an explicitly supplied expected digest is checked there too.

If registration is interrupted, reissue the same finalization request. A matching
committed request returns its receipt with `replayed: true`; `is_current: false`
means the artifact was subsequently superseded. Recovery never reactivates it.
A recovered pre-commit attempt restores prior bytes and reports rollback;
reissue only after inspecting that result to prepare a fresh attempt. Unknown
state/target changes block recovery. Pending journals block unrelated writers.
Retain submissions, boundary evidence, journals and history; do not strip the
selector or use an old checkout to recover a selected run.

Selected runs retain each terminal verification result in
`control.latest_verification_result`. The initial result consumes no round.
Before changing a verified subject, use `update-state --to-stage repair` with
`--failure-ref verification-report@N` identifying the latest result and
`--evidence-ref BB-NNN` for each applicable recorded modification request.
One `repair.rounds` record reserves one slot in `repair.active_attempt`.
Several issues or combined contract/code changes share that slot. Resume it
after interruption; a fresh terminal report completes it without another
increment. Completed release remains immutable. A prior PASS may enter repair
before completed release, preserving its verdict but invalidating release
authority until independent re-verification.

Evidence-only recovery requires an attributable unchanged contract, packaged
source and archive. Unknown subject identity is not equality. Recovery cannot
hide contract/source drift or substitute an old report for a fresh verdict.
Post-verification brief/contract assignments require an in-progress round.

Four rounds are initially available. A passing fourth result can proceed
through ordinary gates; a fifth modification cannot start automatically.
Create a `REPAIR_LIMIT_EXHAUSTED` bounce-back with the exact exhausted result.
The command derives `round_review_basis`. Use the existing independent Verifier
as a separate process reviewer with
`role-boundary start --review-event BB-NNN` instead of `--artifact`.
Only its assigned `round-review.json` is writable; this does not activate a
product verification report. Finish the audit before requesting user approval.

After evidence-only recovery, the latest report must have an authenticated
unchanged-subject lineage to the exhausted round's original result; see the
[S3 recovery clarification](../docs/contracts/round-recovery-clarification.md).
The completed round's original result is never rewritten.

A bounded recommendation records `schema_version: "1.0"`,
`artifact_type: iteration-threshold-review`, `run_id`, `reviewer_role`,
`reviewer_invocation_ref`, exact `basis`, `recommendation: BOUNDED_CONTINUATION`,
positive integer `additional_rounds`, `unresolved_issues`, `observed_progress`,
`likely_causes`, `evidence_refs`, `proposed_changed_approach`, and
`intent_impact: UNCHANGED`. A recommendation alone grants no allowance.

Retain the user's actual affirmative response in approval JSON with
`schema_version: "1.0"`, `artifact_type: iteration-continuation-approval`,
`run_id`, `user_role: user`, `response`, `decision: APPROVE`, timezone-aware
`timestamp`, `review_path`, `review_sha256`, exact `basis`, `additional_rounds`,
`proposed_changed_approach`, and `intent_impact: UNCHANGED`. The amount and
approach must match the review. Root cannot manufacture this evidence from
silence or its own paraphrase. Attribution uses the trusted local model;
the JSON is not cryptographic human authentication.

Resolve the event through `update-bounce-back`, using `USER_DECIDED`,
`resolved_by: user`, decision/evidence references and changed retry basis.
Add `continuation` with `review_path`, `review_sha256`, `review_invocation_ref`,
`boundary_evidence_ref`, `approval_path`, `approval_sha256`, `additional_rounds`
and `new_maximum_attempts`. The command checks provenance and unchanged subject,
then atomically adds the approved allowance while retaining every prior round.
Identical resolution replay cannot add it twice. Missing, stale, denied or
intent-changing authorization does not raise the ceiling.

S7 publishes selected operation after integrated role and rollout review. Verify
effective role loading and exact-file permission in the operating installation;
static configuration alone is insufficient. Models, reasoning, independence and
delegation boundaries remain unchanged, and unbound role selection grants no
write permission. Retain a compatible installation before procedure-byte updates
or rollback. Recover interrupted work against original paths, then obtain fresh
owner bindings before forward use. Never rewrite prior evidence or receipts.
No existing-run migration, framework/product release, baseline promotion or
additional-round permission follows from S7 or the default override. Existing
legacy runs keep `1.0`; new runs default to `1.2`.

## Intent realization compatibility (2026-09-09)

New initialized runs record `control.intent_realization: "1.0"`. The owner of
`problem_frame` is then `intent_realizer`; unmarked legacy runs keep
`problem_framer`. Unsupported or null markers fail validation. The `framing`
stage, artifact ID, headings and `10_framing/problem_frame.md` path are unchanged.
Role-boundary start, persistence/finalization and active-identity validation use
the run-selected owner. Under legacy boundary control both roles are read-only;
selected `1.1`/`1.2` grants only the current Realizer's assigned submission file.
The roles are not interchangeable.
Historical examples below keep their original owner; use `--role intent_realizer`
for this artifact in newly initialized runs. Do not relabel completed evidence.

The new role discovers missing realization conditions; contractor separately
challenges those proposals and authors requirements/acceptance. Root coordinates
decisions and writes source. This is not a new observability/reproduction system;
existing deterministic release safeguards remain in place. The original
2026-09-09 revision record was already absent before the two-workflow revision;
its preserved deletion, completed checks and limits are documented in
[the two-workflow review (source history)](../docs/provenance.md).

## Entry Point and Requirements

### Two-workflow control revision — TW-20260913, 2026-09-13

S7 compatibility annotation (2026-11-01): this retained revision account describes
the legacy two-attempt repair path. Selected `1.1`/`1.2` instead uses the
Root-owned round controls above, including authorized repair after a PASS before
completed release. No historical evidence or legacy allowance is changed.

Trigger: practical product revisions motivated separate intent preparation and
implementation intake. `workflow.py` now derives direct B solely from canonical
`build_request.handoff.next_stage: contract` with a bound request identity. A's
prepared run resumes at Contractor; direct B keeps unused framing PENDING/null.
Contextual validation, transitions, semantic adoption, exact-baseline resolution
and verifier preparation share this route. State-only validation stays strict.

New requests are hash-bound on initialization. New contracts name consumed request
and applicable brief versions/hashes; declared local intent/delegation snapshots
are checked. Stale sources block adoption/progression while intermediate owner
correction remains possible. Captured returned bytes are parsed, validated and
persisted consistently. Existing unbound runs retain their interface and owners.

A recorded exact-report bounce-back can reopen prior verification PASS before
completed release. It sets verification IN_PROGRESS and incomplete release PENDING,
retains the old candidate basis, and requires a fresh independent verdict. A
contract/candidate change requires normal failed/blocked verification → repair;
that transition clears the binding and increments the unchanged maximum of two.
Completed release cannot reopen. No new agent, harness, status enum or repair credit.

Before completed release, candidate reconciliation also compares packaged canonical
source entries with existing manifest hashes/sizes through the same source check
used by verifier preparation. Completed baseline validation keeps its immutable
archive basis: live source changes for a subsequent revision do not invalidate
the old release. Non-packaged additions are outside this source-inventory check.

Principal components: workflow/state/validation, semantic finalization, initializer,
boundary and harness inputs, revision resolution, skills/configs and routing docs.
Compatibility and migration: no rewrite of historical runs; direct B is explicit
for newly bound requests. Operational commands are in the
[gate map](../../../.agents/skills/build-tool-pipeline/references/gate-map.md).
Completed regression/trial evidence and known limitations are recorded in the
[authoritative revision review (source history)](../docs/provenance.md).
The earlier intent-realization record mentioned above was already deleted in the
user's working tree; this revision preserves that deletion and does not restore
or silently rewrite its historical claims.

Run these command examples from `tools/intent-tool-pipeline/` using the Nexus_AI root virtual environment:

```powershell
..\..\.venv\Scripts\python.exe pipeline_ops.py -h
```

Python 3.11 or later and PyYAML are required. PyYAML is already pinned in the repository `requirements.txt`.

Every subcommand supports `-h` and `--help`. Relative paths are resolved from `--project-root`, whose default is the installed tool directory, independent of the current directory. Resolved inputs and outputs may not escape that root.

## Output and Exit Contract

Human-readable output is the default. Add `--format json` before the subcommand for stable machine-readable fields:

```powershell
..\..\.venv\Scripts\python.exe pipeline_ops.py --format json validate-contract `
  --contract workspace/build_runs/<run_id>/20_contract/product_contract.yaml
```

The JSON object always contains:

- `command`: selected operation;
- `ok`: overall deterministic result;
- `diagnostics`: sorted objects with `code`, `path`, and `message`;
- `data`: successful output metadata or retained failure-result metadata.

Exit code `0` means the requested deterministic check or operation passed. Exit code `1` means a validation, gate, test, packaging, or inspection failure. Argument-parser usage errors exit `2`.

## Fixed Run Hierarchy

The framework hierarchy remains fixed and is not configurable through a test or package plan:

```text
workspace/build_runs/<project_id>/
  00_intake/build_request.yaml
  10_framing/problem_frame.md
  20_contract/product_contract.yaml
  30_execution/run_state.json
  30_execution/test_results.json       # active summary generated by run-tests
  30_execution/test_attempts/<attempt-id>/test_results.json
  30_execution/role_boundary/           # mutation baselines, results, and latest-role status
  30_execution/semantic_finalize/failed_attempts/<attempt-id>.json
  40_verification/verification_report.md
  40_verification/probes/               # only semantic-agent write allowance (verifier)
  40_verification/harness/attempts/<attempt-id>/
  40_verification/harness/cleanup/<attempt-id>.json
  40_verification/harness/latest.json
  50_release/release_manifest.json      # generated by package when configured here
  50_release/package_inspection.json    # PENDING after package; PASS/FAIL after inspection
```

Test attempts, boundary/finalize records, harness attempts, cleanup records, and release evidence are durable deterministic outputs. Verification command workspaces instead use a bounded short-lived OS temporary namespace. None of these files adds a semantic owner or replaces the five artifact-contract 1.0 coordination artifacts.

## Revision Initialization

The build-tool initializer accepts ordinary fresh requests unchanged. A bounded revision instead uses `project.request_kind: REVISION` and must provide `revision_of` with the baseline run, archive, active contract, and active verification-report references/hashes plus `delta_request` with `scope_classification: BOUNDED`, `DELTA-*` changes, `NONCHANGE-*` claims, and `FEEDBACK-*` evidence.

Before it creates a run directory, the initializer resolves exactly one completed run and requires release and verification gates `PASSED`, a `READY` report with every requirement `PASS`, the same target repository, and a complete verification-time contract/manifest/inspection/archive binding. A broad, incompatible, ambiguous, missing, unverified, or hash-drifted request returns `FRESH_REQUIRED`; callers must author an explicit fresh non-revision request rather than silently changing modes. Revision state records only the immediate immutable baseline identity, not recursive lineage.

## Commands

### `validate-run`

```powershell
..\..\.venv\Scripts\python.exe pipeline_ops.py validate-run `
  --run-dir workspace/build_runs/<run_id>
```

Checks the six fixed stage directories, required artifacts for the recorded stage, common metadata, supported schema major version, active artifact ID/version/path/hash/provenance agreement (including the run-state artifact's self-version), matching role-boundary PASS evidence, Markdown heading order, run-state namespaces, gate evidence, bounce-back provenance, repair limits, blocker/approval consistency, contract traceability, verification coverage, release reconciliation, and false READY/release claims. For `REVISION` runs it also re-resolves the exact completed baseline and rejects missing or hash-drifted contract, report, manifest, inspection, or archive evidence. Once a revision contract is active, it verifies exact unchanged requirement bundles and complete, disjoint baseline/current impact coverage.

An early-stage run may leave downstream active artifact references null. `IN_PROGRESS` is the normal registration window for framing, contract, and verification: the owning artifact may be null before `finalize-semantic-return` and active afterward. Terminal `PASSED`, `FAILED`, or `BLOCKED` semantic stages require their corresponding active artifact. Release consumes the already registered verification report and therefore requires it as soon as release is non-pending.

### `validate-contract`

```powershell
..\..\.venv\Scripts\python.exe pipeline_ops.py validate-contract `
  --contract workspace/build_runs/<run_id>/20_contract/product_contract.yaml
```

Accepts YAML, YML, or JSON. It validates artifact-contract 1.x common fields, readiness, product and scope structures, stable `REQ-###` and `ACC-###` IDs, uniqueness, required acceptance fields, two-way requirement/acceptance mappings, the all-applicable verification policy, optional declared counts/sets, resolved LLM-judgment references, linked judgment criteria, and the optional structural shape of `revision_control`. Cross-artifact baseline identity and impact coverage are enforced by `validate-run` because they require the active request, run state, and baseline files.

This is structural validation. It cannot decide whether prose captures the user's intent or whether an acceptance procedure is semantically adequate.

### `update-state`

```powershell
..\..\.venv\Scripts\python.exe pipeline_ops.py update-state `
  --run-dir workspace/build_runs/<run_id> `
  --to-stage framing `
  --stage-status IN_PROGRESS `
  --gate-status IN_PROGRESS `
  --rationale "Framing started from the active request." `
  --next-action "Produce and validate problem_frame.md."
```

The command validates the existing state, checks the transition, updates the target stage and gate, increments the run-state artifact version, sets `updated_at`, and atomically replaces `run_state.json`. If any check fails, the state file is unchanged.

Normal progression is:

```text
intake -> framing -> contract -> repository_analysis -> implementation -> verification -> release
                                                               verification -> repair -> verification
```

Important controls:

- Normal advancement requires the current stage and gate to be `PASSED`.
- A semantic stage cannot be recorded as `PASSED`, or used as an advancement prerequisite, unless its owning artifact carries the required machine-readable readiness result: intake handoff `PASS`, framing completion `PASS`, contract readiness `PASS`, or verification overall `READY`.
- These checks enforce the declared result; deciding whether the supporting prose deserves that result remains semantic work.
- Under legacy control, `verification -> repair` requires verification `FAILED` or `BLOCKED`, `--failure-ref`, and an available repair attempt; entering repair increments `active_attempt`. Selected control also permits a prior PASS before completed release on an attributable authorized modification request, reserving one round as described above.
- `repair -> verification` requires a resolved implementation-defect or contract-contradiction bounce-back with an allowed retry and non-empty change basis.
- A `PASSED` gate requires one or more `--evidence-ref` values.
- A stage cannot pass while an applicable blocking record or pending approval remains.
- Entering release requires `verification` and its gate to pass plus `30_execution/test_results.json` status `PASS`.
- Passing release additionally requires `50_release/package_inspection.json` status `PASS`.
- New run-state `1.1` records capture the active verification-report identity when verification passes. When the inspected candidate is present, the identity also binds the active contract, manifest, inspection, and archive paths and SHA-256 values. Release entry and PASS reconcile the current bytes to that identity; only a complete binding is eligible as a future delta baseline.

`--timestamp` is an active runtime control intended for reproducible fixtures and attributable orchestration timestamps. If omitted, the current UTC time is used. `--failure-ref` is active only when entering repair.

### `update-bounce-back`

Use this command instead of editing `run_state.json.bounce_back_events` directly. It validates the current state, constructs the changed state in memory, validates the complete candidate, increments both run-state version fields, and atomically replaces the live file only after validation succeeds. A rejected payload leaves the existing file unchanged.

Create an open event:

```powershell
..\..\.venv\Scripts\python.exe pipeline_ops.py update-bounce-back `
  --run-dir workspace/build_runs/<run_id> `
  --action create `
  --payload workspace/artifacts/<domain>/bounce_back_create.yaml
```

The create payload contains the semantic event fields but not `id`, `created_at`, `status`, `resolution`, `retry.allowed`, or `retry.change_basis`; the command owns those control fields:

```yaml
origin:
  role: independent_verifier
  invocation_ref: verifier-attempt-1
  result_artifact_ref: verification-report@1
  result: NOT_READY
assigned_to: root_codex
classification: IMPLEMENTATION_DEFECT
summary: The implementation failed one or more contract requirements.
affected_stages: [verification, repair]
affected_refs: [REQ-001]
required_resolution: Repair the named defect and regenerate attributable evidence.
retry:
  agent_role: independent_verifier
  prior_invocation_ref: verifier-attempt-1
```

Resolve an existing open event:

```powershell
..\..\.venv\Scripts\python.exe pipeline_ops.py update-bounce-back `
  --run-dir workspace/build_runs/<run_id> `
  --action resolve `
  --payload workspace/artifacts/<domain>/bounce_back_resolve.yaml
```

```yaml
event_id: BB-001
resolved_by: root_codex
resolution_type: IMPLEMENTATION_REPAIRED
summary: The named defect was repaired and attributable evidence was regenerated.
changed_artifact_refs: [source-tree@2]
decision_refs: []
evidence_refs: [test-results@2, package-inspection@2]
retry:
  allowed: true
  change_basis: [IMPLEMENTATION_CHANGED, EVIDENCE_CHANGED]
```

Create always assigns the next `BB-###` identifier and produces an `OPEN` event with retry disabled. Resolve accepts only an existing `OPEN` event. A resolved retry may be enabled only with an allowed non-empty change basis. `--timestamp` is optional and otherwise defaults to the current UTC time.

### `role-boundary`

Start the audit immediately before a semantic/read-only role invocation. This
example uses legacy boundary control `1.0`; selected artifact/review invocations
require the assignment arguments and exact scopes described above:

```powershell
..\..\.venv\Scripts\python.exe pipeline_ops.py --format json role-boundary start `
  --run-dir workspace/build_runs/<run_id> `
  --role independent_verifier `
  --invocation-ref verifier-attempt-1
```

Retain `data.baseline_sha256`, invoke the role serially, and finish with the same role/reference:

```powershell
..\..\.venv\Scripts\python.exe pipeline_ops.py --format json role-boundary finish `
  --run-dir workspace/build_runs/<run_id> `
  --role independent_verifier `
  --invocation-ref verifier-attempt-1 `
  --baseline-sha256 <start-result-sha256>
```

Policies are derived from role and selected invocation and classified as `PROTECTED`, `ALLOWED_DURABLE`, `ALLOWED_EPHEMERAL`, or `EXCLUDED_BY_POLICY`. Under legacy control, `problem_framer`, `product_contract_agent`, and `explorer` have no run write allowance; `independent_verifier` may write only ephemeral `40_verification/probes/**`. Selected control adds only the assigned noncanonical file and the Verifier's exact invocation probe scope; process review permits only its exact review file. Protected files retain SHA-256/size/mode, while allowed roots retain root and reparse identity without recursively hashing ordinary descendants. The diff still detects protected create, content modification/overwrite, truncation, delete, and rename. A reparse path under an allowed root must resolve inside that root, and protected disappearance or unreadability fails the audit. Ephemeral descendant churn is permitted. Legacy baselines without the explicit path-policy block remain finish-compatible.

`finish` writes immutable per-invocation evidence plus a latest-result index. Unauthorized mutation returns `BOUNDARY_VIOLATION`, and if the invocation changed/deleted `run_state.json`, the command restores its exact baseline bytes before returning. `update-state` refuses PASS or advancement while any role's latest result is a violation. Contain the filesystem changes and run a new audited invocation with a new reference; a later PASS supersedes that role's latest status without deleting the original violation evidence.

The baseline file is hash-bound through the value returned by `start`. This is a deterministic accidental/instruction-failure control for the trusted, serial, local operating model, not an adversarial tamper-proof audit store or OS permission sandbox.

### `finalize-semantic-return`

This is the activation path after `role-boundary start` and completion of the
semantic body. The example shows legacy returned-body transport; selected calls
use the exact assigned source and mandatory `--expected-source-sha256` above:

```powershell
..\..\.venv\Scripts\python.exe pipeline_ops.py --format json finalize-semantic-return `
  --run-dir workspace/build_runs/<run_id> `
  --artifact product_contract `
  --role product_contract_agent `
  --invocation-ref contract-attempt-1 `
  --baseline-sha256 <start-result-sha256> `
  --source workspace/artifacts/<domain>/product_contract.returned.yaml
```

The command preflights source containment, role ownership, and semantic structure; finishes the matching mutation audit; archives an existing canonical version; atomically writes and activates the exact returned bytes; and validates the complete run. Any artifact, state, or post-validation failure restores the prior canonical bytes and run state. Structured failures are retained under `30_execution/semantic_finalize/failed_attempts/`. Invalid semantic content is rejected, never repaired or reinterpreted by the command.

### `persist-artifact` (legacy compatibility composition)

For legacy control only, after a matching boundary PASS, Root stores the semantic role's complete returned body at a separate repository path and runs. Selected control rejects this command:

```powershell
..\..\.venv\Scripts\python.exe pipeline_ops.py --format json persist-artifact `
  --run-dir workspace/build_runs/<run_id> `
  --artifact verification_report `
  --source workspace/artifacts/<domain>/verification_report.returned.md `
  --source-invocation-ref verifier-attempt-1 `
  --boundary-evidence-ref workspace/build_runs/<run_id>/30_execution/role_boundary/results/<audit-id>.json
```

Supported artifact keys are `problem_frame`, `product_contract`, and `verification_report`. The source must not be the canonical active path. The command requires a new boundary-control run, a latest matching boundary PASS, the expected artifact ID, complete structural validity, and exact next version. It archives an existing active version, writes a same-directory temporary payload, verifies SHA-256, atomically replaces the canonical file, then atomically activates version/path/hash/semantic owner/Root persistence owner/source invocation/boundary evidence in `run_state.json`. If state activation or post-validation fails, it attempts bounded restoration of the prior state and canonical bytes.

Registration is a normal semantic-stage lifecycle transition, not a validation exception. Before registration, an owning stage may be `IN_PROGRESS` with a null active reference. The command validates that pre-state, constructs the complete registered candidate state, validates it under the same run invariants, and only then commits the canonical bytes and active reference. A terminal semantic stage can never rely on an unregistered document.

Filesystem presence alone never activates a semantic artifact. `role-boundary finish` plus `persist-artifact` remains available for legacy orchestration and diagnostics; selected control rejects `persist-artifact`. New runs should use `finalize-semantic-return` so audit completion and activation cannot be misordered. Existing completed run-state `1.0` records remain readable but are not implicitly upgraded; new initializations use run-state `1.1` and this activation protocol.

### `run-tests`

```powershell
..\..\.venv\Scripts\python.exe pipeline_ops.py run-tests `
  --run-dir workspace/build_runs/<run_id> `
  --plan pipeline_control/examples/test_plan.yaml `
  --attempt-id implementation-1
```

The plan defines one or more commands as argument arrays. Commands use `shell=False`; shell operators, expansion, and quoting are not interpreted. Every command runs even if an earlier command fails. Return codes, stdout, stderr, timeouts, and per-command status are retained in `30_execution/test_results.json` by default.

Test-plan fields:

- `schema_version`: supported plan major; currently `1.x`.
- `commands`: ordered, non-empty command list.
- `commands[].id`: unique evidence identifier.
- `commands[].argv`: executable and arguments as separate strings; active runtime control.
- `commands[].cwd`: repository-relative working directory; active runtime control, default `.`.
- `commands[].timeout_seconds`: positive timeout up to 3600; active runtime control, default 300.
- `commands[].expected_exit_codes`: accepted integer codes; active runtime control, default `[0]`.
- `commands[].artifact_paths`: required repository-relative list of command-attributed outputs or inputs. Files retain existence, size, and SHA-256; directories retain existence, entry inventory, and a tree SHA-256. An empty list is allowed only when the command has no attributable artifact.

Each execution first writes an immutable `30_execution/test_attempts/<attempt-id>/test_results.json`, then updates the canonical `30_execution/test_results.json` active summary. Attempt IDs cannot be reused, and a later pass never overwrites a superseded failure. The evidence retains its repository-relative `result_path`, `attempt_path`, `plan_path`, and `plan_sha256`, in addition to command, return code, stdout, stderr, timeout state, result, and artifact snapshots; the canonical summary also records the immutable attempt SHA-256. Consumers reject moved result evidence or a plan whose current hash no longer matches the recorded hash.

`--output` changes only the test-result location. Release gating and `package` use the fixed default `30_execution/test_results.json`, so alternate output is suitable for diagnostics but does not satisfy those gates. `--timestamp` affects evidence metadata only.

### `package`

```powershell
..\..\.venv\Scripts\python.exe pipeline_ops.py package `
  --run-dir workspace/build_runs/<run_id> `
  --spec pipeline_control/examples/package_spec.yaml
```

Packaging requires default-path test results with status `PASS`. It selects only files matched by the explicit include list, removes prohibited files, confirms every required file, writes one fixed archive root, normalizes ZIP timestamps and permissions, sorts entries, computes per-file and archive SHA-256 values, and writes the release manifest.

After creating or replacing the archive, it writes `package_inspection.json` with `PENDING`. This prevents a prior inspection from authorizing a newly packaged archive.

Package-spec fields:

- `schema_version`: supported package-spec major; currently `1.x`.
- `source_root`: repository-relative maintained source directory; active runtime control.
- `artifact_root`: the single top-level archive directory name; active runtime control.
- `archive_path`: repository-relative ZIP output path; active runtime control.
- `manifest_path`: repository-relative manifest output path; active runtime control.
- `include`: explicit source-relative file or directory glob list; active runtime control.
- `required`: exact source-relative files that must survive selection; active runtime control.
- `approval.contract_ref`: active product-contract artifact reference; it must match `run_state.json`.
- `approval.decision_refs`: non-empty list of decisions that must exist with status `APPROVED` in the active contract.
- `approval.required_roles`: exact mandatory role map `readme`, `source`, `tests`, and `examples`. Every role must contain at least one non-overlapping path, every path must also be listed in `required`, and path shape is checked against its role.
- `exclude`: optional additional source-relative prohibited patterns; active runtime control.

Archive and manifest paths must remain outside `source_root`. Symlinks are rejected. The default prohibited policy covers `pytest-cache-files-*`, `__pycache__`, `.pytest_cache`, bytecode, Excel workbooks, common temporary files, and desktop metadata. Excel exclusions are global at every depth.

### `inspect-package`

```powershell
..\..\.venv\Scripts\python.exe pipeline_ops.py inspect-package `
  --run-dir workspace/build_runs/<run_id> `
  --manifest workspace/build_runs/<run_id>/50_release/release_manifest.json
```

The command reads the archive named by the manifest unless `--archive` supplies an override. It verifies archive SHA-256, exact manifest inventory, every entry hash and size, required entries, one declared root, safe paths, entry count, and prohibited-content policy. The result is written to `50_release/package_inspection.json` unless `--output` is provided.

An alternate archive or output is useful for diagnostics. Release transition enforcement reads only the fixed default inspection location.

### `prepare-verification`

Run this after `package` and a passing fixed-path `inspect-package`, before invoking the independent verifier:

```powershell
..\..\.venv\Scripts\python.exe pipeline_ops.py prepare-verification `
  --run-dir workspace/build_runs/<run_id> `
  --plan pipeline_control/examples/verifier_plan.yaml `
  --attempt-id verifier-1
```

The shell-free plan binds the active contract, release manifest, package inspection, and exact archive by path and SHA-256. The harness rejects unsafe or mismatched ZIPs, explicit command arguments that depend on repository paths outside the extracted package or its isolated temp/output roots, repository-valued inherited environment entries, and an explicit repository-root literal in the package-local entrypoint that will actually execute. Recognized Python commands additionally receive a per-command CPython filesystem audit guard; disabled or missing activation, or a guarded external read, fails closed and is recorded in `python_audit_status`. The harness extracts once into a bounded short scratch namespace, runs every declared scenario and complete-suite repetition against that same extraction with isolated temp/environment directories, and compares the complete canonical source tree plus the active semantic/state/package identities before and after each command. Package or protected-input mutation fails the attempt. Immutable attempt evidence is promoted before scratch removal, and cleanup/latest evidence is still written if promotion or cleanup fails. Cached output never counts as a repeatability execution.

Before the independent verifier is invoked, a null current verification report is expected and does not block `prepare-verification`. The active build request, problem frame, product contract, run state, canonical source, manifest, inspection, and archive remain mandatory protected inputs. If an already active verification report exists during a later preparation attempt, the harness protects its exact identity; malformed non-null report entries and report mutations fail closed.

Harness success is deterministic evidence only: every result declares `independent_verifier_judgment: NOT_PERFORMED`. The independent verifier must still inspect the exact candidate and may reject the supplied evidence. Additional probes are confined to legacy `40_verification/probes/**` or, for selected control, only its assigned `40_verification/probes/<audit-id>/` directory.

## Example Configuration

- `examples/test_plan.yaml` shows the full executable test-plan framework.
- `examples/package_spec.yaml` shows the full package-spec framework.
- `examples/verifier_plan.yaml` shows the exact-candidate verifier harness contract.

Edit paths and command arguments for the active run. The examples are documentation inputs and are not automatically discovered or executed.

## Safety and Ownership

- All paths are constrained to `--project-root`.
- State writes and JSON evidence writes use same-directory atomic replacement.
- Test commands never use a shell.
- Package selection does not follow symlinks.
- Packaging cannot run after failed or missing tests.
- Release cannot pass after failed/missing tests or without a matching successful archive inspection.
- A semantic-agent boundary violation prevents activation and pipeline progression; direct changes to an active artifact are detected by its recorded SHA-256.
- Release reconciles the verification-report bytes and the exact contract, manifest, inspection, and archive candidate binding captured when verification passed.
- Revision mode re-resolves one exact release-passed, independently verified candidate and never inherits recursive lineage.
- No control-plane module imports or calls an LLM or agent runtime.

Producing semantic readiness judgments, external-model authorization, product decisions, verifier conclusions, and user phase approval remains outside these utilities. Once an owning artifact records one of those results, the control plane deterministically enforces its status and reference integrity.

## Migration and Superseded Context

Preserve older engineering/UX handoffs and refer to them descriptively as `SUPERSEDED_CONTEXT`; do not overwrite or promote them into canonical artifacts. That label is not a `source_context.authority` enum: use `REFERENCE_ONLY` unless explicit approval grants stronger authority. Start a new fixed-layout run and reference the old file from its build request instead of copying legacy root-level state or ad hoc frames into active paths.

Completed run-state `1.0`/`1.1` files remain read-compatible and are not auto-upgraded. Existing `role-boundary finish` and `persist-artifact` commands remain available, legacy boundary baselines without `path_policy` use compatibility handling, and old test results are not backfilled with attempts. A historical release without a complete `candidate_binding` remains readable but cannot seed delta mode; an explicit fresh request is required.

## Limitations and Deferred Work

- Only artifact-contract and utility-plan major version `1` are supported.
- Validation is imperative rather than published JSON Schema; schema migration tooling remains deferred until observed need.
- Markdown validation checks structure, metadata, requirement result coverage, and readiness consistency, not prose quality.
- The ZIP writer packages regular files with normalized read permissions; preservation of executable mode bits, empty directories, and symlinks is intentionally unsupported.
- Concurrent writers to one `run_state.json` are not coordinated beyond atomic replacement; Phase 5 orchestration must retain one state owner.
- The tool does not invoke roles, author semantic conclusions, create bounce-back resolutions, or create user approvals. `finalize-semantic-return` validates and registers the complete supplied bytes without changing their conclusion: selected calls use the role-authored assigned file and expected digest; legacy calls use Root's unchanged copy of the returned body. `prepare-verification` is not verifier judgment.
- Per-agent OS write denial, adversarial tamper resistance, concurrent multi-writer transactions, process/container isolation, RBAC, and cryptographic signing remain outside this local trusted-agent revision.
- Verifier-harness dependency controls inspect argv, inherited environment values, and the executed package entrypoint; recognized Python commands also use CPython audit events. This is not an OS sandbox: native/`ctypes` access and non-Python code that computes or decodes an external path without exposing it through argv, environment, or the entrypoint literal remain outside complete containment, as does network isolation. Protected-input writes are still detected by the identity guard.
- Delta mode trusts the caller's explicit `scope_classification: BOUNDED`; target and provenance/hash disagreements still deterministically return `FRESH_REQUIRED` before run creation.
- Read-valid historical runs without a complete verification `candidate_binding` are not eligible delta baselines.

## Verification

Run the maintained suite with a repository-local pytest temporary root on this Windows workspace:

```powershell
..\..\.venv\Scripts\python.exe -m pytest tests -q `
  --basetemp=test_workspace\framework_boost_full
```

The suite covers valid and invalid command fixtures, optimized path-policy boundaries, protected and reparse mutations, ephemeral churn, semantic finalize success and rollback injection, immutable test attempts, exact verifier-harness binding and cleanup, revision baseline drift and impact coverage, release reconciliation, legacy reads, allowed and rejected transitions, deterministic packaging, agent/skill contract parity, subcommand help, JSON diagnostics, and absence of LLM/agent calls.

## Revision History

### 1.0.0 — 2026-08-15 — Immutable baseline

- Source request: explicit user request to execute framework development Phase 4,
  governed by the now-retained
  `workspace/framework_development/history/legacy/Frame_work_develope.md`, artifact
  contract `1.0`, and the approved Phase 3 completion baseline.
- Objective: establish deterministic structural gates, state management, test execution, packaging, and package inspection without LLM execution behavior.
- Initial interfaces: `pipeline_ops.py` with `validate-run`, `validate-contract`, `update-state`, `run-tests`, `package`, and `inspect-package`.
- Initial outputs: atomic `run_state.json` updates, `test_results.json`, deterministic ZIP archive, `release_manifest.json`, and `package_inspection.json`.
- Initial source: `pipeline_control/`, `pipeline_ops.py`, examples, and `tests/test_pipeline_control.py`.
- Assumptions: artifact contract major version 1 remains authoritative; Root remains the single orchestration/state owner; semantic verification and user approval remain separate.

### 1.0.1 — 2026-08-16 — Phase 4 review repair

- Trigger: user review asked whether deterministic checks had been fully extracted, whether state was an enforcement mechanism rather than a log, and whether test evidence was independently reusable; the user then approved repair.
- Behavioral differences: stage advancement and stage PASS now require the owning artifact's declared readiness; run-state self-version is synchronized and validated; package specs require contract-bound approval plus mandatory README/source/tests/examples roles; test evidence records its own path, plan hash, and command-attributed artifact snapshots.
- Main files changed: `validation.py`, `state.py`, `packaging.py`, `test_runner.py`, `evidence.py`, both example plans, the maintained tests, and this README.
- Compatibility: package specifications and test plans written for 1.0.0 must add `approval` and `artifact_paths`; previously emitted test evidence lacks the new attribution fields and cannot satisfy current release/package gates.
- Verification: 24 maintained tests passed, including blocked-contract transition rejection, omitted-README-role rejection, unapproved-decision rejection, run-state self-version synchronization, retained evidence attribution, moved-result rejection, and changed-plan rejection. Python compilation and the active Phase 3 contract validation passed; the historical Phase 3 run still fails only for its already-recorded missing `50_release/` directory.

### 1.1.0 — 2026-08-26 — Semantic-role persistence boundary control

- Trigger: Phase 6 Pilot B revise exposed that an `independent_verifier` could write the canonical active report even though the ownership contract made Root the persistence owner.
- Behavioral differences: new runs use run-state `1.1`; `role-boundary start/finish` records deterministic run mutations and blocks progression after violations; `persist-artifact` is the Root-only semantic activation path; active semantic artifacts carry SHA-256 and provenance; verification PASS captures release-reconciliation identity.
- Main files changed: `boundary.py`, `artifacts.py`, `io_utils.py`, `validation.py`, `state.py`, `cli.py`, the initializer, maintained tests, skill/gate instructions, artifact-contract documents, and this README.
- Compatibility: existing completed run-state `1.0` artifacts retain read validation and are not implicitly migrated. New controls do not add RBAC, sandboxing, signing, generalized transactions, or multi-user security behavior.
- Verification: see the Phase 6 semantic-boundary revision note for the final maintained-suite result and the host-specific symlink fixture status.

### 1.1.1 — 2026-08-31 — Semantic document registration lifecycle repair

- Trigger: the first governed transient-PSIJ revision followed the documented `framing IN_PROGRESS` sequence and exposed a bootstrap deadlock: run validation required an active problem frame before `persist-artifact` could register it. The same run also exposed drift between the problem-framer developer output contract and the validator's required headings.
- Behavioral differences: framing, contract, and verification now treat `IN_PROGRESS` as the normal document-registration window; terminal semantic states still require their active artifact. The problem-framer contract now includes `Contract Metadata` and `Decisions` in the validator-defined order.
- Compatibility: no artifact shape or schema version changes. Existing valid run-state `1.0` and `1.1` records remain valid, terminal gates are not weakened, and provenance, boundary, hash, rollback, and release reconciliation controls remain mandatory.
- Verification: maintained control-plane, agent-contract parity, pipeline-skill, and full framework regression tests cover pre-registration `IN_PROGRESS`, atomic registration, terminal artifact requirements, and heading-order parity.

### 1.2.0 — 2026-09-01 — Pipeline boost-up

- Trigger and source request: implement `workspace/framework_development/pipeline_boostup_plan_20260901.md` step by step without weakening semantic ownership, deterministic gates, independent verification, exact candidate identity, repeatability, or release reconciliation.
- Behavioral differences: boundary evidence now uses explicit path policies and bounded verifier scratch; `prepare-verification` reconciles and extracts one inspected candidate, records immutable execution/cleanup evidence, guards canonical inputs, rejects undeclared repository dependencies through argv/environment/entrypoint controls and fail-closed CPython auditing, and leaves judgment `NOT_PERFORMED`; `finalize-semantic-return` atomically validates, archives, writes, activates, validates, journals, and rolls back semantic returns; exact-baseline `REVISION` initialization and validation now enforce full completed-run provenance, complete current impact coverage, cycle rejection, and contract/manifest/inspection/archive drift reconciliation through release.
- Principal components: `boundary.py`, `scratch.py`, `verifier_harness.py`, `artifacts.py`, `revision.py`, `validation.py`, `state.py`, `io_utils.py`, `cli.py`, `test_runner.py`, the run initializer, artifact-contract templates, semantic role contracts, build-pipeline guidance, and maintained regression tests.
- Compatibility and migration: run-state `1.0` and `1.1` reads and the individual boundary/persistence commands remain supported. Historical releases without a complete verification-time `candidate_binding` remain readable but cannot seed delta mode. Earlier handoffs remain `SUPERSEDED_CONTEXT`, not active artifacts. Verification plans that relied on undeclared repository files, repository-valued inherited environment entries, or Python audit-disable flags now fail and must package or explicitly model their required inputs.
- Verification and independent review: Root's final fresh full suite passed `164 passed, 3 skipped`; focused harness passed `55 passed, 1 skipped`; documentation/role parity passed. Independent Round 2 passed seven dependency probes, `55 passed, 1 skipped` harness tests, `58 passed, 1 skipped` cross-workstream/parity tests, and the full `164 passed, 3 skipped` suite, and returned `READY`. The duplicate-ZIP warning is an intentional rejection fixture.
- Known limitations and incomplete checks: three symlink/reparse fixtures were skipped because the current Windows token cannot create symlinks. The verifier harness is a trusted-local error-control boundary, not an adversarial OS/process sandbox; native or `ctypes` access outside CPython audit events, non-Python paths hidden from argv/environment/entrypoint inspection, and network isolation remain outside its claims.

### 1.2.1 — 2026-09-03 — Pre-verifier report lifecycle repair

- Trigger and source request: the PSI-J 3.1 compose/report revision reached an inspected candidate but `prepare-verification` failed because the harness incorrectly required the not-yet-produced current verification report. The causal analysis and approved patch scope are retained in `workspace/framework_development/verifier_harness_lifecycle_patch_plan_20260903.md`.
- Behavioral differences: harness preparation now accepts a null current verification report while retaining all upstream semantic and candidate guards; an already active report is still protected and malformed non-null entries fail closed. Verification transitions to `PASSED`, `FAILED`, or `BLOCKED` now require a current report before persistence and leave state bytes unchanged when that prerequisite is absent. The generated Python audit guard uses a portable access-mode mask when `os.O_ACCMODE` is unavailable on Windows.
- Principal components: `verifier_harness.py`, `state.py`, lifecycle and transition regressions in `tests/test_verifier_harness.py` and `tests/test_pipeline_control.py`, build-pipeline documentation parity tests, the build-tool-pipeline skill/gate map, and this README.
- Compatibility and migration: no command signature, artifact schema, or run-state schema changed. Existing run-state 1.0/1.1 reads and completed runs remain compatible; no placeholder report or historical-artifact migration is required.
- Verification: Root's repaired full maintained suite passed `174 passed, 3 skipped`; the warning is the intentional duplicate-ZIP rejection fixture. Independent Round 1 found and retained the terminal-transition atomicity defect as `NOT_READY`. After repair, independent Round 2 ran a fixture-independent raw public lifecycle through release, passed a 13-test focused regression, satisfied `PATCH-ACC-001` through `PATCH-ACC-012`, and returned `READY`. Round 3 demonstrated `NamedTemporaryFile` with the active audit handshake on Windows, confirmed a dynamically constructed forbidden external read still fails closed, passed five focused regressions, and retained `READY`.
- Known limitations and incomplete checks: verifier-owned deeply nested Windows test paths can exceed legacy path limits; shortened verifier-owned identifiers reproduced the same relevant scenarios successfully. The existing trusted-local harness and symlink-privilege limitations remain unchanged.

### 1.2.2 — 2026-09-07 — Pipeline semantic-agent model change

- Trigger: user request to move every pipeline custom semantic agent from GPT-6
  Astra to GPT-5.6 Sol.
- Behavioral differences: `problem_framer`, `product_contract_agent`, and
  `independent_verifier` now select `gpt-5.6-sol` while retaining `high`
  reasoning effort, their existing role instructions, sandbox modes, ownership
  boundaries, and delegation prohibition.
- Principal components: the three `.codex/agents/*.toml` semantic-role
  definitions, agent configuration regression coverage, and this framework
  revision record.
- Compatibility and migration: pipeline artifacts, schemas, commands, role
  names, and completed runs are unchanged. New role invocations use the revised
  model after the Codex project configuration is reloaded.
- Verification: TOML parsing confirmed all three roles select `gpt-5.6-sol`
  with `high` reasoning and retain their prior sandbox modes. The focused agent-
  delegation suite passed 7 tests. The full maintained framework suite passed
  176 tests with 3 expected skips; its one warning came from the intentional
  duplicate-ZIP rejection fixture.
- Known limitation: an already-running agent invocation retains the model with
  which it started; the setting applies when a new invocation loads the updated
  project configuration.

### 1.2.3 — 2026-09-24 — GPT-6 Sol semantic-agent migration

- Trigger: user request to replace remaining GPT-5.6 Sol custom-agent model
  selections with GPT-6 Sol at high reasoning effort.
- Behavioral differences: `problem_framer`, `product_contract_agent`, and
  `independent_verifier` now select `gpt-6-sol`; all three retain `high`
  reasoning effort and their existing role, sandbox, ownership, and delegation
  boundaries. `intent_realizer` remains on `gpt-6-astra` / `high`.
- Principal components: the three `.codex/agents/*.toml` semantic-role
  definitions, agent-configuration regression expectations, and this revision
  record.
- Compatibility and migration: artifact schemas, commands, role names, and
  completed historical evidence are unchanged. New invocations use the revised
  model after project configuration reload.
- Verification: the focused agent-delegation policy suite passed 17 tests,
  including TOML parsing and exact model/effort assertions. Per user direction,
  no additional full-suite result is required for this configuration-only
  revision.
- Known limitation: live model availability and an actual new custom-agent
  invocation were not exercised; already-running invocations retain their
  original runtime configuration.


### 2026-09-13 — FD-20260913-CLEAN historical-path correction

The user archived completed framework development records and discarded six
selected mixed/open documents. Earlier revision-history entries above retain
source paths as recorded at the time; their current retained locations include:

- [Pipeline boost-up plan (source history)](../docs/provenance.md).
- [Verifier harness lifecycle patch plan (source history)](../docs/provenance.md).

The full old-to-new mapping and user-directed disposal list are in the
[framework history index (source history)](../docs/provenance.md).
No control-plane behavior or artifact schema changed. Completed validation for
this organization-only revision is recorded in the
[current framework inventory](../docs/current-framework.md).

### 1.2.4 — 2026-10-01 — GPT-6.1 Sol agent selections

- Trigger: user request to replace current GPT-6 Sol agent selections with
  GPT-6.1 Sol throughout the repository.
- Behavioral differences: `problem_framer`, `product_contract_agent`, and
  `independent_verifier` now select `gpt-6.1-sol`. Root's fallback subagent
  model and worker Sol allowlist entry also select `gpt-6.1-sol`.
- Components: `.codex/config.toml`, three semantic-agent TOMLs, `AGENTS.md`,
  agent-delegation regression expectations, and repository policy history
  (`AM-20261001` in `workspace/framework_development/REPO_HISTORY.md`).
- Compatibility/migration: reasoning effort, other models, role instructions,
  sandbox modes, concurrency, delegation restrictions, schemas, and historical
  evidence are preserved. New invocations load the updated configuration.
- Verification: repository `.venv` agent-delegation policy suite passed 17
  tests, including TOML parsing and exact model/effort assertions.
- Limitations: live model invocation and the full framework suite were not run;
  already-running invocations retain their original model.
