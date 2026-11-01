"""Selected-policy round accounting and attributable verification snapshots.

The ledger describes the existing repair counter. It never counts role calls,
failed requirements, evidence recovery, or status updates separately.
"""

from __future__ import annotations

import hashlib
import re
import zipfile
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from typing import Any

from .io_utils import InputError, normalize_repository_reference, read_structured, resolve_within, sha256_file
from .result import CommandResult, Diagnostic

TERMINAL = {"PASSED", "FAILED", "BLOCKED"}
SNAPSHOT_FIELDS = {"report_ref", "report_path", "report_sha256", "source_invocation_ref", "boundary_evidence_ref", "stage_status", "recorded_at", "candidate_binding", "harness_attempt"}
BINDING_FIELDS = {"product_contract_ref", "product_contract_path", "product_contract_sha256", "manifest_path", "manifest_sha256", "inspection_path", "inspection_sha256", "archive_path", "archive_sha256"}


def _same_subject(left: Any, right: Any) -> bool:
    if not isinstance(left, dict) or not isinstance(right, dict):
        return False
    a, b = left.get("candidate_binding", {}), right.get("candidate_binding", {})
    if not isinstance(a, dict) or not isinstance(b, dict):
        return False
    fields = ("product_contract_ref", "product_contract_sha256", "archive_path", "archive_sha256")
    return all(a.get(field) is not None and a.get(field) == b.get(field) for field in fields)


def _timestamp(value: Any) -> bool:
    try:
        return isinstance(value, str) and datetime.fromisoformat(value.replace("Z", "+00:00")).utcoffset() is not None
    except ValueError:
        return False


def _sha(value: Any) -> bool:
    return isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value) is not None


