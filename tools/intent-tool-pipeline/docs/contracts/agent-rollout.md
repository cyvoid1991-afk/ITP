# Selected artifact control: new-run operation and recovery

**New runs default to control `1.2` for procedure-bound specialist work.
Explicit `1.1` remains compatible; use explicit `1.0` only when a new legacy run
is requested. Existing runs keep their recorded procedure.**

## Current override — ITP-20261101-DEFAULT12

Date: 2026-11-01. The user authorized this new-run default change after S7.
Omitting `--control-revision`, or omitting Python `initialize`'s `control_revision`
argument, now selects `1.2`. Explicit `--control-revision 1.0` retains the legacy
route; explicit `1.1` retains its compatible artifact protocol. The override
supersedes S7's former default-`1.0` decision only for newly initialized runs.
Existing selectors, bindings, receipts, evidence and round history remain intact.
It grants no migration, baseline promotion, release or additional-round authority.

**Key judgment:** procedure binding should apply automatically to newly authorized
governed work. The trade-off is that previously unqualified new-run commands now
require the `1.2` assignment/loading/result procedure; callers needing legacy
transport must select `1.0` explicitly. Missing exact roles, effective file-write
support, original procedures or valid binding still block affected work. Do not
fall back to `1.0` or `1.1` to bypass a failed `1.2` prerequisite or gate. Preserve
a complete compatible S7 installation before these procedure bytes change and
use the recovery rules below for old assignments.

## S7 activation provenance

Historical activation revision: `ITP-20261101-ARTIFACT-S7`, 2026-11-01. This superseded the S6 readiness
status of this operational guide after rollout review. It is a companion
to the [artifact protocol](agent-artifact-protocol.md) and
[procedure binding](procedure-binding.md), not a migration or release. The
protocol's original S1 status is historical design status. Actual-role and
distribution results remain source-bound historical evidence; S7 does not rewrite
or extend them. Models, reasoning, role independence and delegation boundaries
remain unchanged. S7 grants no existing-run migration, baseline promotion,
framework/product release or additional-round permission.

## Selection and identities

| Run selector | Supported route | Preserved state |
| --- | --- | --- |
| `control.semantic_role_boundary: "1.0"` | Explicit new-run legacy choice; existing complete-body return and Root finalization | Existing two-attempt policy; no selected receipt/round fields |
| `"1.1"` | Exact specialist submission, digest-bound finalization and receipt recovery | Root-owned four-round ledger and immutable receipts |
| `"1.2"` | New-run default; `1.1` rules plus registry-owned assignment loading/result binding | Original procedure bytes/digests and bound receipts; no rewrite of earlier evidence |
| Unknown/unsupported or inconsistent metadata | Stop and select a compatible installation | No inferred version, marker removal or downgrade |

Initializer JSON reports `operational_status: PROCEDURE_BOUND` for `1.2`,
`ARTIFACT_SUBMISSION` for `1.1`, and `LEGACY` for `1.0`. These identify the selected
transport; they do not assert semantic readiness, release or round approval.

Selected runs also require `control.intent_realization: "1.0"`; this is a
different selector with its existing meaning. Run-state `schema_version` remains
`"1.1"`; semantic artifact schemas remain `"1.0"`. The initializer's selector
and default affect **new runs only**. It refuses an existing project directory.
`--run-id` changes identity metadata, not the `workspace/build_runs/<project-id>`
directory. Choose a short project ID before allocation; do not move a live run
to satisfy the generated-path budget.

The following PowerShell examples run from the repository root with the declared
`.venv`. Replace bracketed placeholders with recorded values; these are command
templates, not a script that allocates a run automatically.

```powershell
$env:PYTHONIOENCODING = 'utf-8'
$py = (Resolve-Path .\.venv\Scripts\python.exe).Path
$ops = (Resolve-Path tools/intent-tool-pipeline/pipeline_ops.py).Path
$init = (Resolve-Path .agents/skills/build-tool-pipeline/scripts/initialize_run.py).Path
$project = '<absolute-project-root>'
$run = '<absolute-original-run-directory>'

# Default 1.2 for new procedure-bound work; stop during a freeze.
& $py $init --project-root $project --request '<project-local-request.yaml>' --format json

# Equivalent explicit selection for new procedure-bound work.
& $py $init --project-root $project --request '<project-local-request.yaml>' --control-revision 1.2 --format json

# Legacy new-run route only when requested.
& $py $init --project-root $project --request '<project-local-request.yaml>' --control-revision 1.0 --format json

# Explicit compatible route without the 1.2 procedure-binding extension.
& $py $init --project-root $project --request '<project-local-request.yaml>' --control-revision 1.1 --format json

& $py $ops --project-root $project --format json validate-run --run-dir $run
```

