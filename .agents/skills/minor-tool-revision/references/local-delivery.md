# Local patch and full delivery

**Local packages carry bounded evidence; they do not create a formal verified release or an eligible pipeline baseline.** Use this reference after minor-revision qualification. Package-only requests may reuse current source evidence covering the exact source snapshot. Preserve authoritative source in place and put independently assembled packages and durable records in repository-root `deliverables/`.

## Choose the package

| Form | Use when | Required package evidence |
| --- | --- | --- |
| Patch | A small change can be applied to proven coherent installed states, including prerequisite changes. | All-target preflight, supported-state application/loading, wrong-state rejection, repeat no-op, and failure recovery. |
| Full | A self-contained snapshot is clearer or a coherent patch base cannot be established. | Clean extraction and the documented loading or execution procedure in the declared environment. |

An unknown **pipeline baseline** does not imply an unknown **patch base**. A patch may use a separately evidenced local state. If no coherent patch state can be proved, use a qualified full package or stop that delivery; never guess target bytes. A full package does not authorize overwriting an installation with unknown local changes.

## Build and verify

1. Identify authoritative source, revision IDs, declared environment, exported files, relevant tests/dependency files, and documented entry point. Preserve provenance and local changes. Exclude secrets, environments, caches and unrelated files; preflight member paths against the extraction destination.
2. Retain focused and complete maintained-suite results bound to the current source inventory. Reuse evidence only when its identity and scope still match. State unrun or failing checks accurately; they cannot support a completed accepted delivery record.
3. Assemble the scoped archive and inventory without modifying a prior package. Record ZIP-member hashes and source correspondence. Packaging-only files such as an installer or package guide have no `source_path`; inspect and exercise them as package contents.
4. Perform checks on the actual archive. For full packages, extract to a new short directory and follow documented loading/execution steps, including integrations and assembled dependencies needed by that procedure. Source-suite PASS or reused component evidence cannot substitute for this check.
5. For patches, establish each supported coherent state and execute the checks below using isolated copies. Keep observations in durable evidence. The checker is read-only: the operator owns assembly, application, backups, rollback and semantic judgment.
6. Write the manifest and evidence below, append the authoritative history link and revision IDs, then run record checks: history identity is itself checked. Report actual package/record paths and limitations. Do not accept a record with missing evidence or unresolved material decisions.

## Patch invariants

- Identify a complete supported state, including exact base and required predecessor/prerequisite changes. Do not accept arbitrary per-file alternatives mixing incompatible states. Record hashes for untouched prerequisites and every operation path, and explicit absence for additions.
- Before **any** installation write, check every declared target and prerequisite against one supported state, archive/payload hashes, safe destination paths, absence expectations, backup destination and recovery readiness. Partial application, missing prerequisites or unknown drift within that surface must stop before writing. Preserve unrelated files; the checker does not classify an entire installation as clean or dirty. The operator must justify that the declared prerequisite surface covers compatibility.
- Back up every file to replace/remove and preserve an operation log outside the installation. Recheck target identity immediately before mutation. Define rollback for partial failure, additions and removals; exercise recovery on an isolated copy. Preserve recovery evidence.
- Use `add`, `replace` and `remove` only for declared paths. After application, verify every resulting operation path and untouched prerequisite, then exercise documented loading/execution.
- Reapplication to the exact resulting state with prerequisites must be a no-op. Unknown later states must fail rather than allowing an older patch to downgrade them. Include missing-prerequisite, mixed/dirty-state, partial-application and later-state rejection probes where applicable. A filename or version string cannot establish monotonic version semantics.

The common checker preflights declared hashes and resulting-state identity. It cannot prove that declared states are semantically coherent, all prerequisites were declared, an applicator checks before writing, or backup/recovery works. Actual application, rejection/recovery observations and operator judgment supply that evidence.

## Manifest and evidence contract

Use JSON with `schema_version: "1.0"` and `artifact_type: "local-tool-delivery"`. Paths are repository-relative unless stated otherwise. Use forward slashes, exact-byte SHA-256 digests, safe relative paths and unique inventory paths. Exclude the manifest, its evidence and authoritative history bytes from source inventory to avoid self-reference. Explicitly cover exported source plus relevant tests/dependencies; this selected inventory does not prove the absence of unrelated files elsewhere.

| Field | Required content |
| --- | --- |
| `delivery_id`, `producer` | Nonempty delivery and producer identities. |
| `disposition` | Exactly `PRE_EXISTING_DELTA_NOT_VERIFIED_BASELINE`. |
| `baseline` | `"unknown"`, or an exact-evidence object with nonempty `run_id`, `archive_sha256`, `product_contract_ref`, `product_contract_sha256`, `verification_report_ref`, and `verification_report_sha256`. The local checker checks reference shape and digest syntax; it does not qualify pipeline baseline eligibility. |
| `source` | Authoritative `root`; unique nonempty `revision_ids`; authoritative `history_path`; `files` inventory; `snapshot_sha256`. |
| `source.files` | Objects `{path, sha256}` with source-relative paths. `snapshot_sha256` binds the canonical sorted inventory using the checker's algorithm. |
| `package` | `kind: "patch"` or `"full"`, ZIP `path`, exact archive `sha256`, and `entries`. |
| `package.entries` | Objects `{path, sha256, source_path}`. `path` is ZIP-relative; `source_path` is source-relative, or `null` for packaging-only additions. |
| `checks` | A current record for every required criterion, as below. |
| `judgment` | `criterion`, `assessment: "ACCEPT"`, `subject_sha256` equal to `package.sha256`, hash-bound `evidence`, and explicit `assumptions`, `uncertainties`, `unresolved` lists. Acceptance requires an empty `unresolved` list. |