def validate_round_metadata(state: dict[str, Any]) -> list[Diagnostic]:
    """Pure shape/linkage checks; contextual audit checks are separate."""
    errors: list[Diagnostic] = []

    def error(path: str, message: str) -> None:
        errors.append(Diagnostic("ROUND_METADATA", path, message))

    repair = state.get("repair")
    if not isinstance(repair, dict):
        error("$.repair", "round policy requires repair metadata")
        return errors
    count, ceiling, records = (repair.get(key) for key in ("active_attempt", "maximum_attempts", "rounds"))
    if type(count) is not int or count < 0 or not isinstance(records, list) or count != len(records):
        error("$.repair", "active_attempt must equal the number of consecutive ledger records")
        return errors
    if type(ceiling) is not int or ceiling < 4 or count > ceiling:
        error("$.repair.maximum_attempts", "round ceiling must be at least four and cover started rounds")

    def snapshot(value: Any, path: str) -> None:
        if not isinstance(value, dict) or set(value) != SNAPSHOT_FIELDS:
            error(path, "terminal snapshot must contain the protocol's exact fields")
            return
        if not isinstance(value["report_ref"], str) or re.fullmatch(r"verification-report@[1-9]\d*", value["report_ref"]) is None:
            error(path, "report_ref must identify a positive verification report version")
        for field in ("report_path", "source_invocation_ref", "boundary_evidence_ref"):
            if not isinstance(value[field], str) or not value[field].strip():
                error(f"{path}.{field}", "must be a nonempty reference")
        if not _sha(value["report_sha256"]) or not isinstance(value["stage_status"], str) or value["stage_status"] not in TERMINAL or not _timestamp(value["recorded_at"]):
            error(path, "snapshot needs SHA-256, terminal status and timezone timestamp")
        binding = value["candidate_binding"]
        if not isinstance(binding, dict) or set(binding) != BINDING_FIELDS:
            error(f"{path}.candidate_binding", "must retain all candidate fields, explicitly null when unavailable")
        else:
            for name in ("product_contract", "manifest", "inspection", "archive"):
                raw_path, digest = binding[f"{name}_path"], binding[f"{name}_sha256"]
                if raw_path is not None and (not isinstance(raw_path, str) or not raw_path.strip()) or digest is not None and not _sha(digest):
                    error(f"{path}.candidate_binding", "candidate paths/digests must be valid or null")
                if digest is not None and raw_path is None:
                    error(f"{path}.candidate_binding", "a candidate digest must have a corresponding path")
            if not isinstance(binding["product_contract_ref"], str) or re.fullmatch(r"product-contract@[1-9]\d*", binding["product_contract_ref"]) is None or not _sha(binding["product_contract_sha256"]):
                error(f"{path}.candidate_binding", "even incomplete results require known contract identity")
            if value["stage_status"] == "PASSED" and any(item is None for item in binding.values()):
                error(path, "PASSED cannot retain incomplete candidate identity")
        harness = value["harness_attempt"]
        if harness is not None:
            if not isinstance(harness, dict) or set(harness) != {"path", "content_sha256", "cleanup_path", "cleanup_sha256"}:
                error(f"{path}.harness_attempt", "must be null or a complete attempt identity")
            elif not all(isinstance(harness[field], str) and harness[field] for field in ("path", "cleanup_path")) or not all(_sha(harness[field]) for field in ("content_sha256", "cleanup_sha256")):
                error(f"{path}.harness_attempt", "attempt and cleanup identities must be complete")

    previous_result = None
    for index, record in enumerate(records):
        path = f"$.repair.rounds[{index}]"
        if not isinstance(record, dict) or set(record) != {"number", "started_at", "request_refs", "source_verification", "status", "result_verification"}:
            error(path, "round must contain the protocol's exact fields")
            continue
        if type(record["number"]) is not int or record["number"] != index + 1 or not _timestamp(record["started_at"]):
            error(path, "rounds must be consecutive with timezone start timestamps")
        refs = record["request_refs"]
        if not isinstance(refs, list) or not refs or any(not isinstance(ref, str) or re.fullmatch(r"BB-\d{3,}", ref) is None for ref in refs) or len(set(refs)) != len(refs):
            error(f"{path}.request_refs", "round must identify distinct existing modification events")
        snapshot(record["source_verification"], f"{path}.source_verification")
        if index and record["source_verification"] != previous_result and not _same_subject(record["source_verification"], previous_result):
            error(path, "round source must equal the preceding completed result")
        if record["status"] == "IN_PROGRESS":
            if index != len(records) - 1 or record["result_verification"] is not None:
                error(path, "only the last round may be in progress, without a result")
        elif record["status"] == "COMPLETED":
            snapshot(record["result_verification"], f"{path}.result_verification")
            if isinstance(record["source_verification"], dict) and isinstance(record["result_verification"], dict) and record["source_verification"].get("report_ref") == record["result_verification"].get("report_ref"):
                error(path, "a completed round requires a fresh verifier report")
        else:
            error(path, "round status must be IN_PROGRESS or COMPLETED")
        previous_result = record["result_verification"]
    latest = state.get("control", {}).get("latest_verification_result")
    if latest is not None:
        snapshot(latest, "$.control.latest_verification_result")
    if records and isinstance(records[-1], dict):
        last = records[-1]
        expected = last.get("source_verification") if last.get("status") == "IN_PROGRESS" else last.get("result_verification")
        if latest != expected and not (last.get("status") == "COMPLETED" and _same_subject(latest, expected)):
            error("$.control.latest_verification_result", "latest result must agree with the last reserved/completed round")
        source = last.get("source_verification")
        if not isinstance(source, dict) or repair.get("last_failure_ref") != source.get("report_ref"):
            error("$.repair.last_failure_ref", "must identify the latest round's source report")
    elif repair.get("last_failure_ref") is not None or "last_failure_ref" not in repair:
        error("$.repair.last_failure_ref", "must be explicitly null before the first round")
    return errors


def _project_path(root: Path, run: Path, raw: str) -> Path:
    normalized = normalize_repository_reference(raw)
    candidate = root / normalized
    if candidate.is_relative_to(run) or candidate.exists():
        return candidate
    if Path(normalized).parts[0] in {"00_intake", "10_framing", "20_contract", "30_execution", "40_verification", "50_release"}:
        return run / normalized
    return candidate


