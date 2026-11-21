# ITP revision plan for verification, packaging and stage ownership

Approved and implemented on 2026-11-21. Revisions 1 and 2 extend the CLI. Revisions 3 through 5 cover specialist escalation, the implementation gate and worker delegation. The preceding Markdown verdict fix supplies the parser used in revision 1. [Component history](../../CHANGELOG.md)

| Revision | Before | Implemented behavior |
| --- | --- | --- |
| 1. Record the verifier's result | Read the registered report and supply two status arguments. A control 1.2 fixture recorded an UNVERIFIED report as FAILED. | Request the report-derived transition once. Decide what evidence to acquire or implementation to repair after seeing the recorded result. |
| 2. Inspect a newly built candidate | Run package creation, read its manifest location, then issue a separate inspection command. | Request creation and inspection together. Review the candidate evidence or the diagnostic from the failing step. |
| 3. Resolve specialist questions | Root receives questions about intent or contract gaps. | Specialists supply the evidence and consequences. Root resolves outstanding questions before escalating user decisions. |
| 4. Check implementation test evidence | Root runs the tests and requests a passing gate. | The gate checks the recorded passing evidence at completion and before advancement. |
| 5. Delegate implementation work | Root acts as the sole product-tree writer. | Workers may prepare scoped changes in isolation. Root chooses when to delegate, integrates accepted work and verifies the combined result. |

## Revision 1. Derive terminal verification state from the active report

1. Add `--from-verifier` to `update-state --to-stage verification`. Make it mutually exclusive with explicit stage and gate status arguments. Preserve the existing explicit form for other stages and compatible callers. Run, rationale, next action and supporting evidence follow the existing transition contract.
2. In the shared transition path, resolve the active report and verify its identity. Read its declared assessment and requirement results with the existing parser. Map READY with complete all-PASS coverage to PASSED, NOT_READY to FAILED, and UNVERIFIED to BLOCKED. Apply the same result to the stage and its gate. Reject conflicting explicit terminal values at the same boundary, including direct Python callers.
3. Use the existing transition and round machinery for ownership, evidence checks, candidate identity, atomic persistence and replay. Finalization still registers the specialist's report. Report-derived recording runs afterwards. Root owns decisions on repair, additional evidence and release.
4. Test the automatic and explicit entry points, including the two non-passing states in both directions. Check missing or changed report, ambiguous declaration and missing requirement coverage. For every rejection compare the prior state and round ledger byte-for-byte. Verify exact supported replay adds no round and a superseded report cannot authorize a new transition. Preserve historical receipts. For existing control 1.2 assignments, follow the documented procedure-drift recovery path when bound procedure bytes change.

Implementation and test references: [CLI](../../pipeline_control/cli.py), [state transitions](../../pipeline_control/state.py), [semantic checks](../../pipeline_control/validation.py), [round fixtures](../../tests/test_agent_rounds.py), [procedure binding](../../docs/contracts/procedure-binding.md).

## Revision 2. Inspect the candidate in the package invocation

1. Add opt-in `package --inspect` using the existing run and spec arguments. On successful creation, pass the actual returned manifest path to the existing inspector and use its standard inspection output. Keep the standalone commands available for packaging and for reinspection of the same candidate.
2. Return a combined result identifying the completed steps, archive, manifest, inspection result and any failing step. Creation failure ends the command before inspection. Inspection failure returns failure even if the archive exists. Preserve the existing invalidation of prior inspection evidence. Keep release authorization and independent verification at their existing gates.
3. Compare combined and separate commands on the same inputs. Check identical archive digest, manifest and inspection verdict. Exercise creation failure, interruption between steps, inspection failure, reinspection of an unchanged candidate and replacement of a previously passing candidate. Verify that a previous PASS cannot attest to the replacement and that successful inspection leaves release pending.

Implementation and test references: [packaging and inspection](../../pipeline_control/packaging.py), [control fixtures](../../tests/test_pipeline_control.py), [candidate workflow](../../../../.agents/skills/build-tool-pipeline/references/gate-map.md).

For revisions 1 and 2, update the CLI help, gate map, operating instructions and component history together. Run focused rejection and replay tests, then the full framework suite. Report the historical public-seed rebuild result separately from regressions. Check both the prepared A-to-B and Direct B paths.

## Revision 3. Questions raised by specialists

Realizer and Contractor should identify the source they checked, what remains unresolved, the consequential difference between plausible answers, and their recommendation when supported. A specialist can correct its own artifact directly when the supplied evidence settles the issue. Root owns the first resolution of outstanding issues using the original intent, prior decisions, implementation context and delegated authority. Root brings a material user-reserved choice to the user. The specialist incorporates the outcome into its own artifact.

