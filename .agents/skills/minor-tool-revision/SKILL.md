---
name: minor-tool-revision
description: Implement a bounded compatible revision to one existing authoritative local tool, optionally deliver a local patch or full package, and preserve evidence for a later pipeline run. Also use for package-only local delivery with current source evidence. Exclude new tools, broad behavior, incompatible schemas, migrations, formal verified releases, or changes needing a new product contract or independent verification.
---

# Minor Tool Revision

## Repository integration

For pipeline work, first read [the tool rules](../../../tools/intent-tool-pipeline/AGENTS.md).
The pipeline project root is `tools/intent-tool-pipeline/`, not the Nexus_AI root.
Paths such as `docs/`, `codex_workspace/`, `workspace/`, `intent_deliver/`,
and `test_workspace/` in this workflow are relative to that tool root.
Local delivery archives and their records belong in repository-root `deliverables/`;
tool-root `deliverables/` remains reserved for formal ITP releases.
Shared `.agents/` and `.codex/` paths are relative to the Nexus_AI root.
Run workflow command examples from the tool directory; use the root virtual environment.
General research or standalone role use does not start Workflow A/B.


Use this workflow for an authorized small revision or local delivery when the full `$build-tool-pipeline` would be disproportionate. The outcome is maintained product source and optional local packages with proportionate evidence. A local package is not a pipeline-verified release or a new eligible revision baseline. Read [local-delivery.md](references/local-delivery.md) when packaging, checking a delivery record, or carrying deliveries into B.

## Qualify the change

Use this skill only when every condition holds:

- the target is one existing tool in its declared authoritative location, including an existing `codex_workspace/<tool_name>/`, `develop/`, or `tools/` location; resolve source identity from its own documentation rather than moving or copying it to qualify;
- the requested behavior and explicit non-changes are stable;
- the change is isolated to a small, reviewable surface;
- existing public input, output, recipe, CLI, and persisted-result schemas remain compatible;
- no data migration, new dependency, security boundary, or cross-tool contract is introduced;
- focused regression tests plus the maintained product suite can provide proportionate local evidence; and
- the user is requesting source maintenance or local patch/full delivery, without a formal verified release, formal acceptance, or independent verification.

Route to `$build-tool-pipeline` when staged delivery is needed and its source-location rules apply; otherwise return the exact qualification failure for an appropriate development procedure. An unfinished pipeline stage owning or potentially mutating the tree prevents this workflow. Do not split broad work into artificial minor edits or use local packaging to bypass a failed B gate.

## Establish the baseline boundary

1. Read the repository and nearest product `AGENTS.md`, product documentation, revision history, and relevant source/tests.
2. Inspect the working tree and preserve unrelated work. Resolve overlap with user changes before editing.
3. Check `workspace/build_runs/` for a target-related unfinished run when discoverable. Never edit a product tree concurrently owned by an implementation, verification, repair, or release operation.
4. Identify the most recent eligible pipeline baseline only from its exact completed run evidence. If it cannot be proven, record it as unknown; never invent an archive, contract, report, hash, or run ID.
5. Treat every change made through this skill as `PRE_EXISTING_DELTA_NOT_VERIFIED_BASELINE`. Local tests do not make it an exact pipeline baseline.

## Implement and verify

- Keep changes inside the authoritative product tree and make the smallest cohesive edit that satisfies the request.
- Preserve calculation bytes, schemas, identities, compatibility, and other explicit non-changes when those are outside scope.
- Add deterministic regression coverage for the changed behavior and its important boundary cases.
- Run focused tests, then the complete maintained product suite using the repository virtual environment. Report any check that cannot run.
- For a package-only request, inspect existing focused/full evidence and confirm that it covers the exact current source; rerun stale or missing checks. Packaging does not require a gratuitous source edit.
- Keep source verification distinct from package verification. Optional patch/full delivery follows [local-delivery.md](references/local-delivery.md); do not claim pipeline verification, independent verification, formal release readiness, or product acceptance.

## Record the revision

Append the tool's authoritative revision history in the same change. Include the repository-required date/revision ID, trigger, behavioral differences, affected components, compatibility or migration impact, completed verification, and limitations.

