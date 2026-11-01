# Problem Frame

## Contract Metadata

- Schema version: `1.0`
- Artifact ID: `problem-frame`
- Version: `1`
- Lifecycle status: `DRAFT`
- Semantic owner: `problem_framer`
- Persistence owner: `root_codex`
- Source artifacts: `build-request@1`
- Created at: `null` (replace with an ISO 8601 timestamp)
- Updated at: `null` (replace with an ISO 8601 timestamp)

## Completion Status

`BLOCKED` — Replace with `PASS`, `PASS_WITH_ASSUMPTIONS`, or `BLOCKED` and a one-sentence rationale.

## Input Reviewed

- List only the named inputs actually reviewed.
- For a revision, list the resolved baseline run, contract, verification report, and archive identities plus every delta/non-change/feedback item.

## Active Problem

Describe the problem being solved without proposing implementation.

## Objective and User Need

Describe the target outcome and why the user needs it.

## Target UX Flow

1. Describe the externally visible flow in order.

## Scope

- List included behavior.
- For a revision, consolidate inherited and changed behavior into the complete current scope and name affected interfaces.

## Non-Scope

- List intentionally excluded behavior.
- Preserve explicit non-change claims without silently paraphrasing exact baseline requirements.

## Inputs and Outputs

Describe externally visible inputs, outputs, side effects, and interfaces.

## Failure Behavior

Describe material invalid-input, operational-failure, and partial-success behavior.

## Constraints

- List compatibility, dependency, safety, and environmental constraints.

## Assumptions

Use stable IDs such as `ASM-001`. For each assumption record its owner, source, impact if wrong, confirmation need, and status. Write `None` when empty.

## Decisions

Use stable IDs such as `DEC-001`. Distinguish user-approved decisions from `AGENT_DECIDED` implementation-level choices. Write `None` when empty.

## Open Issues and Blockers

### Blocking

Use stable IDs such as `BLK-001` and state the required resolution. Write `None` when empty.

### Non-Blocking

List visible issues that can be carried forward without changing the readiness result.

## Validation Needs

- Describe behavior and evidence that the product contract should formalize.
- For a revision, include migration impact, adjacent regressions, and full all-applicable reverification rather than delta-only checks.

## Handoff Readiness

State the next stage, required carried assumptions, unresolved blockers, and whether the next role can proceed without reconstructing the transcript.

For a bounded revision, confirm this is a complete current frame and the exact verified baseline remains usable. Return fresh-framing need instead of forcing delta mode when the change is broad, incompatible, or materially ambiguous.
