# Minimal Artifact Contract

## Purpose

This contract defines the smallest Phase 2 interface that can transfer a product-delivery run between roles without reconstructing the source conversation. It defines five artifacts, their ownership, their minimum content, their status namespaces, and the checks required before a downstream stage relies on them.

This is the documentation and interface contract. The companion `pipeline_control/` package implements deterministic validation, state transitions, packaging, boundary controls, semantic finalize, verifier preparation, and revision-baseline checks; it still does not make semantic judgments or user decisions.

## Contract Version

**New runs default to boundary control `1.2`** under the user-authorized post-S7
override `ITP-20261101-DEFAULT12` (2026-11-01); see the
[selected new-run operating procedure](agent-rollout.md).
Explicit `1.1` remains compatible and new legacy `1.0` requires explicit selection.
Existing runs retain their selectors, receipts and round history.
The [agent-owned artifact protocol](agent-artifact-protocol.md)
defines selected submissions and rounds; [procedure binding](procedure-binding.md)
adds the `1.2` assignment/result interface. The
[S3 recovery clarification](round-recovery-clarification.md) reconciles
uncounted evidence recovery with threshold review while preserving round history.
Selected operation preserves these semantic schemas and gates, configured models
and role boundaries. Threshold continuation requires independent review and actual
user approval; S7 supplies neither that approval nor migration/release authority.

- Contract version: `1.0`
- Semantic artifact schemas remain `1.0`; newly initialized `run_state.json` uses backward-compatible minor version `1.1` for repository-level boundary controls. Revision request fields, revision contract metadata, and verified-candidate binding are additive.
- Compatibility rule: a consumer must reject an unsupported major version rather than guessing.
- Change rule: after an artifact is used by a downstream stage, changes require a version increment and an explicit decision or deviation record.

## Fixed Run Layout

The framework owns the run hierarchy. YAML does not relocate these stage directories.

```text
workspace/build_runs/<project_id>/
  00_intake/build_request.yaml
  10_framing/problem_frame.md
  20_contract/product_contract.yaml
  30_execution/run_state.json
  30_execution/test_results.json
  30_execution/test_attempts/<attempt-id>/test_results.json
  30_execution/role_boundary/
  30_execution/semantic_finalize/failed_attempts/
  40_verification/verification_report.md
  40_verification/probes/
  40_verification/harness/attempts/
  40_verification/harness/cleanup/
  40_verification/harness/latest.json
  50_release/
```

The templates and Phase 2 example remain under `docs/contracts/`. A later manual pipeline may copy or instantiate them under `workspace/build_runs/<project_id>/`.

## Artifact Ownership

### 2026-09-13 two-workflow intake

Workflow A prepares realized intent and existing delegation; B begins with Root
and Contractor. Prepared B resumes A's run and audited brief. Direct B sets
existing `build_request.handoff.next_stage: contract` before initialization;
framing/gate remain PENDING and `problem_frame` stays null. Missing/framing route
retains the prepared/legacy sequence. All other gates and semantic owners remain.

New initialization binds request bytes with the existing active-reference
`content_sha256`. New contracts identify the active build-request version/hash
and, only for prepared intake, the active problem-frame version/hash in
`source_artifacts`. Local original-intent and delegation snapshots may declare
repository-relative `path` and `content_sha256` in `source_context`; declaration
requires those exact bytes at adoption and advancement. Hashes live in external
records, never self-referentially inside the artifact whose identity they express.
Unbound historical requests remain readable without retrofitted source identities.

Bound input changes stop downstream progression until the affected owners update
the consumed contract. Structurally valid intermediate states remain repairable.
For prior verification PASS before completed release, a recorded exact-report
bounce-back may reopen verification IN_PROGRESS. The old candidate identity remains
the review basis until a new PASS or formal repair; it cannot authorize release
while verification is in progress. Contract/candidate changes cannot bypass the
selected round limit or legacy two-attempt bound. See the [gate map](../../../../.agents/skills/build-tool-pipeline/references/gate-map.md).

