---
name: build-tool-pipeline
description: Deliver an approved local software tool through Workflow B using prepared intent or direct Root and Contractor intake, followed by implementation, tests, independent verification, bounded repair, and release. Use for new or revised tools under codex_workspace/ needing staged delivery. Exclude framework maintenance, simple isolated fixes, generic analysis, and standalone documentation editing without a verified release request.
---

# Build Tool Pipeline

## Repository integration

For pipeline work, first read [the tool rules](../../../tools/intent-tool-pipeline/AGENTS.md).
The pipeline project root is `tools/intent-tool-pipeline/`, not the Nexus_AI root.
Paths such as `docs/`, `codex_workspace/`, `workspace/`, `intent_deliver/`,
`test_workspace/` and `deliverables/` in this workflow are relative to that tool root.
Shared `.agents/` and `.codex/` paths are relative to the Nexus_AI root.
Run workflow command examples from the tool directory; use the root virtual environment.
General research or standalone role use does not start Workflow A/B.


Turn one approved build request into a verified local deliverable while preserving user authority, semantic-agent independence, deterministic gates, and a resumable evidence trail.

## Establish Control

1. Read the nearest `AGENTS.md` files and preserve unrelated work.
2. Read [gate-map.md](references/gate-map.md) before the first run-state change.
   Read the repository-relative `docs/governance/Root_Autonomy_Instruction_v0.3.md`,
   `docs/governance/Root_Delegation_and_Delta_Procedure_v0.3.md`, and
   `docs/governance/Task_Delegation_Contract_Template_v0.3.md` at intake and resume. They define
   decision authority and handoff content; this skill maps them to runtime gates.
3. Confirm that the request identifies a concrete tool or code deliverable. If it does not, return to ordinary repository handling.
4. Keep Root Codex as the only run-state owner, product-source writer, and release owner.
5. Keep one active writer for each owned artifact. Never let agents concurrently edit `run_state.json` or the product tree.
6. Treat every nonzero control-plane result as a stopped gate. Do not reinterpret or bypass it.
7. For every invocation in this governed workflow, read [invocation.md](references/invocation.md), name the role-specific skill and adapter in the call, and supply their current inputs. Start every `intent_realizer`, `product_contract_agent`, `independent_verifier`, and read-only `explorer` invocation with `role-boundary start`. For semantic artifacts, complete the invocation through `finalize-semantic-return`, which finishes the boundary audit and activates the complete owner-authored artifact as one transaction; selected threshold process review instead finishes its audit without semantic activation. A `BOUNDARY_VIOLATION` result prohibits artifact activation, gate PASS, and stage advancement.
8. Keep top-level delegation Root-owned. Root may spawn bounded agents for independent work. The exact custom semantic roles must not spawn further agents; built-in workers and explorers retain the execution environment's current delegation authority.

### Selected runs and legacy behavior

Control `1.2` runs, including new runs initialized without a selector, use the workflow-owned registry and
[assignment entry](references/assignment-entry.md). The child loads mandatory
procedures through its exact assignment; Root supplies intent and assignment
identity instead of assembling a substitute procedure list. Selected `1.1`
file/round rules below also apply, with mandatory result binding and current
procedure checks described by the invocation reference. Revision
`ITP-20261101-DEFAULT12` (2026-11-01), authorized by the user after S7,
makes this the new-run default; existing run behavior remains unchanged.

The current new-run default is control.semantic_role_boundary: "1.2".
The "1.1" procedure below remains supported and also supplies `1.2` transport
and round rules. New legacy runs require explicit `--control-revision 1.0`;
`--control-revision 1.1` remains an explicit compatible route. Do not silently
upgrade existing runs or infer their selection from semantic-role choice. Follow the
[rollout procedure](../../../tools/intent-tool-pipeline/docs/contracts/agent-rollout.md)
for compatible recovery and procedure-drift handling. Read
[invocation.md](references/invocation.md) for the transport branches.
Generic roles and generic contract/verifier skills remain reusable independently
of this pipeline; only an explicit governed call loads these procedures.

| Control | Owner-authored semantic output | Modification bound |
| --- | --- | --- |
| Legacy "1.0" / supported historical control | Complete body returned; Root saves and finalizes unchanged | Existing two-attempt policy |
| Selected "1.1" / "1.2" | Complete file at start-result submission_path; compact actual identity/status return; Root registers exact digest; "1.2" also binds original procedures | Four lifetime rounds initially, with finite continuation only after independent review and explicit user approval |

