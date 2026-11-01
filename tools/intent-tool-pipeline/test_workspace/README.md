# Development Test Workspace

Use this directory for temporary fixtures, command probes, and integration runs
created during development. The contents are intentionally non-authoritative.

- `fixtures/`: temporary input structures
- `runs/`: generated test output and logs
- `scratch/`: short-lived experiments

Move reusable tests into the relevant tool project or the root `tests/`
directory. This workspace may be cleaned without affecting released tools or
framework history.
