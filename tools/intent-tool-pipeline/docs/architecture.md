# Two-workflow revision specification — TW-20260913

## Current layout note

The specification and dated phase records below are retained provenance.
Current Nexus_AI placement puts pipeline runtime and governance documents under
`tools/intent-tool-pipeline/`; shared `.agents/` and `.codex/` remain at repository
root. Historical references to publishing documents at the root refer to the
earlier flat framework layout. Read [current framework](current-framework.md)
and [migration](migration.md) for current paths. This does not revise recorded
phase outcomes or grant new pipeline authority.

## Authority and scope

This document preserves the two-workflow responsibility and flow specification.
Current operating authority comes from the user's request, AGENTS.md and the
maintained v0.3 documents in docs/governance/. Original transition plans and
predecessor documents are historical provenance, not required runtime inputs;
see [source provenance](provenance.md).

## Responsibility and flow

| Owner | Workflow A: intent refinement / realization | Workflow B: intent implementation |
| --- | --- | --- |
| User | Interactively converges purpose, experience, preferences and material choices, often in external ChatGPT; supplies accessible intent and decisions | Decides newly discovered material choices outside existing authority; accepts the delivered product |
| Root | Preserves source intent; prepares a minimal authority skeleton; investigates; obtains necessary user decisions; records existing delegation; persists and binds the handoff | Performs first intake with Contractor; supplies evidence, selects delegated engineering trade-offs, implements and coordinates bounce-backs; owns state, persistence and release |
| Intent Realizer | Authors realized brief, derived conditions, uncertainty and realization readiness | Reviews affected brief content when needed; does not become a mandatory first B invocation or a governance/authority owner |
| Contractor (`product_contract_agent`) | May trial-consume the handoff; its intake is independent of Realizer readiness | Owns actual contract intake, complete contract, acceptance and contract readiness; corrects contract semantics |
| Verifier (`independent_verifier`) | No contract or delegation authorship | Independently judges requirement evidence and revalidation; Root cannot replace or direct its verdict |

Prepared flow: user/external discussion → supplied intent → Root + Realizer (A)
→ prepared handoff → Root + Contractor intake (B) → contract → repository analysis
→ implementation/tests → candidate packaging/inspection and existing verification
harness → independent verification → bounded repair when eligible → release.

Direct flow: clear/simple request → Root + Contractor intake (B) → the same
contract, implementation, verification, repair and release obligations.

An operational workflow boundary is not a new control-plane stage. B intake is
the joint examination before contract authoring; a prepared run resumes its
existing contract stage rather than repeating the completed A stages.

## Inputs, outputs and handoff criteria

A receives the accessible source intent, explicit user decisions, constraints,
approved scope and relevant existing product/baseline evidence. External chat is
not an automatically available input. Root retains the supplied source text or
accessible source references, identifying excerpts, revisions and authority.
Root summaries and technical proposals remain distinguishable from user choices.

A produces one logical handoff using existing records:

- source intent and explicit decisions, with applicable versions/locations;
- Realizer-authored complete brief and its readiness/return provenance;
- Root's lightweight task delegation boundary, grounded in existing policy and
  decisions, with user-reserved matters and any unapproved authority request;
- assumptions, open decisions, affected holds, independent work, evidence and
  re-review triggers; a compact index identifies the exact applicable versions.

The handoff is ready when Contractor can evaluate obligations without materially
guessing the intended outcome, relevant conditions or authority. Important
unresolved semantic choices cannot be hidden as defaults. Visible non-blocking
assumptions and delegated implementation choices may remain. Root freezes the
references and owner-adopted bytes; this neither approves new authority nor
overrides Realizer readiness. A ready brief does not compel a ready contract.

B receives that handoff, or the clear direct request with original sources and
common authority rules. Root checks completeness, currency, provenance, pending
decisions and delegation; Contractor checks meaning, feasibility conditions,
scope and acceptance readiness against original sources. B outputs the complete
current contract, implemented product, attributable tests/package evidence,
independent verdict, revision history and completion report.

Direct entry is appropriate only when the outcome, observable scope and material
constraints are sufficiently clear, Contractor can formalize acceptance, and no
unresolved material choice needs upstream realization. Root records this basis
in the existing intake rationale/decisions. A full delegation template or a
synthetic Realizer brief is not required. Uncertain technical details alone do
not disqualify direct entry; discovery can occur under Root in B.

## Returns, delta checks and preserved gates

| Issue | Resolution and owner |
| --- | --- |
| Missing accessible context or bounded technical evidence | Root supplies/investigates in B; receiving owner reviews the affected result |
| Delegated engineering choice or implementation failure | Root resolves in B, with required tests and Verifier revalidation |
| Contract misstates already explicit intent | Contractor corrects and reassesses in B; correction alone requires no new user approval |
| Brief error with existing source-supported answer | Realizer corrects the affected brief through Root; no full intent restart |
| New material meaning, preference, scope, acceptable loss or external authority unsupported by existing sources/delegation | Hold affected commitment; return only that issue to A/user with evidence, recommendation and realistic consequences |
| No useful next technical approach or exhausted operating allowance | Report limits and needed input/resource/direction; do not ask the user to supply a technical answer or disguise repair |

On an upstream change, preserve the original source and explicit change decision,
update affected handoff versions and delegation, and route each changed semantic
artifact to its owner. Compare both the individual delta against the last valid
basis and cumulative behavior against original intent plus explicit user changes.
Root decisions never reset the user-intent baseline. Unaffected work may continue
within authority; affected reviews, tests, approvals and verdicts must be renewed
before their gates pass. Existing blockers, required approvals, bounce-back events,
semantic finalization and candidate identity checks remain authoritative.

