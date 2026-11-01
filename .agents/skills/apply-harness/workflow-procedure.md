# Workflow Construction Procedure

Revision: 2.3.1

Build inspectable verification and judgment records into the workflow, and make receiving steps use them. Activate this procedure only for an explicit user request for workflow harness construction/revision or Standard for the workflow being designed, as defined in SKILL.md. Automatic Light and ordinary tool/workflow work do not activate it. Within the requested scope it is a construction requirement, not a common runtime or a requirement to use JSON for every domain.

## Scope and reuse

Apply to new workflows and, for revisions, changed steps and affected handoff boundaries. Existing unaffected runs need no migration. A step is a meaningful execution, verification, decision, or responsibility boundary, not every tool call or private reasoning step.

Use existing schemas, tests, storage, and orchestration when they satisfy the requirements. Preserve compatible interfaces; use adapters or separately authorized migrations for necessary incompatible changes. Review-only requests identify gaps without implementing them. Design-only requests specify contracts and checks and mark execution NOT_RUN. One-off execution or analysis does not require constructing a recording subsystem.

## Implement the contracts

1. **Define boundaries.** Identify each relevant producer and consumer, required inputs and outputs, acceptance criteria, allowed next steps, and the owner of unresolved decisions. Include terminal acceptance when there is no downstream step.
2. **Implement mechanical checks.** Store and reuse code, schemas, assertions, or tests for mechanically decidable conditions. Define required fields, valid values, and cross-record conditions. Execute checks against the actual inputs and artifacts. Record the method/version and observed result; a schema-valid record alone is not a correctness pass.
3. **Structure judgments.** For conditions needing domain or LLM judgment, record the criterion, assessment, supporting evidence, material assumptions, uncertainties, and unresolved questions. Identify the reviewer or method and its version/configuration when relevant. Preserve concise decision rationale, not private reasoning transcripts. Do not label judgment as deterministic proof.
4. **Connect the records.** Use machine-readable records, such as JSON, typed messages, or database rows. Define the contract and its version in the owning workflow. Support the information below through fields or resolvable references; reuse domain-native representations rather than requiring a universal schema.
5. **Implement consumption.** Receiving steps load the records and validate required fields, evidence availability, subject/version correspondence, required check results, and unresolved conditions before advancing. Do not rely solely on a producer's ready flag or success narrative. Encode the mechanical gate in the workflow; specify responsible review for semantic conditions. Route failures and unavailable prerequisites to explicit failure, blocked, or repair paths, within existing authority and retry limits.
6. **Retain and verify.** Preserve the records and check implementation as described below, execute relevant acceptance and rejection paths, and connect the results to the control map.

### Minimum record information

| Information | Purpose |
| --- | --- |
| Contract version, record/run/step identity, producer | Identify and interpret the handoff |
| Requirement or criterion IDs | Connect the record to the requested behavior |
| Input and artifact references with version identity | Establish what was actually evaluated |
| Check method/version, status, observed result, evidence reference | Support mechanical verification claims |
| Judgment criterion, assessment, evidence, assumptions, uncertainty | Expose the basis and limits of semantic decisions |
| Unresolved conditions and next-step prerequisites | Let the consumer decide whether and where to proceed |

Include the sections relevant to the step; explain exclusions in the contract. Preserve the distinction between PASS, FAIL, BLOCKED, and NOT_RUN, or document an equivalent native status mapping. Unknown, missing, or unrun required checks must not become a success by default. Define which judgments require further review rather than treating every uncertainty as an automatic block.

## Retention and traceability

Choose the owning component's official source and run-record locations before execution. Keep reusable check code/schema in authoritative source and run-specific records in retained storage. Disposable directories may hold reproducible scratch work, never the only copy of required evidence or implementation.

Retain enough input identity, script/configuration/dependency versions, and execution instructions to repeat mechanical checks. Bind evidence to the evaluated artifact version; a commit ID is insufficient for uncommitted changes unless the actual content is also identified. Use immutable versions, content digests, snapshots, or equivalent existing mechanisms. Hashes identify content; they do not prove correctness. Preserve failed attempts and add new results for repairs without overwriting the history needed to interpret a claim.

Ensure authorized consumers can resolve evidence references. Respect data and secret boundaries; use approved restricted storage or redacted references rather than copying protected data into general records. Disclose inaccessible evidence, unavailable inputs, and external-service or LLM nondeterminism. Do not promise deterministic replay of semantic judgments.

## Continuity across execution boundaries

Use the checkpoint lifecycle in [work-guidance.md](work-guidance.md). Bind the current entry to the applicable procedure, subject, and authoritative records. A resumed Root is a consumer just as a different agent or procedure is. Preserve unfinished work, relevant facts versus hypotheses, decisions, unresolved conditions, and the next action with its required reading. Keep the entry compact; link original records rather than duplicate their claims.

Define who refreshes the entry after material findings, decisions, failures, source changes, and before planned handoffs. Maintain a clear current pointer and retain the prior evidence needed to interpret changes. Do not depend on receiving advance notice of compaction. Expose the current step, last meaningful outcome, failure/wait reason, and allowed continuation through existing records rather than requiring a telemetry subsystem.

Consumers reconcile actual inputs, procedure versions, and evidence applicability before acting. Source or procedure drift invalidates affected claims and checks; determine the affected scope and preserve unaffected evidence only with a justified basis. A checkpoint's proposed next action never overrides the receiving procedure's contract or existing authority. Preserve mandatory original-source reading when using a shorter navigation index.

## Completion checks

Verify the implementation at the relevant boundaries:

- An acceptable handoff is consumed and reaches the permitted next step.
- Missing required evidence and mismatched artifact versions cannot advance as successful handoffs.
- Failed, blocked, and unrun mandatory checks remain distinguishable and cannot bypass prerequisites.
- A schema-valid record with an unresolved mandatory semantic condition reaches the declared review/block path rather than passing on format alone.
- Reused contracts and consumers still work across any changed boundary.
- For workflows that span contexts, a fresh execution context can identify the current subtask, unfinished work, constraints, applicable evidence, and permitted next action from retained records. Include changed-source and interrupted-work cases; record actual observations separately from deterministic replay or identity checks.

Select concrete cases matching the workflow; explain exclusions and mark unexecuted checks NOT_RUN. Record observed results in the existing task/run record. Missing required verification prevents an overall verification PASS. Keep workflow implementation status separate from the status of a demonstration run that correctly encounters a blocked input.

Report locations of the contract, check code, retained records, and consumer enforcement, plus remaining gaps. This verifies a particular implementation; it does not establish universal agent compliance or better task accuracy.

Evaluate recording and recovery overhead when it is material. Compare task outcomes, repeated investigation, recovery effort and measured time/token/tool use under comparable conditions. Unavailable metrics remain unmeasured; do not equate more records or more passing checks with better performance.

For an illustrative producer/consumer handoff, read [references/workflow-record-example.md](references/workflow-record-example.md). Adapt its information model; its sample identifiers and files are not real evidence or mandatory names.
