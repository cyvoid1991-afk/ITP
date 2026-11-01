"""Exact semantic submission assignments and their consumed local identities."""

from __future__ import annotations

import hashlib
import os
import stat
from pathlib import Path
from typing import Any, Iterable

from .io_utils import InputError, normalize_repository_reference, read_structured, repository_relative, sha256_file
from .validation import semantic_artifact_owner


SUBMISSION_FILES = {
    "problem_frame": "brief.md",
    "product_contract": "contract.yaml",
    "verification_report": "report.md",
}


def submission_audit_id(role: str, invocation_ref: str) -> str:
    return hashlib.sha256(f"{role}\0{invocation_ref}".encode()).hexdigest()[:24]


def _reparse(metadata: os.stat_result) -> bool:
    return bool(getattr(metadata, "st_file_attributes", 0) & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0))


def assert_plain_path(root: Path, path: Path, *, require_file: bool = False) -> None:
    """Reject aliases without resolving away the lexical identity being checked."""
    root = Path(os.path.abspath(root))
    path = Path(os.path.abspath(path))
    try:
        parts = path.relative_to(root).parts
    except ValueError as exc:
        raise InputError("submission/input path escapes project root") from exc
    current = root
    for index, part in enumerate(parts):
        # Windows case aliases, short names, streams and trailing-dot spellings
        # are not alternate identities for the assigned exact pathname.
        if ":" in part or part.endswith((".", " ")):
            raise InputError("submission/input path uses an alternate spelling")
        if current.is_dir():
            names = {entry.name for entry in os.scandir(current)}
            if part not in names and os.path.lexists(current / part):
                raise InputError("submission/input path uses an alternate spelling")
        current = current / part
        if not os.path.lexists(current):
            continue
        metadata = current.lstat()
        if current.is_symlink() or _reparse(metadata):
            raise InputError("submission/input path must not traverse a symlink or reparse point")
        if stat.S_ISREG(metadata.st_mode) and metadata.st_nlink != 1:
            raise InputError("submission/input path must not be a hard-link alias")
        if index < len(parts) - 1 and not stat.S_ISDIR(metadata.st_mode):
            raise InputError("submission/input ancestor must be a directory")
    if require_file and (not path.is_file() or not stat.S_ISREG(path.lstat().st_mode)):
        raise InputError("submission/input must be a regular file")


def preflight_submission_path(project_root: Path, run_dir: Path, relative: str) -> Path:
    path = Path(os.path.abspath(run_dir / relative))
    assert_plain_path(project_root, path)
    if len(str(path.parent)) >= 180:
        raise InputError("submission absolute parent must be shorter than 180 characters; choose a shorter project ID/run directory (metadata --run-id does not shorten it)")
    if any(len(part) > 32 for part in path.parent.parts[1:]) or len(path.name) > 64:
        raise InputError("submission path exceeds directory (32) or filename (64) budget")
    if os.path.lexists(path):
        raise InputError("assigned submission path already exists")
    return path


def _run_input(project_root: Path, run_dir: Path, raw: str) -> Path:
    normalized = normalize_repository_reference(raw)
    # Active semantic references support their existing run-relative form and
    # project-relative form. Reject ambiguous files rather than choosing one.
    candidates = [project_root / normalized, run_dir / normalized]
    existing = [path for path in candidates if path.is_file()]
    if len(existing) > 1 and existing[0].absolute() != existing[1].absolute():
        raise InputError(f"ambiguous run input reference: {raw}")
    if existing:
        return existing[0]
    # A declared project-relative missing file still keeps its own identity.
    if candidates[0].absolute().is_relative_to(run_dir.absolute()):
        return candidates[0]
    return candidates[1]


def current_round_number(state: dict[str, Any]) -> int | None:
    rounds = state.get("repair", {}).get("rounds", [])
    active = [record for record in rounds if isinstance(record, dict) and record.get("status") == "IN_PROGRESS"]
    if len(active) > 1:
        raise InputError("multiple in-progress rounds cannot bind an assignment")
    return active[0].get("number") if active else None


