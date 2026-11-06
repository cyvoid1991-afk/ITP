# ITP installation on Windows with Claude Code

Date: 2026-11-06. Scope: installation guidance for the existing repository snapshot; no framework source changes. Target: native Windows, an existing Python installation without `.venv`, and user-confirmed Opus 5 high / Sonnet 5 high availability.

## Decision

**Preserve the repository layout and add a destination-local Claude adapter.** The Python CLI can be installed separately from the agent integration. Successful CLI tests do not establish that Claude can perform the governed roles correctly.

This is a proposed host adaptation, not a verified Claude release. The original repository requires GPT models and a repository virtual environment. The destination's explicit operating profile must override only those host/environment choices; it must retain role ownership, independent verification, procedure binding, and deterministic gates. The user's Windows/no-venv/Claude requirements are the basis for that profile.

| Layer | Keep | Adapt at destination |
| --- | --- | --- |
| Python runtime | CLI, schemas, tests, pinned requirements | Select one installed Python 3.11+ executable |
| Repository layout | `.agents/`, `.codex/`, `tools/intent-tool-pipeline/` | Change the installation root, e.g. `C:\itp` |
| Instructions | Original `AGENTS.md` and bound procedures | Add `CLAUDE.md` with imports and a narrow host override |
| Roles | Full semantic instructions, exact role IDs, write boundaries | Add `.claude/agents/*.md` definitions |
| Skills | Original `.agents/skills/` and relative references | Add small Claude skill entry wrappers |
| Evidence | Existing hashes, receipts, history and schema identities | Record actual Claude host/model separately |

The benefit is a reversible installation without a source fork. The cost is maintaining and testing a host adapter. If the installed Claude runtime cannot honor an exact role or its required output boundary, stop that governed operation; changing role IDs or bypassing a gate is not a workaround.

## 1. Restore the snapshot

Copy these files to the destination computer:

- `ITP-full-20261104-163615.zip`
- `ITP-full-20261104-163615.zip.sha256`
- This guide, which was created after the ZIP and is not inside it.

Use a new, short directory. The ZIP contains repository contents directly, without an enclosing `ITP` directory. PowerShell:

```powershell
$archive = 'C:\transfer\ITP-full-20261104-163615.zip'
$repo = 'C:\itp'
$expected = ((Get-Content -LiteralPath ($archive + '.sha256') -Raw).Trim() -split '\s+')[0]
if ((Get-FileHash -LiteralPath $archive -Algorithm SHA256).Hash -ne $expected) {
    throw 'Archive checksum mismatch'
}
if (Test-Path -LiteralPath $repo) { throw 'Choose a new extraction directory' }
Expand-Archive -LiteralPath $archive -DestinationPath $repo
Set-Location -LiteralPath $repo
git fsck --full
git status --short
```

Install Git for Windows if the Git checks are unavailable. Expect no Git integrity errors and a clean restored working tree before adding local configuration. The archive contains `.git` and the local snapshot, including hidden directories. Its checksum detects transfer corruption; it is not a publisher signature.

Do not flatten `tools/intent-tool-pipeline/`. Keep generated parent paths below 180 characters, directory segments at most 32, and filenames at most 64. A short root reduces later run-path failures.

**Do not use the preserved seed manifest as a current-snapshot acceptance test.** `SOURCE_MANIFEST.json` describes the original public seed; current source already differs. `verify_bundle.py` can report those differences and newly added Claude files. Do not rewrite historical hashes to produce PASS. See `SOURCE_IDENTITY.md` and the root README.

## 2. Select Python and install dependencies without a virtual environment

Run in PowerShell. If `python` is not the desired interpreter, replace the first command with its absolute executable path. All later commands must use the same `$py`.

```powershell
$repo = (Resolve-Path -LiteralPath 'C:\itp').Path
Set-Location -LiteralPath $repo
$py = (python -c "import sys; print(sys.executable)").Trim()
if ($LASTEXITCODE -ne 0 -or -not (Test-Path -LiteralPath $py)) {
    throw 'Select an installed Python executable'
}
& $py -c "import sys; print(sys.version); print(sys.executable); assert sys.version_info >= (3,11), 'Python 3.11+ required'; assert sys.prefix == sys.base_prefix, 'Select a non-venv interpreter'"
if ($LASTEXITCODE -ne 0) { throw 'Python preflight failed' }
& $py -m pip --version
```

If pip is missing, use `& $py -m ensurepip --upgrade`, then retry. Install the repository's declared dependencies:

```powershell
& $py -m pip install --user -r "$repo\tools\intent-tool-pipeline\requirements-dev.txt"
if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed' }
& $py -m pip check
if ($LASTEXITCODE -ne 0) { throw 'Resolve dependency conflicts before continuing' }
& $py -c "import sys,yaml,pytest,tomllib; print(sys.executable); print('PyYAML',yaml.__version__); print('pytest',pytest.__version__)"
```

