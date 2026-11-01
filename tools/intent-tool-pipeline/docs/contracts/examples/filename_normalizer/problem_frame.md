# Problem Frame

## Contract Metadata

- Schema version: `1.0`
- Artifact ID: `problem-frame`
- Version: `1`
- Lifecycle status: `ACTIVE`
- Semantic owner: `problem_framer`
- Persistence owner: `root_codex`
- Source artifacts: `build-request@1`
- Created at: `2026-08-09T17:45:11+09:00`
- Updated at: `2026-08-09T17:45:11+09:00`

## Completion Status

`PASS` — The approved input defines the UX, normalization, classification, ordering, safety, reporting, and exit behavior sufficiently for requirement and acceptance formalization.

## Input Reviewed

- `build-request@1`
- Referenced approved source: `experiments/subagent_practice/test_input.md`

No transcript reconstruction or other product-context source was used.

## Active Problem

Define the UX and behavior for a reusable Python CLI that safely previews and applies deterministic filename normalization to eligible CSV and JSON files in one local directory.

## Objective and User Need

An operations analyst needs to normalize inconsistent filenames without editing each file manually or risking silent overwrites. The batch must be visible before execution, safe renames must follow the approved preflight classification, isolated failures must remain visible, and terminal and CSV results must be deterministic.

## Target UX Flow

1. Run `python normalize_names.py <input_directory>`.
2. Validate that the path exists and is a directory.
3. Inspect supported regular files directly inside the directory.
4. Precompute normalized targets, collisions, and occupied targets.
5. Display sorted preview rows without mutating the filesystem.
6. When `--apply` is supplied, attempt only candidates approved by preflight.
7. Continue after an isolated rename failure.
8. Write or replace `rename_report.csv`, print summary counts, and return the defined exit code.

## Scope

- Directly contained regular `.csv` and `.json` files, matched case-insensitively.
- Deterministic ASCII stem normalization and lowercase extensions.
- Leading-dot hidden-file classification.
- Preview and explicit apply modes.
- Complete collision and occupied-target preflight.
- Deterministic terminal/report ordering and defined summary counts.
- Windows and Linux support.

## Non-Scope

- Recursive traversal, directory renaming, file-content changes, GUI, watcher service, undo, conflict suffixes, platform-specific hidden attributes, and external deployment.

## Inputs and Outputs

- Input: required `<input_directory>` and optional `--apply`; `-h` and `--help` are supported.
- Preview: current name, proposed name, action status, and final summary; no mutation and no report.
- Apply: safe renames, terminal rows and summary, and `rename_report.csv` with `original_name`, `normalized_name`, and `status`.
- Unsupported files, nested files, and reserved `rename_report.csv` are omitted from candidate evaluation.

## Failure Behavior

- Missing or non-directory input prints a clear stderr error, performs no file operation, and exits `2`.
- Policy skips are not operational failures.
- Per-file rename failures are recorded as `failed`; remaining safe renames continue and final exit is `1`.
- Report creation or replacement failure exits `1` without rolling back completed renames.
- A preview or apply run without operational failure exits `0`.

## Constraints

- Python 3.11 or later and standard library only.
- Preview is the default; no rename may overwrite a different existing file.
- All collision and occupied-target classification precedes mutation.
- Only approved per-file statuses may be emitted.
- Help performs no filesystem operation.
- Deliverable includes script, tests, README, and example-directory description.

## Assumptions

None. No behavior-changing inference is required.

## Decisions

- `DEC-001` — User-approved preview/apply safety boundary; status `APPROVED`.
- `DEC-002` — User-approved preflight and overwrite rule; status `APPROVED`.
- `DEC-003` — User-approved partial-failure continuation rule; status `APPROVED`.

## Open Issues and Blockers

### Blocking

None.

### Non-Blocking

- Exact presentation wording and internal implementation structure remain reversible implementation choices.

## Validation Needs

- Verify help and invalid-path behavior without side effects.
- Verify every normalization and per-file classification rule.
- Verify complete preflight, deterministic order, and non-overwrite guarantees.
- Verify preview non-mutation, apply results, reporting, summaries, continuation, and exit codes.
- Verify report failure behavior, reserved-report handling, and platform compatibility.

## Handoff Readiness

The Product Contract stage may proceed from `build-request@1` and `problem-frame@1` without the source transcript. There are no carried assumptions or open blockers.
