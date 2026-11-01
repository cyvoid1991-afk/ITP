# Apply Harness 2.3.1

**Install the complete package for explicit skill invocation or for the full
procedure applied through AGENTS.md.** Both modes start at SKILL.md; their entry
trigger differs. Linking only work-guidance.md applies a smaller subset.
All operational documents are inside this folder. No particular repository,
pipeline, Python environment, external service, or other skill is required.
Instructions support quality, reliability, and efficiency; they do not guarantee
agent compliance or measured improvement.

| Mode | Entry trigger | Files needed |
| --- | --- | --- |
| A: skill invocation | User invokes `$apply-harness` | Entire `apply-harness/` folder |
| B: standing full procedure | Applicable AGENTS.md requests this procedure throughout work | Same entire folder plus the supplied AGENTS.md setup text |

Full procedure includes profile selection, Inspect/Map/Fill/Verify/Record,
the selected control map, completion checks, and conditional references.
It does not mean Standard or every H1-H17 control on every task. Light remains
the default; Standard and workflow-harness construction retain explicit-request rules.

## Common installation in another repository

Extract the ZIP and copy the whole folder into the target repository:

```text
target-repo/
  AGENTS.md                         # mode B entry
  .agents/skills/apply-harness/
    SKILL.md
    work-guidance.md
    harness-checklist.md
    workflow-procedure.md
    references/workflow-record-example.md
    agents/openai.yaml
    setup/AGENTS.full.md
    setup/skill-invocation.txt
    README.md
```

The archive's MANIFEST.json is for optional integrity checks; it is not a runtime
dependency. Preserve existing instructions and reconcile local changes before
replacing an installed copy. No originating repository needs to be available.

## Mode A: invoke as a skill

Copy the entire `apply-harness/` folder into a skill directory supported by your
agent host. For a repository that discovers `.agents/skills/`, the resulting entry
is `.agents/skills/apply-harness/SKILL.md`. Preserve an existing installation until
its local changes and version are reconciled. Confirm discovery in that host.

No AGENTS.md edit is required for this mode. Invoke `$apply-harness` with the task.
An unspecified profile uses Light. Copy prompts from
[setup/skill-invocation.txt](setup/skill-invocation.txt).
Request Standard or workflow harness construction explicitly when needed:

```text
$apply-harness Review this implementation using Light controls.
$apply-harness Use Standard to design the verification and handoff controls for this workflow.
```

Start at [SKILL.md](SKILL.md). It selects the required local guidance and controls.
The [checklist](harness-checklist.md) defines H1-H17; the
[workflow procedure](workflow-procedure.md) applies only under its activation rule.

## Mode B: apply the full procedure through AGENTS.md

After the common installation, merge [setup/AGENTS.full.md](setup/AGENTS.full.md)
into the target repository's root AGENTS.md. If none exists, use the example as
the new file. Keep unrelated instructions. The example's link is relative to
the target repository root, where it is installed, not to the setup directory.

Ready-to-copy configuration:

```markdown
## AI work procedure

Apply [Apply Harness](.agents/skills/apply-harness/SKILL.md) as the standing
work procedure for tasks in this repository. Read that entry at task start
and after context loss; follow its profile rules, application steps, selected
control map, completion checks, and conditional document references.
Use Light by default. This standing instruction requests the full skill
procedure; it does not select Standard or automatically authorize workflow
harness construction. Follow SKILL.md's explicit-request rules for those.
Reuse existing records; a compact map can be kept in the normal task result.
Preserve task scope, permissions, component requirements, and unrelated work.
If the entry or a required reference is unavailable, report that setup gap
before claiming the procedure was applied; continue unaffected authorized work.
```

This mode follows the same SKILL.md procedure as explicit invocation, without
needing a `$apply-harness` message each time or host skill discovery. The host
must load AGENTS.md or an equivalent instruction file. In another layout, keep
the package together and adjust the entry link relative to that instruction file.
Do not replace the full entry with work-guidance.md alone.

After setup, ask the agent to identify its loaded entry, selected profile, and
required references for a small task. Inspect actual loading and task behavior;
copying files alone does not establish adoption or compliance.

## Optional: common guidance only

[work-guidance.md](work-guidance.md) has no external file dependencies and may be
copied or linked by itself. That applies common work/context/continuity guidance,
not the full skill procedure or checklist. Use mode A or B for the complete migration.

If both modes are used, select one maintained copy of the common guidance and
track deployed copies by revision. Avoid divergent copies of the same policy.
The host must actually load or follow your chosen instruction file; merely
copying a document does not establish that it was applied.

## Contents and maintenance

| File | Role |
| --- | --- |
| `SKILL.md` | Invocation, profile selection, control map and completion procedure |
| `work-guidance.md` | Portable common core, continuation, workflow design and overhead |
| `harness-checklist.md` | Stable H1-H17 definitions and completion gate |
| `workflow-procedure.md` | Explicit workflow-harness construction and consumption rules |
| `references/workflow-record-example.md` | Fictional handoff and resume example, read on demand |
| `agents/openai.yaml` | Optional host UI metadata; no runtime tool dependency |
| `setup/AGENTS.full.md` | Merge into the target root AGENTS.md for mode B |
| `setup/skill-invocation.txt` | Copyable explicit invocation examples for mode A |
| `README.md` | Portable adoption and version information |

The development repository's authoritative source is `.agents/skills/apply-harness/`.
That provenance path is not a loading dependency in another repository. A copied
installation is a deployment of this source revision, not a competing source tree.
No license grant for third-party material is implied.

Revision 2.3.1 clarifies full standing adoption and adds portable setup examples.
Revision 2.3's work guidance, controls, activation rules and H1-H17 identities remain.
Replacing instructions
does not migrate existing task schemas or records, or mechanically enforce gates.
Verify local links and loading after installation; assess actual behavior on
representative tasks before claiming reliability or performance improvements.