This additive use of existing fields/statuses keeps semantic schema 1.0 and state
1.1. Completed checks, reasons and limits are in the
[two-workflow review (source history)](../provenance.md).

### 2026-09-09 additive intent-realization routing

New runs have `control.intent_realization: "1.0"`; their `problem_frame` semantic
owner is `intent_realizer`. Missing marker retains legacy `problem_framer`.
Explicit null/unknown marker values are invalid. The `framing` stage,
`10_framing/problem_frame.md`, `problem-frame` ID and existing headings remain
compatibility interfaces. Their content is now a realization brief, not a second
initial problem-discussion exercise. Do not rewrite historical run owners/hashes.
The existing templates/examples are legacy examples, not a new-run owner override.

| Artifact | Semantic owner | Persistence owner | Primary consumers | Owner may change content? |
| --- | --- | --- | --- | --- |
| `build_request.yaml` | User for requested behavior; Root Codex for faithful intake structure | Root Codex | Intent Realizer, Contract Agent, Root | Root may normalize structure but may not alter user intent. |
| `problem_frame.md` | Intent Realizer for marked runs; Problem Framer for legacy runs | Root Codex | Product Contract Agent, Root | The owner completes the body through the bound transport; Root registers it. |
| `product_contract.yaml` | Product Contract Agent | Root Codex | Implementer, Independent Verifier, Root | Contract owner may formalize intent but may not silently redesign approved behavior. |
| `run_state.json` | Root Codex; Phase 4 deterministic control plane for approved transitions | Root Codex/control plane | Every stage | Only the orchestration owner or approved control plane changes state. |
| `verification_report.md` | Independent Verifier | Root Codex | Root, repair owner, user | Verifier owns conclusions; Root may persist but may not convert failed or unverified results to passing. |

Each artifact has exactly one semantic owner and one persistence owner at a time. The same role may hold both responsibilities. Read-only agents return complete artifact bodies to Root; they do not receive an implied write permission.

Selected control `1.2` adds workflow-owned procedure assignments
and mandatory result binding through [procedure-binding.md](procedure-binding.md).
The `1.1` transport and round rules remain inherited; old receipts remain
unchanged. New initialization defaults to `1.2`. The assigned child loads original procedures and
inputs, while supported admission/forward commands enforce their binding.

For boundary control `1.1` or `1.2`, the assigned
specialist instead writes its complete noncanonical submission and returns compact
identities. Root registers its unchanged bytes and consumers read the registered
artifact. The selector, exact-file scope, digest binding and receipts are defined
in the [control protocol](agent-artifact-protocol.md); the bound
[invocation procedure](../../../../.agents/skills/build-tool-pipeline/references/invocation.md)
keeps generic semantic judgment independent. Write permission remains conditional
on the exact bound assignment; selecting a role alone grants no write scope.
Procedure-byte drift requires compatible recovery and a fresh owner binding,
never rewriting prior evidence. This introduces no semantic schema change.

## Common Provenance Rules

Structured artifacts use these common concepts:

- `schema_version`: the artifact schema major/minor version.
- `artifact_id`: stable identifier within the run.
- `version`: positive integer incremented when the artifact changes after first persistence.
- `lifecycle_status`: `DRAFT`, `ACTIVE`, or `SUPERSEDED`.
- `owner_role`: semantic owner role.
- `source_artifacts`: artifact IDs and versions used to create the artifact.
- timestamps: ISO 8601 values with an explicit timezone; `null` is permitted in an uninstantiated template only.

Markdown artifacts express the same information in their `Contract Metadata` section.

`ACTIVE` means the current version is the one downstream consumers should read. It does not mean that its semantic gate passed. Gate and readiness results use separate fields.

### Run-state 1.1 boundary-control extension

New runs retain the five-artifact semantic interface while adding deterministic persistence provenance to active references for `problem_frame`, `product_contract`, and `verification_report`:

- artifact version and canonical path;
- SHA-256 of the exact Root-persisted bytes;
- semantic owner and `root_codex` persistence owner;
- source invocation reference;
- matching role-boundary PASS evidence reference.

Canonical-file existence alone is not activation. Root normally uses `finalize-semantic-return` to finish the semantic invocation's mutation audit, validate a complete supplied body, archive history, atomically write and activate it, post-validate the run, and restore exact prior bytes on failure. The older `role-boundary finish` plus `persist-artifact` composition remains available only for legacy compatibility. Under legacy control, `problem_framer`, `product_contract_agent`, and read-only `explorer` invocations allow no run writes; `independent_verifier` may write only `40_verification/probes/**`. Selected control instead uses the exact assigned submission and invocation-scoped Verifier probes; process review permits only its exact review file.

Under legacy control, `intent_realizer` has the same no-write boundary. Activation validates the exact
run-selected owner in the returned body, active reference and boundary evidence;
the new and legacy roles are not interchangeable. Realization conditions and
source-linked proposals go inside the existing Constraints/Decisions/Assumptions/
Validation Needs sections. Contractor dispositions go in existing contract
decisions, assumptions and blockers. No additional semantic artifact is introduced.

The `control.verification_validation_identity` record is null until verification passes. At PASS it captures artifact ID/version/path/hash and validation time. When candidate inspection is complete it also records exact contract, manifest, inspection, and archive path/SHA-256 values as `candidate_binding`. Release entry and completion reconcile the current report bytes against this identity. Existing completed run-state `1.0` records remain valid for read validation without the new fields and are not implicitly migrated.

## Status Vocabulary

Status values are namespace-specific. Consumers must not infer one namespace from another.

### Artifact lifecycle

- `DRAFT`: incomplete or not yet accepted by its stage gate.
- `ACTIVE`: current authoritative version for the run.
- `SUPERSEDED`: retained for history but not the current version.

### Framing and contract readiness

- `PASS`: ready for the next stage without behavior-changing assumptions.
- `PASS_WITH_ASSUMPTIONS`: ready only if listed non-blocking assumptions are carried forward.
- `BLOCKED`: a material ambiguity or contradiction prevents reliable handoff.

### Stage and gate state

- `PENDING`: not started or not evaluated.
- `IN_PROGRESS`: active work is occurring.
- `PASSED`: the defined gate succeeded.
- `FAILED`: evaluated evidence did not satisfy the gate.
- `BLOCKED`: progress requires a material decision, permission, or external change.

### Requirement verification

- `PASS`: attributable evidence satisfies the requirement.
- `FAIL`: evidence demonstrates that the requirement is not satisfied.
- `UNVERIFIED`: available evidence cannot establish pass or fail.

### Overall verification assessment

- `READY`: all contractually applicable requirements pass and no blocker, waiver, or required approval remains.
- `NOT_READY`: at least one contractually applicable requirement fails or a release-blocking defect exists.
- `UNVERIFIED`: required evidence is missing or unusable, so readiness cannot be established.

This vocabulary adopts the meaning of the repository bounce-back policy. `NOT_READY` starts contract-preserving repair; `UNVERIFIED` starts evidence acquisition. Only Root evaluates the release gate.

### Decision status

- `APPROVED`
- `AGENT_DECIDED`
- `REJECTED`
- `DEFERRED`
- `SUPERSEDED`

`AGENT_DECIDED` is limited to reversible implementation-level choices that preserve approved behavior and phase scope.

### Issue status

- `OPEN`
- `RESOLVED`
- `ACCEPTED`
- `DEFERRED`

Every issue separately declares `blocking: true` or `blocking: false`. A blocking issue with `OPEN` status prevents a readiness `PASS` or a stage gate `PASSED`.

## Assumptions, Blockers, and Decisions

An assumption record must identify:

- a stable ID such as `ASM-001`
- the statement
- its source or owner
- whether it changes observable behavior if wrong
- whether user confirmation is required
- its status

A blocker record must identify:

- a stable ID such as `BLK-001`
- the blocking condition
- its owner or decision authority
- affected stage or requirements
- the resolution needed
- its status

A decision record must identify:

- a stable ID such as `DEC-001`
- the decision and rationale
- decision owner
- decision status
- source reference where available
- impact on behavior, scope, validation, or later stages

Empty lists must be present when no assumptions, blockers, or decisions exist. Omission is not equivalent to none.

## Requirement ID and Acceptance Rule

- Product requirements use `REQ-001`, `REQ-002`, and so on.
- IDs are unique within one product contract and are not reused.
- Once an approved contract is consumed downstream, existing IDs remain stable; new requirements receive new IDs.
- Requirement category is stored separately as `FUNCTIONAL`, `NON_FUNCTIONAL`, `DOCUMENTATION`, or `COMPATIBILITY`; it is not encoded in the ID.
- Every requirement present in the active contract is contractually applicable and belongs to verification scope. A non-applicable item belongs in exclusions or a decision record, not in the active requirement list.
- Conditional requirements remain applicable and state their triggering condition in the requirement statement.
- Importance, criticality, or business priority is not the primary verification classification and is not required on each requirement.
- Acceptance methods use `ACC-001`, `ACC-002`, and so on.
- Every contractually applicable requirement references at least one acceptance method.
- Every acceptance method references at least one existing requirement.
- One acceptance method may cover multiple requirements when one procedure produces attributable evidence for each.
- Acceptance methods state evidence method, procedure, expected result, and required evidence.
- Verification results reference requirement and acceptance IDs from the approved contract.
- The mapping remains inside `product_contract.yaml`; no separate trace file is part of the minimal contract.

## Verification Nature and Scope

The contract classifies requirements by how conformance can be demonstrated, not by how important the requirement is.

- Verification scope is `ALL_APPLICABLE_REQUIREMENTS`.
- Deterministic verification is the default and requires no exceptional requirement tag.
- Requirements needing semantic interpretation are listed explicitly in `verification_policy.llm_judgment_requirements`.
- A listed LLM-judgment requirement remains subject to evidence and explicit judgment criteria; it is not exempt from verification.
- An LLM judgment flag does not imply greater product importance or allow the verifier to change the contract.
- A requirement may combine deterministic evidence with LLM judgment. The acceptance methods define the evidence, and the flagged requirement list identifies the additional judgment need.
- The verifier reports `PASS`, `FAIL`, or `UNVERIFIED` for every applicable requirement, regardless of verification nature.

For every requirement listed in `llm_judgment_requirements`, at least one linked acceptance method must include `judgment_criteria`. Requirements not listed there must be decidable from the stated procedure, expected result, and attributable evidence without open-ended semantic judgment.

## Artifact-Specific Contract

### `build_request.yaml`

Required content:

- project identity and request kind
- requested outcome
- source-context references and their authority
- target repository and output path
- selected build profile
- user decisions, assumptions, blockers, and constraints known at intake
- handoff readiness for framing

User-editable values are documented inline in the YAML template. Paths are repository-relative unless explicitly marked otherwise.

A bounded delta request sets `project.request_kind: REVISION` and supplies both of these mappings:

```yaml
revision_of:
  run_id: <completed-run-id>
  archive_sha256: <sha256>
  product_contract_ref: product-contract@<version>
  product_contract_sha256: <sha256>
  verification_report_ref: verification-report@<version>
  verification_report_sha256: <sha256>
delta_request:
  scope_classification: BOUNDED
  requested_changes: [{id: DELTA-001, statement: ...}]
  explicit_non_changes: [{id: NONCHANGE-001, statement: ...}]
  feedback_evidence: [{id: FEEDBACK-001, source_ref: ..., summary: ...}]
```

