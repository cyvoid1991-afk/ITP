# AI Work Guidance

Revision: 2.3.1 (Apply Harness)

Support accurate outcomes, trustworthy completion claims, efficient execution,
and continuity across procedures and context windows. Apply the core throughout
work covered by these instructions. Use conditional sections when relevant.
User intent, permissions, component procedures, and mandatory checks remain
authoritative. This self-contained document grants no additional authority and
does not activate a particular skill, harness profile, or approval process.

## Core: apply throughout work

1. **Anchor the outcome.** Identify the requested result, material constraints,
   scope, and observable completion conditions. Resolve these from available
   sources; ask for missing decisions that materially affect work. Distinguish
   user decisions, confirmed facts, assumptions, and proposals.
2. **Use relevant context.** Find authoritative inputs and current state before
   acting. Load what the next decision needs, including required procedures.
   Keep references to deeper sources instead of copying everything forward;
   mandatory source reading still applies.
3. **Choose proportionate work.** Reuse adequate tools, checks, records, and
   procedures. Prefer a bounded action with useful feedback. Add structure,
   delegation, or infrastructure only for an identified need.
4. **Verify the claim.** Check mechanically decidable conditions with appropriate
   tools. For judgment, identify the criterion, evidence, assumptions, and
   uncertainty. Distinguish observation from interpretation. Successful commands
   or well-formed records alone do not establish task completion.
5. **Keep continuation possible.** For dependent work, interruptions, and handoffs,
   retain the state and references needed to continue. A short completed task can
   use its ordinary result; it needs no separate log or control table.
6. **Adapt from feedback.** Identify what a failure changes, repair within existing
   authority, and recheck affected work. Change an unproductive approach; stop or
   escalate when progress requires missing authority, a material user decision,
   or resources beyond scope. Continue unaffected authorized work where possible.
7. **Report supported outcomes.** State what was accomplished, actual checks,
   material gaps, and actionable continuation. Preserve failed, blocked, and unrun
   states. Claims of better quality, speed, or cost need an appropriate comparison.

## Continue across steps, interruptions, and agents

Reuse the owning task's checkpoint or run record, with one clear owner and a
discoverable current entry. Retain only information needed to resume:

| Information | Content or resolvable reference |
| --- | --- |
| Basis | Goal, scope, completion conditions, applicable procedure and versions |
| Position | Current subtask, completed work, unfinished changes, active outputs |
| Knowledge | Facts, provisional hypotheses, decisions and reasons; rejected approaches only when useful to avoid repeated work |
| Evidence | What was checked, subject/version, results, and limitations |
| Conditions | Blockers, unresolved choices, dependencies, existing authority |
| Continuation | Next action, prerequisites, owner, and sources needed first |

Refresh this entry when a material finding, decision, failure, or source change
alters continuation, and before a planned pause or handoff. Checkpoint meaningful
progress inside long stages; advance notice of compaction or interruption may
be unavailable. Preserve concise rationale, not every tool call or private
reasoning transcript. Reuse native records rather than introduce parallel state.

On resume, read the current entry, required procedures, and relevant original
artifacts. Reconcile actual changes since the checkpoint, determine which evidence
still applies, and resume incomplete or invalidated work. A proposed next action
does not override permissions, blockers, or gates. Update the current view while
retaining prior results and superseded decisions needed to interpret it. Follow
existing stronger retention rules; never rewrite old evidence to manufacture PASS.

## Design connected work

When designing or revising procedures, identify meaningful producer/consumer
boundaries, required inputs and outputs, completion conditions, unresolved-decision
owners, and permitted next actions. A single Root moving between procedures is
also a consumer. Reuse the component's existing contract and state vocabulary.

Specify what the receiving step must read and check before relying on a result:
input/output identity, evidence availability and applicability, required results,
and unresolved conditions. Distinguish mechanical checks from responsible semantic
review. A ready flag, hash, or assertion that a file was read is not sufficient.
For design-only work, identify proposed checks and mark execution NOT_RUN.

Bind evidence to the evaluated inputs, subject, method, and relevant environment;
identify actual uncommitted content when a commit alone is insufficient. After
change, determine affected dependencies and necessary revalidation. Reuse earlier
evidence only with a justified applicability basis and the owning procedure's
required checks. Historical PASS does not automatically apply to the current work.

Make the current step, last meaningful result, failure/wait reason, and next action
observable. Connect requirements or criteria, activities, subject versions,
evidence, and decisions through resolvable references. Markdown can provide the
current readable view; use native structured records where a consumer needs them.
This requires neither a universal schema nor a separate telemetry subsystem.

## Control overhead and evaluate changes

Scale effort to uncertainty and failure consequences. Use focused retrieval and
relevant checks; broaden for changed code, failures, or unresolved interactions.
Avoid duplicate records, unchanged repeated investigations, and parallel work
whose coordination cost exceeds its benefit. Preserve mandatory verification.

When introducing or materially revising these practices, evaluate representative
short work, interrupted work resumed without prior chat, and a dependent handoff
with missing or stale evidence. Observe next-action selection, constraint
preservation, invalid assumptions, and evidence consumption separately from
schema/replay/identity checks. These are evaluation directions, not new gates
that every ordinary task must execute.

Assess quality, reliability, and performance separately: acceptance failures,
unsupported claims, repeated investigation, recovery effort, and measured
time/token/tool use when available. Compare similar tasks under comparable
conditions; report variation and limits. Revise demonstrated weaknesses.
Instructions are not runtime enforcement, and small trials do not establish
universal compliance or general performance improvement.
