---
name: apply-harness
description: Apply proportionate quality, evidence, context-continuity, and efficiency controls to AI work. Supports explicit invocation and a portable standing-guidance document. Only Light may be selected automatically; Standard and workflow construction controls require an explicit request.
---

# Apply Harness

Revision: 2.3.1

Reduce repeated user supervision and support quality, reliability, and efficient execution. Reuse working controls and fill gaps; do not build a new framework by default. Assess actual improvement separately from compliance with instructions.

Read the core of [work-guidance.md](work-guidance.md) when applying this skill. Read its continuity section for dependent work, interruption, or handoff, and its workflow section when designing procedures. [README.md](README.md) distinguishes explicit invocation from AGENTS.md adoption of this full procedure: both use this entry and its conditional references. Adopting work-guidance.md alone supplies only the common-guidance subset. A standing request to follow this skill defaults to Light; it does not itself select Standard or workflow-harness construction.

Read `harness-checklist.md` beside this file before applying or revising controls. It is the authoritative control definition; this file defines the application procedure. Follow higher-priority instructions and organizational restrictions.

## Select the profile

Honor the user's explicit profile and scope. Only Light may be selected automatically; ordinary work does not require this skill merely because an agent performs it.

| Profile | Selection rule |
| --- | --- |
| Light | May be selected automatically when useful for bounded, low-consequence work, including use of an established tool. Keep its overhead proportionate. |
| Standard | Requires an explicit user request for Standard or comprehensive harness controls. Tool/workflow design is an intended use, but is not itself authorization to activate Standard. |

An explicit invocation without a profile defaults to Light unless the request explicitly calls for comprehensive controls. Do not escalate to Standard or add Standard-only controls merely because consequences are unclear, the task is complex, or it involves tool/workflow construction. Do not routinely interrupt work to solicit Standard activation. Explicitly requested individual H8-H17 controls may be applied without activating the whole profile. Existing task-specific tests, safety rules and acceptance gates still apply independently of this skill. Record the selected profile briefly.

## Apply

Follow [workflow-procedure.md](workflow-procedure.md) only when the user explicitly requests workflow harness construction/revision, or Standard for the workflow being designed. Automatic Light does not activate it. Once requested, it requires structured verification and judgment records that downstream steps consume. For revisions, cover changed steps and affected handoff boundaries; reuse adequate existing mechanisms. One-off tasks and review-only requests do not require implementing this procedure. For design-only requests, specify the contracts and identify unimplemented checks without claiming runtime enforcement.

1. **Inspect.** Identify the target task or workflow, acceptance criteria, permitted actions, and existing tools, tests, policies, and records. Resolve details from available context. Keep audit-only or document-only requests within their requested scope.
2. **Map.** Map the selected controls to existing mechanisms. Check their coverage and relevance to the current inputs and version; names or declarations alone do not establish coverage.
3. **Fill.** Add or revise only missing or insufficient controls. Prefer small changes to existing mechanisms. Do not introduce a framework, dependency, subagent, or reporting subsystem without a concrete need. For workflow construction, put controls in the workflow being built, not only in the current conversation.
4. **Verify.** Follow the checklist's completion gate. Check changed controls and relevant failure paths. For analysis without executable tests, review claims against sources, assumptions, and counterchecks; identify judgment-based conclusions. Never substitute self-confidence for verification.
5. **Record and continue.** Update the compact control map and report the supported result. For continuing work, reuse a current checkpoint linked to source and evidence; refresh it when a material change affects continuation and before a planned handoff. On resume, reconcile current inputs and required procedures before selecting the next action. Escalate material ambiguity, missing authority, or unresolved blockers rather than inventing decisions.

## Revise

Keep H1-H17 stable. Interpret strengthening requests as concrete changes to coverage or enforcement. Record the changed method and rerun affected checks; do not silently change acceptance thresholds. Apply revisions to the current task unless the user requests a persistent policy update.

## Control map and completion report

Use the existing task or run record; a small table is sufficient:

`ID | Method / location | Evidence / check result | Disposition`

Disposition: `REUSED`, `ADDED`, `MODIFIED`, `NOT_APPLICABLE`, or `GAP`. Cover selected controls; explain exclusions and gaps. Distinguish instruction-only from runtime-enforced methods. Mark unexecuted checks `NOT_RUN`, not passing. Creating a control does not prove it works.

Report the profile and overrides, task status, material changes or gaps, and the control-map/evidence location. Do not repeat the full map unless requested. Keep harness verification status separate from task status when they differ.

When the workflow procedure was explicitly activated, also report the contract, retained-record, and consumer-check locations, with actual failure-path results. It is an additional completion requirement within that requested scope, not a third profile or an automatic trigger.

## Design references

Pattern references only; do not fetch or install these repositories during use:

- `obra/superpowers`: `skills/verification-before-completion/SKILL.md`; `skills/writing-skills/SKILL.md`.
- `wshobson/agents`: `docs/authoring.md`; `docs/plugin-eval.md`.