def _receipt_baseline(root: Path, run: Path, state: dict[str, Any], report_ref: str) -> tuple[dict, dict, dict]:
    from .boundary import boundary_initial_state
    from .submissions import submission_audit_id

    receipts = state.get("control", {}).get("semantic_registrations", {})
    matches = [item for item in receipts.values() if isinstance(item, dict) and item.get("artifact_key") == "verification_report" and item.get("artifact_ref") == report_ref]
    if len(matches) != 1:
        raise InputError("terminal snapshot requires exactly one registered verifier report")
    receipt = matches[0]
    audit_id = submission_audit_id("independent_verifier", receipt["source_invocation_ref"])
    baseline_path = run / "30_execution/role_boundary/baselines" / f"{audit_id}.json"
    initial = boundary_initial_state(run, role="independent_verifier", invocation_ref=receipt["source_invocation_ref"], baseline_sha256=receipt["baseline_sha256"])
    baseline = read_structured(baseline_path)
    if baseline.get("run_dir") != run.relative_to(root).as_posix() or baseline.get("submission", {}).get("artifact_key") != "verification_report" or baseline["submission"].get("artifact_version") != int(report_ref.rsplit("@", 1)[1]):
        raise InputError("verifier baseline does not bind this run/report version")
    if receipt.get("round_number") != baseline["submission"].get("round_number"):
        raise InputError("verifier receipt and audited round assignment disagree")
    evidence = read_structured(resolve_within(root, receipt["boundary_evidence_ref"], must_exist=True))
    if evidence.get("status") != "PASS" or any(evidence.get(field) != value for field, value in {"role": "independent_verifier", "invocation_ref": receipt["source_invocation_ref"], "baseline_sha256": receipt["baseline_sha256"]}.items()):
        raise InputError("terminal report requires its matching passing role-boundary audit")
    return receipt, baseline, initial


def _inputs(baseline: dict) -> dict[str, dict]:
    inputs = baseline.get("submission", {}).get("inputs")
    if not isinstance(inputs, list) or any(not isinstance(item, dict) or not isinstance(item.get("path"), str) for item in inputs):
        raise InputError("verifier baseline inputs are malformed")
    return {item["path"]: item for item in inputs}


