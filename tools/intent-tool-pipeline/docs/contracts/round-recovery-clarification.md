# S3 threshold review after evidence recovery

**A verified, unchanged-subject evidence recovery may supply the latest threshold-review basis without changing the exhausted round's original result or granting another round.**

- Record: `ITP-20261030-ARTIFACT-S3-C1`, 2026-10-30.
- Scope: a bounded compatibility clarification to D4-D6 in the frozen [S1 protocol](agent-artifact-protocol.md). Preserve that document and both plans byte-for-byte as the design baseline. This addendum governs the interaction described here.
- Authority: Root's authorized S3 implementation and technical reconciliation, reviewed by the read-only S3 source reviewer. The existing user decision remains independent review followed by explicit user approval; this does not authorize any actual additional round.

## Decision basis

| Fact | Interpretation | Impact |
| --- | --- | --- |
| D5 permits uncounted evidence-only recovery with an unchanged subject | A fresh recovery report can follow the fourth completed modification round | The round count and original completed result must remain immutable |
| D4 records each latest terminal result | A recovered result becomes the latest report | It must not be hidden or replaced by an earlier report |
| D6 originally requires “the exact latest terminal result equal to the last completed round's result” | Literal equality makes continuation unreachable after legitimate evidence recovery | Permit an authenticated recovery lineage to that exact completed round, retaining every authority and subject check |

The alternative is to stop permanently after valid evidence recovery, or rewrite the completed round. Both conflict with accepted recovery/history behavior. The clarification adds proof obligations instead of treating equal archive hashes alone as sufficient.

## Required proof

1. The existing allowance is exhausted, its last round is COMPLETED, and no round is IN_PROGRESS.
2. Either latest equals that round's result, as originally specified, or it is a later uncounted recovery result. Each recovery receipt and authenticated input baseline has `round_number: null`.
3. The hash-bound pre-invocation state and an applicable `EVIDENCE_GAP` event trace each recovery report to its predecessor. Report versions strictly increase forward; backward traversal is finite and must reach the exhausted round's exact original result. A matching subject without this lineage is insufficient.
4. Contract and archive identity remain equal throughout recovery, with current source/manifest/archive reconciliation. Unknown identity or drift blocks continuation.
5. The review and actual user approval bind the exact current latest result, finite allowance and changed approach. Retain the original completed round result, all receipt identities and the review inputs. Historical authorization remains resolvable after later counted work.

This adds no counter, semantic artifact, stage, automatic allowance or user authority. The existing threshold basis fields remain unchanged. Missing, conflicting or unverifiable lineage is a rejection, not a reason to infer approval. Initial default selection, legacy behavior, quality gates and operational activation remain unchanged.

## Verification status

Implementation and regression evidence belong in the [S3 checkpoint index](../../workspace/framework_development/README.md). This clarification alone is not a runtime PASS or live-role result.