## Assignment, registration and round operations

Before starting, verify the installed inventory, declared environment, exact
custom-role discovery and effective conditional write procedure. Reuse retained
actual-role evidence only where the installed role, permissions and relevant
procedure behavior still match; static configuration alone proves no runtime
write support. Selecting a role without the bound task procedure remains ordinary
role use. Direct B starts with Contractor; prepared A-to-B consumes the registered
brief and original sources. No synthetic Direct B brief is required.

Root starts the boundary for the exact specialist and passes the returned
baseline digest, original project/run paths and assigned submission path to it.
Use `intent_realizer`/`problem_frame`, `product_contract_agent`/`product_contract`
or `independent_verifier`/`verification_report` as the corresponding pair. The
paths remain `30_execution/sub/<audit-id>/{brief.md,contract.yaml,report.md}`
inside the original run. Additional local sources use repeatable `--input-ref`.

```powershell
& $py $ops --project-root $project --format json role-boundary start --run-dir $run --role product_contract_agent --invocation-ref '<invocation>' --artifact product_contract

# Required for 1.2: the child reads returned original procedures and actual inputs.
& $py $ops --project-root $project --format json load-role-assignment --run-dir $run --role product_contract_agent --invocation-ref '<invocation>' --baseline-sha256 '<baseline-sha256>'

# Root registers the specialist's unchanged assigned file, under both 1.1 and 1.2.
& $py $ops --project-root $project --format json finalize-semantic-return --run-dir $run --artifact product_contract --role product_contract_agent --invocation-ref '<invocation>' --baseline-sha256 '<baseline-sha256>' --source '<exact-assigned-file>' --expected-source-sha256 '<submission-sha256>'
```

The `1.2` result copies `required_result_binding` exactly: one top-level
`procedure_binding` in YAML/JSON, or one
`<!-- procedure-binding: {JSON} -->` comment in Markdown. Do not add a sidecar.
The receipt remains under `control.semantic_registrations[<audit-id>]` and the
journal under `30_execution/semantic_finalize/tx/<audit-id>.json`.
`persist-artifact` rejects selected work; it is not a fallback.

The specialist returns the assigned path, version/digest, readiness and unresolved
conditions as a compact index. Root checks admission and routes the unchanged
artifact rather than transcribing it or routinely repeating specialist judgment.
Consumers read the actual registered bytes: Contractor compares original sources,
Root consumes the contract when implementing, and Verifier consumes the exact
contract, candidate and evidence. A compact return is never the artifact.

Admission is distinct from semantic readiness. Forward consumers must consume
actual registered bytes and satisfy the existing gates/current procedures.
For round entry, Root uses existing `update-bounce-back create/resolve` payloads
and `update-state --to-stage repair --failure-ref <latest-report-ref>
--evidence-ref <BB-ID>` with the normal status/rationale/next-action arguments.
The one count is `repair.active_attempt`, substantiated by `repair.rounds`.
Recovery does not reserve a new round or refund one. Four completed rounds do
not imply failure; further modification requires the existing separate review
and explicit user approval. See the
[round clarification](round-recovery-clarification.md) for the exact route.

## Freeze and side-by-side recovery

**Retain the complete compatible installation before changing bound procedure
bytes, including an S7 guidance update, or reverting operational code.** Such a
change does not upgrade old assignments: forward use rejects stale `1.2` bindings.
Recover interrupted work through the compatible reader/recovery route below,
then obtain fresh owner assignments and replace affected artifacts before forward
use. A recovery reservation may precede those assignments under the
[binding recovery rules](procedure-binding.md). Never rewrite old procedure
snapshots, binding hashes, receipts, verdicts or round records.

**Root's freeze is a trusted operational instruction, not a runtime switch or
an enforced access-control feature.** Record its scope, timestamp, selected run
paths, in-flight invocations/transactions and retained control source identity
in the framework evidence. Stop new selected initialization, boundary assignment,
fresh registration, subject modification, round entry and threshold continuation.
Quiesce active specialist writers before inspecting or recovering a transaction.
Retain their completed exact submissions; do not reconstruct them from messages.

Keep the complete compatible repository/bundle installation side by side before
reverting an operational installation. It needs `pipeline_ops.py`, its complete
`pipeline_control` package and the installed registry's original `.agents` and
tool procedure assets, including templates and required referenced procedures.
Keep its known source identity and declared Python dependencies. A diagnostic
copy is not a new framework release. Preserve the original product project,
run, canonical/history files, baselines, state backups, submissions, journals,
receipts, evidence, candidate identities and round ledger **at their original
paths**. Do not copy a run into the compatible installation or repoint its
project root there.