def capture_verification_result(root: Path, run: Path, state: dict[str, Any], status: str, timestamp: str) -> dict:
    """Capture supplied/audited identities, never post-invocation replacements."""
    report = state.get("active_artifacts", {}).get("verification_report")
    if not isinstance(report, dict):
        raise InputError("terminal verification requires the active report")
    report_ref = f"{report.get('artifact_id')}@{report.get('version')}"
    receipt, baseline, initial = _receipt_baseline(root, run, state, report_ref)
    records = state.get("repair", {}).get("rounds", [])
    expected_round = records[-1]["number"] if records and records[-1]["status"] == "IN_PROGRESS" else None
    if receipt.get("round_number") != expected_round:
        raise InputError("terminal report was not assigned to the current round/recovery invocation")
    inputs = _inputs(baseline)
    report_path = _project_path(root, run, receipt["path"])
    if sha256_file(report_path) != receipt["content_sha256"]:
        raise InputError("terminal report bytes differ from their registered identity")
    contract = initial.get("active_artifacts", {}).get("product_contract")
    if not isinstance(contract, dict):
        raise InputError("verification input requires known contract identity")
    current_contract = state.get("active_artifacts", {}).get("product_contract")
    if not isinstance(current_contract, dict) or any(current_contract.get(key) != contract.get(key) for key in ("artifact_id", "version", "content_sha256")):
        raise InputError("current contract changed after the verifier invocation")
    if sha256_file(_project_path(root, run, current_contract["path"])) != contract.get("content_sha256"):
        raise InputError("current contract bytes changed after the verifier invocation")
    binding = dict.fromkeys(BINDING_FIELDS)
    binding.update(product_contract_ref=f"{contract['artifact_id']}@{contract['version']}", product_contract_path=contract["path"], product_contract_sha256=contract["content_sha256"])

    def supplied(raw: str) -> tuple[Path, dict]:
        path = _project_path(root, run, raw)
        identity = inputs.get(path.relative_to(root).as_posix())
        if not isinstance(identity, dict):
            raise InputError(f"candidate reference was not supplied to verifier: {raw}")
        return path, identity

    def data(raw: str) -> dict:
        path, identity = supplied(raw)
        if identity.get("availability") != "PRESENT":
            return {}
        if not path.is_file() or sha256_file(path) != identity.get("content_sha256"):
            raise InputError(f"supplied verification evidence changed after invocation: {raw}")
        try:
            value = read_structured(path)
        except InputError:
            return {}
        return value if isinstance(value, dict) else {}

    contract_path, contract_input = supplied(contract["path"])
    if contract_input.get("content_sha256") != contract["content_sha256"]:
        raise InputError("audited contract input identity differs from active-at-invocation contract")
    inspection_raw = (run / "50_release/package_inspection.json").relative_to(root).as_posix()
    inspection = data(inspection_raw)
    manifest_raw = inspection.get("manifest_path", (run / "50_release/release_manifest.json").relative_to(root).as_posix())
    manifest = data(manifest_raw)
    archive_raw = inspection.get("archive_path", manifest.get("archive_path"))
    for name, raw in (("inspection", inspection_raw), ("manifest", manifest_raw), ("archive", archive_raw)):
        if isinstance(raw, str):
            _, identity = supplied(raw)
            binding[f"{name}_path"] = raw
            binding[f"{name}_sha256"] = identity.get("content_sha256") if identity.get("availability") == "PRESENT" else None
    # If no parseable manifest/inspection exists, retain any explicitly supplied
    # candidate from the request, including its known pre-existing hash.
    if archive_raw is None:
        request = initial.get("active_artifacts", {}).get("build_request", {})
        request_data = data(request["path"])
        raw = request_data.get("target", {}).get("output_path")
        if isinstance(raw, str):
            _, identity = supplied(raw)
            binding.update(archive_path=raw, archive_sha256=identity.get("content_sha256"))
    if _sha(binding.get("archive_sha256")):
        candidate = resolve_within(root, binding["archive_path"], must_exist=True)
        if not candidate.is_file() or sha256_file(candidate) != binding["archive_sha256"]:
            raise InputError("known supplied candidate changed after the verifier invocation")
    latest_raw = (run / "40_verification/harness/latest.json").relative_to(root).as_posix()
    latest = data(latest_raw)
    harness = None
    if isinstance(latest.get("attempt_path"), str):
        summary = latest["attempt_path"].rstrip("/") + "/summary.json"
        cleanup = latest.get("cleanup_path")
        if cleanup is None and isinstance(latest.get("attempt_id"), str):
            cleanup = (run / "40_verification/harness/cleanup" / f"{latest['attempt_id']}.json").relative_to(root).as_posix()
        if isinstance(cleanup, str):
            _, attempt_identity = supplied(summary)
            _, cleanup_identity = supplied(cleanup)
            if attempt_identity.get("availability") == cleanup_identity.get("availability") == "PRESENT":
                harness = {"path": summary, "content_sha256": attempt_identity["content_sha256"], "cleanup_path": cleanup, "cleanup_sha256": cleanup_identity["content_sha256"]}
    snapshot = {"report_ref": report_ref, "report_path": receipt["path"], "report_sha256": receipt["content_sha256"], "source_invocation_ref": receipt["source_invocation_ref"], "boundary_evidence_ref": receipt["boundary_evidence_ref"], "stage_status": status, "recorded_at": timestamp, "candidate_binding": binding, "harness_attempt": harness}
    return snapshot


