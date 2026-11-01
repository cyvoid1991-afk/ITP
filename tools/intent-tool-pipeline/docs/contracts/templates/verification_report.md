# Verification Report

## Contract Metadata

- Schema version: `1.0`
- Artifact ID: `verification-report`
- Version: `1`
- Lifecycle status: `DRAFT`
- Semantic owner: `independent_verifier`
- Persistence owner: `root_codex`
- Source artifacts: `product-contract@1`, `run-state@1`
- Created at: `null` (replace with an ISO 8601 timestamp)
- Updated at: `null` (replace with an ISO 8601 timestamp)

## Overall Assessment

`UNVERIFIED` — Replace with `READY`, `NOT_READY`, or `UNVERIFIED` and an evidence-based rationale.

## Inputs and Evidence Reviewed

- List the exact contract path/version/SHA-256, manifest path/SHA-256, passing inspection path/SHA-256, archive path/SHA-256, implementation paths, immutable test attempts, verifier-harness attempt and cleanup evidence, commands, outputs, documentation, and any additional probes reviewed.
- State explicitly that harness status is deterministic preparation evidence, not the independent verifier judgment.

## LLM Judgment Scope

- List only requirements named in `product_contract.yaml.verification_policy.llm_judgment_requirements`, the applicable judgment criteria, and the evidence to which judgment was applied. Write `None` when empty.

## Requirement Results

| Requirement | Status | Acceptance methods | Evidence method | Evidence | Finding |
| --- | --- | --- | --- | --- | --- |
| `REQ-001` | `UNVERIFIED` | `ACC-001` | `TEST` | None | Replace with an attributable finding. |

Every contractually applicable requirement must appear exactly once with `PASS`, `FAIL`, or `UNVERIFIED`, including requirements that do not require LLM judgment.

## Missing or Unusable Evidence

- Identify missing evidence and the requirement IDs it prevents from being evaluated. Write `None` when empty.

## Contract, Interface, and Documentation Drift

- Identify contradictions or drift separately from implementation defects. Write `None` when empty.

## Repair Requests

- For each implementation defect, name affected requirement IDs, observed evidence, expected behavior, and required revalidation. Write `None` when empty.

## Risks, Waivers, and Blockers

- Record unresolved risks, approved waivers, and open blockers. A waiver requires user authority. Write `None` when empty.

## Revalidation Needs

- List the exact checks that must run after repair or evidence acquisition.

## Root Return

- Overall assessment: `UNVERIFIED`
- Failed requirements: `None`
- Unverified requirements: `REQ-001`
- Recommended next action: Acquire the required evidence and re-evaluate; do not release.
