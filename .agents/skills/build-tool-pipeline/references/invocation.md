# Semantic Role Invocation Binding

## Workflow-owned assignment: selected 1.2 runs

For control `1.2`, including the new-run initializer default, mandatory procedure selection belongs to the control
registry. Root supplies task intent, authorized decisions and the exact boundary
assignment identity. The child loads [assignment-entry.md](assignment-entry.md)
and `load-role-assignment`, then reads the required procedures and actual inputs.
The [binding contract](../../../../tools/intent-tool-pipeline/docs/contracts/procedure-binding.md)
governs result metadata, admission, drift and replay. The selected file-writing,
compact-return, ownership and four-round rules below also apply to `1.2`;
references to `1.1` preserve that earlier protocol's unchanged behavior.
Do not reconstruct a substitute procedure list in the task prompt. Missing or
stale mandatory binding blocks registration/forward use, including raw-spawn
results. Generic roles and existing legacy `1.0` runs remain unchanged.
`ITP-20261101-DEFAULT12` (2026-11-01) is the user-authorized post-S7
new-run default override; follow the
[rollout procedure](../../../../tools/intent-tool-pipeline/docs/contracts/agent-rollout.md).

This reference applies to Workflow A, Workflow B and resuming their governed
historical runs. A custom role by itself does not select any of these workflows.
Root selects the applicable procedure and binds it in the invocation; the role
retains its independent semantic judgment and common runtime restrictions.

## Select and load the adapter

| Assignment | Exact role | Required procedure and adapter |
| --- | --- | --- |
| Workflow A or scoped realization return | `intent_realizer` | [intent-realization](../../intent-realization/SKILL.md), including its Governed run adapter |
| Prepared or direct Workflow B contract | `product_contract_agent` | [author-product-contract](../../author-product-contract/SKILL.md) and [contract-adapter.md](contract-adapter.md) |
| Workflow B verification or revalidation | `independent_verifier` | [independent-verification](../../independent-verification/SKILL.md) and [verification-adapter.md](verification-adapter.md) |
| Unmarked historical run with the recorded framing owner (fresh invocation blocked: retired role) | `problem_framer` | [problem-framing](../../problem-framing/SKILL.md) and [framing-adapter.md](framing-adapter.md) |

The `problem_framer` registration is retired. Historical artifact validation
retains its identity, but a fresh invocation is blocked pending explicitly
authorized migration or restoration. Do not invoke the successor under the old
name or relabel historical evidence. Current A/B role bindings are unchanged.

Root names the required procedure and adapter in each invocation or follow-up.
The agent reads the relevant documents before producing its governed return.
Loading one role's adapter does not require loading the other roles' adapters.
An unavailable required adapter blocks affected governed work; do not substitute
ordinary output or a different role. Existing artifact schemas and templates
remain authoritative for exact field names and report structure.

## Select the governed transport

**Control.semantic_role_boundary: "1.1" or "1.2" selects agent-authored
submissions. Normal initialization selects "1.2" for new runs.**
Explicit `--control-revision 1.0` selects a new legacy run; explicit `1.1`
remains compatible. Read the maintained agent-artifact protocol
and round-recovery clarification under tools/intent-tool-pipeline/docs/contracts/.
Never infer selection from a role name, a file, a requested limit or schema_version.
Do not upgrade an existing run or strip its marker for rollback.
Missing `1.2` dependencies or failed binding gates block affected work; do not
fall back to `1.0` or `1.1` to bypass them.

| Invocation | Owner-authored output | Root action |
| --- | --- | --- |
| Ordinary reusable role or another procedure | Calling task's useful return format and authorized boundary | No pipeline procedure is required solely by role selection |
| Governed legacy control "1.0" or supported historical run | Complete semantic body returned to Root; existing read-only/probe allowances | Save the exact returned body separately and finalize through the legacy interface |
| Selected artifact invocation "1.1" / "1.2" | Complete semantic file at the exact start-result submission_path; compact identity/status return; "1.2" adds exact procedure binding | Register the same bytes with their expected digest, read the canonical artifact, then apply readiness gates |
| Selected threshold process review | Only the exact review_path returned for --review-event | Finish the audit; obtain a specific actual user response before resolving a finite allowance |