def _require_subject_modification_round(state: dict[str, Any], artifact_key: str) -> None:
    """Initial owner iteration is free; post-verification subject changes are not."""
    if (
        artifact_key in {"problem_frame", "product_contract"}
        and state.get("control", {}).get("latest_verification_result") is not None
        and current_round_number(state) is None
    ):
        raise InputError("post-verification brief/contract modification requires a reserved IN_PROGRESS round")


def collect_submission_inputs(
    project_root: Path, run_dir: Path, state: dict[str, Any], artifact_key: str,
    input_refs: Iterable[str | Path] = (),
) -> list[dict[str, Any]]:
    """Collect current supplied evidence, never the previous PASS candidate."""
    records: dict[str, dict[str, Any]] = {}
    active = state.get("active_artifacts", {})

    def add(path: Path, *, entry: dict[str, Any] | None = None, missing_ok: bool = False) -> None:
        assert_plain_path(project_root, path)
        reference = repository_relative(project_root, path)
        if not path.is_file():
            if os.path.lexists(path):
                raise InputError(f"submission input must be a regular file: {reference}")
            if not missing_ok:
                raise InputError(f"mandatory submission input is missing or unusable: {reference}")
            record: dict[str, Any] = {"path": reference, "availability": "MISSING"}
        else:
            record = {"path": reference, "availability": "PRESENT", "content_sha256": sha256_file(path)}
        if entry is not None:
            if record.get("content_sha256") != entry.get("content_sha256"):
                raise InputError(f"active submission input hash does not match its file: {reference}")
            record.update(artifact_id=entry.get("artifact_id"), version=entry.get("version"))
        prior = records.get(reference)
        if prior is not None and "artifact_id" in prior and entry is None:
            return
        records[reference] = record

    def add_active(key: str) -> Path:
        entry = active.get(key)
        if not isinstance(entry, dict) or not isinstance(entry.get("path"), str):
            raise InputError(f"submission requires the active {key}")
        path = _run_input(project_root, run_dir, entry["path"])
        add(path, entry=entry)
        return path

    request_path = add_active("build_request")
    request = read_structured(request_path)
    if not isinstance(request, dict):
        raise InputError("active submission request must be an object")
    for context in request.get("source_context", []):
        if not isinstance(context, dict):
            continue
        raw = context.get("path")
        if raw is None and "content_sha256" not in context:
            continue
        if not isinstance(raw, str) or not raw.strip():
            raise InputError("locally bound source context must declare a path")
        if "://" in raw and "content_sha256" not in context:
            continue
        path = project_root / normalize_repository_reference(raw)
        if context.get("type") == "REPOSITORY" and "content_sha256" not in context and path.is_dir():
            continue
        add(path)
        if "content_sha256" in context and records[repository_relative(project_root, path)].get("content_sha256") != context["content_sha256"]:
            raise InputError("locally bound source context changed")
    handoff = request.get("handoff")
    direct = isinstance(handoff, dict) and handoff.get("next_stage") == "contract"
    if artifact_key != "problem_frame" and not direct:
        add_active("problem_frame")
    if artifact_key == "verification_report":
        add_active("product_contract")
        inspection_path = run_dir / "50_release/package_inspection.json"
        fixed_manifest_path = run_dir / "50_release/release_manifest.json"
        add(inspection_path, missing_ok=True)
        add(fixed_manifest_path, missing_ok=True)
        archive_path: Path | None = None

        def supplied_data(path: Path) -> dict[str, Any]:
            if not path.is_file():
                return {}
            try:
                data = read_structured(path)
            except InputError:
                # Unusable regular evidence retains its attributable bytes.
                return {}
            return data if isinstance(data, dict) else {}

        inspection = supplied_data(inspection_path)
        raw_manifest = inspection.get("manifest_path")
        manifest_path = _run_input(project_root, run_dir, raw_manifest) if isinstance(raw_manifest, str) else fixed_manifest_path
        add(manifest_path, missing_ok=True)
        # Parse the manifest actually supplied by this inspection. The fixed
        # interface remains captured, but cannot substitute an older archive.
        for data in (inspection, supplied_data(manifest_path)):
            if isinstance(data.get("archive_path"), str):
                archive_path = project_root / normalize_repository_reference(data["archive_path"])
                add(archive_path, missing_ok=True)
        # The authoritative request supplies the expected archive even when no
        # manifest or inspection was produced.
        if archive_path is None:
            target = request.get("target")
            raw = target.get("output_path") if isinstance(target, dict) else None
            if isinstance(raw, str):
                add(project_root / normalize_repository_reference(raw), missing_ok=True)
        latest_path = run_dir / "40_verification/harness/latest.json"
        add(latest_path, missing_ok=True)
        if latest_path.is_file():
            try:
                latest = read_structured(latest_path)
            except InputError:
                latest = {}
            if isinstance(latest, dict):
                raw = latest.get("attempt_path")
                if isinstance(raw, str):
                    add(project_root / normalize_repository_reference(raw) / "summary.json", missing_ok=True)
                raw = latest.get("cleanup_path")
                if isinstance(raw, str):
                    add(project_root / normalize_repository_reference(raw), missing_ok=True)
                elif isinstance(latest.get("attempt_id"), str):
                    identifier = latest["attempt_id"]
                    if "/" in identifier or "\\" in identifier or identifier in {".", ".."}:
                        raise InputError("harness attempt ID is not a path segment")
                    add(run_dir / "40_verification/harness/cleanup" / f"{identifier}.json", missing_ok=True)
    for raw in input_refs:
        path = Path(raw)
        if not path.is_absolute():
            path = project_root / normalize_repository_reference(raw)
        add(path)
    return [records[key] for key in sorted(records)]


