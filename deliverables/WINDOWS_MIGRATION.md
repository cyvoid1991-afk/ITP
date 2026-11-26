# ITP migration to Claude Code on Windows

This archive contains the complete tracked ITP checkout at `4e6a6bd` and its
Git history. It also includes this guide and the local registration script.
Use this guide for this archive. The older Windows guide under `deliverables/`
belongs to the earlier snapshot.

## 1. Extract and set up Python

Use PowerShell, Python 3.11 or newer, Git for Windows and Claude Code. Extract
into a new, short directory such as `C:\itp`. The ZIP opens directly into the
repository root. The checksum file sits next to the ZIP.

```powershell
$zip = 'C:\transfer\ITP-4e6a6bd-windows.zip'
$repo = 'C:\itp'
$expected = ((Get-Content -LiteralPath "$zip.sha256" -Raw).Trim() -split '\s+')[0]
if ((Get-FileHash -LiteralPath $zip -Algorithm SHA256).Hash -ne $expected) {
    throw 'Archive checksum mismatch'
}
if (Test-Path -LiteralPath $repo) { throw 'Choose a new extraction directory' }
Expand-Archive -LiteralPath $zip -DestinationPath $repo
Set-Location -LiteralPath $repo
git rev-parse --short HEAD
git status --short --untracked-files=no

py -3 -c "import sys; assert sys.version_info >= (3, 11), 'Python 3.11+ required'"
if ($LASTEXITCODE -ne 0) { throw 'Select Python 3.11 or newer' }
py -3 -m venv .venv
if ($LASTEXITCODE -ne 0) { throw 'Virtual environment setup failed' }
$python = '.\.venv\Scripts\python.exe'
& $python -m pip install -r tools/intent-tool-pipeline/requirements-dev.txt
if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed' }
```

Expect `4e6a6bd` and an empty tracked status. The repository's venv path
matches the original Windows procedure commands. See the official
[Claude Code installation guide](https://code.claude.com/docs/en/setup).

## 2. Register ITP and start Claude

```powershell
& $python .\setup_itp_claude.py
if ($LASTEXITCODE -ne 0) { throw 'Claude registration failed' }
& $python tools/intent-tool-pipeline/pipeline_ops.py --help
if ($LASTEXITCODE -ne 0) { throw 'ITP CLI check failed' }
& $python .agents/skills/build-tool-pipeline/scripts/initialize_run.py --help
if ($LASTEXITCODE -ne 0) { throw 'Initializer check failed' }
claude --version
claude
```

Setup prints **9 skills, 6 custom agents**. It installs local copies of the skill
directories and supporting files under `.claude/skills/`, the Markdown agent
registrations under `.claude/agents/`, and one root `CLAUDE.md` to import the
existing rules. Windows can use these files directly without junctions or
symbolic links. The authoritative procedures and CLI paths remain under
`.agents/` and `tools/intent-tool-pipeline/`. Setup stops before writing if a
destination file already exists with different contents.

Set Root's model and effort in Claude locally. To set an individual role's model
or effort, add `model:` and `effort:` in that role's
`.claude/agents/<role>.md` frontmatter. Both fields are omitted by the installer.

## 3. Check registration before the first real run

1. In Claude, use `/context all` to check project instructions, the `/` menu to
   find the skills, and `/agents` to check all six project roles. Use
   `/intent-tool-pipeline` to check routing with a read-only inspection request.
2. For actual `1.2` use, check one disposable assignment for each of
   `intent_realizer`, `product_contract_agent` and `independent_verifier`.
   Use the real assignment loader, confirm the role writes the exact authorized
   submission with its binding, and have Root register the unchanged bytes.
   Check protected paths and verify that an out-of-scope write is denied or
   rejected. Check that the Verifier leaves the candidate and delivered tests
   intact. Stop after these checks rather than running a complete product build
   and release. See the [assignment entry](.agents/skills/build-tool-pipeline/references/assignment-entry.md).

The three artifact roles need shell and write tools for the loader and bounded
output. Keep their permission prompts in the default mode and grant only the
operations authorized by the assignment. A native Windows shell can write files
through subprocesses. For OS-enforced isolation, use WSL2 with the Claude sandbox
or a separate Windows OS permission boundary. ITP continues to check binding,
ownership and output at admission. Existing runs retain their recorded paths,
selectors and receipts. [Claude sandbox documentation](https://code.claude.com/docs/en/sandboxing)
