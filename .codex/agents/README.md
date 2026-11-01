# Nexus_AI Custom Agents

Standalone TOML files in this directory are the authoritative, project-scoped
agent configurations for Nexus_AI. They are discovered by local Codex clients;
they are not personal registrations under `~/.codex/agents/`. The `name` field
identifies each role. See the [official custom-agent documentation](https://learn.chatgpt.com/docs/agent-configuration/subagents).

## Roles and Entry Points

| Agent | Purpose | Model / effort | Write boundary |
| --- | --- | --- | --- |
| [theoretical_analysis_agent](theoretical_analysis_agent.toml) | Mathematical and engineering model validity, derivation review, assumptions, and interpretation | `gpt-6.1-sol` / `high` | Read-only |
| [product_intake_consultant](product_intake_consultant.toml) | Free discussion, challenge, clarification, and convergence of user product/tool intent before formal framing | `gpt-6-astra` / `high` | Read-only |
| [collaborative_intent_shaping_agent](collaborative_intent_shaping_agent.toml) | Make partially understood problems concrete, examine solution directions, and progressively refine user intent | `gpt-6-astra` / `high` | Read-only |
| [intent_realizer](intent_realizer.toml) | Discover realization conditions for supplied intent | `gpt-6-astra` / `high` | Read-only by default; exact bound submission only |
| [product_contract_agent](product_contract_agent.toml) | Behavioral and acceptance contract authoring | `gpt-6.1-sol` / `high` | Read-only by default; exact bound submission only |
| [independent_verifier](independent_verifier.toml) | Independent evidence-based verification | `gpt-6.1-sol` / `high` | Bound result file and explicitly isolated evidence only |

Use a local Codex session opened in this repository. Root coordinates custom
roles through the supported subagent tools; configuration alone does not start a
role or a workflow. Project defaults are in [config.toml](../config.toml).
Read the [delegation policy](../../.agents/delegation-policy.md) before invocation.
All six roles prohibit nested delegation. Current custom agents inherit parent
permissions; a custom-role `sandbox_mode` value does not override them. Existing
values are retained as compatibility metadata, not proof of enforcement. See the
[official permission model](https://learn.chatgpt.com/docs/agent-configuration/subagents).
Task instructions and audits limit authorized writes within those permissions;
they do not establish adversarial operating-system isolation.

## Reusable semantics and scoped output

Revision `ITP-20261030-ARTIFACT-S4` preserves the three artifact roles' semantic
reasoning, models, effort and no-delegation rules. Their separate generic runtime
boundary supports an explicitly authorized procedure assigning one exact new
noncanonical output file. Ordinary Realizer/Contractor calls remain read-only;
the Verifier retains its explicitly authorized isolated evidence boundary.
File transport does not change semantic ownership, acceptance meaning or
independence. Root owns canonical registration and state changes.

No pipeline marker, schema, command, status vocabulary or artifact layout belongs
in the semantic instruction. Other tasks can use these roles without a pipeline
run. Governed ITP calls load the
[invocation procedure](../../.agents/skills/build-tool-pipeline/references/invocation.md),
which uses the new transport for control revision `1.1` or `1.2`.
The user-authorized post-S7 override `ITP-20261101-DEFAULT12` (2026-11-01)
makes `1.2` the new-run default. Explicit `1.1` remains compatible; new legacy
`1.0` requires explicit selection. Existing legacy complete-body returns remain.
Missing governed dependencies block the affected work, without ordinary fallback.

After edits, check fresh exact-role discovery and the effective loaded boundary.
Observe a permitted fixture write before claiming write support; a static TOML
or a file-read assertion alone is insufficient. If current roles remain stale,
resume in a refreshed repository session. Actual S4 evidence and any reload
limitation belong in the
[S4 checkpoint](../../tools/intent-tool-pipeline/workspace/framework_development/aa-impl/s4-checkpoint.md).
Current selection and recovery instructions are in the
[rollout procedure](../../tools/intent-tool-pipeline/docs/contracts/agent-rollout.md).
S7 changes operational scope, not role models, judgment or write boundaries.

## Collaborative Intent Shaping Agent 0.3.0

Revision `AGENT-20261011-CIS` registers the user-approved final semantic under
[collaborative_intent_shaping_agent](collaborative_intent_shaping_agent.toml), with
`gpt-6-astra` / `high`. The [final attachment](sources/intent-shaping-final.md)
is preserved byte-for-byte. Its full semantic text is embedded verbatim after
line-ending normalization; repository integration, task-procedure/return rules,
read-only operation, Root-mediated dialogue/persistence, and disabled nested
delegation are separately appended or prefixed. No fixed output template or
question count is added. 0.3.0 identifies this approved named consolidation;
0.2.1 was the preceding design candidate.

Use this role to clarify an emerging problem, develop and examine possible
solution directions, and refine the user's intent. Example: ask Root to invoke
`collaborative_intent_shaping_agent` with the idea, current uncertainties,
and sufficiently settled choices. Role selection does not start a workflow.

The user explicitly retired `problem_framer` and
`collaborative_intent_framing_agent`. They have no active registration or alias.
Their exact prior configurations are retained outside the discovery directory:
[Problem Framer](../retired/problem_framer.toml),
[Collaborative Intent Framing Agent](../retired/collaborative_intent_framing_agent.toml),
and [retirement identities](../retired/manifest.json). Historical evidence keeps
its original owners and hashes. Governed historical runs requiring the retired
`problem_framer` cannot obtain a fresh role invocation without an explicitly
authorized migration or restoration; do not substitute the successor under
that recorded identity. Current A/B roles and validators remain unchanged.

Registration verification is recorded in the
[development record](../../develop/framing-agent/registration.md).
Live discovery, model dispatch, and final-semantic behavior are NOT_RUN.
Use a fresh repository session and check the exposed role before invocation;
configuration edits do not prove that this existing session has reloaded them.

## Collaborative Intent Framing Agent 0.1.0 (retired history)

Revision `AGENT-20261010-CIF` registers the user-supplied semantics as
[collaborative_intent_framing_agent](../retired/collaborative_intent_framing_agent.toml),
with `gpt-6-astra` / `high`. The requested display name is
"collaborative intent framing agent"; the callable name uses underscores to
match existing registrations. The supplied title and Role identity are renamed
from collaborative problem framing; the four semantic sections otherwise retain
the user's wording, with Markdown headings and apostrophe normalization only.
The conversation supplied on 2026-10-10 is the provenance source.

This role was used for provisional, collaborative framing when the problem and
solutions remained tentative. At registration, `problem_framer` was also available
for research and formal framing. Both registrations were retired by
`AGENT-20261011-CIS` above. No workflow stage or automatic routing was added.
Repository integration adds read-only operation, Root-mediated conversation and
persistence, and no nested delegation. These boundaries limit direct action
without changing the user's ownership of material intent decisions.

Historical invocation example (retired): ask Root to invoke `collaborative_intent_framing_agent`
with the current problem, tentative directions, and settled decisions.

Validation and limitations are recorded in the dated repository changelog.
Live discovery, model dispatch, and conversational behavior are NOT_RUN.
If the role is absent, start a fresh repository session and check discovery;
do not substitute a generic role and claim this custom agent ran.

| Control | Method / evidence | Disposition |
| --- | --- | --- |
| H1 | User-supplied semantics; exact name, model, effort checks | ADDED |
| H2 | Read-only TOML and no-delegation instructions; enforcement not live-tested | REUSED |
| H3 | TOML parsing, unique names, settings, links, path budgets, diff checks | REUSED |
| H4 | Maintained TOML and dated validation record in repository changelog | ADDED |
| H5 | Four supplied sections retained; explicit identity and integration changes above | ADDED |
| H6 | Missing discovery/model access blocks invocation; live checks disclosed | REUSED |
| H7 | Project-scoped registration and invocation guidance above | ADDED |
| H8 | Source-to-instruction semantic review; behavioral evaluation NOT_RUN | ADDED |

Profile: Light plus H8 for semantic fidelity. This is a one-off registration.

## Product Intake Consultant Runtime Revision 2026-10-06

Revision `AGENT-20261006-INTAKE` changes `product_intake_consultant` from
`gpt-6.1-sol` to `gpt-6-astra`, retaining `high` effort. Role instructions,
read-only scope and delegation restrictions remain unchanged. TOML parsing,
exact settings and preservation of all other configuration fields were checked.
Live Astra dispatch is NOT_RUN; the editing session still advertises Sol/high.
Check the available role in a refreshed session before using the updated model.

## Problem Framer Runtime Revision 2026-10-05 (retired history)

Revision `AGENT-20261005-PF` changes `problem_framer` to `gpt-6-astra` / `high`
at the user's request. Role instructions, read-only scope, and no-delegation
boundaries remain unchanged. The model-policy suite passed all 17 tests.
The editing session still advertises a fixed Sol/high role; Astra dispatch
has not been verified. Use a refreshed repository session and check its actual
available role before invoking it. Configuration changes alone are not evidence
that an existing runtime has reloaded them.

## Theoretical Analysis Agent 0.1.0

Registered 2026-10-03 from the [user attachment](sources/theoretical-analysis-original.txt),
retained byte-for-byte as provenance (its Jul 5 label has no year). The maintained
source is [theoretical_analysis_agent.toml](theoretical_analysis_agent.toml).
All ten instruction sections retain their original wording, with whitespace
formatting only. Added repository boundaries keep persistence with Root and
prohibit nested delegation. Model and effort follow the repository defaults.

Use for a specific mathematical or engineering question, including checking
derivations, physical meaning, approximation validity, and failure boundaries.
Numerical checks remain optional; required file outputs go through Root.
Example: `theoretical_analysis_agent를 호출해서 이 모델의 가정과 유도 과정을 검토해줘.`

Verification: TOML parsing, unique role name, settings, ten-section text fidelity,
source byte identity, local links, and path limits checked. Live discovery and
model dispatch are NOT_RUN: this session's role list predates registration.
Start a fresh repository session if the role is absent; do not substitute a
generic role and claim this agent ran. Read-only operation limits direct output
generation, while preserving the supplied reasoning and optional-check policy.
Existing roles and pipeline release identities are unchanged.

## Product Intake Consultant 0.1.0

**Judgment:** use this role while the user is freely discussing and converging
what a product or tool should enable and feel like. Use downstream roles for
formal framing, realization, contracts, implementation, or verification.

Example request to Root:

```text
product_intake_consultant를 호출해서 나와 intent 자유토론을 진행해줘.
내가 원하는 것은 ...
root는 대화 맥락과 내 결정을 전달하고, agent의 검토 의견을 통합해줘.
확정 intent, 탐색 중인 제안, 미해결 결정을 구분해줘.
```

The user owns material intent choices. The consultant clarifies and challenges;
Root coordinates turns, supplies source context, and persists the result. The
consultant receives user replies through Root when operating as a subagent.
It must not claim direct user interaction or treat a Root summary as user approval.
This is a collaboration boundary for a future conversation-iteration procedure,
not an implemented three-party protocol or a separate user-visible chat.

**Trade-off:** concise, adaptive discussion reduces form-filling and unnecessary
rounds, while preserving explicit unresolved choices instead of claiming complete
requirements. Readiness is advisory: if the user proceeds early, carry the gaps
forward. Quality and speed improvements require later live evaluation.

**Source identity:** [user-supplied Draft v0.1](sources/product-intake-draft-v0.1.md),
whose pasted header includes Aug 16 without a year. The source is an exact byte
copy of the attachment; SHA256:
`c28ba71b2e7537fc7f306bac2411b4a0ad45ba8f2f55d2e8b2e802a10e0bf8c5`.
The TOML is the maintained adaptation; the source copy is provenance evidence.
Revision 0.1.0, registered 2026-10-02, adds free-discussion continuity,
question prioritization, Korean-language alignment, explicit user/Root/consultant
ownership, and runtime boundaries. It preserves the draft's six semantic sections
without granting downstream authority.

**Acceptance and verification:** TOML parsing, unique role identity, exact model
and effort, read-only/no-delegation configuration, source-copy byte identity,
local links, generated path limits, source-semantic review, and the existing
agent delegation regression checks. Live role discovery, model dispatch, and
conversation behavior are not established by static checks. If the role is
absent from the current session's available agents, start a fresh repository
session and check discovery before invocation. Do not substitute a generic role
and report it as this custom agent. Missing discovery or model access blocks
live use; user-confirmation errors or downstream-role drift invalidate semantic
behavior even if the configuration parses.

## Registration Control Map

Light harness with H8 added for semantic fidelity. This is a bounded agent
registration, not workflow construction. Configuration and source checks are
mechanical; semantic fidelity and conversation boundaries are instruction-only
and require future behavioral evaluation. The new agent is not made a required
ITP stage and does not modify existing release evidence or distribution lists.

| ID | Method / location | Evidence / check | Disposition |
| --- | --- | --- | --- |
| H1 | Source draft and requested model/effort | Source reviewed; exact runtime settings checked | ADDED |
| H2 | TOML sandbox and disabled delegation; role instructions | Static settings checked; live enforcement NOT_RUN | ADDED |
| H3 | Repository Python `tomllib`, path/link checks, existing regression suite | See dated repository history for actual results | REUSED |
| H4 | Source copy, TOML, this record, repository history | Inspectable artifacts and reported check results | ADDED |
| H5 | Source identity and adaptation description above | Six source sections mapped in semantic review | ADDED |
| H6 | Discovery/model-access failures; advisory readiness and visible gaps | Failure guidance reviewed; live behavior NOT_RUN | ADDED |
| H7 | Project-scoped configuration and invocation guidance | Files present; registration distinguished from live use | ADDED |
| H8 | Mission, authority, commitment state, downstream boundaries, handoff | Source-to-instruction review; live behavior NOT_RUN | ADDED |