def create_submission_assignment(
    project_root: Path, run_dir: Path, state: dict[str, Any], *, role: str,
    invocation_ref: str, artifact_key: str, input_refs: Iterable[str | Path] = (),
) -> dict[str, Any]:
    if artifact_key not in SUBMISSION_FILES:
        raise InputError(f"artifact must be one of {sorted(SUBMISSION_FILES)}")
    if semantic_artifact_owner(state, artifact_key) != role:
        raise InputError("artifact semantic owner does not match the selected role")
    _require_subject_modification_round(state, artifact_key)
    active = state.get("active_artifacts", {}).get(artifact_key)
    version = active.get("version", 0) + 1 if isinstance(active, dict) else 1
    relative = f"30_execution/sub/{submission_audit_id(role, invocation_ref)}/{SUBMISSION_FILES[artifact_key]}"
    preflight_submission_path(project_root, run_dir, relative)
    return {
        "artifact_key": artifact_key, "artifact_id": artifact_key.replace("_", "-"),
        "artifact_version": version, "path": relative,
        "inputs": collect_submission_inputs(project_root, run_dir, state, artifact_key, input_refs),
        "round_number": current_round_number(state),
    }


def validate_submission_assignment(
    project_root: Path, run_dir: Path, state: dict[str, Any], *, role: str,
    invocation_ref: str, baseline_sha256: str, artifact_key: str, source_path: Path,
    artifact_version: int | None = None, check_live_inputs: bool = True, require_result: bool = True,
) -> dict[str, Any]:
    audit_id = submission_audit_id(role, invocation_ref)
    baseline_path = run_dir / "30_execution/role_boundary/baselines" / f"{audit_id}.json"
    if sha256_file(baseline_path) != baseline_sha256:
        raise InputError("submission baseline SHA-256 mismatch")
    baseline = read_structured(baseline_path)
    if not isinstance(baseline, dict) or any(baseline.get(key) != value for key, value in {
        "control_revision": state.get("control", {}).get("semantic_role_boundary"), "role": role, "invocation_ref": invocation_ref,
        "audit_id": audit_id, "run_dir": repository_relative(project_root, run_dir),
    }.items()):
        raise InputError("submission baseline run/role/invocation/control binding mismatch")
    submission = baseline.get("submission")
    expected_relative = f"30_execution/sub/{audit_id}/{SUBMISSION_FILES.get(artifact_key, '')}"
    if not isinstance(submission, dict) or any(submission.get(key) != value for key, value in {
        "artifact_key": artifact_key, "artifact_id": artifact_key.replace("_", "-"), "path": expected_relative,
    }.items()):
        raise InputError("submission artifact assignment mismatch")
    assigned = run_dir / expected_relative
    raw_source = source_path if source_path.is_absolute() else project_root / source_path
    # Compare strings before resolving: alternate lexical aliases cannot gain
    # admission by resolving to the assigned file.
    if str(raw_source.absolute()) != str(assigned.absolute()) or ".." in raw_source.parts:
        raise InputError("source must equal the exact assigned submission path")
    assert_plain_path(project_root, assigned, require_file=require_result)
    if assigned.exists() and not assigned.is_file():
        raise InputError("assigned submission must be a regular file")
    if artifact_version is not None and submission.get("artifact_version") != artifact_version:
        raise InputError("submission artifact version differs from assignment")
    if baseline.get("control_revision") not in {"1.1", "1.2"}:
        raise InputError("submission baseline requires selected boundary control")
    if baseline.get("control_revision") == "1.2":
        from .procedures import _original_state, result_binding, validate_procedure_binding, validate_result_binding

        validate_procedure_binding(project_root, run_dir, _original_state(baseline), baseline, current=check_live_inputs)
        from .boundary import BoundaryPolicy

        policy = BoundaryPolicy(allowed_durable_files=(expected_relative,),
            allowed_ephemeral_roots=(f"40_verification/probes/{audit_id}",) if role == "independent_verifier" else ())
        if baseline.get("path_policy") != policy.as_dict() or "round_review" in baseline:
            raise InputError("procedure submission boundary differs from its exact assigned output")
        if require_result:
            validate_result_binding(assigned.read_bytes(), assigned, result_binding(baseline, baseline_sha256))
    if check_live_inputs:
        _require_subject_modification_round(state, artifact_key)
        if semantic_artifact_owner(state, artifact_key) != role:
            raise InputError("submission semantic owner changed")
        entry = state.get("active_artifacts", {}).get(artifact_key)
        next_version = entry.get("version", 0) + 1 if isinstance(entry, dict) else 1
        if submission.get("artifact_version") != next_version or submission.get("round_number") != current_round_number(state):
            raise InputError("submission version/round assignment is stale")
        inputs = submission.get("inputs")
        if not isinstance(inputs, list):
            raise InputError("submission input assignment must be a list")
        for record in inputs:
            if not isinstance(record, dict) or not isinstance(record.get("path"), str):
                raise InputError("submission input identity is malformed")
            path = project_root / normalize_repository_reference(record["path"])
            assert_plain_path(project_root, path)
            if record.get("availability") == "MISSING":
                if os.path.lexists(path) or "content_sha256" in record:
                    raise InputError("missing submission input appeared or has an invalid digest")
            elif record.get("availability") != "PRESENT" or not path.is_file() or sha256_file(path) != record.get("content_sha256"):
                raise InputError("submission input disappeared or changed")
            if "artifact_id" in record:
                entries = [value for value in state.get("active_artifacts", {}).values()
                           if isinstance(value, dict) and value.get("artifact_id") == record["artifact_id"]]
                if len(entries) != 1 or any(entries[0].get(key) != record.get(key) for key in ("version", "content_sha256")):
                    raise InputError("submission active input version/hash changed")
        # Compare mandatory identities afresh; this also detects newly bound
        # sources and newly supplied candidate/harness references.
        current = collect_submission_inputs(project_root, run_dir, state, artifact_key)
        recorded = {record["path"]: record for record in inputs}
        if any(recorded.get(record["path"]) != record for record in current):
            raise InputError("mandatory submission inputs changed")
    return baseline