def validate_round_context(root: Path, run: Path, state: dict[str, Any]) -> list[Diagnostic]:
    """Historical snapshots resolve against receipts and audited input hashes.

    Archives may legitimately advance after a counted round. Historical archive
    identities are checked against their original baseline, never today's bytes.
    """
    errors = []
    snapshots: dict[str, dict] = {}
    latest = state.get("control", {}).get("latest_verification_result")
    if isinstance(latest, dict):
        snapshots[latest.get("report_ref", "")] = latest
    for record in state.get("repair", {}).get("rounds", []):
        if not isinstance(record, dict):
            continue
        for name in ("source_verification", "result_verification"):
            snapshot = record.get(name)
            if isinstance(snapshot, dict):
                ref = snapshot.get("report_ref", "")
                if ref in snapshots and snapshots[ref] != snapshot:
                    errors.append(Diagnostic("ROUND_IDENTITY", "$.repair.rounds", "one report cannot identify conflicting snapshots"))
                snapshots[ref] = snapshot
        for ref in record.get("request_refs", []):
            event = next((event for event in state.get("bounce_back_events", []) if isinstance(event, dict) and event.get("id") == ref), None)
            if not modification_event(event, record.get("source_verification", {})):
                errors.append(Diagnostic("ROUND_REQUEST", "$.repair.rounds", "round request must bind an attributable subject modification event"))
    for ref, snapshot in snapshots.items():
        try:
            receipt, baseline, initial = _receipt_baseline(root, run, state, ref)
            if any(snapshot.get(a) != receipt.get(b) for a, b in (("report_path", "path"), ("report_sha256", "content_sha256"), ("source_invocation_ref", "source_invocation_ref"), ("boundary_evidence_ref", "boundary_evidence_ref"))):
                raise InputError("snapshot report provenance differs from registered receipt")
            active = state.get("active_artifacts", {}).get("verification_report", {})
            canonical = _project_path(root, run, receipt["path"])
            historical = canonical.parent / "history" / f"{canonical.stem}.v{ref.rsplit('@', 1)[1]}{canonical.suffix}"
            # Admission validates an in-memory state before replacing canonical
            # bytes or creating history. The previous canonical is still valid
            # evidence during that window; finalized states use history normally.
            paths = [canonical, historical]
            if not any(path.is_file() and sha256_file(path) == snapshot["report_sha256"] for path in paths):
                raise InputError("retained terminal report bytes differ from their identity")
            inputs = _inputs(baseline)
            binding = snapshot["candidate_binding"]
            for name in ("product_contract", "manifest", "inspection", "archive"):
                raw = binding.get(f"{name}_path")
                digest = binding.get(f"{name}_sha256")
                if raw is None:
                    continue
                path = _project_path(root, run, raw)
                item = inputs.get(path.relative_to(root).as_posix())
                if not isinstance(item, dict) or digest != item.get("content_sha256"):
                    raise InputError(f"snapshot {name} identity was not supplied to verifier")
                if name == "product_contract" and binding.get("product_contract_ref") != f"{item.get('artifact_id')}@{item.get('version')}":
                    raise InputError("snapshot contract version differs from audited input")
                if name == "product_contract":
                    contract_history = path.parent / "history" / f"{path.stem}.v{item['version']}{path.suffix}"
                    if not any(retained.is_file() and sha256_file(retained) == digest for retained in (path, contract_history)):
                        raise InputError("retained contract version is missing or changed")
            harness = snapshot.get("harness_attempt")
            if isinstance(harness, dict):
                for path_field, hash_field in (("path", "content_sha256"), ("cleanup_path", "cleanup_sha256")):
                    item = inputs.get(harness[path_field])
                    if not isinstance(item, dict) or item.get("content_sha256") != harness[hash_field] or sha256_file(resolve_within(root, harness[path_field], must_exist=True)) != harness[hash_field]:
                        raise InputError("immutable harness attempt differs from audited identity")
            assigned_round = receipt.get("round_number")
            prior = initial.get("control", {}).get("latest_verification_result")
            if assigned_round is not None:
                rounds = state.get("repair", {}).get("rounds", [])
                initial_rounds = initial.get("repair", {}).get("rounds", [])
                if type(assigned_round) is not int or not 1 <= assigned_round <= len(rounds) or not initial_rounds or initial_rounds[-1].get("number") != assigned_round or initial_rounds[-1].get("status") != "IN_PROGRESS" or initial_rounds[-1].get("source_verification") != rounds[assigned_round - 1].get("source_verification"):
                    raise InputError("terminal report does not bind its reserved in-progress round")
            elif isinstance(prior, dict):
                validate_threshold_lineage(root, run, state, snapshot, prior)
        except (InputError, OSError, ValueError, KeyError, TypeError) as exc:
            errors.append(Diagnostic("ROUND_IDENTITY", f"$.control.latest_verification_result/{ref}", str(exc)))
    return errors


