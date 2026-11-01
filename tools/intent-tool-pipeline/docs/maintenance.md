# Maintain the framework and tool products

Edit authoritative product source, tests and operator docs under tool-local
`codex_workspace/<tool_name>/`. Demos belong in `demo_workspace/`, probes in
`test_workspace/`, run evidence in `workspace/build_runs/`, and verified release
archives in `deliverables/`. Generated candidates are not product source.
Other existing tools retain their documented authoritative locations. A bounded
local revision does not require moving them into `codex_workspace/`. Local
independently assembled patch/full outputs belong in repository-root
`deliverables/`; they do not become formal ITP releases.

Before editing, inspect root and nearest `AGENTS.md`, current changes, product
history and active runs that may own the paths. Record material revisions with
date, revision ID, trigger, behavior/interface change, affected components,
compatibility, actual verification and limitations. Released history is
append-only. Cross-cutting repository changes belong in
[root history](../../../CHANGELOG.md); pipeline changes belong in
[tool history](../CHANGELOG.md).

Use the repository `.venv` for focused checks and the maintained suite. From the
tool directory, run `../../.venv/Scripts/python.exe -m pytest tests -q --basetemp=../../.tmp/itp`
on Windows. Check paths and documentation against actual commands. Local tests do
not replace governed independent verification or candidate inspection. Record
unrun checks as `NOT_RUN`.

On Windows, an editor watching repository scratch files can temporarily prevent
atomic replacement of a ZIP or state file. S6 directly observed a Visual Studio
Code lock through Windows Restart Manager; the original failing attempts remain
in its evidence. Preserve the error and identify the lock before classifying it.
For regression checks, keep the same declared Python environment and use a fresh,
short system-temporary `--basetemp` outside the watched repository if needed.
Record the actual path and original failure; do not waive assertions, rewrite
evidence, disable protection, or treat a retry as the original successful attempt.
For operational runs, quiesce conflicting readers and follow the existing
transaction recovery procedure; never move a live run or strip its markers.

For authorized local source revisions or package-only delivery, use
[$minor-tool-revision](../../../.agents/skills/minor-tool-revision/SKILL.md) and its
[local-delivery reference](../../../.agents/skills/minor-tool-revision/references/local-delivery.md).
Source focused/full tests and package loading/application evidence are separate.
Retain `PRE_EXISTING_DELTA_NOT_VERIFIED_BASELINE` and link the repository-relative
manifest from authoritative history using `Local delivery record: ` followed by
its backtick-enclosed path. The next B intake validates linked records and carries
their cumulative scope without relaxing exact-baseline or release gates.

Docs-only local corrections do not modify old releases. A requested formal
documentation release follows Workflow B. The
[optional-workflows reference](../../../.agents/skills/intent-tool-pipeline/references/optional-workflows.md)
describes the pre-package documentation assessment. Preserve original source
manifests, run-specific hashes and candidate identities; do not refresh evidence
to force a pass.

## Create the next framework bundle

Read the [publication boundary](distribution.md) before changing the inventory.
The diagnostic bundle distinguishes bundled operational dependencies from exact
source-only history references; an undeclared missing target remains an error.

Update tool `VERSION`, append actual changes and checks to history, and review
`packaging/itp/include-list.json`. Its explicit inventory includes repository-root
configuration and the tool under `tools/intent-tool-pipeline/`, preserving the
integrated layout. It must not include private intents, product sources,
generated runs, environments, secrets or Git metadata. From the tool directory:

```powershell
../../.venv/Scripts/python.exe packaging/itp/build.py
```

The archive is `dist/intent-tool-pipeline-<VERSION>.zip` under the tool directory.
It has repository-shaped entries rather than the original flat seed layout and
a new manifest for those entries. Extract to a new short directory and verify
before creating caches or installing dependencies:

```powershell
python tools/intent-tool-pipeline/verify_bundle.py
```

Repeat setup, CLI and maintained tests in the extraction. Preflight the longest
member path against the destination. Inspect staged files before committing.
Building a framework bundle does not grant pipeline verification to a product.