For patches also include:

| Field | Required content |
| --- | --- |
| `operations` | Objects `{path, action, payload}`. Paths are target-relative; action is `add`, `replace` or `remove`; payload names a ZIP member for add/replace and is `null` for remove. |
| `supported_states` | Objects `{id, files}` declaring coherent bases. Every state covers the same complete set of operation and prerequisite paths. Each inventory contains `{path, sha256}` for target-relative paths; `null` records required absence. |

Each `checks` item contains `criterion_id`, nonempty `method` and `method_version`, `status`, `subject_sha256`, and `evidence: {path, sha256}`. Status is `PASS`, `FAIL`, `BLOCKED`, or `NOT_RUN`; completed record checking requires all required criteria to pass.

| Applies to | Required IDs | Subject identity |
| --- | --- | --- |
| Every package | `source-focused`, `source-suite` | `source.snapshot_sha256` |
| Every package | `package-load` | `package.sha256` |
| Patch additionally | `patch-preflight`, `patch-rejection`, `patch-reapply`, `patch-recovery` | `package.sha256` |

Each check's hash-bound evidence is JSON repeating `status` and `subject_sha256`, with nonempty `observed` actual results or resolvable evidence references. Preserve commands, environment, target identities and outputs so a reader can assess what ran. Judgment JSON evidence repeats criterion, assessment, subject hash, assumptions, uncertainties and unresolved items. `REVIEW` or `REJECT` judgments may remain as incomplete/failed evidence but cannot support an accepted record.

Reuse a retained report across criteria when it has the same subject identity and contains each criterion's actual outcomes. A separate evidence file per criterion is unnecessary; source checks may share one report and package checks/judgment may share another if all required information is present.

For inventory hashing, import `snapshot_sha256` from `pipeline_control.local_delivery` when assembling the record. It hashes UTF-8 JSON of `sorted(files, key=lambda item: item["path"])` with `sort_keys=True`, `separators=(",", ":")`, and `ensure_ascii=False`. Archive and evidence hashes remain hashes of their exact file bytes.

The operator must judge whether methods address the criteria and observations support acceptance. The checker verifies identities, required records, archive/source correspondence and optional target preflight; it does not independently rerun commands or issue product acceptance.

## Check commands

Run from `tools/intent-tool-pipeline/` using the repository virtual environment. The repository root is explicit; record/source/output paths are relative to it. `--target` identifies an installation root for read-only patch preflight.

```powershell
../../.venv/Scripts/python.exe minor_delivery.py --repository-root ../.. check `
  --record "deliverables/<delivery-id>/local-delivery.json" --check-source

../../.venv/Scripts/python.exe minor_delivery.py --repository-root ../.. check `
  --record "deliverables/<delivery-id>/local-delivery.json" --target "<installation-root>"
```

`--check-source` compares declared inventory to current authoritative files. Omit it when checking immutable historical delivery bytes after source legitimately advances. Historical checks still verify package and retained evidence. A successful `--target` check writes no installation files or backup.

## History and next B intake

Append authoritative tool history, including package-only deliveries. Discovery reads `REVISION_HISTORY.md`, `CHANGELOG.md`, and `README.md` at the source root; use the owning tool's authoritative file or labeled README section among these, and preserve its existing history conventions. Retain date/revision, scope, compatibility, checks and limitations, plus `Disposition: PRE_EXISTING_DELTA_NOT_VERIFIED_BASELINE` and this exact link syntax:

```text
Local delivery record: `deliverables/<delivery-id>/local-delivery.json`
```

Before B initialization, collect marked history and validate every linked record. Intake writes a new receipt without changing source or prior records:

```powershell
../../.venv/Scripts/python.exe minor_delivery.py --repository-root ../.. intake `
  --source "<repository-relative-authoritative-tool>" `
  --output "<repository-relative-new-receipt.json>"
```

Retain exact discovered record content hashes in the build request's existing hash-bound `source_context`; preserve history and relevant delivery evidence as intake/feedback context. For source outside the pipeline project, provide an exact-byte record snapshot inside the project through an existing permitted `source_context` type/authority, with `content_sha256` matching the original JSON. This snapshot is intake evidence, not a competing source tree. The initializer discovers the external authoritative `source.root` through the supplied record and collects its linked history; it does not expand B target or baseline eligibility. It validates discovered records and stores a receipt in the new run without changing governed artifact schemas.

The receipt uses `schema_version: "1.0"`, `artifact_type: "minor-delivery-intake"`, `method_version`, `source_roots`, hash-bound `history` entries, verified `records`, and `status: "PASS"`. A receipt records deterministic intake checks; it grants no baseline or release authority.

Compare current source with the exact eligible baseline archive and carry accumulated minor behavior into cumulative delta, impact map and complete current contract. The combined candidate still requires tests, packaging, inspection and independent verification. Missing linked records, drifted package/evidence identities or absent intake bindings stop initialization; do not remove links to evade checks. If the exact pipeline baseline is unknown or ineligible, follow `FRESH_REQUIRED`; local archives, receipts or accepted judgments cannot substitute for it.