The two mappings are required together and forbidden for other request kinds. Initialization re-resolves one release-passed, independently verified candidate with an exact contract/report/manifest/inspection/archive binding and the same target repository. An ineligible, broad, incompatible, ambiguous, missing, or hash-drifted baseline returns `FRESH_REQUIRED` before creating a run; it is never silently converted to fresh framing.

### `problem_frame.md`

Required sections:

- Contract Metadata
- Completion Status
- Input Reviewed
- Active Problem
- Objective and User Need
- Target UX Flow
- Scope
- Non-Scope
- Inputs and Outputs
- Failure Behavior
- Constraints
- Assumptions
- Decisions
- Open Issues and Blockers
- Validation Needs
- Handoff Readiness

Structural presence does not establish semantic sufficiency. The readiness result must agree with the recorded assumptions and blockers.

A revision frame is a complete current frame, not a delta note. It preserves exact baseline behavior where unchanged and explicitly consolidates requested changes, non-change claims, affected interfaces, migration impact, adjacent regression scope, and the evidence needed for all applicable requirements.

### `product_contract.yaml`

Required content:

- provenance and contract readiness
- product objective and observable interface
- scope and exclusions
- decisions, assumptions, and blockers
- atomic requirements with source references
- verification scope and the explicit list of requirements needing LLM judgment
- acceptance methods with evidence expectations
- requirement-to-acceptance references in the same file
- downstream handoff status

Internal architecture is included only when it is required by observable behavior, feasibility, compatibility, or acceptance.

A revision contract remains a complete current contract. Its optional `revision_control` is required for a `REVISION` run and contains:

- `mode: DELTA` and the six exact `revision_of` identities;
- every exact unchanged requirement as `requirement_ref` plus `baseline_bundle_sha256`, where the bundle hashes the full requirement record and every linked acceptance record;
- one `impact_map` entry for every `DELTA-*` and `NONCHANGE-*` item, with disposition, baseline/current requirement references, source/test/documentation/packaging references, migration impact, and `reverification_scope: ALL_APPLICABLE_REQUIREMENTS`.

Every baseline and current requirement must be classified exactly once as unchanged or impacted. Requirements may not disappear, and changing one shared acceptance record impacts every linked requirement.

### `run_state.json`

Required content:

- project and run identity
- current pipeline stage
- one status entry for every defined stage
- gate outcomes and evidence references
- active artifact versions and paths; new run-state `1.1` semantic references also require content hash, owners, source invocation, and boundary evidence
- active repair attempt and the maximum permitted attempts
- blockers and required approvals
- bounce-back events, their assignment, resolution state, and retry basis
- next allowed action
- semantic-role boundary control revision and the verification identity captured for release reconciliation
- for a revision only, `control.revision_baseline` with the resolved baseline run, target, contract, report, manifest, inspection, archive identities, and resolution time

`run_state.json` is generated state, not user configuration. JSON comments are not supported; field guidance is maintained here and in the template example values.

Allowed stage IDs are:

```text
intake
framing
contract
repository_analysis
implementation
verification
repair
release
```

An allowed transition normally moves to the next stage. `verification` may transition to `repair`, and a successful repair returns to `verification`. The maximum automatic repair attempts remains `2`. Phase 4 implements this enforcement through `pipeline_ops.py update-state`.

`validate-run` re-resolves a recorded revision baseline on every check. Removing a baseline run or changing any bound bytes deterministically blocks the revision. The record imports only the immediate verified candidate identity, never recursive lineage.

### Bounce-back trace

Every returned result that pauses or redirects a stage, requires Root or user action, starts repair or evidence acquisition, or will cause an agent to be called again must create a compact entry in `run_state.json.bounce_back_events`.

The semantic detail remains in the originating artifact:

- framing gaps and product ambiguity in `problem_frame.md`;
- contract contradictions, assumptions, blockers, and decisions in `product_contract.yaml`;
- failed requirements, missing evidence, risks, and repair requests in `verification_report.md`.