The current pins are `PyYAML==6.0.3` and `pytest==9.1.0`. The minimum version is a prerequisite, not a guarantee for every newer Python. Confirm compatibility with the checks below. Without `.venv`, user-site package changes can affect other projects. If user-site packages are disabled or conflicting, use a separately installed non-venv Python with an appropriate package location; do not silently upgrade the requirements or switch interpreters.

```powershell
$project = Join-Path $repo 'tools\intent-tool-pipeline'
$ops = Join-Path $project 'pipeline_ops.py'
$env:PYTHONIOENCODING = 'utf-8'
& $py $ops --help
if ($LASTEXITCODE -ne 0) { throw 'CLI smoke check failed' }
& $py "$repo\.agents\skills\build-tool-pipeline\scripts\initialize_run.py" --help
if ($LASTEXITCODE -ne 0) { throw 'Initializer smoke check failed' }
$testTemp = '.tmp\cc-' + (Get-Date -Format 'MMddHHmmss')
& $py -m pytest tools/intent-tool-pipeline/tests -q --basetemp=$testTemp
if ($LASTEXITCODE -ne 0) { throw 'Record and resolve test failures' }
```

Run tests before adding Claude adapters to separate baseline failures from adaptation failures. Do not delete failing tests. The Codex delegation tests inspect original TOML/model policy; leaving `.codex/` intact preserves that baseline, but passing them does not validate Claude configuration.

## 3. Install and start Claude Code

If not installed, use the official Windows installation procedure, for example `winget install Anthropic.ClaudeCode`. Open a new terminal, check `claude --version`, then launch `claude` from `C:\itp` and authenticate. Git for Windows provides Git Bash; recent versions can also use a PowerShell tool. Native Windows does not provide Claude's OS sandbox. [Official Windows setup](https://code.claude.com/docs/en/setup).

All command blocks in this guide are PowerShell. Launching Claude from PowerShell does not imply that its shell tool also executes PowerShell. Ask it to use the PowerShell tool; if unavailable, invoke a saved PowerShell script explicitly through `powershell.exe -NoProfile -File <path>` or `pwsh -NoProfile -File <path>`. Do not paste `$py`, `&`, or PowerShell here-strings directly into Bash. Shell-call variables may not survive subsequent calls; initialize paths in each script or pass absolute paths.

## 4. Add the local instruction bridge

Create `C:\itp\CLAUDE.md` at the destination, preserving existing files if one already exists. Use this content, replacing the Python placeholder with the exact path reported above:

```markdown
@AGENTS.md
@tools/intent-tool-pipeline/AGENTS.md

## Destination host profile: Windows / Claude Code

The user selected native Windows, no virtual environment, and Claude Code.
Repository root: C:/itp
Runtime project root: C:/itp/tools/intent-tool-pipeline
Python executable: <absolute path selected and checked during setup>

This local profile overrides only Codex host/model selection and .venv command
prefixes. Execute documented Python commands with the selected interpreter.
Preserve original procedure files and all workflow gates and write boundaries.
Root coordination runs on user-authorized Opus 5 high. Semantic roles run on
Opus 5 high. Bounded implementation/execution workers run on Sonnet 5 high.
Record the effective exact model IDs; do not silently substitute other tiers.

Read nearest nested AGENTS.md files before working in their scope.
Read skills and references at their original .agents paths. Resolve each
relative link from the file containing it, not from the current shell directory.
Keep semantic role names and serialized root_codex values unchanged.
root_codex is a compatibility identifier, not a claim that Codex executed work.
Record actual host/model identity separately in new installation/run evidence.

Root owns assignments, implementation integration, canonical registration and
state transitions. Semantic roles cannot delegate. The independent verifier
must not edit the implementation, delivered tests or acceptance baseline.
Use original assigned paths for governed submissions; no per-role worktrees.
Forward each child's explicit assignment, interpreter, inputs and boundaries.
Do not assume that a child received Root's conversation or shell variables.
Do not bypass failed checks, rewrite historical evidence or migrate old runs.
```