The formal repair maximum stays two, counted on existing repair-stage entry.
Initial intake/context clarification is not automatically repair. Post-verification
contract/code repair still consumes the applicable attempt; an A return or a new
run cannot reset it. No acceptance weakening or substitute Root PASS is permitted.

## Existing-document and implementation impact

| Component | Required revision | Preserved / obsolete assumption |
| --- | --- | --- |
| Root Autonomy v0.3 | Add A support, B direction and prepared/direct intake responsibilities | Preserve stable semantic principles; remove universal realization-first interpretation |
| Delegation & Delta Procedure v0.3 | A preparation; B consumption; selective return; source/version and cumulative checks | Preserve bounce-back classification, owner adoption and repair; obsolete B always drafts delegation from scratch |
| Delegation Template v0.3 | Prepare/maintain in A; reference in B; direct path uses only needed exceptions | No duplicate product contract; no authority created by writing |
| `intent-realization` skill and existing Realizer config | Explain self-contained A inputs, handoff and readiness, scoped return | No new role or broadened authority; preserve user-edited model |
| `build-tool-pipeline`, contractor skill/config and root routing | Root + Contractor B intake; prepared/direct paths; selective feedback | Preserve contractor critical review and all downstream gates |
| Control plane, initializer and relevant tests/docs | Minimal route-aware prerequisites and source identity validation | Preserve state enums, semantic schemas, legacy ownership, boundary audit and verification harness |
| Completion report | Show entry path, source/delegation basis, important choices, holds and revalidation | Preserve delivery/approval outcomes and evidence requirements |

## Implementation decisions and rationale

1. Preserve v0.2 inputs and publish v0.3 successors at the root. Link the common
   semantic instruction from root routing and the procedures from relevant skills;
   do not duplicate the common authority policy in two workflows.
2. Reuse the existing A run and its audited `problem_frame` when entering B. The
   compatibility `framing` stage/path stays intact; no repeated Realizer invocation
   is needed merely to consume the prepared handoff. A can stop at that handoff.
3. Reuse `build_request.handoff.next_stage: contract` for explicit direct B entry,
   and `framing` (including legacy missing-field behavior) for A/legacy routing.
   The existing field is the route discriminator; no state enum, agent, harness
   or new control marker is needed. The unused framing stage remains `PENDING`,
   never reported as a fictitious PASS. Downstream gates omit it only for an
   explicitly validated direct route. Route changes after consumption must not
   invalidate provenance or become an escape from failed framing/repair gates.
4. Use existing source references, decisions and durable run records to bind the
   handoff. Keep semantic authorship attributable through existing boundary and
   finalize evidence. Mechanically detectable stale inputs block advancement;
   semantic fidelity still requires owner review rather than an automatic claim.

These decisions implement the supplied transition, create no new user authority
or product requirement, and preserve unrelated baseline policy. Exact minimal
code changes and compatibility tests are Phase 3 work.

## Phase 1 review — completed 2026-09-13

Reviewed the transition and all three baseline documents against current skills,
role configs, artifact contract and control constraints. The prepared, direct,
technical-gap, miswritten-contract and material-loss cases have a distinct next
owner and hold condition. Root's storage and handoff binding do not override
semantic authorship. No material responsibility/handoff ambiguity remains.
Phase 2 may now revise and trial the upstream handoff; B runtime is unchanged at
this checkpoint. No product-quality improvement is claimed from this review.

## Phase 3 implementation addendum

The implementation uses the selected existing-field route and source identities.
An actual control gap required one narrowly scoped transition proposal: a prior
verification PASS could not be reopened when new intent/evidence invalidated it.
Before adopting it, Root explained the need for recorded revalidation using the
existing event, status and repair vocabulary. The resulting transition requires
an exact-report open bounce-back and prior candidate binding, reopens verification
IN_PROGRESS and clears incomplete release readiness. It does not reopen a completed
release or grant a new repair attempt.

Independent review exposed a first-draft repair bypass when revalidation cleared
the previous candidate. The final implementation retains that existing identity
until formal repair or a new verified PASS. Contract changes require repair before
adoption; changed candidate or packaged source bytes cannot pass evidence-only
review. Evidence-only reconsideration requires a new owner return. Canonical source
checks apply before completed release; a retained completed baseline remains bound
to its archive because later authorized revisions may change the live source tree.

Direct runs requiring a later native A return preserve their B route and repair
history and link a scoped preparation run/source snapshot. They do not manufacture
an audited frame or change the route to erase failed gates. Original source meaning,
authority, cumulative effects and cross-run repair continuity still require Root
and semantic-owner judgment; hashes cannot prove these properties automatically.

No unresolved framework decision requiring user judgment remains. The realized
boundaries implement the supplied transition without new agents, harnesses, state
enums, user authority or repair allowance. Actual results and known limits are in
`two_workflow_review.md`; this addendum does not rewrite the Phase 1 checkpoint.

## Revision history

### 2026-09-13 — TW-20260913-P1

- Trigger: user-requested sequential two-workflow framework transition.
- Difference: defined A/B responsibility, handoff, direct and scoped-return rules
  and mapped changes to the existing implementation before editing workflow code.
- Components: this specification only at Phase 1 completion.
- Compatibility: v0.2 source documents, user-edited model, deleted historical
  record, product trees, current run state and existing gates remain unchanged.
- Verification: cross-document responsibility/source/repair review and read-only
  control inspection completed; no executable changes or runtime tests yet.
- Limitation: Phase 2 handoff trials and Phase 3 integrated execution remain to be
  performed; their results will be recorded separately.