Root reads actual registered artifacts and ensures that downstream consumers do
the same. A compact return, file existence or registration receipt is not a
semantic readiness verdict. Coordinate source/authority and deterministic checks
without routinely duplicating specialist adjudication or transcribing bodies.

### Budget and reuse agent threads

Treat spawned agents as task-scoped, reusable threads. A completed turn does not
prove that the runtime released the agent or its thread slot, and Root must not
assume that it did.

- Before initializing a run and before every spawn, inspect the current agent
  inventory and the runtime's available thread budget when those capabilities
  are exposed. Confirm that every required exact semantic role can be served by
  an existing compatible agent or by remaining capacity.
- Confirm that the runtime exposes the exact required role, not merely that its
  TOML file exists. Workflow A requires callable `intent_realizer`; prepared or
  direct Workflow B requires Contractor and Verifier, with Realizer capacity only
  when an actual upstream return needs that role. After a role
  configuration change, use a refreshed runtime context if necessary and check
  again. Never substitute a generic agent and label it the exact custom role.
- Maintain at most one reusable agent for each exact semantic role within a
  root task. Continue later runs, revisions, verifier retries, and repairs with
  `followup_task` on that same-role agent instead of spawning duplicates.
- Semantic independence comes from the fixed role, write boundary, fresh
  invocation reference, current artifact inputs, and role-boundary audit. Do
  not create a fresh agent merely to simulate independence unless an explicit
  policy or evidence-backed context-contamination concern requires it.
- When a fresh agent is required, record the reason and capacity impact before
  spawning it. Never repurpose an agent whose fixed type differs from the exact
  required role.
- Reserve required semantic-role capacity before optional workers or explorers.
  If the runtime cannot accommodate all unique roles needed for the run, do not
  initialize a run that cannot advance. Use a separately authorized root task,
  or persist and validate the existing run for an explicit task handoff.
- Do not start `role-boundary start` until the selected existing agent or new
  slot is available. If spawning fails after a boundary baseline was created,
  and any protected run artifact subsequently changes, abandon that unused
  invocation reference and start a new boundary on resume.
- If the runtime provides no agent-disposal operation, instructions cannot make
  a completed agent disappear. Prevent exhaustion through reuse and preflight;
  do not rely on prompt text to release a slot.

Accept the user's best available intent, including UX-only input. In Workflow A,
Root and the intent realizer discover and resolve missing implementation conditions with
bounded evidence gathering; a complete engineering guide is not an intake
prerequisite. Keep open-ended theoretical experimentation, model exploration, and
engineering-deliberation research outside this delivery pipeline when it requires
a new objective or cannot be bounded to the requested outcome. Return the specific
unresolved decision and useful evidence, not a generic request for a better handoff.
Do not consume a repair attempt merely to explore alternatives.

## Optional documentation work
Before candidate packaging, assess the product documentation using
[optional workflows](../intent-tool-pipeline/references/optional-workflows.md).
Required documentation defects remain implementation obligations. Suggest
optional restructuring; execute only within existing user authorization.
An explicit request for a new verified release of a documentation revision
belongs to B, even if the product's executable behavior is unchanged.
Keep all existing contract, test, candidate and verification gates.
Documentation-only editing without release uses the rework skill.

## Create the Run

First select the entry path, independently of NEW_PRODUCT versus REVISION:

- **Prepared A → B:** resume the existing initialized run with the audited current
  Realizer brief and source/delegation handoff. B starts with Root and Contractor
  consuming those identities. Do not initialize a duplicate run or repeat A.
- **Direct B:** for sufficiently clear intent, Root and Contractor perform the
  first substantive intake. Set existing `handoff.next_stage: contract` before
  initialization. Record why original intent, scope, authority and acceptance
  basis are sufficient. Keep framing stage/gate PENDING and frame null; no fake PASS.
- **Preparation needed:** use `$intent-realization` for Workflow A with
  `handoff.next_stage: framing` (also the absent-field legacy default). Stop at
  the consumable handoff when only preparation was requested. A does not authorize B.

External-chat A material is a source snapshot, not automatically an audited native
Realizer artifact. Either A adopts it through the exact role and existing finalizer,
or B explicitly uses the direct route with Contractor review. Preserve authorship.
Select the route once; a material return records the affected question and sources
in the existing bounce-back/delegation records. Never rewrite a consumed route to
evade gates. A direct run requiring a native A return pauses and links a separate
preparation run; its eventual B continuation consumes the authorized source snapshot
on the direct route or explicitly hands over to the prepared run. No invented frame.

