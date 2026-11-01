# Workflow procedure binding (selected control 1.2)

**Control `1.2` binds workflow-owned procedures to an invocation and its result.
It is the new-run initialization default; explicit `1.1` remains compatible and
new legacy `1.0` requires explicit selection.**

Current override: `ITP-20261101-DEFAULT12`, 2026-11-01, user-authorized after S7.
The default change applies only to new runs; prior selectors and evidence stay
unchanged. S7 activation: `ITP-20261101-ARTIFACT-S7`, 2026-11-01; new-run guidance
is published in the [operating and recovery procedure](agent-rollout.md).
Design identity: `ITP-20261030-ARTIFACT-S5`, 2026-10-30. The original isolated-trial
status is retained as design provenance; it is superseded by this S7 annotation.
This supplements the
[1.1 artifact protocol](agent-artifact-protocol.md) and preserves its ownership,
round, receipt and recovery rules. Explicit `1.1` remains compatible; ordinary
unbound roles, configured models/reasoning and role boundaries stay unchanged.
No migration, release or additional-round permission follows. It does not redefine
old receipts. The retained design is
[S5 design](../../workspace/framework_development/aa-impl/s5-design.md).

## Assignment and loading

The control package's fixed registry derives the workflow, step, role and required
procedures from the artifact or threshold-review assignment. Root cannot replace
the mandatory list. Trusted `agents` and `tool` namespaces resolve only allowlisted
assets from the installed framework and its repository/bundle `.agents` tree.
The product project root still bounds ordinary input references.

`role-boundary start` retains `procedure_binding` in the existing baseline,
including mandatory asset identities and original bytes. The baseline hash binds
the run, role, invocation, procedures, inputs and exact output assignment together.
The child reads the stable
[assignment entry](../../../../.agents/skills/build-tool-pipeline/references/assignment-entry.md)
and invokes `load-role-assignment` with the run, role, invocation and baseline
digest. Loading is read-only; the child must then read original inputs and perform
its own semantic judgment. No child sidecar or control-state write is authorized.

## Result and admission

Copy the loader's `required_result_binding` exactly into the single assigned file:

```json
{"control_revision":"1.2","assignment_sha256":"<baseline SHA-256>","procedure_sha256":"<binding SHA-256>"}
```

- Product contract YAML: one top-level `procedure_binding` mapping.
- Brief/report Markdown: one `<!-- procedure-binding: {JSON} -->` comment.
- Threshold review JSON: one top-level `procedure_binding` mapping.

This is transport metadata, not another semantic contract. Duplicate structured
keys or comments, missing/unsupported/mismatched binding, stale procedures or
inputs, aliases and unauthorized output reject admission. Existing readiness,
candidate identity, boundary and gate checks remain mandatory. Producer claims
cannot replace the bound assignment. Raw-spawn results have exactly the same
admission requirements; this does not prevent raw spawning on the host.

Root registers unchanged bytes and the receipt retains the binding. Consumers
read actual registered artifacts. State validation checks retained provenance;
forward mutations also require current procedures. Fresh owner assignment and
replacement are the route after procedure drift, with no silent old-record edit.
Retain the complete compatible installation and original procedure assets before
updating procedure bytes; use its reader/recovery against the original project
and run paths to resolve interrupted work before new binding and forward use.
Matching committed replay checks retained bytes and returns the old receipt even
if current procedures changed; it never reactivates historical work. Uncommitted
admission requires current procedures. Retain compatible readers during rollback.

## Evidence boundaries

| Evidence | What it establishes |
| --- | --- |
| Generated assignment and digests | The assigned procedure/input/output identities |
| Producer binding/acknowledgment | The producer's claim to use that assignment |
| Observed file-read/loader tool trace | Access to those bytes was observed |
| Independent verdict with relevant evidence | Bounded semantic conformance judgment |

None proves universal comprehension or adversarial isolation. Threshold process
review remains separate from product verification and still needs actual user
approval before real additional rounds. Test-only approval fixtures are not user
authorization. S5 actual-role evidence and S6 distribution evidence remain
source-bound historical results; S7 publication does not rewrite or extend them.

## Recovery clarification from implementation review

Procedure currency must not prevent the operations needed to recover it. A
retained-valid modification event and repair reservation may precede fresh owner
assignments after drift. Forward consumers require current procedures for the
artifacts they consume; a superseded verdict retained during an active repair
does not stand in for the fresh verdict and must not prevent producing it.
Release and terminal product verification still require the current bound verdict.
An interrupted PREPARED registration whose installed bytes are recognized but whose
procedure is now stale follows exact-byte rollback, retaining its failed attempt;
it must not remain permanently pending or silently commit stale work.