The run-state event is the coordination trace and must contain:

- unique `BB-###` ID and timestamp;
- origin role, invocation reference, result artifact reference, and returned result;
- assignee (`root_codex`, `user`, or another authorized role);
- classification, summary, affected stages, and affected requirement/acceptance references;
- required resolution and `OPEN`, `RESOLVED`, or `SUPERSEDED` status;
- resolution details when resolved, including resolver, resolution type, changed inputs/artifacts, decision references, and evidence references;
- retry target and whether retry is allowed;
- retry change basis proving that input, evidence, implementation, or decision state changed.

Allowed bounce-back classifications are:

```text
DISCOVERABLE_CONTEXT
NON_MATERIAL_CHOICE
IMPLEMENTATION_DEFECT
EVIDENCE_GAP
CONTRACT_CONTRADICTION
MATERIAL_AMBIGUITY
PERMISSION_OR_EXTERNAL_AUTHORITY
UNACCEPTABLE_RISK
REPAIR_LIMIT_EXHAUSTED
```

Allowed resolution types are:

```text
ROOT_ANSWERED
USER_DECIDED
CONTEXT_ADDED
IMPLEMENTATION_REPAIRED
EVIDENCE_ADDED
CONTRACT_REVISED
WAIVER_APPROVED
CANCELLED
```

An open event may block only its named affected stages; it does not automatically block safe earlier work. A resolved event may permit retry only when `change_basis` contains at least one of `INPUT_CHANGED`, `EVIDENCE_CHANGED`, `IMPLEMENTATION_CHANGED`, or `DECISION_CHANGED`. Root must not repeat an unchanged agent invocation.

A transient tool error recovered within the same agent execution, or an informational suggestion that changes no stage, gate, artifact, decision, evidence, or follow-up action, does not require a bounce-back event.

The initial five-artifact model does not add a separate bounce-back file. A dedicated append-only log may be proposed later only if pilots show that run-state history is too large, needs multiple writers, or requires independent audit controls.

### `verification_report.md`

Required sections:

- Contract Metadata
- Overall Assessment
- Inputs and Evidence Reviewed
- LLM Judgment Scope
- Requirement Results
- Missing or Unusable Evidence
- Contract, Interface, and Documentation Drift
- Repair Requests
- Risks, Waivers, and Blockers
- Revalidation Needs
- Root Return

Every contractually applicable requirement receives `PASS`, `FAIL`, or `UNVERIFIED` with evidence. Requirements flagged for LLM judgment must cite the applied judgment criteria. The inputs section identifies the exact contract, manifest, passing inspection, archive SHA-256, verifier-harness attempt and cleanup evidence, and any additional probes. A harness PASS is not semantic judgment. A polished summary cannot substitute for requirement-level results.

## Handoff Readiness Rules

A downstream stage may proceed only when:

1. every required upstream artifact exists at the active version;
2. structural validation succeeds;
3. the semantic readiness or gate result permits progression;
4. no open blocking issue affects the downstream work;
5. required assumptions are explicitly carried forward;
6. the current state permits the transition; and
7. no required user approval is outstanding.

The full transcript is not a required pipeline input. A source discussion may remain referenced for audit, but downstream execution must be possible from the active artifacts and named repository context.

## Structural Validation Expectations

Phase 2 validation checks:

