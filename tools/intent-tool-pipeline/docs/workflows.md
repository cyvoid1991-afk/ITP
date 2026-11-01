# Choose a workflow

All runtime paths below are relative to `tools/intent-tool-pipeline/`. Research and experiments do not automatically enter these workflows.

The [router skill](../../../.agents/skills/intent-tool-pipeline/SKILL.md) selects a procedure; the sibling skills contain the actual gates and artifact requirements. This table is a starting decision aid, not a replacement for those skills.

| Request | Path | Completion boundary |
| --- | --- | --- |
| Realize supplied intent and prepare a handoff | Workflow A, `$intent-realization` | Audited brief and handoff; stop if only preparation was authorized. |
| Build a new tool or make a material behavioral revision | Workflow B, `$build-tool-pipeline` | Contract, implementation, tests, independent verification, inspected release candidate. |
| Continue an audited A handoff | Existing run, then B | Validate and resume the same run; no duplicate A or synthetic frame. |
| Resume an in-progress B run | B resume | Validate current state, active artifacts, role capacity, and gates before advancing. |
| Small compatible change to one existing authoritative tool, or package-only local delivery | `$minor-tool-revision`, if every qualification holds | Source evidence and optional local patch/full package with distinct package checks, history and carry-forward record; no eligible pipeline baseline. |
| Improve an existing product's operator documentation | `$rework-product-docs` | Evidence-based documentation changes and review, within authorized scope. |

Direct B is allowed when intent is sufficiently clear for Root and Contractor intake. It uses the existing `handoff.next_stage: contract` route and leaves the framing stage pending. Prepared A to B consumes the active Realizer handoff. Workflow A and B are separate choices; performing A does not itself authorize B. A later material return follows the existing delegation and bounce-back procedure rather than a fabricated state.

For a governed A/B entry or resume, read the tool-local authority, delegation, and contract template documents named by `AGENTS.md`; follow [the invocation adapter](../../../.agents/skills/build-tool-pipeline/references/invocation.md). The control plane in `pipeline_ops.py` validates stage transitions and release evidence. A nonzero result stops the affected gate. From the tool directory, run `../../.venv/Scripts/python.exe pipeline_ops.py -h` for command syntax and use the selected skill's gate map; do not guess artifact fields or mark a failed gate passed.

A `REVISION` needs the build skill's exact eligible baseline. A minor revision after that baseline must be carried forward into the next request and current contract. If baseline proof fails, follow the build skill's `FRESH_REQUIRED` outcome without editing historical evidence. Documentation adequacy is assessed after implementation and before packaging; [optional documentation guidance](../../../.agents/skills/intent-tool-pipeline/references/optional-workflows.md) explains when to rework it.

Local patch/full delivery uses the tool's existing declared authoritative source without moving or copying it to qualify. Its archives and linked manifest/evidence belong in **repository-root** `deliverables/`; formal ITP release archives remain in tool-root `deliverables/`. See the minor skill's [local-delivery reference](../../../.agents/skills/minor-tool-revision/references/local-delivery.md) for coherent patch states, hash checks, recovery and clean-extraction checks. The checker validates records and preflights target state; it does not assemble or apply packages. A locally known patch base need not be an eligible B baseline. B still consumes all marked history and linked delivery records as cumulative delta and stops at any failed gate.
