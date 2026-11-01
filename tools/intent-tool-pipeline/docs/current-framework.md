# Current framework
- Runtime/project root: `tools/intent-tool-pipeline/`; interpreter: repository-root `.venv/`.
- [Repository common rules](../../../AGENTS.md)
- [Tool rules](../AGENTS.md)
- [Unified entry](../../../.agents/skills/intent-tool-pipeline/SKILL.md)
- [Authority](governance/Root_Autonomy_Instruction_v0.3.md)
- [Delegation](governance/Root_Delegation_and_Delta_Procedure_v0.3.md)
- [Task boundary](governance/Task_Delegation_Contract_Template_v0.3.md)
- [Architecture](architecture.md)
- [Artifact contract and templates](contracts/README.md)
- [Control plane](../pipeline_control/README.md)
- [Local delivery checks and intake contract](../../../.agents/skills/minor-tool-revision/references/local-delivery.md)
- [Source provenance](provenance.md)
- [Pipeline history](../CHANGELOG.md) and [repository history](../../../CHANGELOG.md)

**New runs default to control `1.2`** under the user-authorized post-S7 override
`ITP-20261101-DEFAULT12` (2026-11-01). Start with the
[operating and recovery procedure](contracts/agent-rollout.md).
This enables registry-owned assignments and bound results without an option;
`1.1` remains an explicit compatible route and new legacy `1.0` requires explicit
selection. Existing runs retain their selectors, receipts and round history.
Generic roles, configured models/reasoning, independence and delegation boundaries
remain unchanged. Procedure-byte updates require retained compatible recovery and
fresh owner assignments before forward use. Keep prior bindings/evidence intact.
S7 grants no existing-run migration, framework/product release, baseline promotion
or additional rounds.