def modification_event(event: Any, source: dict) -> bool:
    if not isinstance(event, dict) or event.get("classification") not in {"IMPLEMENTATION_DEFECT", "CONTRACT_CONTRADICTION", "NON_MATERIAL_CHOICE", "MATERIAL_AMBIGUITY", "PERMISSION_OR_EXTERNAL_AUTHORITY"}:
        return False
    origin = event.get("origin", {})
    return source.get("report_ref") in event.get("affected_refs", []) and origin.get("result_artifact_ref") == source.get("report_ref") and bool({"repair", "verification"} & set(event.get("affected_stages", [])))


def evidence_recovery_event(event: Any, source: dict) -> bool:
    if not isinstance(event, dict) or event.get("classification") != "EVIDENCE_GAP" or event.get("status") != "RESOLVED":
        return False
    retry, origin = event.get("retry", {}), event.get("origin", {})
    return (
        "verification" in event.get("affected_stages", [])
        and source.get("report_ref") in event.get("affected_refs", [])
        and origin.get("result_artifact_ref") == source.get("report_ref")
        and retry.get("agent_role") == "independent_verifier"
        and retry.get("prior_invocation_ref") == source.get("source_invocation_ref")
        and retry.get("allowed") is True
        and "EVIDENCE_CHANGED" in retry.get("change_basis", [])
        and not set(retry.get("change_basis", [])) & {"INPUT_CHANGED", "IMPLEMENTATION_CHANGED"}
    )


def validate_threshold_lineage(root: Path, run: Path, state: dict[str, Any], snapshot: dict, round_result: dict) -> None:
    """Resolve finite uncounted recovery through authenticated baseline backups.

    No ledger result is replaced. Each null-round invocation must name a prior
    result, retain unchanged subject identity, and consume its resolved evidence
    event. Decreasing report versions make cycles and invented resets fail closed.
    """
    current = snapshot
    visited: set[str] = set()
    while current != round_result:
        ref = current.get("report_ref")
        if not isinstance(ref, str) or ref in visited:
            raise InputError("threshold recovery lineage is cyclic or malformed")
        visited.add(ref)
        receipt, baseline, initial = _receipt_baseline(root, run, state, ref)
        if receipt.get("round_number") is not None:
            raise InputError("threshold recovery lineage cannot cross another counted round")
        previous = initial.get("control", {}).get("latest_verification_result")
        if not isinstance(previous, dict) or not _same_subject(current, previous):
            raise InputError("threshold recovery lineage has an unknown or changed subject")
        if int(previous["report_ref"].rsplit("@", 1)[1]) >= int(ref.rsplit("@", 1)[1]):
            raise InputError("threshold recovery lineage must use earlier verifier reports")
        if not any(evidence_recovery_event(event, previous) for event in initial.get("bounce_back_events", [])):
            raise InputError("threshold recovery lineage lacks an attributable resolved evidence event")
        if any(current.get(a) != receipt.get(b) for a, b in (("report_path", "path"), ("report_sha256", "content_sha256"), ("source_invocation_ref", "source_invocation_ref"), ("boundary_evidence_ref", "boundary_evidence_ref"))):
            raise InputError("threshold recovery snapshot differs from its registered report")
        canonical = _project_path(root, run, receipt["path"])
        historical = canonical.parent / "history" / f"{canonical.stem}.v{ref.rsplit('@', 1)[1]}{canonical.suffix}"
        if not any(path.is_file() and sha256_file(path) == receipt["content_sha256"] for path in (canonical, historical)):
            raise InputError("threshold recovery report version is missing or changed")
        # Audit the candidate's attributable hash inputs without asking old
        # archives to remain live after an authorized subsequent modification.
        inputs = _inputs(baseline)
        binding = current["candidate_binding"]
        for name in ("product_contract", "archive"):
            path = _project_path(root, run, binding[f"{name}_path"])
            if inputs.get(path.relative_to(root).as_posix(), {}).get("content_sha256") != binding[f"{name}_sha256"]:
                raise InputError("threshold recovery subject was not an audited input")
        current = previous
    if current != round_result:
        raise InputError("threshold recovery does not resolve to the exhausted round result")


