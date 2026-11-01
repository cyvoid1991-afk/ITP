# Bound workflow assignment entry

**For an explicitly selected `1.2` run, load the workflow-owned assignment before
performing the assigned semantic work.** Ordinary and legacy roles retain their
existing procedures. Role selection alone does not select this workflow.

Root supplies the task intent/authorized decisions, project root, run directory,
role, invocation and baseline SHA-256. From the repository root run the installed
control CLI with the declared repository Python environment:

```powershell
$env:PYTHONIOENCODING = 'utf-8'
.\.venv\Scripts\python.exe tools/intent-tool-pipeline/pipeline_ops.py --project-root <project-root> --format json load-role-assignment --run-dir <run-directory> --role <role> --invocation-ref <invocation> --baseline-sha256 <sha256>
```

Read the returned mandatory procedure bodies, their relevant references/templates,
and the actual assigned inputs. Use the assigned semantic owner and exact output
path. Missing or stale binding blocks work; do not substitute an ordinary return
or invent another procedure list. The registry identifies mandatory procedures,
not a new semantic judgment policy. Apply the role's independent judgment and
the bound skill's readiness criteria.

The loader supplies `required_result_binding`. Include it unchanged as one
top-level `procedure_binding` in contract YAML or review JSON; for brief/report
Markdown include exactly one `<!-- procedure-binding: {JSON} -->` comment.
See [the binding contract](../../../../tools/intent-tool-pipeline/docs/contracts/procedure-binding.md).
Do not add a sibling acknowledgment file. Produce only the exact assigned semantic
file and, for product Verifier work, authorized isolated probes. Never modify
canonical artifacts, prior submissions, run state, procedure sources or product
files outside the assigned implementation role.

Return path, artifact/version, invocation, final SHA-256, semantic status,
inputs actually read, unresolved conditions and evidence references. Do not send
the complete body for Root transcription. Root registers unchanged bytes and
consumes the actual registered artifact. Format/admission success is not semantic
readiness, and a loading acknowledgment is not independently observed compliance.

For threshold process review use its separate assigned review shape and exact
output file. Do not turn it into a product verdict or approve continuation. Real
additional rounds require independent review followed by an actual user response.