Update the role-specific handoff instructions and common bounce-back procedure consistently. Check with three examples: a resolved omission, a decision Root can recover from existing context, and a new user preference. The expected owners are the specialist, Root and the user respectively. Use the existing records. [Bounce-back ownership](../../docs/governance/Root_Delegation_and_Delta_Procedure_v0.3.md)

## Revision 4. Test evidence at the implementation gate

Root owns the test plan and implementation quality. The control plane must check the recorded passing test evidence when recording implementation PASSED and when consuming that pass to advance into verification. Reuse the existing test evidence validator. A local control 1.2 fixture accepted implementation PASSED with the canonical test results absent.

Test missing evidence, a failed run, a changed plan and valid passing evidence on prepared and Direct B routes. Rejected transitions must preserve stage and gate state. Keep the separate source-currency proposal below subject to its own approval. [Stage transition](../../pipeline_control/state.py) and [test evidence validator](../../pipeline_control/evidence.py)

## Revision 5. Give Root standing discretion to delegate implementation

During authorized Workflow B implementation, Root may delegate a bounded change to a worker. Root specifies the relevant contract, agreed interface, scope and expected behavior. The worker prepares a change and its test results in an isolated workspace. Root owns architectural choices affecting multiple components, acceptance of the change, application to the official product tree, and integrated tests. Independent verification remains with the Verifier. Preserve capacity for the required semantic roles.

When choosing parallel implementation, Root should be able to name both of the following:

1. A concrete task Root can finish before the worker returns, using the agreed interface.
2. A concrete integration check Root will use to accept the returned change, including the observable expected result.

If either answer is unclear, settle the shared decision, redraw the assignment or implement it directly. For standalone delegation, even when Root must wait, a substantial independent task with a clear acceptance test can justify the handoff. Small changes with an evident fix usually favor direct implementation. Apply these questions when assigning work in the existing workflow. They require no extra approval, form or gate.

For example, settle how the parser distinguishes an empty file from malformed input. The worker can then implement the parser while Root finishes the empty-state and error handling against that interface. On integration, importing an empty file must show the empty state and importing a malformed file must show the error. If the distinction is still open, Root resolves it before dispatch.

Update the implementation skill and delegation guidance together. Check the instructions against the example above, an unsettled interface, a small direct fix and a substantial standalone assignment. Confirm the worker returns a reviewable change and Root runs the integrated checks before requesting implementation PASS. [Implementation skill](../../../../.agents/skills/build-tool-pipeline/SKILL.md) and [delegation policy](../../../../.agents/delegation-policy.md)

## Implementation verification

The CLI and Python regression cases cover report-derived and explicit transitions, disagreement rejection, all three verifier outcomes, and counted-round replay. Prepared and Direct B fixtures exercise the canonical test evidence check at implementation completion and advancement. The combined package command is tested against standalone results, failure, interruption and reinspection.

An isolated worker implemented the parser while Root completed and tested the caller against the agreed interface. After reviewing and integrating the change, Root verified the empty, malformed and valid input cases. The escalation procedure was checked against its three routing scenarios. The full framework suite result and operating limits are recorded in the [component history](../../CHANGELOG.md).

## Further review candidates

These findings were reproduced on 2026-11-21 with local framework fixtures. Both await a separate decision.

| Priority | Observed behavior | Proposed change and acceptance check |
| --- | --- | --- |
| 1. Detect source changes between testing and packaging | A source test passed and captured the tested file in its evidence. After editing that file, packaging and inspection passed. Rerunning the same source test failed. This observation ends at candidate inspection. | Bind source inputs to the test attempt and compare the relevant identities at packaging. Start with files declared as test inputs, distinguish generated outputs, and define coverage for added or removed package members. A changed covered input must require fresh tests. An unrelated file outside the declared scope must permit reuse. |
| 2. Reject duplicate test attempts before running commands | Two calls with the same attempt ID executed the test command twice. The second call then returned TEST_ATTEMPT_EXISTS. | Validate and reserve the attempt ID before dispatch. A repeated or concurrent request with the same ID must invoke the test plan only once. Retain interrupted attempts distinctly and use a fresh ID for an intentional rerun. |

Evidence paths: [test execution and attempt allocation](../../pipeline_control/test_runner.py), [passing evidence checks](../../pipeline_control/evidence.py), [packaging preconditions](../../pipeline_control/packaging.py).
