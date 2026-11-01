# Product Contract Adapter

For explicitly selected `1.2` runs, first load the workflow-owned assignment via
[assignment-entry.md](assignment-entry.md). Apply the selected `1.1` file/compact
transport below and include its exact `required_result_binding` as one top-level
`procedure_binding` mapping. Read the registry-bound original procedures/inputs;
do not infer readiness from successful loading or omit unresolved conditions.
Legacy and ordinary behavior below remains unchanged.

Apply only to the governed run named by Root. Read [invocation.md](invocation.md)
for the calling boundary. This document binds the reusable `product_contract_agent` role
to the existing artifact contract; it does not apply to ordinary role use.

Use the native `$author-product-contract` skill for contract-authoring and contract-revision tasks. If the skill is unavailable, return `BLOCKED` and identify the missing dependency.

Then read `docs/contracts/README.md` as the active repository execution procedure. Contract version `1.0` is the approved baseline and must not be silently revised.

Read `docs/contracts/templates/product_contract.yaml`
for the exact output shape. It is a flat top-level mapping: `readiness`, `product`,
`scope`, `decisions`, `assumptions`, `blockers`, `verification_policy`,
`requirements`, `acceptance_methods`, `implementation_constraints`,
`documentation_obligations`, and `handoff` are siblings of `artifact` and
`source_artifacts`, not children of a `contract` wrapper. Use the template's
`statement`, `title`, `evidence_required` and other exact field names;
`evidence_method` is TEST, INSPECTION, ANALYSIS or DEMONSTRATION, not prose.

Execution contract:

- Accepted primary inputs: the active `build_request.yaml`, original intent/delegation source snapshots and, on the prepared path, the adopted `problem_frame.md` explicitly named by the parent for one `workspace/build_runs/<pilot_id>/` run. The latter is the intent realization brief for marked runs. Direct B uses `handoff.next_stage: contract` and has no frame. Read original authorized sources to independently test consequential claims; do not rely only on Root's or Realizer's summary.
- Consumed identity: for a SHA-256-bound request, list `build-request` version/content_sha256 in source_artifacts and the active `problem-frame` version/content_sha256 only when prepared. Use the actual supplied identities, never placeholders or fabricated provenance.
- Return boundary: keep contract corrections and source-supported decisions in B. Return missing technical evidence to Root; return an unsupported material intent/preference/authority/loss choice with its affected scope and consequences. Do not restart all intent work or silently create a user decision. Compare individual and cumulative differences against original intent, not only the previous Root choice.
- Approved baseline input: for a `REVISION` request, use only the exact resolved verified baseline explicitly named by the parent, including its run, release-archive, product-contract, and verification-report references and SHA-256 identities. Treat those identities and the prior `product_contract.yaml` as immutable baseline context, not as proof that the active run is accepted.
- Required output: one complete product_contract.yaml body conforming to artifact contract 1.0. Under selected control.semantic_role_boundary: "1.1", write it at the exact role-boundary start submission_path, with the assigned version and existing canonical-path metadata. Otherwise return the complete body to Root.
- Registration/activation owner: Root Codex. Selected file authorship does not authorize canonical persistence or a gate decision.
- Permitted write path: selected "1.1" permits only the exact assigned submission file. Legacy governed use permits no writes; ordinary role use keeps its calling boundary. Do not create siblings, descendants, aliases or a canonical replacement.
- Delegation: prohibited. Do not spawn, steer, or otherwise manage sub-agents; complete the assignment directly and return its actual result to Root Codex.
- Source-tree modification: prohibited. Outside the exact selected submission file, do not create, edit, move, or delete implementation, test, configuration, documentation, run-state, or release files.
- Context boundary: read only the semantic instruction, named procedure and its required references/templates, artifact-contract README, explicitly named primary inputs, their authorized source references needed for critical review, and an explicitly named approved same-product baseline unless the parent names another approved source.
- Traceability: preserve approved decisions, use stable `REQ-###` and `ACC-###` identifiers, keep bidirectional requirement/acceptance references, and verify every applicable requirement.
- Verification nature: use `ALL_APPLICABLE_REQUIREMENTS`; deterministic evidence is the default; list only requirements needing semantic judgment in `verification_policy.llm_judgment_requirements`, with linked judgment criteria.
- Readiness: return `PASS`, `PASS_WITH_ASSUMPTIONS`, or `BLOCKED` consistently with assumptions, contradictions, and blockers.