The reusable roles and generic author-product-contract / independent-verification
skills retain their own semantic judgment and ordinary operation. These governed
adapters select transport and execution only when explicitly bound to a run.
They do not make the semantic instructions depend on this pipeline.

## Bind the current task

Supply the judgment requested, current stage and scope; original intent and
approved source references; delegated choices and unresolved decisions; exact
current artifact and baseline identities when required; expected complete artifact
and canonical path/version; Root registration/activation ownership; and the
role-boundary invocation reference. For selected control "1.1" or "1.2", also supply the
start result's exact submission_path, derived artifact version, assigned input
identities, round_number and baseline_sha256. The canonical metadata path remains
the existing active path; it is different from the assigned submission file. For Verifier also supply the authorized isolated evidence
path, candidate identities and completed harness evidence required by its adapter.
Use actual inputs, not a summary that replaces authorized source meaning.
Selected mandatory inputs are captured by the command; repeat --input-ref for
additional local files actually supplied. Hash binding does not prove reading:
each role reads the authorized original sources and registered upstream bodies.

The selected role writes the complete current file, including BLOCKED or
UNVERIFIED content when that is its judgment, at the assigned submission_path.
It returns the actual path, artifact ID/version, content SHA-256, invocation,
status, inputs read, unresolved items and evidence references. Do not return the
body for Root to transcribe. Do not write canonical artifacts, prior submissions
or control state. Selected Verifier probes use only its assigned invocation
directory; threshold process review has no probe-parent grant.

Root compares the returned identity with the actual file and registers it through
finalize-semantic-return with --expected-source-sha256. Root then reads the actual
registered brief/contract/report; downstream consumers read the registered body
and its original sources rather than only the compact message. Registration is
not readiness. Do not routinely re-author or duplicate the specialist judgment;
check source/authority consistency, deterministic gates and unresolved decisions.
If the compact response is lost, recover the original receipt with the same
matching finalization request; never guess success, reactivate an old receipt or
create a corrected submission under an already consumed invocation.

The adapter specifies the repeatable protocol; the call supplies task-specific
values. Do not copy a second divergent protocol into each prompt. A resumed or
reused role receives fresh inputs and this binding again. Do not infer current
authorization or applied configuration from an old agent turn.

Root follows [gate-map.md](gate-map.md) for role-boundary start, finalization,
validation and state advancement. The agent owns its semantic return; Root
persists it unchanged through the existing audited mechanism. A document or
an agent assertion alone does not establish an active artifact or a gate PASS.
The same rules apply to legacy owners selected by their recorded run state.

## Ordinary work and other procedures

For an ordinary assignment, provide the source, judgment scope and useful return
format. No build request, run state, REQ/ACC vocabulary, release package or
repository adapter is required solely because a custom role was selected.
The generic role skills may be used when their procedure helps the task.
Another workflow may supply its own procedure and acceptance baseline without
adopting this pipeline. These calls do not need pipeline role-boundary commands.

The role's read/write and no-delegation restrictions still apply. An ordinary
procedure may explicitly assign an exact noncanonical output file under the
generic role boundary without adopting this pipeline. Without such an authorized
output file or an isolated evidence directory, the Verifier remains read-only.
A different procedure cannot authorize changes to its verification target or
weaken independent judgment. Repository routing still determines where newly
authorized evidence belongs; general scratch evidence goes under test_workspace/.

If a governed run is active for the assigned scope, omitting its adapter or
calling the work ordinary does not waive the required gates. Resolve any material
ambiguity in procedure applicability before adopting a result. Ordinary results
may be context for later governed work, but are not activated semantic artifacts
until the designated owner completes the required artifact through the bound
legacy return or selected assigned-file transport and the existing source,
version, boundary and finalization checks pass.
