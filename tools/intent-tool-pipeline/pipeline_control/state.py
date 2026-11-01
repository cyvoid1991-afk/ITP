"""Deterministic run-state transition enforcement."""

from __future__ import annotations

import re
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .boundary import latest_boundary_violations
from .evidence import passing_package_inspection, passing_test_results
from .io_utils import (
    InputError,
    atomic_write_json,
    normalize_repository_reference,
    read_structured,
    repository_relative,
    resolve_within,
    sha256_file,
)
from .result import CommandResult
from .rounds import (
    assert_current_subject, assert_unmodified_before_round, capture_verification_result, complete_verification,
    evidence_recovery_event, modification_event, reserve_round,
)
from .mutation_guard import run_mutation_diagnostics, run_forward_diagnostics
from .workflow import entry_context, validate_contract_sources, validate_run_state_context
from .validation import (
    STAGE_IDS,
    STAGE_STATUSES,
    is_agent_artifact_run,
    validate_run_directory,
    validate_semantic_prerequisites,
    validate_verification_reconciliation,
)


ALLOWED_TRANSITIONS = {
    "intake": {"intake", "framing"},
    "framing": {"framing", "contract"},
    "contract": {"contract", "repository_analysis"},
    "repository_analysis": {"repository_analysis", "implementation"},
    "implementation": {"implementation", "verification"},
    "verification": {"verification", "repair", "release"},
    "repair": {"repair", "verification"},
    "release": {"release"},
}

BOUNCE_BACK_CREATE_FIELDS = {
    "origin",
    "assigned_to",
    "classification",
    "summary",
    "affected_stages",
    "affected_refs",
    "required_resolution",
    "retry",
}
BOUNCE_BACK_RESOLVE_FIELDS = {
    "event_id",
    "resolved_by",
    "resolution_type",
    "summary",
    "changed_artifact_refs",
    "decision_refs",
    "evidence_refs",
    "retry",
}


