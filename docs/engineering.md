# Repository Engineering Guide

Use this guide for generated paths, shared Python checks, and delivery-package
checks. It preserves the detailed defaults formerly recorded in root
[AGENTS.md](../AGENTS.md). Component instructions define their own execution
environment and may impose stricter path or package requirements.

## Generated Paths

- Default limits: directory segments at most 32 characters, filenames at most
  64 characters, and absolute parent paths shorter than 180 characters.
- Resolve and measure generated paths before creating them. Reserve room for
  suffixes and nesting added by execution tools.
- If a path exceeds the budget, shorten generated names or use repository
  `.tmp/` for disposable, reproducible output. Give pytest a short, unique
  `--basetemp`, such as `--basetemp=.tmp/policy-check`.
- Retained source and required evidence must remain outside disposable storage.
  Follow stricter component or application limits where defined.

## Python Environment

- From the repository root, use `.\.venv\Scripts\python.exe` for shared Python
  and ITP checks on Windows. On POSIX, use `.venv/bin/python`.
- Follow a component's declared environment for other tools. Do not silently
  substitute another environment to hide missing dependencies.
- See the [repository setup](../README.md#pipeline-quick-start) for environment
  setup and the [ITP instructions](../tools/intent-tool-pipeline/AGENTS.md)
  for framework checks. Missing prerequisites leave the affected checks incomplete.

## Delivery Packages

- Include required runtime assets, dependencies or setup instructions,
  entry points, and known limitations. Exclude secrets, disposable caches,
  and unrelated data; retain applicable third-party notices.
- Before reporting a ZIP ready for use, extract it into an isolated location
  and verify its documented loading or execution procedure.
- Reuse applicable component evidence, but separately check new connections,
  changed behavior, and the assembled package.
- Missing source identity, failed required checks, or an unusable extracted
  package blocks the affected delivery claim.
- Use the owning component's release procedure. This guide does not replace
  ITP release gates or authorize a release.