Set `$ops` to the retained compatible installation's absolute CLI path and keep
`$project`/`$run` unchanged. `--project-root` is mandatory here because the CLI
otherwise defaults to its own tool directory. The compatible CLI can validate
legacy and selected records; no old writer may touch selected state, including
old low-level boundary operations that predate selector checks. Do not assume
an old installation's validated-reader rejection protects all its writers.

Recover only an already-issued matching request during the freeze. Read the
baseline, submission and journal/receipt to obtain the exact role, invocation,
artifact, baseline digest and source digest. Run the **same** documented
`finalize-semantic-return` command through the compatible CLI; there is no
separate recovery command. Preserve stdout, exit status and diagnostics.

| Durable outcome | Action and expected result |
| --- | --- |
| No journal and no canonical mutation | No transaction recovery exists; leave fresh admission stopped until Root explicitly resumes it |
| `PREPARED`, prior state/partially installed artifact | Matching finalization restores exact recognized prior bytes, retains the failed attempt, reports `FINALIZE_RECOVERED_ROLLBACK` and exits 1; this is a recovered rollback, not successful admission |
| `PREPARED`, intended state/artifact installed | Matching finalization validates and commits the recorded receipt; stale `1.2` procedures or failed validation instead cause recognized exact rollback |
| `COMMITTED`, including historical artifact | Matching finalization returns original receipt with `replayed: true`; `is_current: false` means a newer artifact remains active. Replay performs no reactivation or state rewrite |
| `ROLLED_BACK` | Preserve terminal attempt; no replay restoration occurs. Reissuing may start a fresh snapshotted admission attempt, so do not reissue during the freeze without an explicit scoped Root resumption |
| Unrecognized state/target, missing or altered provenance | Stop; retain conflict evidence. Do not overwrite later work, repair hashes, strip markers or guess original bytes |

Unrelated mutations reject while any `PREPARED` transaction remains. Validate the
run after recovery; a historical replay is not proof that current active inputs
or procedures are valid. Procedure drift requires fresh owner assignments after
resumption. Recover/roll back interrupted registrations with the compatible
implementation **before** operational code rollback; keep the reader/recovery
installation available for all retained selected records afterwards.

Legacy retries keep their original complete-body procedure. Digest checking is
optional on legacy finalization and enforced when supplied. There is no selected
receipt replay guarantee for legacy calls: inspect current active version and
boundary/finalization evidence after a lost reply rather than blindly submitting
the same body again. Fresh corrections use the next permitted version and a new
invocation. Missing historical retired-role dependencies remain blocked under
the existing policy; a new explicitly selected `1.0` run uses `intent_realizer` normally.

## Installation and activation record

1. Root reviews the retained S6 regression, distribution/extraction and rollback
   evidence and resolves affected identity, round, candidate or verification
   failures. Record unrelated failures and their impact explicitly.
2. Verify the installed inventory, original registry assets, documentation links
   and declared environment. Prove the documented CLI from an extracted/copy
   installation against the original project/run paths.
3. Reload/discover the exact three custom roles in the effective host/session;
   preserve their models, reasoning, independence and conditional write scope.
   Use the retained S5 actual-role evidence for what it establishes; repeat live
   checks if installation/procedure/permission changes invalidate that evidence.
4. Use this new-run operating guidance and retain the explicit S7 decision and
   user-authorized `ITP-20261101-DEFAULT12` override, version/revision identity,
   compatibility and remaining limitations. New runs default to integrated
   `1.2`; retain `1.1` explicit selection/reading/recovery and explicit `1.0`
   for requested legacy work. S7 originally retained default `1.0`; that is
   historical activation scope superseded only for new runs by the override.
5. Resume selected admissions only within the recorded activation scope. Existing
   runs keep their selectors and records. No migration, baseline promotion,
   product publication, framework archive or additional-round approval follows
   from S7 alone.

**Trade-off:** retaining a full compatible installation costs storage and requires
source/dependency discipline; it avoids stranding selected records under old
writers. A procedural freeze is proportionate to this trusted local workflow,
but fails if an operator ignores it or concurrent writers remain active. A
runtime disable toggle or adversarial sandbox would be a different scope.

At S7, the subprocess cases in `tests/test_agent_rollout.py` exercised default legacy
initialization/finalization, `1.1`/`1.2` historical replay, nonempty round-ledger
reading, and actual process-exit recovery through a side-by-side compatible
runtime with byte-identical registered procedure assets. They establish bounded
operational compatibility, not enforcement of Root's freeze, universal deployment
compatibility, specialist comprehension or a real user continuation decision.
S7 activation is the recorded operating decision, not a test-generated permission.
The actual assembled-bundle checks remain separate distribution
evidence.
