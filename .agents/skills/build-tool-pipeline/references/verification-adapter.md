# Verification Adapter

For explicitly selected `1.2` runs, load the workflow-owned assignment via
[assignment-entry.md](assignment-entry.md). Apply the selected `1.1` boundaries
below. Product reports include exactly one procedure-binding JSON comment;
threshold reviews include one top-level `procedure_binding` mapping, using the
loader's exact `required_result_binding`. Keep process review and product
verification distinct. Missing binding/evidence never implies a passing verdict.

Apply only to the governed run named by Root. Read [invocation.md](invocation.md)
for the calling boundary. This document binds the reusable `independent_verifier` role
to the existing artifact contract; it does not apply to ordinary role use.

For selected --review-event process work, go directly to Selected threshold
process review below. Its evidence shape replaces the product execution contract;
do not impose a product requirement catalog, product-report template or semantic
report finalization on process review. Keep the reusable role's independence and
no-implementation boundary.

For product verification, use the native `$independent-verification` skill for verification and revalidation tasks. If the skill is unavailable, return `UNVERIFIED` and identify the missing dependency.

Then read `docs/contracts/README.md` as the active repository execution procedure. Contract version `1.0` is the approved baseline and must not be silently revised.
Read `docs/contracts/templates/verification_report.md`
for the exact report headings, metadata and evidence fields.

Execution contract:

- Accepted inputs: the exact active `product_contract.yaml`, release manifest, passing package inspection, release archive, and their captured references and SHA-256 identities; the active `run_state.json`; the completed verifier-harness attempt with command outputs or test results; cleanup evidence; product source path; and active run directory explicitly named by the parent.
- Verification scope: evaluate every applicable `REQ-###` exactly once against its linked acceptance method and attributable evidence.
- Harness interpretation: a verifier-harness `PASS` establishes only that its governed commands and cleanup completed against the captured candidate. It is operational evidence, not semantic judgment and not by itself a requirement `PASS` or release decision.
- Required output: the complete verification_report.md with the existing exact headings and metadata. Selected control.semantic_role_boundary: "1.1" writes it at the exact start-result submission_path; its canonical-path metadata remains the named active report path. Legacy governed use returns the complete body and a compact summary. Root Codex owns registration, canonical activation and state transitions.
- Canonical-report boundary: do not create, edit, replace, or directly write `40_verification/verification_report.md`.
- Only permitted writes: selected "1.1" artifact work allows its exact assigned report submission plus isolated probes under 40_verification/probes/<audit-id>/ supplied by start. Legacy governed use retains the named active run's 40_verification/probes/ allowance. A threshold process review instead allows only its exact round-review.json file, with no parent-directory probe grant. Do not write elsewhere in 40_verification/.
- Delegation: prohibited. Do not spawn, steer, or otherwise manage sub-agents; perform the verification and return the result directly to Root Codex.
- Product boundary: do not create, edit, move, or delete any file under the target product source tree, including delivered tests, documentation, configuration, expected outputs, or generated product artifacts.
- Framework boundary: do not modify `.codex/`, `.agents/`, `agents/`, framework source, artifact-contract templates/examples, `run_state.json`, or release contents.
- Existing tests are evidence: inspect or execute them, but do not change them. New verifier-owned tests use only the authorized invocation probe scope and must import or execute the product without patching the delivery to pass. Process-review mode grants no additional test/probe files.
- Runtime evidence: prefer direct execution when practical. Record commands, exit codes, outputs, evidence paths, environment limitations, and what each observation proves.
- Status integrity: use requirement results `PASS`, `FAIL`, or `UNVERIFIED`; use overall assessment `READY`, `NOT_READY`, or `UNVERIFIED`. Do not convert missing evidence into failure unless the contract requires that evidence and it is demonstrably absent.
- Repair boundary: describe actionable repair requests and revalidation scope, but do not apply repairs.

## Output transport

Before finalizing, inspect filesystem changes attributable to this invocation and
report any write outside its exact assigned allowance as a boundary failure.

### Selected compact return

Under selected "1.1", complete the assigned report even for NOT_READY or UNVERIFIED
and return its actual path, artifact ID/version, content SHA-256, invocation,
assessment, requirement-result summary, inputs read, unresolved items and evidence
references. Root registers those bytes without changing the verdict and consumes
the actual registered report. Do not claim canonical activation or release approval.

### Legacy full-body return

Legacy governed use returns the complete report body even for NOT_READY or
UNVERIFIED. Do not write the canonical report or approve release.

## Selected threshold process review

This separate assignment requires explicit selected control "1.1" and
role-boundary start --review-event <BB-ID>, mutually exclusive with --artifact.
It is process review of exhausted modification rounds, not product verification,
a new permanent role or approval of additional work. Load this adapter and the
retained round, source/candidate/report and original-intent references supplied
by Root. Keep the generic Verifier's independence and no-implementation boundary;
do not present process evidence as a requirement verdict.

Write only the returned exact review_path:
40_verification/probes/<audit-id>/round-review.json. The directory is precreated;
its parent is not an ephemeral/probe write grant. Create no product-report
submission, artifact version reservation or registration receipt.

Use schema_version "1.0", artifact_type "iteration-threshold-review", run_id,
reviewer_role "independent_verifier", reviewer_invocation_ref and the event's
exact basis. Supply recommendation STOP, REQUEST_USER_DECISION or
BOUNDED_CONTINUATION; unresolved_issues, observed_progress, likely_causes and
evidence_refs as lists; proposed_changed_approach and intent_impact. A bounded
recommendation has intent_impact "UNCHANGED" and a positive finite integer
additional_rounds; other recommendations use zero. Preserve unresolved intent
changes for separate user decision. Return the actual review path/hash,
invocation, recommendation, allowance, unresolved items and evidence references.

Root finishes the boundary and retains PASS before presenting a bounded
recommendation to the user. The reviewer cannot implement corrections or approve
its own recommendation. Only an actual affirmative user response to the exact
allowance and approach can authorize Root's existing threshold resolve operation;
silence, a Root paraphrase or the recommendation alone grants no rounds.
