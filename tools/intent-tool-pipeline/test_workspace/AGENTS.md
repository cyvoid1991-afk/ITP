# Development Test Workspace Rules

`test_workspace/` is disposable scratch space for probes, temporary fixtures,
and integration experiments performed while developing tools or the framework.

- Do not place canonical product source or durable framework state here.
- Assume contents of `fixtures/`, `runs/`, and `scratch/` can be deleted.
- Keep deterministic product tests with their tool and framework regression
  tests under root `tests/`.
- When a probe reveals a bug, promote the smallest reproducible fixture and
  assertion to the authoritative test suite before implementing the fix.
- Do not cite this workspace as release evidence unless the evidence is copied
  into the applicable build run or durable verification report.