## Output transport

### Selected compact return

For selected "1.1", return a compact Root message with the actual assigned path,
artifact ID/version, final content SHA-256, invocation, readiness, inputs read,
assumptions/blockers and evidence references. Do not include the complete body for
Root to copy or claim that the canonical contract was activated. Root registers
those exact bytes with --expected-source-sha256 and reads the registered contract
before implementing it. A BLOCKED contract stays BLOCKED; failed admission does
not authorize rewriting it into PASS.

### Legacy full-body return

For legacy governed use, return the complete YAML body followed by a compact
summary of readiness, reviewed input paths, intended canonical path, blockers and
next stage; do not claim to have written it. This adapter changes no generic
contract-authoring semantics or ordinary role procedure.

## Workflow B intake and source binding

In this repository's Workflow B, Root + Contractor own the first substantive
intake. Read the original intent and existing delegation, then either the prepared
A handoff and adopted Realizer brief or a sufficiently clear direct request.
A is not mandatory for simple intent, and the complete delegation template is
not mandatory for direct intake. Root's written delegation records existing
authority; it cannot create it. Read the governing v0.3 instruction/procedure
sections supplied by Root, without taking on Root's orchestration role.

Check both the current change against the last valid basis and the cumulative
result against original intent plus explicit user decisions. Missing technical
evidence, delegated trade-offs and contract corrections stay in B. Only a material
intent, preference, authority or acceptable-loss choice unsupported by existing
sources returns to A/user through Root, with affected scope, evidence, options
and the exact decision. Preserve independent stable work; do not restart all of A.

For newly identity-bound build requests, `source_artifacts` must identify the
active `build-request` version and `content_sha256`; include the active
`problem-frame` version/hash only on the prepared path. Direct B has no frame.
Use the exact template fields. Read original source snapshots, including declared
identity and unresolved decisions, before determining readiness. Hashes identify
consumed bytes; they do not prove semantic fidelity or grant approval.

## Exact Bounded-Revision Control

When the governing runtime identifies the request as a bounded revision, use
only the exact resolved verified baseline supplied for that run. Treat its run
ID, release archive identity, product-contract identity, and verification-report
identity as immutable. Do not substitute another release or infer baseline
identity from prose.

Return a complete current contract, not a patch. Preserve every unaffected
current obligation and acceptance record, and include `revision_control` with:

- `mode: DELTA` and the exact baseline identity;
- `unchanged_requirements`, where each record names one unchanged requirement
  and its `baseline_bundle_sha256`;
- an `impact_map` that maps every requested `DELTA-###` and explicit
  `NONCHANGE-###` item exactly once to its disposition, baseline and current
  requirement references, source, test, documentation, and packaging
  references, migration impact, and reverification scope;
- `ALL_APPLICABLE_REQUIREMENTS` as the reverification scope for every impact-map
  item.

The unchanged bundle identity is the SHA-256 of canonical UTF-8 JSON containing
the full requirement record and every full linked acceptance record, with
acceptance records sorted by ID, object keys sorted, and no insignificant JSON
whitespace. A requirement is unchanged only when this exact bundle identity is
unchanged. If a shared acceptance record changes, classify every requirement
linked to it as impacted.

Classify every baseline and current requirement exactly once across unchanged
and impacted sets, keep those sets disjoint, and do not let a baseline
requirement disappear. Record interface, compatibility, migration,
documentation, packaging, and regression effects where they apply.

If the baseline cannot be resolved exactly or the requested change is broad,
incompatible, or materially ambiguous, do not author a delta contract. Return
`FRESH_REQUIRED`/blocked instead of silently weakening revision control. In the
build-tool-pipeline, return to Root for explicit fresh-request routing; use A only
where the affected intent needs realization. Do not silently initialize a replacement run.
