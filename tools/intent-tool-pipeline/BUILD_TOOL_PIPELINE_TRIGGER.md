# Triggering the Build Tool Pipeline

This Codex-native workflow is an optional local tool in Nexus_AI. Its runtime/project
root is `tools/intent-tool-pipeline/`, while `.agents/` and `.codex/` are at the
repository root. Research and experiments do not automatically trigger A/B.
Read [repository rules](../../AGENTS.md) and [tool rules](AGENTS.md) before use.
The imported framework replaced its older Python agent runtime with native
agents, repository skills, and the deterministic control plane.

Use the current framework when asking Codex to create or behaviorally revise a
local software tool under `codex_workspace/` and you want governed delivery.
Workflow A prepares intent through Root and Intent Realizer when realization is
needed. Workflow B begins with Root and Contractor, either consuming that prepared
handoff or taking a sufficiently clear request directly. Both B routes retain the
product contract, implementation, deterministic tests, independent verification,
bounded repair, and release packaging.

## Short Trigger

Unified form:

> Use `$intent-tool-pipeline` to prepare and deliver `<the tool you want>`.

Explicit B form:

> Use `$build-tool-pipeline` to create `<the tool and behavior you want>`.

Prepared-A-only form:

> Use `$intent-realization` to prepare a source-linked realization and delegation
> handoff for `<the supplied intent>`, then stop before Workflow B.

Explicit direct-B form:

> Use `$build-tool-pipeline` with Direct B for `<the sufficiently clear tool and
> behavior>`. Do not create a problem frame or invoke Intent Realizer.

Natural-language form:

> Create `<the tool you want>` under `codex_workspace/`. Formalize the requirements as a contract, then implement, test, independently verify, and package it.

Include important behavior, inputs, outputs, constraints, and approval boundaries
in the request when known. Current supplied intent files belong in
`intent_deliver/`. Codex will stop and ask when a material product, scope,
authority, waiver, safety, or compatibility decision cannot be made within the
existing intent and delegation.

## When It Does Not Trigger

The pipeline is not intended for framework-repository maintenance, standalone documentation editing without a verified release request, generic analysis or status reporting, or a simple isolated fix that does not need the full staged release workflow.

Selecting a custom semantic role for an ordinary task does not trigger this
pipeline. When the pipeline does apply, Root uses the explicit
[role invocation binding](../../.agents/skills/build-tool-pipeline/references/invocation.md)
and its required adapters; omission does not waive a gate.

## User Control

The user retains material decision and approval authority. Root Codex owns run
state, product writes, semantic-artifact persistence, and release; Realizer owns
the optional prepared brief, Contractor owns contract authorship, and Verifier
owns independent verification. New runs audit semantic-agent filesystem mutations
and bind active artifacts to Root-persisted hashes and invocation evidence. A
failed deterministic gate, boundary violation, or unresolved blocker cannot be
bypassed by asking the workflow to continue.