- all five template files and all five example files exist;
- YAML and JSON files parse successfully;
- `schema_version`, artifact identity, version, lifecycle, and owner fields exist;
- example source-artifact references resolve to the expected artifact IDs and versions;
- required Markdown headings exist in order;
- allowed status values are used;
- IDs are unique within each namespace;
- every requirement has at least one acceptance reference;
- every acceptance reference resolves in both directions;
- verification scope is `ALL_APPLICABLE_REQUIREMENTS` and importance/criticality is not used as the default requirement filter;
- every LLM-judgment requirement reference resolves and has linked judgment criteria;
- every applicable requirement appears exactly once in the verification report regardless of verification nature;
- blockers use explicit blocking flags and statuses;
- bounce-back IDs are unique and allowed classifications/statuses are used;
- every open bounce-back has an assignee, required resolution, affected stage, and retry disabled until change occurs;
- every resolved bounce-back has resolution provenance and a non-empty retry change basis before the same agent may be called again;
- repair attempts and implementation-defect bounce events remain consistent;
- active artifact paths in `run_state.json` point to the five example artifacts;
- the run cannot claim release readiness when verification remains `UNVERIFIED`;
- the example uses embedded traceability and creates no separate trace artifact.
- a revision baseline is a completed release with an exact verification candidate binding and is rechecked for deletion or hash drift;
- a revision contract preserves exact unchanged bundles and completely, disjointly classifies all baseline/current requirements;
- immutable test attempts retain superseded failures while the canonical result identifies the active attempt;
- semantic finalize either activates the whole validated artifact/state pair or restores exact prior bytes and retains a failed-attempt journal;
- verifier preparation reconciles the exact candidate, extracts once, runs declared complete-suite repetitions, and retains cleanup evidence without making a verifier judgment.

The maintained deterministic CLI commands live in `pipeline_ops.py`. Boundary control, semantic finalize, immutable attempts, verifier preparation, and verified-baseline revisions do not change the five-artifact semantic interface or semantic conclusions. Their complete command and evidence contract is documented in `pipeline_control/README.md`. The control plane rejects progression when readiness, mutation boundary, active-byte identity, baseline provenance, or release reconciliation fails. Artifact contract major version `1` remains unchanged.

## Representative Example

`examples/filename_normalizer/` instantiates all five artifacts from the approved Phase 1 controlled case. It represents a snapshot ready to enter implementation:

- intake and framing have passed;
- the product contract is active and maps requirements to acceptance methods;
- implementation has not occurred;
- the active verification report has `UNVERIFIED` results because no implementation evidence exists;
- `BB-001` assigns the resulting evidence-acquisition bounce-back to Root and prevents an unchanged verifier retry;
- release is therefore not allowed.

This snapshot demonstrates both transcript-independent handoff and protection against false completion.

## Limitations and Deferred Work

- The templates are not formal JSON Schema or YAML Schema documents.
- No custom Product Contract Agent or Independent Verifier is created in Phase 2.
- The original Phase 2 snapshot did not include state-transition enforcement; Phase 4 now provides it without changing the five-artifact semantic interface.
- The Phase 6 repository-level mutation audit detects and gates unauthorized writes but does not provide per-agent OS permission enforcement, adversarial tamper-proof storage, or process/container isolation.
- No actual implementation or release package is produced by the example.
- Schema migration and backward-compatibility tooling are deferred until observed need.
- Read-valid historical releases without a complete verification `candidate_binding` cannot be used as delta baselines.
- Additional artifacts require pilot evidence and user-approved scope change where material.

## Migration from Superseded Context

- Preserve older engineering/UX handoffs and classify them in prose as `SUPERSEDED_CONTEXT`; do not overwrite, move, or activate them as one of the five canonical artifacts.
- `SUPERSEDED_CONTEXT` is not a `source_context.authority` enum. Use `REFERENCE_ONLY` unless the user or another approved artifact gives the source stronger authority.
- Create a new fixed-layout run and reference the old material from its build request. Do not copy a root-level legacy state or ad hoc frame into active state.
- Completed run-state `1.0` and `1.1` files remain read-compatible and are not auto-upgraded. Legacy boundary baselines without `path_policy` may finish in compatibility mode.
- Existing `role-boundary finish` and `persist-artifact` commands remain available. Old test results are not retroactively given immutable attempt history.
- A historical release without full `candidate_binding` is delta-ineligible and returns `FRESH_REQUIRED`. To proceed, author an explicit non-revision request; never reinterpret an incomplete `REVISION` request silently.
