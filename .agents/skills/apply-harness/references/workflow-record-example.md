# Structured Verification and Handoff Example

This illustrative report-review workflow separates arithmetic verification from a judgment about source coverage. The JSON is an example record, not a supplied schema, executed check, or universal format. All referenced artifacts and identifiers are fictional.

## Producer record

```json
{
  "contract_version": "report-review/1",
  "record_id": "review-001",
  "run_id": "run-001",
  "step_id": "review-report",
  "producer": "report-reviewer-v1",
  "subject": {
    "artifact_ref": "artifacts/report-v3.md",
    "version": "immutable:report-v3"
  },
  "inputs": [
    {"ref": "inputs/source-a.json", "version": "immutable:source-a-v1"}
  ],
  "checks": [
    {
      "requirement_id": "R1",
      "method": "scripts/check_totals.py",
      "method_version": "immutable:check-totals-v1",
      "status": "PASS",
      "observed": {"expected_total": 120, "actual_total": 120},
      "evidence_ref": "evidence/totals-001.json"
    }
  ],
  "judgments": [
    {
      "requirement_id": "R2",
      "criterion": "The conclusion is supported by the source population",
      "reviewer": "report-reviewer-v1",
      "assessment": "Insufficient support",
      "evidence_refs": ["inputs/source-a.json#sampling"],
      "assumptions": ["The sample represents the target population"],
      "uncertainties": ["The sampling method is undocumented"],
      "unresolved": ["Confirm sampling coverage before publication"]
    }
  ],
  "handoff": {
    "status": "BLOCKED",
    "proposed_next_step": "review-sampling",
    "publication_prerequisites": ["R1 passes", "R2 has supported acceptance"]
  }
}
```

## Contract and consumer behavior

The workflow author implements a domain contract for required fields, types, status values, resolvable references, and subject identity. They store the arithmetic checker and its verification inputs in the workflow source/run locations. The example's `immutable:` labels must resolve to actual retained versions in that implementation; a label alone does not establish immutability.

The publication consumer validates the record and referenced evidence against the report version it is about to publish. It confirms R1 evidence and checks the authoritative R2 assessment against the acceptance policy. A producer's PASS or proposed next step does not itself authorize publication. Here, it routes to sampling review because R2 lacks required support. The record is well-formed and arithmetic passes, but publication remains blocked.

After authorized review or repair, create a new linked record identifying its predecessor and the current subject version. Keep the original blocked record. Reuse earlier checks only if their evidence still applies to the current inputs and artifact version.

## Verification cases to implement

| Case | Expected consumer behavior |
| --- | --- |
| R1 evidence matches the subject and R2 has supported acceptance | Allow the publication step within its existing authorization |
| R1 evidence is absent | Reject the handoff as incomplete; do not publish |
| Evidence evaluates report-v2 but the subject is report-v3 | Reject the stale evidence |
| R1 is FAIL, BLOCKED, or NOT_RUN | Preserve that status and prevent publication |
| The example record above passes schema validation | Route to sampling review; do not publish |

These are proposed cases, not test results. The implemented workflow must retain actual execution outcomes before claiming its consumer gate works. The schema can check structure; it cannot by itself determine whether a source supports a conclusion.

## Interrupted work and procedure change

An illustrative current checkpoint can reference the record above:

```text
Current work: review sampling coverage for report-v3.
Confirmed: R1 arithmetic passed for report-v3; R2 remains unresolved.
Hypothesis: source-a's sample is representative; this is not confirmed.
Unfinished: sampling review; publication remains blocked by R2.
Read next: review-001, source-a-v1#sampling, current review/publication rules.
Next action: establish sampling coverage, then obtain the required assessment.
```

If the resumed consumer finds report-v4 or a changed review procedure, it compares
the actual change with the old subject and criteria. It retains review-001 as
history, identifies affected checks and judgments, and obtains current evidence
before publication. A checkpoint claiming readiness cannot override the blocked
record. Reading the checkpoint is not evidence that the agent reconciled the
change correctly; a recovery trial must observe its actual selected action.

Use the same record links when one Root changes procedures or a new agent takes
over. Update the checkpoint after material discoveries and before planned
handoffs; avoid copying the entire transcript or all evidence into it. These
names and outcomes remain fictional and do not establish a live recovery result.