def _gate_map(state: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {item.get("id"): item for item in state.get("gates", []) if isinstance(item, dict)}


def _stage_map(state: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {item.get("id"): item for item in state.get("stages", []) if isinstance(item, dict)}


def _verified_candidate_binding(
    project_root: Path,
    run_dir: Path,
    state: dict[str, Any],
) -> dict[str, Any] | None:
    """Capture the inspected package inputs when they are already complete.

    Older flows that validated verification before package inspection remain
    readable and transition-compatible, but cannot become revision baselines.
    """

    inspection_path = run_dir / "50_release" / "package_inspection.json"
    inspection_ok, _, inspection = passing_package_inspection(project_root, inspection_path)
    if not inspection_ok or not isinstance(inspection, dict):
        return None
    active = state.get("active_artifacts")
    contract_entry = active.get("product_contract") if isinstance(active, dict) else None
    if not isinstance(contract_entry, dict):
        return None
    contract_raw = contract_entry.get("path")
    if not isinstance(contract_raw, str):
        return None
    def run_file(raw: Any) -> Path:
        if not isinstance(raw, str):
            raise InputError("run-bound candidate path must be a string")
        normalized = normalize_repository_reference(raw)
        candidates = {
            candidate.resolve()
            for candidate in (project_root / normalized, run_dir / normalized)
            if candidate.is_file()
        }
        contained = [candidate for candidate in candidates if candidate.is_relative_to(run_dir.resolve())]
        if len(contained) != 1:
            raise InputError("run-bound candidate path must resolve unambiguously inside the run")
        return contained[0]

    try:
        contract_path = run_file(contract_raw)
        manifest_path = run_file(inspection["manifest_path"])
        archive_path = resolve_within(project_root, inspection["archive_path"], must_exist=True)
    except (InputError, KeyError):
        return None
    if not contract_path.is_file() or not manifest_path.is_file() or not archive_path.is_file():
        return None
    try:
        contract_hash = sha256_file(contract_path)
        manifest_hash = sha256_file(manifest_path)
        inspection_hash = sha256_file(inspection_path)
        archive_hash = sha256_file(archive_path)
    except OSError:
        return None
    if contract_hash != contract_entry.get("content_sha256"):
        return None
    return {
        "product_contract_ref": f"{contract_entry.get('artifact_id')}@{contract_entry.get('version')}",
        "product_contract_path": contract_entry.get("path"),
        "product_contract_sha256": contract_hash,
        "manifest_path": inspection["manifest_path"],
        "manifest_sha256": manifest_hash,
        "inspection_path": repository_relative(project_root, inspection_path),
        "inspection_sha256": inspection_hash,
        "archive_path": inspection["archive_path"],
        "archive_sha256": archive_hash,
    }


def _open_blockers_for(state: dict[str, Any], stage: str) -> list[str]:
    identifiers: list[str] = []
    for item in state.get("blockers", []):
        if not isinstance(item, dict) or item.get("blocking") is not True or item.get("status") != "OPEN":
            continue
        affected = item.get("affected_stages")
        if not isinstance(affected, list) or not affected or stage in affected:
            identifiers.append(str(item.get("id", "<unknown>")))
    for item in state.get("bounce_back_events", []):
        if not isinstance(item, dict) or item.get("status") != "OPEN":
            continue
        affected = item.get("affected_stages")
        if isinstance(affected, list) and stage in affected:
            identifiers.append(str(item.get("id", "<unknown>")))
    return identifiers


def _pending_approvals(state: dict[str, Any]) -> list[str]:
    return [
        str(item.get("id", "<unknown>"))
        for item in state.get("required_approvals", [])
        if isinstance(item, dict) and item.get("status") == "PENDING"
    ]


def _repair_retry_is_changed(state: dict[str, Any]) -> bool:
    if is_agent_artifact_run(state):
        rounds = state.get("repair", {}).get("rounds", [])
        if not rounds or rounds[-1].get("status") != "IN_PROGRESS":
            return False
        current = rounds[-1]
        events = {event.get("id"): event for event in state.get("bounce_back_events", []) if isinstance(event, dict)}
        return all(
            modification_event(events.get(ref), current["source_verification"])
            and events[ref].get("status") == "RESOLVED"
            and events[ref].get("retry", {}).get("allowed") is True
            and bool(set(events[ref].get("retry", {}).get("change_basis", [])) & {"INPUT_CHANGED", "IMPLEMENTATION_CHANGED", "DECISION_CHANGED"})
            for ref in current["request_refs"]
        )
    for event in reversed(state.get("bounce_back_events", [])):
        if not isinstance(event, dict):
            continue
        if event.get("classification") not in {"IMPLEMENTATION_DEFECT", "CONTRACT_CONTRADICTION"}:
            continue
        affected = event.get("affected_stages", [])
        if not isinstance(affected, list) or not ({"repair", "verification"} & set(affected)):
            continue
        retry = event.get("retry")
        if (
            event.get("status") == "RESOLVED"
            and isinstance(retry, dict)
            and retry.get("allowed") is True
            and bool(retry.get("change_basis"))
        ):
            return True
        return False
    return False


def _revalidation_event(state: dict[str, Any], failure_ref: str | None) -> bool:
    """A recorded verifier bounce-back, not Root's desired verdict, opens review."""
    if is_agent_artifact_run(state):
        source = state.get("control", {}).get("latest_verification_result")
        return isinstance(source, dict) and failure_ref == source.get("report_ref") and any(
            isinstance(event, dict)
            and event.get("classification") == "EVIDENCE_GAP"
            and event.get("status") in {"OPEN", "RESOLVED"}
            and source["report_ref"] in event.get("affected_refs", [])
            and "verification" in event.get("affected_stages", [])
            and event.get("retry", {}).get("agent_role") == "independent_verifier"
            and event.get("retry", {}).get("prior_invocation_ref") == source.get("source_invocation_ref")
            for event in state.get("bounce_back_events", [])
        )
    report = state.get("active_artifacts", {}).get("verification_report")
    identity = state.get("control", {}).get("verification_validation_identity")
    if not isinstance(report, dict) or not isinstance(identity, dict):
        return False
    if not isinstance(identity.get("candidate_binding"), dict):
        return False
    if failure_ref != f"{report.get('artifact_id')}@{report.get('version')}":
        return False
    if any(identity.get(k) != report.get(k) for k in ("version", "path", "content_sha256")):
        return False
    return any(
        isinstance(event, dict)
        and event.get("status") == "OPEN"
        and "verification" in event.get("affected_stages", [])
        and failure_ref in event.get("affected_refs", [])
        and event.get("retry", {}).get("agent_role") == "independent_verifier"
        and event.get("retry", {}).get("prior_invocation_ref") == report.get("source_invocation_ref")
        for event in state.get("bounce_back_events", [])
    )


def _validate_payload_fields(
    result: CommandResult,
    payload: Any,
    *,
    required: set[str],
    optional: set[str] | None = None,
) -> dict[str, Any] | None:
    if not isinstance(payload, dict):
        result.add("PAYLOAD_TYPE", "payload", "must contain an object/mapping")
        return None
    missing = sorted(required - set(payload))
    unexpected = sorted(set(payload) - required - (optional or set()))
    for field in missing:
        result.add("PAYLOAD_FIELD_REQUIRED", f"payload.{field}", "required field is missing")
    for field in unexpected:
        result.add("PAYLOAD_FIELD_UNKNOWN", f"payload.{field}", "field is not accepted for this action")
    return payload if result.ok else None


def _next_bounce_back_id(events: list[Any]) -> str:
    numbers = []
    for event in events:
        if not isinstance(event, dict):
            continue
        identifier = event.get("id")
        match = re.fullmatch(r"BB-(\d{3,})", identifier) if isinstance(identifier, str) else None
        if match:
            numbers.append(int(match.group(1)))
    return f"BB-{max(numbers, default=0) + 1:03d}"


def update_bounce_back(
    run_dir: Path,
    *,
    project_root: Path | None = None,
    action: str,
    payload: Any,
    timestamp: str | None = None,
) -> CommandResult:
    """Create or resolve a bounce-back without exposing run-state array placement."""

    result = CommandResult(command="update-bounce-back")
    result.extend(run_mutation_diagnostics(run_dir))
    if not result.ok:
        return result
    state_path = run_dir / "30_execution" / "run_state.json"
    if not state_path.is_file():
        result.add("STATE_MISSING", str(state_path), "run_state.json does not exist")
        return result
    try:
        raw = read_structured(state_path)
    except InputError as exc:
        result.add("PARSE_ERROR", str(state_path), str(exc))
        return result
    if not isinstance(raw, dict):
        result.add("STATE_TYPE", str(state_path), "run_state.json must contain an object")
        return result
    effective_root = (project_root or run_dir.parent).resolve()
    existing_diagnostics = validate_run_state_context(effective_root, run_dir, raw)
    if existing_diagnostics:
        result.extend(existing_diagnostics)
        return result

    effective_timestamp = timestamp or datetime.now(timezone.utc).isoformat(timespec="seconds")
    updated = deepcopy(raw)
    events = updated["bounce_back_events"]
    event_id: str | None = None

    if action == "create":
        create_payload = _validate_payload_fields(result, payload, required=BOUNCE_BACK_CREATE_FIELDS)
        if create_payload is None:
            return result
        retry = create_payload.get("retry")
        if not isinstance(retry, dict):
            result.add("PAYLOAD_TYPE", "payload.retry", "must contain an object/mapping")
            return result
        retry_fields = {"agent_role", "prior_invocation_ref"}
        retry_payload = _validate_payload_fields(result, retry, required=retry_fields)
        if retry_payload is None:
            return result
        event_id = _next_bounce_back_id(events)
        events.append(
            {
                "id": event_id,
                "created_at": effective_timestamp,
                "origin": deepcopy(create_payload["origin"]),
                "assigned_to": create_payload["assigned_to"],
                "classification": create_payload["classification"],
                "status": "OPEN",
                "summary": create_payload["summary"],
                "affected_stages": deepcopy(create_payload["affected_stages"]),
                "affected_refs": deepcopy(create_payload["affected_refs"]),
                "required_resolution": create_payload["required_resolution"],
                "resolution": None,
                "retry": {
                    "agent_role": retry_payload["agent_role"],
                    "allowed": False,
                    "change_basis": [],
                    "prior_invocation_ref": retry_payload["prior_invocation_ref"],
                },
            }
        )
        if is_agent_artifact_run(raw) and create_payload["classification"] == "REPAIR_LIMIT_EXHAUSTED":
            from .continuation import threshold_basis

            try:
                events[-1]["round_review_basis"] = threshold_basis(effective_root, run_dir, raw)
                latest = raw["control"]["latest_verification_result"]
                expected_origin = {"role": "independent_verifier", "invocation_ref": latest["source_invocation_ref"], "result_artifact_ref": latest["report_ref"], "result": latest["stage_status"]}
                if any(events[-1]["origin"].get(key) != value for key, value in expected_origin.items()):
                    raise InputError("threshold event origin must identify the latest terminal verifier result")
            except (InputError, OSError, ValueError, KeyError, TypeError, AttributeError) as exc:
                result.add("CONTINUATION_BASIS", "payload.origin", str(exc))
                return result
    elif action == "resolve":
        resolve_payload = _validate_payload_fields(result, payload, required=BOUNCE_BACK_RESOLVE_FIELDS,
                                                  optional={"continuation"} if is_agent_artifact_run(raw) else None)
        if resolve_payload is None:
            return result
        event_id = resolve_payload.get("event_id")
        event = next(
            (item for item in events if isinstance(item, dict) and item.get("id") == event_id),
            None,
        )
        if event is None:
            result.add("BOUNCE_BACK_MISSING", "payload.event_id", f"no bounce-back event matches {event_id!r}")
            return result
        threshold = is_agent_artifact_run(raw) and event.get("classification") == "REPAIR_LIMIT_EXHAUSTED"
        if "continuation" in resolve_payload and not threshold:
            result.add("CONTINUATION_EVENT", "payload.continuation", "continuation is accepted only on selected threshold events")
            return result
        replaying = threshold and event.get("status") == "RESOLVED"
        if event.get("status") != "OPEN" and not replaying:
            result.add("BOUNCE_BACK_STATUS", "payload.event_id", "only an OPEN bounce-back can be resolved")
            return result
        retry = resolve_payload.get("retry")
        if not isinstance(retry, dict):
            result.add("PAYLOAD_TYPE", "payload.retry", "must contain an object/mapping")
            return result
        retry_fields = {"allowed", "change_basis"}
        retry_payload = _validate_payload_fields(result, retry, required=retry_fields)
        if retry_payload is None:
            return result
        proposed_resolution = {
            "resolved_at": event["resolution"]["resolved_at"] if replaying else effective_timestamp,
            "resolved_by": resolve_payload["resolved_by"],
            "resolution_type": resolve_payload["resolution_type"],
            "summary": resolve_payload["summary"],
            "changed_artifact_refs": deepcopy(resolve_payload["changed_artifact_refs"]),
            "decision_refs": deepcopy(resolve_payload["decision_refs"]),
            "evidence_refs": deepcopy(resolve_payload["evidence_refs"]),
        }
        if "continuation" in resolve_payload:
            proposed_resolution["continuation"] = deepcopy(resolve_payload["continuation"])
        if replaying:
            if proposed_resolution != event.get("resolution") or any(event["retry"].get(key) != retry_payload[key] for key in ("allowed", "change_basis")):
                result.add("CONTINUATION_REPLAY", "payload", "threshold resolution replay differs from the retained outcome")
                return result
            if "continuation" in proposed_resolution:
                from .continuation import prepare_continuation

                try:
                    prepare_continuation(effective_root, run_dir, raw, event, proposed_resolution, historical=True)
                except (InputError, OSError, ValueError, KeyError, TypeError) as exc:
                    result.add("CONTINUATION_AUTHORIZATION", "payload.continuation", str(exc))
                    return result
            result.data = {"state_path": str(state_path), "action": action, "event_id": event_id, "replayed": True,
                           "maximum_attempts": proposed_resolution.get("continuation", {}).get("new_maximum_attempts", raw["repair"]["maximum_attempts"])}
            return result
        event["status"] = "RESOLVED"
        event["resolution"] = proposed_resolution
        event["retry"]["allowed"] = retry_payload["allowed"]
        event["retry"]["change_basis"] = deepcopy(retry_payload["change_basis"])
        if threshold and "continuation" in proposed_resolution:
            from .continuation import prepare_continuation

            try:
                continuation = prepare_continuation(effective_root, run_dir, raw, event, proposed_resolution)
                updated["repair"]["maximum_attempts"] = continuation["new_maximum_attempts"]
            except (InputError, OSError, ValueError, KeyError, TypeError) as exc:
                result.add("CONTINUATION_AUTHORIZATION", "payload.continuation", str(exc))
                return result
    else:
        result.add("BOUNCE_BACK_ACTION", "action", "must be 'create' or 'resolve'")
        return result

    updated["artifact"]["version"] += 1
    updated["artifact"]["updated_at"] = effective_timestamp
    updated["active_artifacts"]["run_state"]["version"] = updated["artifact"]["version"]
    updated_diagnostics = validate_run_state_context(effective_root, run_dir, updated)
    if updated_diagnostics:
        result.extend(updated_diagnostics)
        return result
    try:
        atomic_write_json(state_path, updated)
    except OSError as exc:
        result.add("STATE_WRITE", str(state_path), f"failed to write state atomically: {exc}")
        return result
    result.data = {
        "state_path": str(state_path),
        "action": action,
        "event_id": event_id,
        "artifact_version": updated["artifact"]["version"],
    }
    return result


def update_state(
    run_dir: Path,
    *,
    project_root: Path | None = None,
    to_stage: str,
    stage_status: str,
    gate_status: str,
    evidence_refs: list[str],
    rationale: str,
    next_action: str,
    timestamp: str | None = None,
    failure_ref: str | None = None,
) -> CommandResult:
    result = CommandResult(command="update-state")
    # Repair entry may reserve the round needed to replace stale owner work.
    # All normal transition/round checks below still apply before mutation.
    if to_stage == "repair" and stage_status == gate_status == "IN_PROGRESS":
        result.extend(run_mutation_diagnostics(run_dir))
    else:
        result.extend(run_forward_diagnostics((project_root or run_dir.parent).resolve(), run_dir))
    if not result.ok:
        return result
    state_path = run_dir / "30_execution" / "run_state.json"
    if not state_path.is_file():
        result.add("STATE_MISSING", str(state_path), "run_state.json does not exist")
        return result
    try:
        raw = read_structured(state_path)
    except InputError as exc:
        result.add("PARSE_ERROR", str(state_path), str(exc))
        return result
    if not isinstance(raw, dict):
        result.add("STATE_TYPE", str(state_path), "run_state.json must contain an object")
        return result
    effective_root = (project_root or run_dir.parent).resolve()
    existing_diagnostics = validate_run_state_context(effective_root, run_dir, raw)
    if existing_diagnostics:
        result.extend(existing_diagnostics)
        return result
    if to_stage not in STAGE_IDS:
        result.add("STAGE_ID", "to_stage", f"must be one of {STAGE_IDS}")
    if stage_status not in STAGE_STATUSES:
        result.add("STAGE_STATUS", "stage_status", f"must be one of {sorted(STAGE_STATUSES)}")
    if gate_status not in STAGE_STATUSES:
        result.add("GATE_STATUS", "gate_status", f"must be one of {sorted(STAGE_STATUSES)}")
    if not rationale.strip():
        result.add("RATIONALE_REQUIRED", "rationale", "must be non-empty")
    if not next_action.strip():
        result.add("NEXT_ACTION_REQUIRED", "next_action", "must be non-empty")
    if stage_status == "PASSED" and gate_status != "PASSED":
        result.add("GATE_MISMATCH", "gate_status", "a PASSED stage requires a PASSED gate")
    if gate_status == "PASSED" and stage_status != "PASSED":
        result.add("GATE_MISMATCH", "stage_status", "a PASSED gate requires a PASSED stage")
    if stage_status in {"FAILED", "BLOCKED"} and gate_status != stage_status:
        result.add("GATE_MISMATCH", "gate_status", f"a {stage_status} stage requires a {stage_status} gate")
    if gate_status == "PASSED" and not evidence_refs:
        result.add("GATE_EVIDENCE", "evidence_refs", "a PASSED gate requires at least one evidence reference")
    if not result.ok:
        return result

    current_stage = raw["run"]["current_stage"]
    direct, _ = entry_context(effective_root, run_dir, raw)
    stages = _stage_map(raw)
    selected = is_agent_artifact_run(raw)
    effective_timestamp = timestamp or datetime.now(timezone.utc).isoformat(timespec="seconds")
    round_start = selected and to_stage == "repair" and current_stage in {"verification", "release"}
    # Start/result lost-reply recovery precedes status regression checks. It
    # returns the original state, including timestamps and artifact version.
    if selected and to_stage == "repair" and failure_ref is not None and stage_status == gate_status == "IN_PROGRESS":
        try:
            old_round = next((record for record in raw["repair"]["rounds"] if record["source_verification"]["report_ref"] == failure_ref), None)
            if old_round is not None:
                if sorted(evidence_refs) != old_round["request_refs"]:
                    raise InputError("round start replay conflicts with its recorded modification requests")
                result.data = {"state_path": str(state_path), "replayed": True, "repair_attempt": old_round["number"], "is_current": old_round["status"] == "IN_PROGRESS"}
                return result
            if current_stage != "repair":
                # A new slot is reserved with the ordinary atomic transition.
                pass
            else:
                replay = deepcopy(raw)
                if not reserve_round(replay, evidence_refs, failure_ref, effective_timestamp):
                    result.data = {"state_path": str(state_path), "replayed": True, "repair_attempt": raw["repair"]["active_attempt"]}
                    return result
        except InputError as exc:
            result.add("ROUND_START", "repair", str(exc))
            return result
    terminal_snapshot = None
    if selected and to_stage == "verification" and stage_status in {"PASSED", "FAILED", "BLOCKED"}:
        try:
            latest = raw["control"].get("latest_verification_result")
            active = raw.get("active_artifacts", {}).get("verification_report")
            active = active if isinstance(active, dict) else {}
            active_ref = f"{active.get('artifact_id')}@{active.get('version')}"
            # Historical evidence can legitimately have advanced after a round.
            # An exact replay uses the retained snapshot instead of re-reading it.
            if isinstance(latest, dict) and latest["report_ref"] == active_ref:
                if latest["stage_status"] != stage_status:
                    raise InputError("terminal replay conflicts with the recorded verdict")
                if raw["repair"]["rounds"] and raw["repair"]["rounds"][-1]["status"] == "IN_PROGRESS":
                    raise InputError("a reserved round requires a fresh verifier report")
                result.data = {"state_path": str(state_path), "replayed": True, "repair_attempt": raw["repair"]["active_attempt"], "verification_result": deepcopy(latest)}
                return result
            terminal_snapshot = capture_verification_result(effective_root, run_dir, raw, stage_status, effective_timestamp)
            if stage_status == "PASSED":
                assert_current_subject(effective_root, run_dir, raw, terminal_snapshot)
            in_progress = bool(raw["repair"]["rounds"] and raw["repair"]["rounds"][-1]["status"] == "IN_PROGRESS")
            if isinstance(latest, dict) and not in_progress:
                if not any(evidence_recovery_event(event, latest) for event in raw.get("bounce_back_events", [])):
                    raise InputError("uncounted verification requires an attributable evidence-only recovery event")
                assert_current_subject(effective_root, run_dir, raw, latest)
        except (InputError, OSError, ValueError, KeyError, TypeError) as exc:
            result.add("ROUND_RESULT", "control.latest_verification_result", str(exc))
            return result
    if selected and stages.get("release", {}).get("status") == "PASSED":
        result.add("COMPLETED_RELEASE", "stages.release", "completed selected releases are immutable")
        return result
    reopening = (
        current_stage in {"verification", "release"}
        and to_stage == "verification"
        and stage_status == gate_status == "IN_PROGRESS"
        and stages.get("verification", {}).get("status") in ({"PASSED", "FAILED", "BLOCKED"} if selected else {"PASSED"})
        and stages.get("release", {}).get("status") != "PASSED"
        and bool(evidence_refs)
        and _revalidation_event(raw, failure_ref)
    )
    allowed = set(ALLOWED_TRANSITIONS[current_stage])
    if direct and current_stage == "intake":
        allowed = {"intake", "contract"}
    if reopening:
        allowed.add("verification")
    if round_start:
        allowed.add("repair")
    if to_stage not in allowed:
        result.add("TRANSITION_NOT_ALLOWED", "to_stage", f"cannot transition from {current_stage} to {to_stage}")
        return result

    stages = _stage_map(raw)
    gates = _gate_map(raw)
    current = stages[current_stage]
    current_gate = gates.get(current.get("gate_id"))
    advancing = to_stage != current_stage
    effective_root = (project_root or run_dir.parent).resolve()
    if advancing or stage_status == "PASSED" or gate_status == "PASSED":
        boundary_violations = latest_boundary_violations(run_dir)
        if boundary_violations:
            refs = [str(item.get("evidence_ref", item.get("role", "<unknown>"))) for item in boundary_violations]
            result.add(
                "BOUNDARY_VIOLATION",
                "30_execution/role_boundary/latest.json",
                f"pipeline progression is blocked by latest role-boundary result(s): {refs}",
            )
    if advancing and stage_status == "PENDING":
        result.add("STATUS_REGRESSION", "stage_status", "an advancing transition cannot leave the target stage PENDING")
    if not advancing and current.get("status") == "PASSED" and stage_status != "PASSED" and not reopening:
        result.add("STATUS_REGRESSION", "stage_status", "a PASSED current stage cannot regress")
    if advancing and not reopening:
        if to_stage == "repair" and (current_stage == "verification" or round_start):
            if current.get("status") not in ({"PASSED", "FAILED", "BLOCKED", "IN_PROGRESS"} if round_start and current_stage == "release" else {"PASSED", "FAILED", "BLOCKED"} if selected else {"FAILED", "BLOCKED"}):
                result.add("TRANSITION_PRECONDITION", "current_stage", "verification may enter repair only after FAILED or BLOCKED")
            if not failure_ref:
                result.add("FAILURE_REF_REQUIRED", "failure_ref", "entering repair requires the failed verification reference")
        else:
            if current.get("status") != "PASSED" or not isinstance(current_gate, dict) or current_gate.get("status") != "PASSED":
                result.add("TRANSITION_PRECONDITION", "current_stage", f"{current_stage} and its gate must be PASSED before advancing")
        if current_stage == "repair" and to_stage == "verification" and not _repair_retry_is_changed(raw):
            result.add("UNCHANGED_RETRY", "bounce_back_events", "repair retry requires a resolved defect/contradiction event with an allowed changed-basis retry")

        semantic_stages = {
            "intake": ["intake"],
            "framing": ["intake", "framing"],
            "contract": ["intake", "framing", "contract"],
            "repository_analysis": ["intake", "framing", "contract"],
            "implementation": ["intake", "framing", "contract"],
            "verification": ["intake", "framing", "contract", "verification"],
            "repair": ["intake", "framing", "contract"],
            "release": ["intake", "framing", "contract", "verification"],
        }[current_stage]
        if to_stage == "repair" and (current_stage == "verification" or round_start):
            semantic_stages = ["intake", "framing", "contract"]
        if direct:
            semantic_stages = [stage for stage in semantic_stages if stage != "framing"]
        result.extend(validate_semantic_prerequisites(effective_root, run_dir, raw, semantic_stages))

    if stage_status == "PASSED":
        semantic_stages = {
            "intake": ["intake"],
            "framing": ["intake", "framing"],
            "contract": ["intake", "framing", "contract"],
            "repository_analysis": ["intake", "framing", "contract"],
            "implementation": ["intake", "framing", "contract"],
            "verification": ["intake", "framing", "contract", "verification"],
            "repair": ["intake", "framing", "contract"],
            "release": ["intake", "framing", "contract", "verification"],
        }[to_stage]
        if direct:
            semantic_stages = [stage for stage in semantic_stages if stage != "framing"]
        result.extend(validate_semantic_prerequisites(effective_root, run_dir, raw, semantic_stages))

    if (
        (advancing and not reopening and to_stage in {"repository_analysis", "implementation", "verification", "release"})
        or (stage_status == "PASSED" and to_stage not in {"intake", "framing"})
    ):
        result.extend(validate_contract_sources(effective_root, run_dir, raw))

    if to_stage == "verification" and stage_status in {"PASSED", "FAILED", "BLOCKED"}:
        active = raw.get("active_artifacts")
        report_entry = active.get("verification_report") if isinstance(active, dict) else None
        if report_entry is None:
            result.add(
                "ACTIVE_ARTIFACT",
                "$.active_artifacts.verification_report",
                f"required before verification can become {stage_status}",
            )
        else:
            result.extend(validate_run_directory(effective_root, run_dir).diagnostics)
        if stage_status == "PASSED" and isinstance(report_entry, dict):
            from .validation import validate_revalidation_candidate

            if not selected:
                result.extend(validate_revalidation_candidate(effective_root, run_dir, raw))
            for event in raw.get("bounce_back_events", []):
                retry = event.get("retry", {})
                if retry.get("agent_role") == "independent_verifier" and retry.get("prior_invocation_ref") == report_entry.get("source_invocation_ref"):
                    result.add("UNCHANGED_VERIFIER_RETURN", "active_artifacts.verification_report", "a recorded revalidation requires a new independent verifier return")
                    break

    blockers = _open_blockers_for(raw, to_stage)
    if stage_status == "PASSED" and blockers:
        result.add("OPEN_BLOCKER", "blockers", f"cannot pass {to_stage}; open blocking records: {blockers}")
    if stage_status == "PASSED" and _pending_approvals(raw):
        result.add("PENDING_APPROVAL", "required_approvals", f"cannot pass a gate with pending approvals: {_pending_approvals(raw)}")

    if to_stage == "release":
        result.extend(validate_verification_reconciliation(effective_root, run_dir, raw))
        verification = stages.get("verification", {})
        verification_gate = gates.get(verification.get("gate_id"), {})
        if verification.get("status") != "PASSED" or verification_gate.get("status") != "PASSED":
            result.add("RELEASE_PRECONDITION", "stages.verification", "verification and its gate must be PASSED before release")
        tests_ok, tests_message, _ = passing_test_results(
            run_dir / "30_execution" / "test_results.json",
            effective_root,
        )
        if not tests_ok:
            result.add("TESTS_NOT_PASSING", "30_execution/test_results.json", tests_message)
        if stage_status == "PASSED":
            required_passed = ["intake", "framing", "contract", "repository_analysis", "implementation", "verification"]
            if direct:
                required_passed.remove("framing")
            incomplete = [stage_id for stage_id in required_passed if stages.get(stage_id, {}).get("status") != "PASSED"]
            if incomplete:
                result.add("RELEASE_PRECONDITION", "stages", f"release requires prior stages to pass: {incomplete}")
            inspection_ok, inspection_message, _ = passing_package_inspection(
                effective_root,
                run_dir / "50_release" / "package_inspection.json",
            )
            if not inspection_ok:
                result.add("PACKAGE_NOT_INSPECTED", "50_release/package_inspection.json", inspection_message)

    if not result.ok:
        return result

    updated = deepcopy(raw)
    updated_stages = _stage_map(updated)
    updated_gates = _gate_map(updated)
    if reopening:
        release_stage = updated_stages["release"]
        release_stage["status"] = "PENDING"
        release_gate = updated_gates.get(release_stage["gate_id"])
        if release_gate is not None:
            release_gate.update(status="PENDING", evidence_refs=[], rationale="Awaiting independent revalidation of the changed basis.")
    target = updated_stages[to_stage]
    target["status"] = stage_status
    gate_id = target["gate_id"]
    gate = updated_gates.get(gate_id)
    if gate is None:
        gate = {"id": gate_id, "status": "PENDING", "evidence_refs": [], "rationale": "Not yet evaluated."}
        updated["gates"].append(gate)
    gate["status"] = gate_status
    gate["evidence_refs"] = list(evidence_refs)
    gate["rationale"] = rationale
    updated["run"]["current_stage"] = to_stage
    updated["run"]["next_allowed_action"] = next_action
    if to_stage == "verification" and stage_status == "PASSED" and isinstance(updated.get("control"), dict):
        verification_entry = updated.get("active_artifacts", {}).get("verification_report")
        if isinstance(verification_entry, dict):
            verification_path = verification_entry.get("path")
            candidate_path = effective_root / verification_path if isinstance(verification_path, str) else None
            if candidate_path is not None and not candidate_path.exists():
                candidate_path = run_dir / verification_path
            if candidate_path is None or not candidate_path.is_file():
                result.add("VERIFICATION_IDENTITY", str(verification_path), "active verification report is missing")
                return result
            try:
                current_sha256 = sha256_file(candidate_path)
            except OSError as exc:
                result.add("VERIFICATION_IDENTITY", str(candidate_path), f"cannot hash active report: {exc}")
                return result
            recorded_sha256 = verification_entry.get("content_sha256")
            if current_sha256 != recorded_sha256:
                result.add(
                    "ACTIVE_ARTIFACT_HASH",
                    str(candidate_path),
                    "verification report changed before its validation identity could be captured",
                )
                return result
            updated["control"]["verification_validation_identity"] = {
                "artifact_id": verification_entry.get("artifact_id"),
                "version": verification_entry.get("version"),
                "path": verification_entry.get("path"),
                "content_sha256": recorded_sha256,
                "validated_at": effective_timestamp,
            }
            candidate_binding = _verified_candidate_binding(effective_root, run_dir, updated)
            if selected:
                if candidate_binding is None:
                    result.add("VERIFICATION_CANDIDATE", "control.verification_validation_identity", "selected PASSED requires a complete current inspected candidate")
                    return result
                audited = terminal_snapshot["candidate_binding"] if terminal_snapshot is not None else {}
                from .rounds import _project_path
                if any(
                    (_project_path(effective_root, run_dir, value) != _project_path(effective_root, run_dir, audited[key]) if key.endswith("_path") else value != audited.get(key))
                    for key, value in candidate_binding.items()
                ):
                    result.add("VERIFICATION_CANDIDATE", "control.latest_verification_result", "current PASS candidate differs from the verifier's audited inputs")
                    return result
            if candidate_binding is not None:
                updated["control"]["verification_validation_identity"]["candidate_binding"] = candidate_binding
    updated["artifact"]["version"] += 1
    updated["artifact"]["updated_at"] = effective_timestamp
    updated["active_artifacts"]["run_state"]["version"] = updated["artifact"]["version"]
    if advancing and to_stage == "repair":
        if selected:
            try:
                assert_unmodified_before_round(effective_root, run_dir, raw)
                reserve_round(updated, evidence_refs, failure_ref, effective_timestamp)
            except (InputError, OSError, ValueError, KeyError, TypeError) as exc:
                result.add("REPAIR_LIMIT" if raw["repair"]["active_attempt"] >= raw["repair"]["maximum_attempts"] else "ROUND_START", "repair", str(exc))
                return result
            updated_stages["verification"]["status"] = "IN_PROGRESS"
            updated_gates[updated_stages["verification"]["gate_id"]].update(status="IN_PROGRESS", evidence_refs=[], rationale="Awaiting the reserved round's fresh verification result.")
            updated_stages["release"]["status"] = "PENDING"
            release_id = updated_stages["release"]["gate_id"]
            if release_id not in updated_gates:
                updated_gates[release_id] = {"id": release_id}
                updated["gates"].append(updated_gates[release_id])
            updated_gates[release_id].update(status="PENDING", evidence_refs=[], rationale="Awaiting fresh verification after modification.")
        else:
            updated["repair"]["active_attempt"] += 1
        if isinstance(updated.get("control"), dict):
            updated["control"]["verification_validation_identity"] = None
        updated["repair"]["last_failure_ref"] = failure_ref
        if updated["repair"]["active_attempt"] > updated["repair"]["maximum_attempts"]:
            result.add("REPAIR_LIMIT", "repair.active_attempt", "repair attempt would exceed maximum_attempts")
            return result

    if terminal_snapshot is not None:
        try:
            complete_verification(updated, terminal_snapshot)
        except InputError as exc:
            result.add("ROUND_RESULT", "control.latest_verification_result", str(exc))
            return result

    if reopening and selected:
        try:
            assert_current_subject(effective_root, run_dir, raw, raw["control"]["latest_verification_result"])
        except (InputError, OSError, ValueError, KeyError, TypeError) as exc:
            result.add("RECOVERY_SUBJECT", "control.latest_verification_result", str(exc))
            return result

    updated_diagnostics = validate_run_state_context(effective_root, run_dir, updated)
    if updated_diagnostics:
        result.extend(updated_diagnostics)
        return result
    try:
        atomic_write_json(state_path, updated)
    except OSError as exc:
        result.add("STATE_WRITE", str(state_path), f"failed to write state atomically: {exc}")
        return result
    result.data = {
        "state_path": str(state_path),
        "from_stage": current_stage,
        "to_stage": to_stage,
        "stage_status": stage_status,
        "gate_status": gate_status,
        "artifact_version": updated["artifact"]["version"],
        "repair_attempt": updated["repair"]["active_attempt"],
    }
    return result
