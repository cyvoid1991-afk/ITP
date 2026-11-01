"""Verified-baseline resolution and revision-contract reconciliation."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .evidence import passing_package_inspection
from .io_utils import InputError, normalize_repository_reference, read_structured, repository_relative, resolve_within, sha256_file
from .result import CommandResult, Diagnostic


BASELINE_FIELDS = (
    "run_id",
    "archive_sha256",
    "product_contract_ref",
    "product_contract_sha256",
    "verification_report_ref",
    "verification_report_sha256",
)


def _fresh(result: CommandResult, path: str, message: str) -> None:
    result.add("FRESH_REQUIRED", path, message)


def _artifact_ref(entry: dict[str, Any]) -> str:
    return f"{entry.get('artifact_id')}@{entry.get('version')}"


def _resolve_active_path(project_root: Path, run_dir: Path, entry: dict[str, Any]) -> Path:
    raw = entry.get("path")
    if not isinstance(raw, str):
        raise InputError("active artifact path is missing")
    normalized = normalize_repository_reference(raw)
    candidate = resolve_within(project_root, normalized)
    if not candidate.is_file():
        candidate = (run_dir / normalized).resolve(strict=False)
    try:
        candidate.relative_to(run_dir.resolve())
    except ValueError as exc:
        raise InputError("active semantic artifact must remain inside its run") from exc
    if not candidate.is_file():
        raise InputError(f"active artifact does not exist: {raw}")
    return candidate


def _resolve_bound_path(
    project_root: Path,
    run_dir: Path,
    raw: Any,
    *,
    run_bound: bool,
) -> Path:
    if not isinstance(raw, str) or not raw.strip():
        raise InputError("captured path must be a non-empty string")
    normalized = normalize_repository_reference(raw)
    if not run_bound:
        candidate = resolve_within(project_root, normalized, must_exist=True)
        if not candidate.is_file():
            raise InputError(f"captured path is not a file: {raw}")
        return candidate
    candidates = {
        candidate.resolve()
        for candidate in (project_root / normalized, run_dir / normalized)
        if candidate.is_file()
    }
    contained = [candidate for candidate in candidates if candidate.is_relative_to(run_dir.resolve())]
    if len(contained) != 1:
        raise InputError("captured run path must resolve unambiguously inside the baseline run")
    return contained[0]


def _find_baseline_run(project_root: Path, run_id: str) -> Path:
    runs_root = resolve_within(project_root, "workspace/build_runs")
    if not runs_root.is_dir():
        raise InputError("workspace/build_runs does not exist")
    matches: list[Path] = []
    for candidate in sorted(runs_root.iterdir(), key=lambda item: item.name):
        state_path = candidate / "30_execution" / "run_state.json"
        if not candidate.is_dir() or not state_path.is_file():
            continue
        try:
            state = read_structured(state_path)
        except InputError:
            continue
        if isinstance(state, dict) and isinstance(state.get("run"), dict) and state["run"].get("run_id") == run_id:
            matches.append(candidate)
    if len(matches) != 1:
        raise InputError(f"baseline run_id must resolve to exactly one run; found {len(matches)}")
    return matches[0]


def _stage_passed(state: dict[str, Any], stage_id: str) -> bool:
    stages = {item.get("id"): item for item in state.get("stages", []) if isinstance(item, dict)}
    gates = {item.get("id"): item for item in state.get("gates", []) if isinstance(item, dict)}
    stage = stages.get(stage_id)
    if not isinstance(stage, dict) or stage.get("status") != "PASSED":
        return False
    gate = gates.get(stage.get("gate_id"))
    return isinstance(gate, dict) and gate.get("status") == "PASSED"


def _candidate_binding_matches_files(
    project_root: Path,
    run_dir: Path,
    binding: dict[str, Any],
    result: CommandResult,
) -> dict[str, Path] | None:
    paths: dict[str, Path] = {}
    for name in ("product_contract", "manifest", "inspection", "archive"):
        raw = binding.get(f"{name}_path")
        if not isinstance(raw, str) or not raw.strip():
            _fresh(result, f"baseline.control.candidate_binding.{name}_path", "captured path must be non-empty")
            continue
        try:
            paths[name] = _resolve_bound_path(
                project_root,
                run_dir,
                raw,
                run_bound=name != "archive",
            )
        except InputError as exc:
            _fresh(result, f"baseline.control.candidate_binding.{name}_path", str(exc))
    if not result.ok:
        return None
    for name, path in paths.items():
        expected = binding.get(f"{name}_sha256")
        try:
            actual = sha256_file(path) if path.is_file() else None
        except OSError as exc:
            _fresh(result, f"baseline.control.candidate_binding.{name}_sha256", str(exc))
            continue
        if not isinstance(expected, str) or actual != expected:
            _fresh(result, f"baseline.control.candidate_binding.{name}_sha256", f"{name} bytes do not match the captured verified-candidate identity")
    return paths if result.ok else None


def resolve_revision_baseline(
    project_root: Path,
    request: dict[str, Any],
    *,
    _lineage_guard: frozenset[Path] | None = None,
) -> CommandResult:
    """Resolve one exact completed verified release without importing its lineage."""

    result = CommandResult(command="resolve-revision-baseline")
    project = request.get("project")
    if not isinstance(project, dict) or project.get("request_kind") != "REVISION":
        result.add("REQUEST_KIND", "$.project.request_kind", "revision baseline resolution requires request_kind REVISION")
        return result
    revision_of = request.get("revision_of")
    if not isinstance(revision_of, dict):
        _fresh(result, "$.revision_of", "a REVISION request requires an exact verified baseline")
        return result
    run_id = revision_of.get("run_id")
    if not isinstance(run_id, str) or not run_id.strip():
        _fresh(result, "$.revision_of.run_id", "baseline run_id must be non-empty")
        return result
    try:
        baseline_dir = _find_baseline_run(project_root, run_id)
        baseline_key = baseline_dir.resolve()
        if baseline_key in (_lineage_guard or frozenset()):
            raise InputError("revision baseline lineage contains a cycle")
        state = read_structured(baseline_dir / "30_execution" / "run_state.json")
        baseline_request = read_structured(baseline_dir / "00_intake" / "build_request.yaml")
    except (InputError, OSError) as exc:
        _fresh(result, "$.revision_of.run_id", str(exc))
        return result
    if not isinstance(state, dict) or not isinstance(baseline_request, dict):
        _fresh(result, "$.revision_of", "baseline state and build request must be mappings")
        return result
    # Import lazily because validation.py invokes this module for revision runs.
    from .validation import (
        is_controlled_run_state,
        parse_verification_results,
        validate_build_request_data,
        validate_product_contract_data,
        validate_run_directory,
    )

    full_validation = validate_run_directory(
        project_root,
        baseline_dir,
        _revision_guard=(_lineage_guard or frozenset()) | {baseline_key},
    )
    if not full_validation.ok:
        summary = "; ".join(
            f"{item.code} at {item.path}: {item.message}"
            for item in full_validation.diagnostics[:3]
        )
        _fresh(result, "$.revision_of.run_id", f"baseline run is not a valid completed release: {summary}")
    if not _stage_passed(state, "release") or not _stage_passed(state, "verification"):
        _fresh(result, "$.revision_of.run_id", "baseline release and verification gates must both be PASSED")

    requested_target = request.get("target")
    baseline_target = baseline_request.get("target")
    try:
        requested_repository = normalize_repository_reference(requested_target.get("repository_path")) if isinstance(requested_target, dict) else ""
        baseline_repository = normalize_repository_reference(baseline_target.get("repository_path")) if isinstance(baseline_target, dict) else ""
    except (InputError, TypeError) as exc:
        _fresh(result, "$.target.repository_path", str(exc))
        requested_repository = baseline_repository = ""
    if requested_repository != baseline_repository:
        _fresh(result, "$.target.repository_path", "revision target must equal the verified baseline repository path")

    active = state.get("active_artifacts")
    contract_entry = active.get("product_contract") if isinstance(active, dict) else None
    report_entry = active.get("verification_report") if isinstance(active, dict) else None
    if not isinstance(contract_entry, dict) or not isinstance(report_entry, dict):
        _fresh(result, "baseline.active_artifacts", "baseline must have active contract and verification report identities")
        return result
    try:
        contract_path = _resolve_active_path(project_root, baseline_dir, contract_entry)
        report_path = _resolve_active_path(project_root, baseline_dir, report_entry)
        contract = read_structured(contract_path)
        report_text = report_path.read_text(encoding="utf-8")
    except (InputError, OSError, UnicodeError) as exc:
        _fresh(result, "baseline.active_artifacts", str(exc))
        return result

    if validate_build_request_data(baseline_request):
        _fresh(result, "baseline.build_request", "baseline build request is not structurally valid")
    from .workflow import validate_run_state_context

    if validate_run_state_context(project_root, baseline_dir, state) or not is_controlled_run_state(state):
        _fresh(result, "baseline.run_state", "baseline run state is not valid controlled provenance")
    contract_diagnostics = validate_product_contract_data(contract)
    if contract_diagnostics:
        _fresh(result, "baseline.product_contract", "baseline product contract is not structurally valid")
    overall, requirement_results, report_diagnostics = parse_verification_results(report_text)
    contract_items = contract.get("requirements", []) if isinstance(contract, dict) else []
    contract_ids = {
        item.get("id") for item in contract_items
        if isinstance(item, dict) and isinstance(item.get("id"), str)
    }
    if report_diagnostics or overall != "READY" or set(requirement_results) != contract_ids or any(value != "PASS" for value in requirement_results.values()):
        _fresh(result, "baseline.verification_report", "baseline report must be READY and cover every requirement with PASS")

    try:
        contract_hash = sha256_file(contract_path)
        report_hash = sha256_file(report_path)
    except OSError as exc:
        _fresh(result, "baseline.active_artifacts", str(exc))
        return result
    if contract_entry.get("content_sha256") != contract_hash:
        _fresh(result, "baseline.active_artifacts.product_contract.content_sha256", "active contract hash does not match its bytes")
    if report_entry.get("content_sha256") != report_hash:
        _fresh(result, "baseline.active_artifacts.verification_report.content_sha256", "active report hash does not match its bytes")
    expected_pairs = {
        "product_contract_ref": _artifact_ref(contract_entry),
        "product_contract_sha256": contract_hash,
        "verification_report_ref": _artifact_ref(report_entry),
        "verification_report_sha256": report_hash,
    }
    for field, actual in expected_pairs.items():
        if revision_of.get(field) != actual:
            _fresh(result, f"$.revision_of.{field}", "request does not match the baseline active artifact identity")

    control = state.get("control")
    identity = control.get("verification_validation_identity") if isinstance(control, dict) else None
    binding = identity.get("candidate_binding") if isinstance(identity, dict) else None
    if not isinstance(identity, dict) or not isinstance(binding, dict):
        _fresh(result, "baseline.control.verification_validation_identity", "baseline lacks a fully captured verified-candidate binding")
        return result
    for field in ("artifact_id", "version", "path", "content_sha256"):
        if identity.get(field) != report_entry.get(field):
            _fresh(result, f"baseline.control.verification_validation_identity.{field}", "captured report identity no longer matches the active report")
    if binding.get("product_contract_ref") != _artifact_ref(contract_entry) or binding.get("product_contract_sha256") != contract_hash:
        _fresh(result, "baseline.control.candidate_binding.product_contract_sha256", "captured contract identity no longer matches the active contract")
    paths = _candidate_binding_matches_files(project_root, baseline_dir, binding, result)
    if paths is not None:
        if paths["product_contract"] != contract_path.resolve():
            _fresh(result, "baseline.control.candidate_binding.product_contract_path", "captured contract path does not identify the active contract")
        try:
            inspection_ok, inspection_message, inspection = passing_package_inspection(project_root, paths["inspection"])
        except OSError as exc:
            _fresh(result, "baseline.package_inspection", str(exc))
            inspection_ok, inspection_message, inspection = False, str(exc), None
        if not inspection_ok:
            if not any(item.path == "baseline.package_inspection" and item.message == inspection_message for item in result.diagnostics):
                _fresh(result, "baseline.package_inspection", inspection_message)
        elif isinstance(inspection, dict):
            try:
                inspection_manifest = _resolve_bound_path(
                    project_root, baseline_dir, inspection.get("manifest_path"), run_bound=True
                )
                inspection_archive = _resolve_bound_path(
                    project_root, baseline_dir, inspection.get("archive_path"), run_bound=False
                )
            except InputError as exc:
                _fresh(result, "baseline.package_inspection", str(exc))
            else:
                if inspection_manifest != paths["manifest"] or inspection_archive != paths["archive"]:
                    _fresh(result, "baseline.package_inspection", "inspection does not identify the captured manifest and archive")
        else:
            _fresh(result, "baseline.package_inspection", "inspection must be a mapping")
    if revision_of.get("archive_sha256") != binding.get("archive_sha256"):
        _fresh(result, "$.revision_of.archive_sha256", "request archive SHA-256 does not match the verified candidate")
    if not result.ok:
        return result

    result.data = {
        "mode": "VERIFIED_DELTA_SOURCE",
        "run_id": run_id,
        "run_dir": repository_relative(project_root, baseline_dir),
        "target_repository_path": requested_repository,
        "archive_path": binding["archive_path"],
        "archive_sha256": binding["archive_sha256"],
        "product_contract_ref": _artifact_ref(contract_entry),
        "product_contract_path": repository_relative(project_root, contract_path),
        "product_contract_sha256": contract_hash,
        "verification_report_ref": _artifact_ref(report_entry),
        "verification_report_path": repository_relative(project_root, report_path),
        "verification_report_sha256": report_hash,
        "manifest_path": binding["manifest_path"],
        "manifest_sha256": binding["manifest_sha256"],
        "inspection_path": binding["inspection_path"],
        "inspection_sha256": binding["inspection_sha256"],
    }
    return result


def requirement_bundle_sha256(contract: dict[str, Any], requirement_id: str) -> str:
    """Hash one full requirement and all acceptance records linked to it."""

    requirement = next(
        (item for item in contract.get("requirements", []) if isinstance(item, dict) and item.get("id") == requirement_id),
        None,
    )
    if requirement is None:
        raise InputError(f"unknown requirement: {requirement_id}")
    linked_ids = requirement.get("acceptance_refs", [])
    acceptance = sorted(
        (
            item for item in contract.get("acceptance_methods", [])
            if isinstance(item, dict) and item.get("id") in linked_ids
        ),
        key=lambda item: str(item.get("id")),
    )
    payload = json.dumps(
        {"requirement": requirement, "acceptance_methods": acceptance},
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def validate_revision_contract(
    project_root: Path,
    build_request: dict[str, Any],
    state: dict[str, Any],
    current_contract: dict[str, Any] | None,
    *,
    _lineage_guard: frozenset[Path] | None = None,
) -> list[Diagnostic]:
    """Re-resolve baseline drift and validate a complete delta impact map."""

    diagnostics: list[Diagnostic] = []
    kind = build_request.get("project", {}).get("request_kind") if isinstance(build_request.get("project"), dict) else None
    control = state.get("control")
    recorded = control.get("revision_baseline") if isinstance(control, dict) else None
    if kind != "REVISION":
        if recorded is not None:
            diagnostics.append(Diagnostic("REVISION_MODE", "$.control.revision_baseline", "non-REVISION runs must not retain a revision baseline"))
        if isinstance(current_contract, dict) and current_contract.get("revision_control") is not None:
            diagnostics.append(Diagnostic("REVISION_MODE", "$.revision_control", "non-REVISION contracts must not declare revision_control"))
        return diagnostics

    resolved = resolve_revision_baseline(
        project_root,
        build_request,
        _lineage_guard=_lineage_guard,
    )
    if not resolved.ok:
        return list(resolved.diagnostics)
    if not isinstance(recorded, dict):
        return [Diagnostic("REVISION_BASELINE", "$.control.revision_baseline", "REVISION run state must record its exact baseline")]
    for field, value in resolved.data.items():
        if field != "resolved_at" and recorded.get(field) != value:
            diagnostics.append(Diagnostic("REVISION_BASELINE_DRIFT", f"$.control.revision_baseline.{field}", "recorded baseline no longer matches the resolved verified candidate"))
    if current_contract is None:
        return diagnostics
    revision_control = current_contract.get("revision_control")
    if not isinstance(revision_control, dict):
        diagnostics.append(Diagnostic("REVISION_CONTROL_REQUIRED", "$.revision_control", "a revision contract must contain a complete revision_control map"))
        return diagnostics
    baseline_meta = revision_control.get("baseline")
    if isinstance(baseline_meta, dict):
        for field in BASELINE_FIELDS:
            if baseline_meta.get(field) != build_request.get("revision_of", {}).get(field):
                diagnostics.append(Diagnostic("REVISION_BASELINE_DRIFT", f"$.revision_control.baseline.{field}", "contract baseline must equal the active revision request"))

    try:
        baseline_contract = read_structured(resolve_within(project_root, resolved.data["product_contract_path"], must_exist=True))
    except InputError as exc:
        return diagnostics + [Diagnostic("FRESH_REQUIRED", "$.revision_control.baseline", str(exc))]
    if not isinstance(baseline_contract, dict):
        return diagnostics + [Diagnostic("FRESH_REQUIRED", "$.revision_control.baseline", "baseline contract must be a mapping")]

    baseline_ids = {item.get("id") for item in baseline_contract.get("requirements", []) if isinstance(item, dict) and isinstance(item.get("id"), str)}
    current_ids = {item.get("id") for item in current_contract.get("requirements", []) if isinstance(item, dict) and isinstance(item.get("id"), str)}
    missing = baseline_ids - current_ids
    if missing:
        diagnostics.append(Diagnostic("REVISION_REQUIREMENT_REMOVED", "$.requirements", f"baseline requirements may not disappear: {sorted(missing)}"))

    unchanged_records = revision_control.get("unchanged_requirements", [])
    unchanged_ids: set[str] = set()
    if isinstance(unchanged_records, list):
        for index, item in enumerate(unchanged_records):
            if not isinstance(item, dict) or not isinstance(item.get("requirement_ref"), str):
                continue
            req_id = item["requirement_ref"]
            unchanged_ids.add(req_id)
            if req_id not in baseline_ids or req_id not in current_ids:
                diagnostics.append(Diagnostic("REVISION_REQUIREMENT_REF", f"$.revision_control.unchanged_requirements[{index}].requirement_ref", "unchanged requirement must exist in baseline and current contracts"))
                continue
            expected = requirement_bundle_sha256(baseline_contract, req_id)
            current = requirement_bundle_sha256(current_contract, req_id)
            if item.get("baseline_bundle_sha256") != expected or current != expected:
                diagnostics.append(Diagnostic("REVISION_UNCHANGED_DRIFT", f"$.revision_control.unchanged_requirements[{index}]", "unchanged requirement bundle differs from its exact baseline identity"))

    impact = revision_control.get("impact_map", [])
    impacted_baseline: set[str] = set()
    impacted_current: set[str] = set()
    mapped_items: list[str] = []
    if isinstance(impact, list):
        for item in impact:
            if not isinstance(item, dict):
                continue
            ref = item.get("delta_item_ref")
            if isinstance(ref, str):
                mapped_items.append(ref)
            baseline_refs = {ref for ref in item.get("baseline_requirement_refs", []) if isinstance(ref, str)}
            current_refs = {ref for ref in item.get("current_requirement_refs", []) if isinstance(ref, str)}
            if not baseline_refs <= baseline_ids:
                diagnostics.append(Diagnostic("REVISION_REQUIREMENT_REF", "$.revision_control.impact_map.baseline_requirement_refs", "impact map contains an unknown baseline requirement"))
            if not current_refs <= current_ids:
                diagnostics.append(Diagnostic("REVISION_REQUIREMENT_REF", "$.revision_control.impact_map.current_requirement_refs", "impact map contains an unknown current requirement"))
            if item.get("disposition") == "IMPACTED":
                impacted_baseline.update(baseline_refs)
                impacted_current.update(current_refs)
            elif item.get("disposition") == "UNCHANGED" and (
                baseline_refs != current_refs or not baseline_refs <= unchanged_ids
            ):
                diagnostics.append(Diagnostic("REVISION_UNCHANGED_MAPPING", "$.revision_control.impact_map", "UNCHANGED impact entries must map identical exact-baseline requirement sets"))

    requested = build_request.get("delta_request", {})
    if not isinstance(requested, dict):
        requested = {}
    expected_items = {
        item.get("id") for key in ("requested_changes", "explicit_non_changes")
        for item in requested.get(key, [])
        if isinstance(item, dict) and isinstance(item.get("id"), str)
    }
    if set(mapped_items) != expected_items or len(mapped_items) != len(expected_items):
        diagnostics.append(Diagnostic("REVISION_IMPACT_COVERAGE", "$.revision_control.impact_map", "every DELTA/NONCHANGE item must appear exactly once"))
    if unchanged_ids & (impacted_baseline | impacted_current):
        diagnostics.append(Diagnostic("REVISION_CLASSIFICATION_OVERLAP", "$.revision_control", "unchanged and impacted requirement sets must be disjoint"))
    if unchanged_ids | impacted_baseline != baseline_ids:
        diagnostics.append(Diagnostic("REVISION_BASELINE_COVERAGE", "$.revision_control", "every baseline requirement must be classified exactly once"))
    if unchanged_ids | impacted_current != current_ids:
        diagnostics.append(Diagnostic("REVISION_CURRENT_COVERAGE", "$.revision_control", "every current requirement must be classified exactly once"))

    # A changed shared acceptance record changes every linked requirement bundle.
    for req_id in unchanged_ids & baseline_ids & current_ids:
        if requirement_bundle_sha256(baseline_contract, req_id) != requirement_bundle_sha256(current_contract, req_id):
            diagnostics.append(Diagnostic("REVISION_SHARED_ACCEPTANCE_IMPACT", f"$.revision_control.unchanged_requirements[{req_id}]", "changed linked acceptance requires every linked requirement to be impacted"))
    return diagnostics
