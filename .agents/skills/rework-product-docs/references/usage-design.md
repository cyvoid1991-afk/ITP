# Design an operator's reading and action paths

Read this before choosing document boundaries or rewriting the operator SKILL.
Use actual supported operations and product evidence to instantiate the procedure;
do not copy generic headings or examples as if they were the product contract.

## Divide information by use

| Role | Put here | Read when |
| --- | --- | --- |
| Operator SKILL | Applicability, responsibility, authority, shared constraints, request-handling procedure, capability navigation, completion and hold rules | Selecting and starting the skill |
| Capability navigation | Goals, supported outcomes, neighboring-operation distinctions, relevant prerequisites and exact links | Choosing the operation or sequence |
| Operation/workflow details | Input/output meanings, versioned defaults, constraints, steps, artifact handoffs, state interpretation, success/partial/blocking checks and troubleshooting | Before the corresponding decision/action |
| README | Human-oriented overview, setup, a usable first run, major capabilities and detailed entry points | Learning or installing the product |
| Examples/templates | Representative request, decisions, complete sample inputs, actions and expected checks | Preparing similar work or testing understanding |

## Choose document boundaries

For multiple independent tasks with substantial detail, default to concise README
and SKILL entry points plus task-focused references. A single short reference may
suffice for a small product. Preserve useful content, not necessarily its current
location; adding headings or links alone does not establish a suitable structure.

- Split detail read for different goals; keep one task's inputs, prerequisites,
  procedure, complete example and result checks together.
- For explanation and knowledge work, keep concepts, assumptions, evidence and
  interpretation limits together. Do not force every topic into a command recipe
  or create one file per CLI command.
- Put substantial shared contracts in one canonical location with explicit
  read-before-use links in each independently enterable operation section that
  needs them; do not rely only on the SKILL route table. Keep critical common
  constraints visible in SKILL. Repeat links or brief reminders, not contracts.
- Move rare derivations, detailed schemas and background into deeper references.
  Label links by the goal or condition that requires reading them.

Choose boundaries by usage and dependencies, not a fixed line count or file quota.
Check whether one document changes purpose midway, or one task requires collecting
essential conditions from many files. Split in the former case; consolidate or
simplify routing in the latter. Account for how the target operator can read files;
do not assume an anchor link automatically limits what enters its context. When
routing to a subsection, include links to any required parent or shared conditions
that would otherwise be skipped. Choose the reading unit so unrelated operations
can be omitted while the selected task remains complete.

Briefly explain the selected structure against the plausible alternative: keeping
the current layout or relocating detail. If retaining a substantial combined
document, explain how operators can read selectively without missing prerequisites.
No formal option matrix is required. Separate operator skills only for genuinely
independent purposes with clear selection boundaries. Avoid empty indexes and long
link chains.

Expose individual supported operations as well as composite workflows. Where the
product accepts an existing intermediate artifact, provide a route that starts
there after checking compatibility; do not make a full end-to-end sequence the
only discoverable way to reach that operation. Preparation alone can also be the
requested outcome when the product supports it.

Assign one canonical explanation location per fact or contract. Other documents
may summarize and link but must not redefine defaults, accepted inputs or result
states. Keep high-impact shared constraints visible at the entry point. Put
operation-specific constraints on the route that must be read before acting;
selective reading must not allow a critical prerequisite to be skipped.

Keep concise implementation/test pointers next to material claims or in a linked
evidence note. Use version/snapshot scope so later changes can be traced. These
pointers justify the documentation; routine use should work from the documentation
or an explicit supported inspection command without repeating source discovery.

## Embed the product-specific intent-compilation procedure

Write an explicit procedure in the operator instructions, using the product's
actual capabilities and documentation routes:

1. Identify whether the user wants explanation, inspection, preparation, execution,
   comparison or result interpretation. Unsupported categories remain boundaries.
2. Select a capability or sequence through navigation; read the relevant details
   and prerequisites before choosing inputs or acting.
3. Classify required information as user-provided facts, facts to inspect,
   documented defaults applicable to the selected version, or still-missing facts.
4. Inspect retrievable facts first. Ask only about material unresolved values or
   decisions. Keep hypotheses and example values separate from confirmed inputs.
5. Construct commands/configuration/sequences from confirmed facts and applicable
   defaults. Establish prerequisites and intermediate-artifact compatibility before
   dependent operations. Never invent a required value merely to make a command run.
6. Use supported validation and execution. Explain, inspect or interpret stored
   results without unnecessary computation or modification. Honor the authorized
   action scope and the product's actual side effects.
7. Check actual output/state against the requested outcome. Explain relevant
   warnings, partial completion, limitations and blockers instead of treating
   command success alone as proof of the user's outcome.

This is the operator LLM's working method, not a new service or agent. For each
supported path, the selected documents must supply what must be known, what action
is supported, expected outputs/states and how to recognize success or a hold.
An operation's structure should be proportional to its complexity.

## Build examples and preserve boundaries

Use a small, varied set of scenarios for decision coverage. Prefer actual supplied
requests; mark invented ones hypothetical. Supply all necessary values for runnable
examples, use controlled new output paths, identify environment requirements and
show checks against expected results. Example values are not defaults.

Derive boundaries from the product: for example, a required delay, an input that
must not be transformed twice, or rendering that reuses a stored result. These are
illustrations, not assumptions to impose on every product. If evidence does not
establish an operation, show the limitation rather than fabricating an example.

When reorganizing, inspect links/callers before moving material. Reuse existing
references, update in-scope links, retain needed compatibility entry points and
distinguish current guidance from history. Report out-of-scope links that cannot
be repaired. Do not add registries, schemas or generation systems by default.