def assert_current_subject(root: Path, run: Path, state: dict[str, Any], snapshot: dict) -> None:
    """Reject unknown/changed subjects while allowing evidence-only rebuilding."""
    from .evidence import reconcile_source

    binding = snapshot.get("candidate_binding", {})
    contract = state.get("active_artifacts", {}).get("product_contract", {})
    if not _sha(binding.get("product_contract_sha256")) or not _sha(binding.get("archive_sha256")):
        raise InputError("unchanged-subject recovery requires known prior contract and archive identities")
    if binding.get("product_contract_ref") != f"{contract.get('artifact_id')}@{contract.get('version')}" or contract.get("content_sha256") != binding["product_contract_sha256"]:
        raise InputError("contract changed during claimed evidence-only recovery")
    if sha256_file(_project_path(root, run, contract["path"])) != binding["product_contract_sha256"]:
        raise InputError("contract source bytes changed during evidence-only recovery")
    archive_path = resolve_within(root, binding.get("archive_path"), must_exist=True)
    if sha256_file(archive_path) != binding["archive_sha256"]:
        raise InputError("archive changed during claimed evidence-only recovery")
    manifest_path = _project_path(root, run, binding.get("manifest_path") or "50_release/release_manifest.json")
    manifest = read_structured(manifest_path)
    if not isinstance(manifest, dict) or manifest.get("archive_sha256") != binding["archive_sha256"] or resolve_within(root, manifest.get("archive_path"), must_exist=True) != archive_path:
        raise InputError("recovered manifest does not identify the unchanged archive")
    inventory = manifest.get("entries")
    checked = CommandResult("round-subject-reconciliation")
    reconcile_source(root, manifest, inventory, checked)
    if not checked.ok:
        raise InputError("source changed or is unknown during claimed evidence-only recovery: " + checked.diagnostics[0].message)
    try:
        with zipfile.ZipFile(archive_path) as archive:
            actual = {item.filename: {"sha256": hashlib.sha256(archive.read(item)).hexdigest(), "size_bytes": item.file_size} for item in archive.infolist()}
            expected = {item["path"]: {"sha256": item["sha256"], "size_bytes": item["size_bytes"]} for item in inventory}
            if actual != expected or len(actual) != len(archive.infolist()):
                raise InputError("recovered manifest source hashes differ from unchanged archive")
    except (zipfile.BadZipFile, KeyError) as exc:
        raise InputError(f"cannot reconcile recovery archive: {exc}") from exc