Recent Claude versions can load `AGENTS.md` directly, depending on configuration. An explicit `@AGENTS.md` import also supports sessions without that capability; confirm loaded instructions in the destination. [Instruction loading and imports](https://code.claude.com/docs/en/memory).

The profile records the requested platform change; it does not assert GPT/Claude equivalence. If organization-managed settings conflict with it, resolve the conflict before governed work.

## 5. Convert agent registrations, preserving semantic instructions

Codex project roles use `.codex/agents/*.toml`; retain those files as source definitions and baseline evidence. [Codex custom-agent configuration](https://learn.chatgpt.com/docs/agent-configuration/subagents).

Claude project agents use Markdown with YAML frontmatter under `.claude/agents/`. Map `developer_instructions` to the Markdown body, retaining the entire text including the runtime boundary. Use exact existing `name` values and descriptions. Claude supports `model`, `effort`, tool restrictions and `permissionMode`; these are not direct equivalents of Codex sandbox settings. [Claude subagent reference](https://code.claude.com/docs/en/sub-agents).

**Proposed model allocation within the two user-authorized tiers:**

| Role | Destination model / effort | Reason |
| --- | --- | --- |
| Root coordinator | Opus 5 / high | Integration and gate decisions |
| `intent_realizer` | Opus 5 / high | Realization conditions and ambiguity |
| `product_contract_agent` | Opus 5 / high | Behavioral contract and acceptance |
| `independent_verifier` | Opus 5 / high | Independent evidence judgment |
| `product_intake_consultant` | Opus 5 / high | Intent convergence |
| `collaborative_intent_shaping_agent` | Opus 5 / high | Problem/intent shaping |
| `theoretical_analysis_agent` | Opus 5 / high | Mathematical and engineering judgment |
| New bounded implementation worker | Sonnet 5 / high | Assigned implementation and checks |

This allocation is a workflow judgment, not a benchmark claim. Using Opus for semantic roles prioritizes judgment consistency; Sonnet workers limit implementation cost. Independence comes from separate roles, context and write ownership, not merely from using different model tiers. Do not reuse an implementation worker as the verifier.

Resolve the actual provider-specific Opus 5 and Sonnet 5 IDs in the target account. Pin those IDs in each definition and record effective dispatch. Do not rely on floating `opus`/`sonnet` aliases to mean version 5, and do not select 5.5 or another tier just because it is available. Set `effort: high` and verify that the installed version/model applies it. A matching field name does not establish equivalence with GPT high reasoning.

Example destination file `.claude/agents/product_contract_agent.md` (a template, not a complete registration):

```yaml
---
name: product_contract_agent
description: Formalizes approved product intent into a behavioral and acceptance contract.
model: REPLACE_WITH_AVAILABLE_OPUS_5_MODEL_ID
effort: high
tools: Read, Glob, Grep, Write, PowerShell
disallowedTools: Agent
permissionMode: default
---
```

After the closing delimiter, paste the **parsed complete** `developer_instructions` value from `.codex/agents/product_contract_agent.toml`. Do not paste TOML delimiters or summarize its boundaries. Repeat for all six active roles. Do not reactivate files under `.codex/retired/`.

Use Python's `tomllib` to extract that value accurately, for example from the repository root:

```powershell
& $py -c "import pathlib,tomllib; p=pathlib.Path('.codex/agents/product_contract_agent.toml'); print(tomllib.loads(p.read_text(encoding='utf-8'))['developer_instructions'])"
```

For the three ordinary read-only roles, use `tools: Read, Glob, Grep`. For Realizer, Contractor and Verifier, the proposed tool list permits assignment loading and an assigned output file; **tool availability does not authorize other writes**. If PowerShell is unavailable, explicitly adapt to the supported shell and retest. The verifier additionally needs execution tools for authorized isolated probes. Shell tools can write files even without `Write`, so tool restrictions alone are not a filesystem boundary.

The model and tool lists above are installation proposals. Review them against actual target capabilities. Keep normal permission checks; do not use `bypassPermissions` to make a fixture pass. Ensure semantic roles cannot spawn children and cannot invoke another CLI to evade that restriction. Use sequential semantic invocations initially; do not assume `.codex/config.toml` concurrency settings carry over.

For an optional Sonnet worker, add a separate Claude definition with its own ID, the exact Sonnet 5 model, `effort: high`, and only the tools its assignment needs. Supply exclusive file ownership and prohibit edits to framework state and other roles' artifacts. Root remains responsible for integration.

## 6. Expose skills without moving their source

Claude loads project skills from `.claude/skills/<name>/SKILL.md`; slash commands invoke them. Add wrappers that direct Claude to the original files instead of copying the procedure tree. [Claude skill locations and invocation](https://code.claude.com/docs/en/skills).

For example, create `.claude/skills/intent-tool-pipeline/SKILL.md`:

```markdown
---
name: intent-tool-pipeline
description: Route ITP tool work using the repository's original procedure.
disable-model-invocation: true
---
Read .agents/skills/intent-tool-pipeline/SKILL.md from the repository root.
Follow that original skill and its selected original references in place.
Resolve relative references against each original file's directory.
Apply the destination CLAUDE.md interpreter and host profile.
Do not start a workflow merely to install or inspect this repository.
```

Use the same wrapper pattern for the skills needed by the selected workflow, including `build-tool-pipeline`, `intent-realization`, `author-product-contract`, and `independent-verification`. Direct reading of original skills remains sufficient when a wrapper is absent. A wrapper is navigation, not a replacement procedure. The Claude entry is `/intent-tool-pipeline`, whereas `$intent-tool-pipeline` in existing documentation is a Codex invocation convention.

## 7. Path and identity rules

| Existing reference | Destination treatment |
| --- | --- |
| `.\.venv\Scripts\python.exe` or `../../.venv/Scripts/python.exe` | Execute with the selected absolute `$py`; leave original procedure bytes intact |
| Old machine's repository path | Replace in new local configuration/commands with `C:\itp` |
| `--project-root` | Use `C:\itp\tools\intent-tool-pipeline`, unless the specific operation explicitly names another project |
| `workspace/`, `intent_deliver/`, `codex_workspace/`, governed `deliverables/` | Relative to the runtime project root |
| `.agents/`, `.codex/`, `.claude/` | Relative to the repository root |
| `root_codex`, `codex-vfy`, `.codex-scratch.json` | Preserve schema/implementation identifiers |
| Existing run paths, receipts and procedure hashes | Preserve; no global replacement or automatic migration |

The control registry in `pipeline_control/procedures.py` resolves original `.agents` assets from the installed repository. `validation.py` requires `persistence_owner == 'root_codex'`. Renaming those to Claude-specific equivalents breaks existing validation. Record actual host/model identity in separate new evidence rather than changing canonical schema fields.

Control `1.2` is the default for new runs. The child must load its real assignment, read original procedures, write only the assigned submission, and retain the exact `required_result_binding`. Root registers unchanged bytes through `finalize-semantic-return`. Follow the original invocation procedure and rollout guide for complete commands. Missing permissions, bindings or role discovery are failures to resolve, not reasons to switch to `1.0` or impersonate the role in Root.

Moving a fresh installation is different from relocating an active run. If the source contains active runs, stop writers and review the existing rollout/recovery procedure before moving anything. This guide does not authorize migration or establish that relocated historical paths remain valid.

## 8. Acceptance checklist and first-session prompt

Complete these checks in the destination and retain results in a new, short installation evidence directory under `tools/intent-tool-pipeline/workspace/`, observing its local `AGENTS.md`:

| Check | Acceptance evidence |
| --- | --- |
| Snapshot | ZIP hash matches; restored Git integrity and status checked |
| Python | Exact executable/version, no venv, dependency versions, pip check |
| Runtime | Both help commands and baseline tests pass, or failures explicitly resolved |
| Instructions | Root and nested rules plus narrow destination overrides are loaded |
| Registration | All six exact active names discovered; correct full bodies loaded |
| Models | Actual Opus 5 / Sonnet 5 dispatch and high effort observed, not self-reported only |
| Read-only behavior | Read-only role has no write/shell/delegation capability |
| Assigned output | Each artifact role completes a disposable authorized assigned-file exercise; protected files remain unchanged |
| Verifier | Separate invocation, independent evidence and no modifications to its target |
| Governed operation | A disposable authorized `1.2` fixture demonstrates assignment loading, unchanged finalization, admission and forward validation |

A claimed refusal is not a substitute for checking file changes. Hash protected inputs before/after a fixture and inspect boundary diagnostics. Keep any fixture within an explicitly assigned disposable directory; it must not modify a real product or historical run. A successful fixture is bounded installation evidence, not a verified product release.

Suggested initial Claude message after configuration:

```text
Inspect this ITP installation using CLAUDE.md and the original repository rules.
Use the configured non-venv Python executable. Do not change framework source.
Confirm exact discovery and effective model/effort for the six semantic roles.
Use Opus 5 high for Root and semantic roles, Sonnet 5 high for bounded workers.
Read original .agents skills in place. Preserve root_codex schema values.
Check CLI/dependencies and report baseline failures before any governed work.
Then exercise role boundaries in a disposable installation fixture, preserving
verifier independence, original procedure binding and all deterministic gates.
Do not migrate historical runs or claim a release from this installation check.
Report actual results, effective paths/models and remaining incompatibilities.
```

## Verification status of this guide

Repository layout, interpreter requirements, original role files, procedure registry and fixed identity checks were inspected. Claude configuration guidance was checked against the official pages linked above on 2026-11-06. The earlier ZIP was extracted and its 208 files matched by SHA-256, with Git integrity checked during packaging.

All five PowerShell blocks passed parser checks. Referenced entry points and all six role source files exist. The original ZIP still matches its SHA-256 sidecar, and tracked repository files have no changes. These are static/document checks, not execution of the installation commands.

No destination installation, package installation, Claude role dispatch, effort enforcement, or end-to-end Claude workflow was executed while writing this guide. No Claude executable was found on the authoring machine's PATH. This document adds guidance only; it does not alter source, original agent settings, procedures, historical manifests or the existing ZIP.
