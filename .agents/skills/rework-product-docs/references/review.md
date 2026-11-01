# Review documentation rework

Read this before reviewing a product rewrite or verifying changes to this skill.
Keep mechanical facts separate from semantic judgment. A file/link/schema pass
does not establish correct capability interpretation or complete operating advice.

## Review a product run

Before editing, choose representative supplied or explicitly hypothetical requests
and identify the facts, actions and boundaries each must expose. Include different
entry artifacts and a missing-input or blocked path when relevant. Evaluate three
distinct aspects; a passing product test suite does not establish usable routing:

1. **Meaning:** compare material claims with code, tests and supported contracts;
   preserve uncertainty, units, defaults, reference meanings and authority.
2. **Operator path:** start at SKILL or README with the request and supplied inputs.
   Follow the documented links, constructing the action or justified hold from
   those documents and any explicitly supported inspection step. Do not use source
   knowledge retained during authoring to fill gaps.
3. **Mechanics:** check file/anchor resolution, applicable formats, example commands
   and safe existing validators/tests. These checks supplement the first two.

For each operator path, note the files or sections actually read, including shared
prerequisites, and any missing fact, unrelated material, unnecessary operation or
decision detour. Include direct entry into linked operation sections when relevant;
check that their prerequisites remain discoverable without the route table. If a
path grows, judge whether added completeness or correctness justifies the burden;
consider whole-document review cost separately. Measure comparable before/after
reading only when claiming a cost improvement, stating the requests and reading
method. No fixed score or separate report file is required. Check that the operator
can find:

- the supported outcome and operation choice, including explanation/inspection
  versus execution and reuse versus recomputation;
- individual supported operations and valid intermediate-artifact starting points,
  rather than only complete sequences;
- required facts, retrievable facts, applicable defaults and values needing input;
- prerequisites, conditional rules and intermediate-artifact handoffs;
- actionable commands or supported inspection steps, with their side effects;
- expected outputs, state meanings, warnings and success/partial/hold checks;
- boundaries around unsupported requests, inaccessible evidence and material
  implementation/commitment conflicts.

If a path needs knowledge found only during source inspection, put it in the
appropriate selected document or route to a supported inspection mechanism.
Repair an explanation or route when evidence permits; otherwise isolate the gap.
Recheck affected paths after repair. A long but correct document and a set of
short files can both fail if essential conditions are hard to find. Do not score
success by file count, length or prose style alone.

## Use a separate reader when it adds confidence

For a substantial redesign across tasks, prefer a fresh-context, read-only operator
pass when delegation is available and authorized. Small local edits can use author
review. Neither another installed skill nor a particular agent role is required.

Give that reader the realistic requests, rewritten operator documents and necessary
user inputs, not the author's preferred structure, source-investigation notes or
expected answers. Ask for the documents used, proposed actions/holds and missing
information. Keep source/contract evidence available to the author for judging the
returned decisions. If a separate reviewer also checks factual fidelity, label
that source-aware pass separately from the document-only operator pass.

The reader does not edit the delivery. Execution requires an explicitly scoped
safe fixture; otherwise inspect proposed actions without running them. The author
owns repair and explains acceptance or rejection of material findings. If no fresh
reader is used, label the walkthrough as author review, not independent validation;
this does not by itself block supported rework.

## Run proportionate mechanical checks

Check existing applicable format/schema rules, declared route targets (files and
anchors), changed links and version scope. Check that required instructions and
prerequisites are reachable along each reviewed supported path; judge their
sufficiency separately. Do not require every reference heading to have a direct
SKILL route: background and subordinate explanations may be reached through the
operation that needs them. Inspect old guidance for contradictions and duplication.
Verify that edits remain in the authorized scope and preserve product behavior,
data, existing results and unrelated work. Use the repository's revision-history
and change-review conventions where applicable.

Reuse available product validators, tests or examples for execution claims when
safe and relevant. Preserve meaningful recipe parsing, input validation and runtime
checks when documents move. Within authorized test-editing scope, update discovery
of relocated examples and checks tied to obsolete locations or exact wording;
link checks do not replace those semantic or execution checks. Establish their
side effects and use controlled fixtures and new output paths; respect local
temporary-path and environment rules. Do not run
expensive, external or mutating operations merely to improve documentation without
appropriate authority. If execution is unavailable, say that checks were document
review only. An unavailable checker does not make supported rework impossible.

Add a narrow helper only for a concrete repeatable predicate that existing tools
cannot handle adequately; specify inputs, assumptions and failure signals. Scripts,
new schemas and an evaluation framework are not required outputs.

## Verify this reprocessing skill when authoring or revising it

Use two layers; do not turn them into a mandatory evaluation system for each run.

1. **Static contract review.** Review actual instructions for actionable inputs,
   scope, responsibilities, workflow, evidence distinctions, decision boundaries,
   reference-reading conditions and completion criteria. Use available mechanical
   format/link checks; judge semantics through reading rather than matching words,
   fixed headings or counts. Check self-containment in an environment without
   other installed skills.
2. **Behavioral scenarios.** Use small existing samples or a minimal isolated
   fixture for normal rework, a material documentation/implementation conflict and
   insufficient evidence. Define expected behavior before judging results. Run
   the skill, inspect actual edits and decisions, and repair observed failures.
   Judge preserved meaning and usable paths, not exact prose or file layout.
   A full-product end-to-end run, fresh-operator benchmark or dedicated evaluation
   infrastructure is not required.

If independent evaluation is useful and authorized, give the evaluator the skill,
realistic request and raw artifacts, not the expected answer or prior conclusions.
Otherwise label self-review accurately. Independent agents are optional. When
revising boundary-selection rules, include both a product needing task separation
and small adequate guidance that should not be fragmented. Judge actual reading
paths and preserved meaning, not prescribed filenames.

## Report accurately

Briefly identify changed files (or an evidenced no-change result), structure choice,
reviewed paths, checks actually executed and their results, review-only coverage,
unverified areas, and blocked scope with the required decision/input. Existing check success must
not be presented as independent evaluation or proof of all usage paths. Do not
claim measured improvements in reading cost or context size without measurements.
Necessary edits and repairs must exist; a list of recommendations is insufficient.