def assert_unmodified_before_round(root: Path, run: Path, state: dict[str, Any]) -> None:
    """Detect known pre-reservation drift without treating unknown as changed."""
    snapshot = state.get("control", {}).get("latest_verification_result")
    if not isinstance(snapshot, dict):
        raise InputError("a modification round requires a terminal source result")
    binding = snapshot["candidate_binding"]
    contract = state.get("active_artifacts", {}).get("product_contract", {})
    if not isinstance(contract, dict) or binding["product_contract_ref"] != f"{contract.get('artifact_id')}@{contract.get('version')}" or contract.get("content_sha256") != binding["product_contract_sha256"]:
        raise InputError("contract identity changed before a round was reserved")
    if sha256_file(_project_path(root, run, contract["path"])) != binding["product_contract_sha256"]:
        raise InputError("contract bytes changed before a round was reserved")
    raw_archive = binding.get("archive_path")
    if not isinstance(raw_archive, str) or not _sha(binding.get("archive_sha256")):
        return  # A failed/blocked result may have no usable candidate yet.
    archive = resolve_within(root, raw_archive)
    if not archive.exists():
        return  # Missing evidence is not proof that replacement bytes exist.
    if not archive.is_file() or sha256_file(archive) != binding["archive_sha256"]:
        raise InputError("archive changed before a round was reserved")
    raw_manifest = binding.get("manifest_path")
    if not isinstance(raw_manifest, str):
        return
    manifest_path = _project_path(root, run, raw_manifest)
    if not manifest_path.is_file():
        return
    try:
        manifest = read_structured(manifest_path)
    except InputError:
        return
    # Only a PASSED result establishes that archive, manifest and source were
    # consistent. A failed result may describe that very inconsistency; keeping
    # its known contract/archive bytes unchanged must still permit repair.
    if snapshot.get("stage_status") == "PASSED" and isinstance(manifest, dict) and isinstance(manifest.get("entries"), list) and manifest["entries"]:
        assert_current_subject(root, run, state, snapshot)


def reserve_round(state: dict[str, Any], request_refs: list[str], failure_ref: str | None, timestamp: str) -> bool:
    """Mutate a copy only; return False for exact lost-reply start recovery."""
    repair = state["repair"]
    source = state["control"].get("latest_verification_result")
    if not isinstance(source, dict) or failure_ref != source.get("report_ref"):
        raise InputError("repair requires the exact latest terminal verifier report")
    if not request_refs or len(set(request_refs)) != len(request_refs):
        raise InputError("repair requires distinct modification-event references")
    requests = {item.get("id"): item for item in state.get("bounce_back_events", []) if isinstance(item, dict)}
    if any(not modification_event(requests.get(ref), source) for ref in request_refs):
        raise InputError("repair request must reference attributable subject modification events")
    refs = sorted(request_refs)
    if repair["rounds"] and repair["rounds"][-1]["status"] == "IN_PROGRESS":
        current = repair["rounds"][-1]
        if current["source_verification"] == source and current["request_refs"] == refs:
            return False
        raise InputError("in-progress round cannot be restarted with conflicting source or requests")
    if repair["active_attempt"] >= repair["maximum_attempts"]:
        raise InputError("round allowance exhausted; independent review and user approval are required")
    repair["active_attempt"] += 1
    repair["last_failure_ref"] = failure_ref
    repair["rounds"].append({"number": repair["active_attempt"], "started_at": timestamp, "request_refs": refs, "source_verification": deepcopy(source), "status": "IN_PROGRESS", "result_verification": None})
    return True


def complete_verification(state: dict[str, Any], snapshot: dict) -> bool:
    """Attach a new result, or recover an identical terminal transition."""
    latest = state["control"].get("latest_verification_result")
    if isinstance(latest, dict) and latest.get("report_ref") == snapshot["report_ref"]:
        comparable = {key: value for key, value in snapshot.items() if key != "recorded_at"}
        if comparable == {key: value for key, value in latest.items() if key != "recorded_at"}:
            return False
        raise InputError("terminal replay conflicts with the recorded result")
    records = state["repair"]["rounds"]
    if records and records[-1]["status"] == "IN_PROGRESS":
        records[-1].update(status="COMPLETED", result_verification=deepcopy(snapshot))
    state["control"]["latest_verification_result"] = deepcopy(snapshot)
    return True