Also include a clearly labeled `Pipeline carry-forward` paragraph or bullet with:

- `Disposition: PRE_EXISTING_DELTA_NOT_VERIFIED_BASELINE`;
- the exact eligible pipeline baseline identity, or `unknown`;
- changed behavior and principal files;
- explicit non-changes and compatibility boundaries;
- focused/full test commands and results;
- incomplete checks, lack of independent verification, and package status; and
- an instruction that the next pipeline must absorb this entry as cumulative delta rather than treat it as baseline evidence.

For a local package, add `Local delivery record: ` followed by the backtick-enclosed repository-relative manifest JSON path. Keep the linked record, package, checks, and package-only delivery entry durable and append-only; never rewrite a prior release to incorporate them.

If several minor revisions accumulate, keep all released history append-only. A later entry may supersede behavior but must not erase the earlier carry-forward record.

## Hand off to a future pipeline

When a later `$build-tool-pipeline` run starts from an older eligible archive:

1. Compare the exact baseline archive with the current authoritative product tree.
2. Collect every later revision-history entry marked `PRE_EXISTING_DELTA_NOT_VERIFIED_BASELINE` and each linked local delivery record; run the delivery intake/check procedure in [local-delivery.md](references/local-delivery.md).
3. Preserve each entry and linked record in intake source/feedback evidence and represent its behavioral scope and delivery constraints in the cumulative delta request and full current contract.
4. Classify baseline requirements affected by the carried-forward behavior as impacted, even when the new user request merely asks to preserve that behavior.
5. Re-run all applicable tests, package the current candidate, and independently verify the combined current behavior.

If no eligible exact baseline exists, follow the pipeline's `FRESH_REQUIRED` path. Never promote a minor-revision record into a verified baseline by editing hashes or run state.
An unknown pipeline baseline does not by itself make a patch target unknown: a separately proven coherent local base may support a patch, while B baseline eligibility remains unchanged.

## Final report

State the changed behavior and files, focused/full test results, revision-history location, and explicit non-changes. For delivery, also state patch/full choice, actual repository-root package and record paths, base/prerequisites, application or clean-extraction checks, recovery limitations, and any unperformed check. Say plainly that local evidence does not establish a pipeline-verified baseline, and quote the carry-forward disposition the next pipeline must consume.

## Revision History

### 2026-10-23 — MP-20261023 local delivery extension

- Trigger: approved local patch/full delivery for bounded revisions without weakening formal release controls.
- Difference: qualify one existing declared authoritative tool location, permit package-only delivery with current evidence, separate source/package checks, and retain linked delivery records for cumulative B intake.
- Components: this skill, UI metadata, local-delivery reference, router, and B/maintenance guidance.
- Compatibility: no product or governed artifact-schema change; `PRE_EXISTING_DELTA_NOT_VERIFIED_BASELINE`, exact baseline eligibility, independent verification, and stopped-gate rules remain.
- Verification: all three modified skill entry points passed `quick_validate.py` in Python UTF-8 mode using the repository virtual environment; `git diff --check` passed. CLI flags and record fields were compared with the implemented checker; broader runtime/integration evidence belongs in the framework revision record.
- Limitation: local delivery evidence establishes only its documented scope and cannot confer formal release or baseline eligibility.

### 2026-09-04 — v1 initial workflow

- Trigger: requested a separately registered minor-revision workflow that remains safe to absorb into later exact-baseline pipeline revisions.
- Behavioral scope: adds bounded-change qualification, product-tree implementation and testing rules, an append-only pipeline carry-forward record, and explicit cumulative-delta ingestion semantics.
- Principal components: this skill and its UI metadata, plus the compatible intake rule in `$build-tool-pipeline`.
- Compatibility: does not change product or pipeline schemas and does not make out-of-pipeline work eligible baseline evidence.
- Verification: `quick_validate.py` passed under Python UTF-8 mode; 27 relevant pipeline-skill, delegation-policy, and revision-framing regression tests passed.
- Known limitation: formal release and independent verification remain pipeline responsibilities.