Normalize the user request into an active artifact-contract `1.0` `build_request.yaml`. Preserve the user's words through source references, distinguish approved decisions from assumptions, and expose blockers. Choose exactly one initialization mode:

- `NEW_PRODUCT`: set `project.request_kind` to `NEW_PRODUCT` and omit `revision_of` and `delta_request`.
- Exact-baseline `REVISION`: set `project.request_kind` to `REVISION`; provide `revision_of` with `run_id`, `archive_sha256`, `product_contract_ref`, `product_contract_sha256`, `verification_report_ref`, and `verification_report_sha256`; and provide `delta_request` with `scope_classification: BOUNDED`, at least one `requested_changes` item, `explicit_non_changes`, and `feedback_evidence`.

For `REVISION`, the initializer resolves the named completed run, same target repository, `READY` all-requirement PASS report, active contract/report bytes, passing release and verification gates, and the captured contract/manifest/inspection/archive candidate binding. Any missing, ambiguous, broad, incompatible, stale, or hash-mismatched baseline returns `FRESH_REQUIRED` and creates no revision run. Never silently convert it to a fresh build.

Before normalizing a revision request, inspect the target product's authoritative revision history for entries after the exact baseline marked `Disposition: PRE_EXISTING_DELTA_NOT_VERIFIED_BASELINE`. Compare the exact baseline archive with the current product tree, preserve every such entry as source/feedback evidence, and include its behavior in the cumulative delta request and complete current contract. Treat affected baseline requirements as impacted even when the new request asks only to preserve the already implemented behavior. These entries are never eligible baselines by themselves; the current candidate must pass applicable tests, packaging, inspection, and independent verification as one combined revision. If the exact baseline is ineligible, follow `FRESH_REQUIRED` without promoting a minor revision or refreshing hashes.

Collect each history link written as `Local delivery record: ` followed by a backtick-enclosed repository-relative manifest JSON path. Follow the minor skill's [local-delivery intake procedure](../minor-tool-revision/references/local-delivery.md) to validate those records and retain their exact hashes in the existing hash-bound `source_context` before initialization. For external authoritative source, supply exact-byte record snapshots inside the pipeline project using existing permitted context fields; this enables discovery without changing B target or baseline eligibility. The initializer checks discovered records and retains a receipt without changing the request schema. Carry source behavior, package scope, and limitations into cumulative delta evidence; package records never establish a verified baseline. A known coherent local patch base may exist while the formal pipeline baseline is unknown. Do not bypass a failed B gate by creating a local package.

The initializer creates a run-state `1.1` control record with
`control.intent_realization: "1.0"` and records `control.revision_baseline` only for
an eligible revision. When A is needed, new runs use `intent_realizer`;
`problem_framer` is excluded from the new-run workflow. Keep the `framing` stage and `problem_frame` key/path as
compatibility names. Unmarked historical runs retain their recorded owner and
semantics; do not relabel their artifacts or hashes. Existing run-state `1.0`
records remain read-compatible, but a legacy run without the fully captured
verified-candidate binding is not eligible as a delta baseline.

Initialize the fixed run hierarchy with:

```powershell
..\..\.venv\Scripts\python.exe ..\..\.agents\skills\build-tool-pipeline\scripts\initialize_run.py `
  --request <repository-relative-build-request>
