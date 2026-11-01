---
name: intent-tool-pipeline
description: Route Codex repository work between Intent-to-Tool Workflow A, governed Workflow B, bounded minor tool revisions, and product-documentation upkeep. Use for a local tool request or an existing run; ordinary analysis and framework maintenance stay outside this router.
---

# Intent-to-Tool Pipeline Router

## Repository integration

For pipeline work, first read [the tool rules](../../../tools/intent-tool-pipeline/AGENTS.md).
The pipeline project root is `tools/intent-tool-pipeline/`, not the Nexus_AI root.
Paths such as `docs/`, `codex_workspace/`, `workspace/`, `intent_deliver/`,
`test_workspace/` and `deliverables/` in this workflow are relative to that tool root.
Shared `.agents/` and `.codex/` paths are relative to the Nexus_AI root.
Run workflow command examples from the tool directory; use the root virtual environment.
General research or standalone role use does not start Workflow A/B.


Select the smallest authorized route that fulfills the request. This skill adds no artifact state, gate, role, or permission. The selected sibling skill and its adapter own the procedure; Root retains run state, product source, and release ownership. Read the nearest `AGENTS.md` and preserve unrelated work.

| Situation | Route |
| --- | --- |
| Converged intent needs conditions, decisions, and a consumable handoff; only preparation is requested | `$intent-realization` for Workflow A. Stop after its audited handoff. Do not begin B from preparation authority alone. |
| Delivery through release is requested, but realization conditions need preparation | Run A through `$intent-realization`, then continue the same audited run through B when handoff readiness and existing user authority permit. Do not ask for B permission again when delivery is already authorized. |
| New or materially changed tool under `codex_workspace/`, with sufficiently clear direct intake | `$build-tool-pipeline` for Direct B, starting Root + Contractor. Keep the framing stage pending as specified there; do not invent an A artifact. |
| An existing initialized A run has a current audited Realizer brief and source/delegation handoff | Resume that exact run under `$build-tool-pipeline` at B intake. Validate current state and source identity before advancing; do not initialize a duplicate or repeat A. |
| Governed B run already exists | Resume through `$build-tool-pipeline` after its intake/resume checks. A failed gate remains stopped. |
| Small compatible change to one existing authoritative tool, or local patch/full delivery with current evidence, without formal verified release or independent verification | Assess `$minor-tool-revision` qualification and its local-delivery reference. Package-only delivery is allowed; qualification failure requires the appropriate development route. |
| Requested rework of an existing product's operator documentation | `$rework-product-docs`; preserve its self-contained workflow. Documentation-only edits do not enter B by default. |

At any governed A/B intake or resume, read the Root authority, delegation, and template documents in `docs/governance/` (preserving their original basenames), and the selected skill. Bind exact role invocations through [invocation.md](../build-tool-pipeline/references/invocation.md). These sources record existing authority; they do not grant new user authority. The control plane owns deterministic transitions and must reject unsupported advances.

For B, distinguish `NEW_PRODUCT` from exact-baseline `REVISION` using the build skill's intake rules. A bounded post-baseline minor change remains cumulative delta evidence and is not itself an eligible baseline. Preserve historical run evidence and hashes.
Collect marked minor history and linked local delivery records at B intake. Local package eligibility and exact pipeline-baseline eligibility are separate judgments. A failed governed gate cannot be bypassed by choosing local delivery.

After implementation and before packaging, use [optional-workflows.md](references/optional-workflows.md) to assess whether operator documentation needs work. Read it when considering a documentation pass or an after-release documentation change. Do not add a documentation stage to the control-plane schema.
