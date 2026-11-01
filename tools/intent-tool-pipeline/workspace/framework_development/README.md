# Framework maintenance

Keep new pipeline framework plans and retained verification evidence here.
Current instructions are indexed in [current framework](../../docs/current-framework.md).
Record pipeline revisions in [tool history](../../CHANGELOG.md), and cross-cutting
repository policy in [root history](../../../../CHANGELOG.md). This directory is
under the tool runtime root. Omitted original source history is described in
[provenance](../../docs/provenance.md).

## Revision plans

- **Current default:** `ITP-20261101-DEFAULT12` applies the user's post-S7
  instruction: new runs default to `1.2`; choose `1.0` only on an explicit legacy
  request. Existing run selectors and history remain unchanged. Current results
  are retained in `aa-impl/d12-completion.md`.
- **Preserved S7 execution record:** [S7 checkpoint](aa-impl/s7-checkpoint.md) records
  activation and closure of the selected new-run procedure. Prefer explicit
  `1.2`; default `1.0` remains unchanged. The
  [operating procedure](../../docs/contracts/agent-rollout.md) defines selection,
  procedure-drift handling and compatible recovery; existing records are preserved.
- **Preserved S6 execution record:** [S6 checkpoint](aa-impl/s6-checkpoint.md) and
  [acceptance reconciliation](aa-impl/s6-acceptance.md) track distribution,
  regression and rollback validation. S6 is complete; S7 activation remains
  separate and legacy 1.0 stays the default. The
  [rollout instructions](../../docs/contracts/agent-rollout.md) describe the
  compatible reader/recovery route without migrating existing runs.
- **Preserved S5 execution record:** read the [S5 checkpoint](aa-impl/s5-checkpoint.md)
  and [acceptance reconciliation](aa-impl/s5-acceptance.md), with both preserved
  plans and the [S5 design addendum](aa-impl/s5-design-addendum.md). Explicit control
  `1.2` implements workflow-owned procedure assignments and bound admission;
  actual role trials cover Direct B, prepared A-to-B, exact-baseline revision,
  counted modifications and recovery. The checkpoint records the current exit
  decision and separate regression/distribution limits. S6 rollout/distribution
  closure and S7 activation remain separate; legacy selection stays the default.
- [Agent-owned artifact revision](agent-artifact-revision-plan.md): revision 1.2
  on 2026-10-29 centers specialist authority to complete stage work and reduces
  Root overlap through scoped artifacts and reference-based handoffs. Root owns
  a maximum of four post-verification modification-to-verification rounds,
  regardless of failed-item count; initial intent/contract iteration is excluded.
  Existing gates, early escalation and separate threshold review remain. Round
  lifecycle/recovery and review-resumption details are frozen in the S1 protocol.
  The plan preserves the design baseline; current execution status is recorded
  in the checkpoints below. S7 records the current operational activation decision.
- [Staged implementation companion](agent-artifact-implementation-plan.md):
  document 1.0 on 2026-10-29 defines S0-S7, preserved interfaces, minimal source
  deltas, protocol decisions, acceptance mapping and checkpoint/resume records.
  Read it together with revision plan 1.2. It preserves the parent and records
  the observed non-green test baseline. Its initial ledger is the planning
  snapshot; use the current checkpoint when resuming execution.
- [S0 execution checkpoint](aa-impl/checkpoint.md): on 2026-10-29, S0 completed
  source-bound baseline capture and failure investigation. Outcome: PROCEED to
  S1. Full suite: 338 passed, 4 skipped, 1 distribution-link failure; focused
  harness probe: 7 passed. Prior Windows evidence-promotion failure remains
  unresolved but was not reproduced. S1-S7 are NOT_STARTED; no runtime change
  or activation occurred. This is the retained S0 result; use S3 below for the
  latest execution status.
- [S1 execution checkpoint](aa-impl/s1-checkpoint.md): S1 freezes the
  [minimal control protocol](../../docs/contracts/agent-artifact-protocol.md).
  D1-D7 are resolved for implementation, including the user's independent-review
  then user-approval rule for additional rounds. At that checkpoint, S2-S7 were
  NOT_STARTED and runtime controls/permissions unchanged. Preserve it as the
  design result; use S3 for the latest implementation status.
- [S2 execution checkpoint](aa-impl/s2-checkpoint.md): S2 COMPLETE, PROCEED to
  S3 when authorized. Exact submissions, input/digest binding, registration
  receipts and interruption/replay recovery are implemented for selected
  fixtures. Full suite: 444 passed, 5 skipped, 1 distribution-link failure;
  source review has no remaining D1-D3 blocker. Legacy default, role permissions
  and semantic gates remain unchanged. S3-S7 are NOT_STARTED; selected round
  progression and operational activation remain blocked. Read both plans, the
  frozen protocol and S3 below when resuming. This remains the historical S2 result.
- [S3 execution checkpoint](aa-impl/s3-checkpoint.md): on 2026-10-30, S3 COMPLETE,
  PROCEED to S4. Selected controls now retain one count per modification round,
  exact terminal/replay linkage, unchanged-subject recovery, fourth-round PASS
  and a stop before further modification without independently reviewed,
  user-approved finite continuation. A separate
  [recovery clarification](../../docs/contracts/round-recovery-clarification.md)
  resolves threshold review after uncounted recovery without rewriting history.
  Final full suite: 537 passed, 5 skipped, 1 existing distribution-link failure;
  source review has no remaining blocker and extracted commands load. Default
  legacy behavior, role permissions and original design documents are unchanged.
  S4-S7 and operational activation were pending at that checkpoint. Preserve this
  S3 result; use S4 below for current status.
- [S4 execution checkpoint](aa-impl/s4-checkpoint.md): on 2026-10-30, S4 COMPLETE,
  PROCEED to S5. Three reusable semantic bodies remain unchanged; generic runtime
  output boundaries and selected ITP procedures are separated. Ordinary/legacy
  behavior and models are preserved. Three exact-role canaries loaded the new
  instructions and passed file-write audits. Final full suite: 553 passed,
  5 skipped, 1 distribution-link failure; final scoped checks are retained in
  the checkpoint evidence. S5 production-adapter integration, S6 distribution
  closure and S7 activation remained pending at S4. Preserve this historical
  result; use the S5 checkpoint above for current execution status.
- [Post-S4 procedure-enforcement review](aa-impl/s4-harness-review.md): assesses
  the requested shift from Root-assembled procedure prompts to workflow-owned
  assignments, subagent procedure loading and admission enforcement. Recommends
  a bounded supplement before S5, preserving S0-S4 and generic role semantics.
  This is a review/proposal; no new control or revised execution sequence is
  activated by the document.