```

Never reuse or overwrite an existing run directory. Resume an existing run from its active artifacts instead.

Treat earlier handoffs and plans that predate the current artifact contract as `SUPERSEDED_CONTEXT`: preserve the files, cite them through ordinary `source_context` records when useful, and build a complete current request and contract, plus a frame only on the prepared path. `SUPERSEDED_CONTEXT` is a migration label, not a new `source_context.authority` enum value. Do not overwrite old evidence or imply that read compatibility makes it an eligible revision baseline.

## Execute the Stages

Run the applicable stages in this order; B's first substantive collaboration is
Root + Contractor. A may already be complete or unnecessary:

1. `intake`
2. Workflow A intent realization when needed (compatibility stage `framing`)
3. `contract`
4. `repository_analysis`
5. `implementation`
6. candidate packaging and inspection as verification evidence, without release authorization
7. `verification`
8. `repair` only when verification returns an eligible failure
9. `release`

At every stage:

1. Read the active upstream artifacts and `run_state.json`.
2. Perform only the current stage's work.
3. Use the selected transport from invocation.md: legacy Root saves the complete returned body; selected "1.1" uses the specialist's exact assigned file and actual digest. Root calls finalize-semantic-return with the start baseline and selected --expected-source-sha256. The command audits, validates, archives, registers and activates recoverably. Never transcribe selected bodies, manually activate them or treat registration as readiness.
4. Record active artifact versions, decisions, blockers, approvals, invocation references, and bounce-back events before retrying or redirecting work. Create and resolve bounce-backs only through `update-bounce-back`; never edit their run-state array directly.
5. Validate the run and execute the mapped deterministic command.
6. Advance only after the stage and gate are both `PASSED`.

### Intake

Have Root own and persist `00_intake/build_request.yaml`. Preserve the user's
original request/source references, outcome, target, constraints and delegated
decisions. Intake may contain unresolved technical conditions for realization;
do not require the user to design the implementation. A fundamentally unclear
outcome requires focused discussion before starting a governed delivery run.

### Intent realization

Invoke the exact custom role `intent_realizer` with
`.agents/skills/intent-realization/SKILL.md`. Legacy calls remain read-only and
return the complete brief. Selected "1.1" calls complete that same full brief at
their assigned submission_path and return its actual identity/status compactly. Audit and activate through
`finalize-semantic-return`; a revision must reason from both the exact baseline
and the complete current request, not only a patch note. The original
`problem-framing` skill remains available to Root for general discussion; it is
not the mandated procedure or custom role for this new-run stage.

Require source-linked derived conditions, concrete failure cases, justified
default policies, unresolved decisions and evidence needs. Root supplies relevant
repository evidence and executes any needed probes. Do not ask the realizer to
implement, write the binding REQ/ACC catalog, or verify the product.

### Root coordination and critical review

Root normalizes intent, answers agent questions from existing decisions, obtains
bounded technical evidence and selects routine implementation policies within
authority. Use an explorer only for a concrete independent repository question
when it fits the retained-agent budget; otherwise Root reads the code directly.
Never run protected-tree writes during a read-only boundary audit.

Use separate reusable `intent_realizer`, `product_contract_agent` and
`independent_verifier` roles because they own different judgments, not to multiply
agents per checklist. Implementation stays Root-owned. Do not silently substitute
Root for a required unavailable semantic role; preserve state and arrange a valid
runtime handoff. No new observability or reproducibility subsystem is in scope;
existing tests, integrity checks, and release evidence remain required.

For every consequential bounce-back, record the question, intent/evidence source,
counterexample or effect, Root answer, decision authority, changed basis and next
owner in the existing event summary/references and affected artifact. Root first
resolves what the supplied intent and delegated authority already answer. Ask the
user only for a material new choice; include a recommendation and its consequences.
If a repeated question has no changed basis, stop the unchanged retry and isolate
the actual decision. Do not invent an additional automatic repair allowance.

### Contract

At B intake, compare the original source intent, delegation and cumulative changes
against the prepared handoff or direct request. Sufficiently clear intent must not
be sent through A merely to complete a checklist. Return only a material missing
intent/authority/acceptable-loss choice upstream. Root resolves evidence gaps within
existing authority; Contractor corrects misformalized obligations in B; an
implementation discrepancy goes to bounded repair after a verifier failure.

Invoke the exact custom role product_contract_agent with [contract-adapter.md](references/contract-adapter.md) explicitly named. Require the author-product-contract workflow and one complete artifact-contract 1.0 contract. Legacy calls remain read-only/full-body; selected "1.1" calls write only the exact assigned submission and return its actual identity/status compactly. Audit and activate it through `finalize-semantic-return`, which records content hash, both owners, source invocation, and boundary evidence. Run `validate-contract` afterward.

Supply original authorized intent sources and delegation, plus the realization
brief when one exists. Newly initialized requests are SHA-256-bound in run state.
The complete contract must list `build-request` version and `content_sha256` in
`source_artifacts`, and also the active `problem-frame` version/hash for prepared
runs. Direct contracts omit the nonexistent frame. Bind local original-intent and
delegation snapshots in request `source_context` using repository-relative `path`
and `content_sha256`; preserve originals, not a Root paraphrase alone. Final byte
hashes live outside the artifact they identify. Legacy unbound inputs retain their
interface; do not silently relabel historical evidence. Adoption and advancement
check consumed-input currency, while an intermediate owner correction remains possible.
Require an independent source-to-obligation comparison: challenge unsupported
defaults, unnecessary restrictions, missing conditions and a plausible behavior
that would pass the proposed checklist but violate the purpose. A realizer PASS
does not compel contract PASS. The realizer owns feasibility/condition proposals;
the contractor owns requirements and the checkable acceptance checklist. Preserve
accepted, rejected and deferred consequential proposals with reasons under the
existing contract decisions, assumptions and blockers; avoid duplicate catalogs.

For a `REVISION`, require the full current contract plus `revision_control.mode: DELTA`, the exact `revision_control.baseline`, hash-bound `unchanged_requirements`, and an `impact_map` that covers every requested change and explicit non-change exactly once. Each map entry records its disposition, baseline/current requirement references, source/test/documentation/packaging references, migration impact, and `ALL_APPLICABLE_REQUIREMENTS` reverification scope. Classify every baseline and current requirement exactly once as unchanged or impacted, keep those sets disjoint, and treat a changed shared acceptance record as impacting every linked requirement. Delta framing never weakens the verification gate.

When revising any active semantic artifact, use `finalize-semantic-return` rather than an ad hoc archive/swap. It copies the active bytes to history, verifies a same-directory temporary payload, atomically replaces the canonical path, activates the validated identity, and restores exact prior bytes on failure. `role-boundary finish` followed by `persist-artifact` remains available only for migration-compatible older orchestration. Never leave `run_state.json` pointing at a missing artifact during an archive/swap.

Do not implement until contract readiness is `PASS` or `PASS_WITH_ASSUMPTIONS` and every carried assumption is visible.

Reject a self-referential acceptance sequence. An applicable requirement judged before release may require the inspected candidate package and may require proof that release is still pending, but it must not require the verifier's already-completed report or Root's future final release-gate decision as input to that same verification. Keep final release authorization as a Root orchestration invariant evaluated after `READY`.

### Repository Analysis

Use a read-only explorer for focused codebase questions when the target already exists or repository conventions affect implementation. Apply the no-write role-boundary audit and have Root record the analyzed paths, constraints, selected implementation boundary, and evidence reference.

Do not turn repository analysis into a second product-framing or contract-authoring stage.

### Implementation

Have Root remain the single product-tree writer. Implement only the active contract, add or update tests and user documentation, preserve the deliverable's revision history, and use the repository virtual environment.

Before writing source, identify the implementation's main responsibilities and choose cohesive module boundaries. Separate domain computation from configuration or input validation, orchestration, rendering, and persistence or publication when they can change independently. If one module would combine three or more such concerns, split it or record why a cohesive single-module design is preferable. Keep a thin stable facade when useful, retain a small cohesive script when separation would add only indirection, and never split solely to meet a line-count target. Treat this as an implementation-quality check, not a product-contract requirement unless observable behavior, feasibility, compatibility, risk, or acceptance depends on the boundary.

Record reversible implementation choices as `AGENT_DECIDED` only when they preserve observable behavior, scope, compatibility, and acceptance. Escalate material choices instead.

Execute the active shell-free test plan through `run-tests --attempt-id <unique-id>` before passing the implementation gate. The command writes immutable evidence under `30_execution/test_attempts/<attempt-id>/test_results.json` and updates the fixed canonical `30_execution/test_results.json` with that attempt identity and hash. Never reuse an attempt ID or substitute cached repeatability evidence. Mark implementation `PASSED` and keep it as the current state while candidate packaging and inspection run. After the inspected candidate exists, enter verification as `IN_PROGRESS`; this is the normal verifier-report registration window and may initially have no active verification report.

Create the contract-bound candidate archive with `package`, then run `inspect-package`, before invoking the verifier. Treat the archive, release manifest, and passing package inspection as candidate evidence only: keep the release stage `PENDING` and do not call the product released. Packaging is repeatable and invalidates prior inspection, so regenerate and reinspect the candidate whenever attributable source, tests, package specification, or contract approval binding changes.

### Verification

After implementation, tests, candidate packaging, and package inspection pass, run `prepare-verification` against a plan bound to the exact active contract, manifest, inspection, and archive paths and SHA-256 values. Require an immutable PASS attempt, one extraction, complete fresh command repetition, PASS cleanup evidence, no undeclared-dependency or protected-mutation diagnostic, and `python_audit_status: PASS` for every recognized Python command. A missing or disabled Python audit activation is a failed attempt, not an optional evidence gap. The harness prepares deterministic evidence only: `independent_verifier_judgment` remains `NOT_PERFORMED`, and its layered argv/environment/entrypoint/Python-audit controls are not an OS sandbox.

At this pre-verifier boundary, a null current verification report is the normal state because the independent verifier has not produced its judgment yet. Require and protect the active build request, product contract, run state, source, manifest, inspection, and archive; protect the required problem frame on the prepared path. Direct B has no frame to manufacture. If an already active verification report exists during a later attempt, protect its exact identity too; a malformed non-null report entry still fails closed.

Then enter verification as `IN_PROGRESS`, start the `independent_verifier` role boundary, and invoke the exact custom role. Give it the harness attempt and cleanup evidence, active contract, immutable source and archive identities, test evidence, release manifest, package inspection, documentation, and prior repair evidence. Require it to use the independent-verification workflow and explicitly named [verification-adapter.md](references/verification-adapter.md); its legacy probe allowance is 40_verification/probes/**; selected "1.1" artifact calls use only the exact assigned report file plus their own 40_verification/probes/<audit-id>/ directory. Symlink/junction escape is a boundary violation.

Finalize the verifier-owned report through `finalize-semantic-return`. Have Root preserve `READY`, `NOT_READY`, `UNVERIFIED`, and requirement-level results exactly; activate its hash-bound run-state reference and pass `validate-run`; only then set the in-progress verification stage to `PASSED`, `FAILED`, or `BLOCKED` according to that report. Verification PASS captures both the report identity and exact contract/manifest/inspection/archive candidate binding used for release reconciliation and future revision eligibility. A terminal verification state may never have a null or missing active report. A polished summary or harness PASS never substitutes for a complete report.

### Repair

For selected "1.1" or "1.2" runs, use the four-round procedure under Enforce the Repair
Bound and the gate-map. After any terminal result, reserve an IN_PROGRESS round
before adopting subject changes, including contract-plus-code corrections,
previous PASS or incomplete-release changes. Bind --failure-ref to the exact
latest report and repeat --evidence-ref for the existing modification-event IDs.
Several issues, role calls, earlier-stage visits and resumed edits can share that
round; the fresh round-bound terminal report completes it without another count.
Do not reuse a report produced before reservation. Clear/rebuild affected release
authority through existing commands and retain immutable prior report bindings.

Evidence-only recovery consumes no round only when contract, archive and source
identity are known and unchanged. Missing identity or drift cannot establish
equality. A fresh null-round recovery report may become the threshold basis only
through authenticated EVIDENCE_GAP lineage to the exhausted completed result;
preserve that result and bind review/approval to the exact latest report.

The remaining repair text in this subsection describes legacy control "1.0":

When new intent/evidence invalidates a prior PASS before completed release, record
the current verifier reference and changed basis in an open bounce-back, then use
the gate-map's controlled verification revalidation entry. The old candidate
binding remains historical/current review context, not release permission.
Evidence-only review needs a fresh Verifier return. Code or contract changes require
an eligible FAILED/BLOCKED verdict and formal repair before adoption; revalidation
does not reset or bypass the two-attempt limit. A completed release is immutable:
subsequent governed candidate or formal release changes use revision intake.
Separately authorized bounded local changes may use `$minor-tool-revision` with
carry-forward evidence; they cannot alter this run or its released evidence.
Never edit gate statuses by hand.

Enter repair only for an evidence-backed implementation defect or contract contradiction. Follow the bounded repair policy below, rerun attributable tests, regenerate and reinspect the candidate package, resolve the bounce-back with a changed basis, and return to the verifier.

Do not enter repair merely because an expected candidate package or inspection was not supplied to the verifier. Acquire that evidence while implementation remains the current passed stage, then re-invoke verification. A contract change still requires the product-contract owner and a version increment; if such a semantic change is necessary, it is a contract repair and uses one bounded repair attempt even when product hashes remain unchanged.

### Release

Enter release only after verification is `READY`, every applicable requirement is `PASS`, default-path test evidence and the currently inspected candidate package still pass, and no blocking issue or pending approval remains.

Revalidate that the active source, test-plan attempt, contract approval binding, release manifest, archive, package inspection, harness attempt, and verification report are the exact candidate evidence the verifier judged. `update-state` and `validate-run` reconcile current bytes with the report and `candidate_binding` captured at verification PASS. Enter release, attach that evidence, and pass the release gate without rebuilding the archive after verification. Any material change makes verification stale and returns the run to tests, candidate packaging, inspection, harness preparation, and independent verification. Never package a governed candidate or formal release through an ad hoc archive command and never claim release success before inspection and verification both pass. Separately authorized local delivery follows the minor skill and repository-root `deliverables/` ownership; it confers no release-gate or exact-baseline eligibility.

## Preserve Artifact Ownership

Keep these semantic and persistence boundaries:

| Artifact | Semantic owner | Persistence owner |
| --- | --- | --- |
| `build_request.yaml` | User intent; Root normalization | Root |
| `problem_frame.md` | `intent_realizer` (new runs); recorded legacy owner for old runs | Root |
| `product_contract.yaml` | `product_contract_agent` | Root |
| `run_state.json` | Root and approved control-plane transitions | Root/control plane |
| `verification_report.md` | `independent_verifier` | Root |

Treat `test_results.json`, `release_manifest.json`, `package_inspection.json`, and the completion report as deterministic or reporting evidence, not new semantic coordination artifacts.

For new runs, each active `problem_frame` (when applicable), `product_contract`, and `verification_report` reference must include artifact version, canonical path, SHA-256, semantic owner, `root_codex` persistence owner, source invocation reference, and matching role-boundary PASS evidence. Filesystem existence alone never activates an artifact.

## Decide or Escalate

Resolve discoverable context and reversible implementation choices without interrupting the user. Record the decision and rationale when it affects later work.

Stop and ask the user when progress requires a material unresolved behavior, scope or UX decision outside existing intent and delegated authority, new external authority, an unsafe action, an incompatible contract change, a waiver, or acceptance of material risk. Routine choices already covered by delegation do not require another approval. Record the blocker or approval in `run_state.json`; do not rely on chat history alone.

First attempt bounded realization work using relevant evidence. When the unresolved
matter requires open-ended theoretical experimentation, model exploration, or a
new product objective, preserve the resolved parts and return the exact decision
for separate discussion. Missing technical guidance alone is not a blocker.

Use the execution environment's current delegation authority for internal custom-agent calls. If an invocation would transmit artifacts outside the currently authorized boundary, obtain artifact-specific approval and record it before transmission.

## Enforce the Repair Bound

Legacy control retains at most two automatic repair attempts. Selected "1.1"
starts with repair.maximum_attempts: 4 and repair.active_attempt: 0; active_attempt
counts rounds started and its existing rounds ledger substantiates the count.
Use update-state to reserve before modification; never edit the count, ceiling
or ledger by hand, reset them on resume or create a replacement run to obtain
free allowance for the same unfinished work.

Before retrying verification:

- resolve the originating bounce-back through `update-bounce-back`;
- record changed artifacts or evidence;
- set at least one allowed change basis;
- rerun the affected tests;
- regenerate and reinspect the candidate archive;
- update source and archive identity;
- request focused revalidation plus any dependency scope named by the verifier.

If the same root cause repeats, investigate non-progress or a contract/architecture
problem early; do not consume remaining allowance on unchanged patches. Legacy
control stops after its second unsuccessful attempt with REPAIR_LIMIT_EXHAUSTED
and escalation.

For selected "1.1", the fourth in-progress round may finish and a fourth PASS
may advance through ordinary quality/release gates. Before any later modification
at exhaustion, create REPAIR_LIMIT_EXHAUSTED through update-bounce-back. Obtain a
separate independent_verifier process review using --review-event, finish its
exact-file audit and retain PASS, then present a bounded recommendation and its
changed approach for explicit user approval. Root cannot approve or paraphrase
the user's response into authority. Resolve only the specific finite allowance
and unchanged-intent approach through USER_DECIDED by user, with retained review
and actual response evidence. The command atomically adds that allowance; replay
does not add it again. Denial, defer or STOP leaves the ceiling unchanged. Repeat
review and approval at every later exhaustion; no quality gate is waived.
See the gate-map for the exact commands, evidence fields and recovery rules.

Treat missing evidence as evidence acquisition, not an implementation repair, unless code or contract changes are actually required.

## Maintain Continuity

Before pausing or yielding:

- validate the run;
- update `next_allowed_action`;
- persist active artifact versions and invocation references;
- record open blockers, `required_approvals`, and bounce-backs;
- state the exact safe resume point.

On resume, reread this skill, the active `run_state.json`, and every active artifact. Run `validate-run` before new work. For a `REVISION`, this re-resolves the exact baseline and stops on archive, contract, report, manifest, inspection, target, or requirement-bundle drift; follow `FRESH_REQUIRED` rather than weakening or silently refreshing the baseline. Reconstruct state from artifacts, never from memory or transcript alone.

## Report the Outcome

Read [completion-report.md](references/completion-report.md) before reporting delivery, escalation, or cancellation. Store the report at `50_release/completion_report.md` for a released run and include its path in the user handoff.

Do not mark framework-phase approval or product acceptance on the user's behalf. End a successful run as delivered and awaiting user approval unless explicit approval is already recorded.

## Revision History

### 2026-10-23 — MP-20261023 local delivery intake

- Trigger: approved minor-revision local patch/full packaging while retaining formal release rules.
- Difference: B consumes linked hash-bound local delivery records as cumulative delta; ad hoc packaging and subsequent-release restrictions explicitly govern B candidates/formal releases.
- Compatibility: request/artifact schemas, exact baseline eligibility, independent verification and failed-gate stops are unchanged; external source evidence does not relax B target rules.
- Verification: all three modified skill entry points passed `quick_validate.py` in Python UTF-8 mode using the repository virtual environment; `git diff --check` passed. CLI flags and record fields were compared with implemented controls; broader integration evidence belongs in the framework revision record.
- Limitation: accepted local delivery records establish no formal release or baseline eligibility.

### 2026-09-13 — TW-20260913

- Trigger: requested two-workflow transition after practical product revisions.
- Difference: A prepares a consumable handoff; B starts with Root + Contractor
  through prepared or direct intake, source-bound adoption and selective returns.
- Components: this skill, gate/report references, semantic role guidance and controls.
- Compatibility: existing artifact/stage names and two repairs remain; old unbound
  runs retain their interface. New direct intake uses existing handoff metadata.
- Completed checks and limitations: see the authoritative sequential evidence and
  final regression results in `workspace/framework_development/two_workflow_review.md`.

### 2026-09-09 — intent realization and critical contract boundary

- Trigger: user requested removal of the pipeline framing agent, stronger delegated
  realization of incomplete intent, and critical review against confirmation bias.
- Change: new runs route to `intent_realizer`; Root coordinates bounded technical
  gaps and contractor independently challenges proposals against original intent.
  Existing framing skill remains unchanged for general use.
- Components: new role/skill, control-plane per-run owner, pipeline/contract guidance,
  reports and regression tests. Historical stage/path names stay compatible.
- Verification and limitations: authoritative completed evidence is recorded in
  `workspace/framework_development/intent_realization_revision.md`.

### 2026-09-07 — persistent-agent budget and reuse policy

- Trigger: repeated Jitter Management revisions retained completed semantic
  agent threads until a later packaging run could not spawn its required
  `problem_framer` and returned `agent thread limit reached`.
- Behavioral difference: Root now preflights task-lifetime agent capacity,
  keeps one reusable agent per exact semantic role, records any justified fresh
  instance, reserves required roles before optional delegation, and never
  assumes completion releases a slot. A failed post-boundary spawn requires a
  new invocation baseline after protected state changes.
- Principal components: this skill and `references/gate-map.md`.
- Compatibility and migration: product, artifact, and run-state schemas are
  unchanged. Existing agents may be reused only for their fixed roles; existing
  runs resume from validated artifacts with a fresh boundary when required.
- Verification: `quick_validate.py` passed under Python UTF-8 mode; the
  build-pipeline skill, delegation-policy, revision-framing, and control-plane
  regression set passed 85 tests with 1 skipped; `git diff --check` passed.
- Known limitation: the current collaboration surface exposes no agent-disposal
  operation, so a new root task may still be required when an existing task has
  already exhausted its retained thread budget.

### 2026-09-04 — out-of-pipeline minor-delta intake compatibility

- Trigger: framework review identified that locally tested minor tool revisions need a durable path into a later exact-baseline pipeline run.
- Behavioral difference: revision intake now discovers marked post-baseline minor revisions, carries them as cumulative delta rather than baseline evidence, and requires their affected requirements to be included in current contract and verification scope.
- Principal components: revision intake guidance in this skill and the new `$minor-tool-revision` workflow.
- Compatibility and migration: pipeline schemas and exact-baseline eligibility rules are unchanged; existing runs remain valid, and unmarked historical changes still require ordinary repository analysis.
- Verification: the new minor-revision skill passed `quick_validate.py` under Python UTF-8 mode; 27 relevant pipeline-skill, delegation-policy, and revision-framing regression tests passed.
- Known limitation: the marker is documentation-driven; repository/archive comparison remains necessary to detect unmarked source drift.

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
