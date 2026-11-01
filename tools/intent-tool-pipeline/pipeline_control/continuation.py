"""Independent process reviews and attributed, finite user continuation decisions.

Approval JSON is schema_version=1.0, artifact_type=iteration-continuation-approval,
run_id, user_role=user, response (the actual user quotation), decision=APPROVE,
timestamp (timezone aware), review_path, review_sha256, basis, additional_rounds,
proposed_changed_approach and intent_impact=UNCHANGED. Structured declarations
attribute the response in the trusted local model; they do not authenticate a
human or infer consent from prose. Review JSON uses the frozen D6 protocol.
"""

from __future__ import annotations

import base64
import json
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

from .io_utils import InputError, normalize_repository_reference, read_structured, repository_relative, sha256_bytes, sha256_file
from .result import Diagnostic
from .submissions import _run_input, assert_plain_path, collect_submission_inputs, submission_audit_id


BASIS_FIELDS = {"round_number", "source_report_ref", "source_report_sha256", "contract_ref", "contract_sha256", "maximum_attempts"}
CONTINUATION_FIELDS = {"review_path", "review_sha256", "review_invocation_ref", "boundary_evidence_ref", "approval_path", "approval_sha256", "additional_rounds", "new_maximum_attempts"}


def _positive(value: Any) -> bool:
    return type(value) is int and value > 0


def _hash(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(c in "0123456789abcdef" for c in value)


def _text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _timestamp(value: Any) -> datetime:
    if not isinstance(value, str):
        raise InputError("continuation timestamp must be a timezone-aware ISO 8601 string")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise InputError("continuation timestamp must be ISO 8601") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise InputError("continuation timestamp must include a timezone")
    return parsed


def _path(root: Path, raw: Any) -> Path:
    if not isinstance(raw, str) or normalize_repository_reference(raw) != raw:
        raise InputError("continuation reference must be an exact normalized project-relative path")
    path = root / raw
    assert_plain_path(root, path, require_file=True)
    return path


def _object(root: Path, raw: Any, digest: Any) -> tuple[Path, dict[str, Any]]:
    path = _path(root, raw)
    if not _hash(digest) or sha256_file(path) != digest:
        raise InputError("continuation evidence SHA-256 mismatch")
    data = read_structured(path)
    if not isinstance(data, dict):
        raise InputError("continuation evidence must contain an object")
    return path, data


def _snapshot_for_basis(state: dict[str, Any], basis: Any) -> dict[str, Any]:
    if not isinstance(basis, dict) or set(basis) != BASIS_FIELDS:
        raise InputError("threshold basis must contain the exact protocol fields")
    if not _positive(basis.get("round_number")) or not _positive(basis.get("maximum_attempts")):
        raise InputError("threshold basis round/maximum must be positive integers")
    if basis["round_number"] != basis["maximum_attempts"]:
        raise InputError("threshold basis must identify an exhausted allowance")
    rounds = state.get("repair", {}).get("rounds", [])
    matched = [r for r in rounds if isinstance(r, dict) and r.get("number") == basis["round_number"]]
    if len(matched) != 1 or matched[0].get("status") != "COMPLETED":
        raise InputError("threshold basis must identify a completed round")
    completed = matched[0].get("result_verification")
    if not isinstance(completed, dict):
        raise InputError("threshold basis lacks a terminal result")
    snapshots = [state.get("control", {}).get("latest_verification_result")]
    for record in rounds:
        if isinstance(record, dict):
            snapshots.extend(record.get(name) for name in ("source_verification", "result_verification"))
    known = [s for s in snapshots if isinstance(s, dict) and s.get("report_ref") == basis.get("source_report_ref")]
    snapshot = known[0] if known else completed
    if not known:
        registrations = state.get("control", {}).get("semantic_registrations", {})
        if not isinstance(registrations, dict):
            raise InputError("historical threshold source requires retained report registrations")
        retained = [r for r in registrations.values() if isinstance(r, dict) and r.get("artifact_key") == "verification_report"
                    and r.get("artifact_ref") == basis.get("source_report_ref") and r.get("content_sha256") == basis.get("source_report_sha256")]
        if len(retained) != 1:
            raise InputError("historical threshold source must identify one retained report registration")
    binding = snapshot.get("candidate_binding")
    if not isinstance(binding, dict):
        raise InputError("threshold review requires known contract/candidate identity")
    expected = {
        "contract_ref": binding.get("product_contract_ref"),
        "contract_sha256": binding.get("product_contract_sha256"),
    }
    if known:
        expected.update(source_report_ref=snapshot.get("report_ref"), source_report_sha256=snapshot.get("report_sha256"))
    if any(basis.get(key) != value for key, value in expected.items()):
        raise InputError("threshold basis does not match the completed terminal result")
    if not all(_text(basis.get(key)) for key in ("source_report_ref", "contract_ref")) or not all(
        _hash(basis.get(key)) for key in ("source_report_sha256", "contract_sha256")
    ):
        raise InputError("threshold basis identities are malformed")
    return snapshot


def threshold_basis(root: Path, run: Path, state: dict[str, Any]) -> dict[str, Any]:
    """Derive an exhausted result; reject an in-progress or unknown subject."""
    repair = state.get("repair", {})
    count, maximum = repair.get("active_attempt"), repair.get("maximum_attempts")
    rounds = repair.get("rounds", [])
    latest = state.get("control", {}).get("latest_verification_result")
    if not _positive(count) or count != maximum or not isinstance(rounds, list) or len(rounds) != count:
        raise InputError("threshold review requires an exhausted allowance")
    if any(not isinstance(r, dict) or r.get("status") != "COMPLETED" for r in rounds):
        raise InputError("threshold review cannot interrupt an in-progress round")
    if not isinstance(latest, dict):
        raise InputError("threshold review requires the exact latest terminal result")
    candidate = latest.get("candidate_binding")
    if not isinstance(candidate, dict):
        raise InputError("threshold review requires a known candidate")
    basis = {"round_number": count, "source_report_ref": latest.get("report_ref"),
             "source_report_sha256": latest.get("report_sha256"),
             "contract_ref": candidate.get("product_contract_ref"),
             "contract_sha256": candidate.get("product_contract_sha256"), "maximum_attempts": maximum}
    _snapshot_for_basis(state, basis)
    from .rounds import assert_current_subject, validate_threshold_lineage

    validate_threshold_lineage(root, run, state, latest, rounds[-1]["result_verification"])
    assert_current_subject(root, run, state, latest)
    return basis


def _check_event(state: dict[str, Any], event: dict[str, Any]) -> dict[str, Any]:
    if event.get("classification") != "REPAIR_LIMIT_EXHAUSTED":
        raise InputError("process review requires a repair-limit event")
    snapshot = _snapshot_for_basis(state, event.get("round_review_basis"))
    origin = event.get("origin", {})
    expected = {"role": "independent_verifier", "result_artifact_ref": event["round_review_basis"]["source_report_ref"]}
    if snapshot.get("report_ref") == event["round_review_basis"]["source_report_ref"]:
        expected.update(invocation_ref=snapshot.get("source_invocation_ref"), result=snapshot.get("stage_status"))
    else:
        registrations = state.get("control", {}).get("semantic_registrations", {})
        receipt = next(r for r in registrations.values() if isinstance(r, dict)
                       and r.get("artifact_key") == "verification_report" and r.get("artifact_ref") == expected["result_artifact_ref"]
                       and r.get("content_sha256") == event["round_review_basis"]["source_report_sha256"])
        expected["invocation_ref"] = receipt.get("source_invocation_ref")
    if not isinstance(origin, dict) or not _text(origin.get("invocation_ref")) or origin.get("result") not in {"PASSED", "FAILED", "BLOCKED"} or any(origin.get(k) != v for k, v in expected.items()):
        raise InputError("threshold event origin does not identify its terminal result")
    return snapshot


def create_review_assignment(root: Path, run: Path, state: dict[str, Any], *, role: str,
                             invocation_ref: str, event_id: str,
                             input_refs: Iterable[str | Path] = ()) -> dict[str, Any]:
    if role != "independent_verifier":
        raise InputError("threshold process reviewer must be independent_verifier")
    events = [e for e in state.get("bounce_back_events", []) if isinstance(e, dict) and e.get("id") == event_id]
    if len(events) != 1 or events[0].get("status") != "OPEN":
        raise InputError("threshold review requires one OPEN event")
    event = events[0]
    snapshot = _check_event(state, event)
    basis = threshold_basis(root, run, state)
    if event.get("round_review_basis") != basis:
        raise InputError("threshold event basis is stale")
    if invocation_ref == snapshot.get("source_invocation_ref"):
        raise InputError("process review must use a separate invocation")
    inputs = collect_submission_inputs(root, run, state, "verification_report", input_refs)
    latest_report = _run_input(root, run, snapshot["report_path"])
    assert_plain_path(root, latest_report, require_file=True)
    if sha256_file(latest_report) != snapshot.get("report_sha256"):
        raise InputError("latest review report no longer matches its result identity")
    extra = [repository_relative(root, latest_report), snapshot.get("boundary_evidence_ref")]
    # Retain references to the actual round results, rather than reconstructed bodies.
    for record in state["repair"]["rounds"]:
        for name in ("source_verification", "result_verification"):
            result = record.get(name)
            if isinstance(result, dict):
                report = _run_input(root, run, result["report_path"])
                if result.get("report_ref") != snapshot.get("report_ref"):
                    version = result["report_ref"].rsplit("@", 1)[1]
                    report = report.parent / "history" / f"{report.stem}.v{version}{report.suffix}"
                assert_plain_path(root, report, require_file=True)
                if sha256_file(report) != result.get("report_sha256"):
                    raise InputError("retained round report no longer matches its result identity")
                extra.extend([repository_relative(root, report), result.get("boundary_evidence_ref")])
    by_path = {item["path"]: item for item in inputs}
    for raw in extra:
        if raw is None:
            continue
        path = _path(root, raw)
        by_path[raw] = {"path": raw, "availability": "PRESENT", "content_sha256": sha256_file(path)}
    return {"event_id": event_id, "basis": deepcopy(basis),
            "path": f"40_verification/probes/{submission_audit_id(role, invocation_ref)}/round-review.json",
            "inputs": [by_path[key] for key in sorted(by_path)]}


def _current_inputs(root: Path, run: Path, state: dict[str, Any], assignment: dict[str, Any], invocation: str) -> None:
    recorded = assignment.get("inputs")
    if not isinstance(recorded, list):
        raise InputError("process review input binding is malformed")
    for item in recorded:
        if not isinstance(item, dict) or not isinstance(item.get("path"), str):
            raise InputError("process review input binding is malformed")
        path = root / normalize_repository_reference(item["path"])
        assert_plain_path(root, path)
        if item.get("availability") == "MISSING":
            if path.exists() or "content_sha256" in item:
                raise InputError("process review missing input appeared")
        elif item.get("availability") != "PRESENT" or not path.is_file() or sha256_file(path) != item.get("content_sha256"):
            raise InputError("process review input changed")
    current = deepcopy(state)
    for event in current.get("bounce_back_events", []):
        if isinstance(event, dict) and event.get("id") == assignment["event_id"]:
            event["status"] = "OPEN"
    fresh = create_review_assignment(root, run, current, role="independent_verifier", invocation_ref=invocation,
                                     event_id=assignment["event_id"])
    by_path = {i["path"]: i for i in recorded}
    if any(by_path.get(i["path"]) != i for i in fresh["inputs"]):
        raise InputError("process review mandatory inputs changed")


def prepare_continuation(root: Path, run: Path, state: dict[str, Any], event: dict[str, Any],
                         resolution: dict[str, Any], *, historical: bool = False) -> dict[str, Any]:
    """Validate a complete decision before the existing state transaction commits."""
    continuation = resolution.get("continuation")
    if not isinstance(continuation, dict) or set(continuation) != CONTINUATION_FIELDS:
        raise InputError("continuation must contain the exact protocol fields")
    snapshot = _check_event(state, event)
    basis = event["round_review_basis"]
    if not historical and threshold_basis(root, run, state) != basis:
        raise InputError("continuation threshold basis is stale")
    if resolution.get("resolution_type") != "USER_DECIDED" or resolution.get("resolved_by") != "user":
        raise InputError("continuation requires an attributed USER_DECIDED resolution by user")
    allowance = continuation.get("additional_rounds")
    if not _positive(allowance) or continuation.get("new_maximum_attempts") != basis["maximum_attempts"] + allowance:
        raise InputError("continuation requires a positive finite allowance and exact new ceiling")
    invocation = continuation.get("review_invocation_ref")
    if not _text(invocation) or invocation == snapshot.get("source_invocation_ref"):
        raise InputError("process review invocation must be distinct from product verification")
    audit_id = submission_audit_id("independent_verifier", invocation)
    review_path = run / f"40_verification/probes/{audit_id}/round-review.json"
    if continuation["review_path"] != repository_relative(root, review_path):
        raise InputError("continuation review path is not the exact assigned file")
    _, review = _object(root, continuation["review_path"], continuation["review_sha256"])
    expected = {"schema_version": "1.0", "artifact_type": "iteration-threshold-review",
                "run_id": state.get("run", {}).get("run_id"), "reviewer_role": "independent_verifier",
                "reviewer_invocation_ref": invocation, "basis": basis, "recommendation": "BOUNDED_CONTINUATION",
                "additional_rounds": allowance, "intent_impact": "UNCHANGED"}
    if any(review.get(k) != v for k, v in expected.items()):
        raise InputError("review ownership, basis, recommendation, allowance or intent impact is invalid")
    for name in ("unresolved_issues", "observed_progress", "likely_causes", "evidence_refs"):
        if not isinstance(review.get(name), list) or not all(_text(i) for i in review[name]):
            raise InputError(f"review {name} must be a list of attributed strings")
    if not review["evidence_refs"] or not _text(review.get("proposed_changed_approach")):
        raise InputError("review requires evidence and a proposed changed approach")
    evidence_path = run / f"30_execution/role_boundary/results/{audit_id}.json"
    if continuation["boundary_evidence_ref"] != repository_relative(root, evidence_path):
        raise InputError("continuation boundary evidence path is not canonical")
    evidence = read_structured(_path(root, continuation["boundary_evidence_ref"]))
    if not isinstance(evidence, dict) or any(evidence.get(k) != v for k, v in {
        "schema_version": "1.0", "artifact_type": "role-boundary-result", "audit_id": audit_id, "role": "independent_verifier",
        "invocation_ref": invocation, "status": "PASS",
    }.items()):
        raise InputError("continuation requires matching retained boundary PASS")
    baseline_path = run / f"30_execution/role_boundary/baselines/{audit_id}.json"
    if evidence.get("baseline_path") != repository_relative(root, baseline_path):
        raise InputError("process-review baseline path mismatch")
    _, baseline = _object(root, evidence["baseline_path"], evidence.get("baseline_sha256"))
    assignment = baseline.get("round_review")
    if not isinstance(assignment, dict) or any(assignment.get(k) != v for k, v in {
        "event_id": event.get("id"), "basis": basis, "path": review_path.relative_to(run).as_posix(),
    }.items()) or "submission" in baseline:
        raise InputError("process-review assignment mismatch")
    if any(baseline.get(k) != v for k, v in {
        "schema_version": "1.0", "artifact_type": "role-boundary-baseline",
        "control_revision": state.get("control", {}).get("semantic_role_boundary"), "audit_id": audit_id, "role": "independent_verifier",
        "invocation_ref": invocation, "run_dir": repository_relative(root, run),
    }.items()):
        raise InputError("process-review baseline owner/run mismatch")
    if baseline.get("control_revision") == "1.2":
        from .procedures import _original_state, result_binding, validate_procedure_binding, validate_result_binding

        validate_procedure_binding(root, run, _original_state(baseline), baseline, current=not historical)
        validate_result_binding(review_path.read_bytes(), review_path, result_binding(baseline, evidence["baseline_sha256"]))
    from .boundary import BoundaryPolicy

    if baseline.get("path_policy") != BoundaryPolicy(allowed_durable_files=(assignment["path"],)).as_dict():
        raise InputError("process-review boundary granted more than its exact file")
    inputs = assignment.get("inputs")
    if not isinstance(inputs, list) or not inputs:
        raise InputError("process-review assignment lacks input identities")
    seen_inputs = set()
    for item in inputs:
        if not isinstance(item, dict) or not isinstance(item.get("path"), str) or normalize_repository_reference(item["path"]) != item["path"] or item["path"] in seen_inputs:
            raise InputError("process-review input identity is malformed or duplicated")
        seen_inputs.add(item["path"])
        if item.get("availability") == "PRESENT":
            if not _hash(item.get("content_sha256")):
                raise InputError("present process-review input needs a valid digest")
        elif item.get("availability") != "MISSING" or "content_sha256" in item:
            raise InputError("missing process-review input must explicitly lack a digest")
    mutations = evidence.get("allowed_mutations")
    if not isinstance(mutations, list) or not any(
        isinstance(m, dict) and m.get("path") == assignment["path"]
        and isinstance(m.get("after"), dict) and m["after"].get("sha256") == continuation["review_sha256"]
        for m in mutations
    ) or evidence.get("unauthorized_mutations") != []:
        raise InputError("review bytes do not match the completed boundary audit")
    # Authenticate original state provenance without comparing its version to today.
    try:
        backup = base64.b64decode(baseline.get("run_state_backup_base64", ""), validate=True)
        if sha256_bytes(backup) != baseline.get("run_state_sha256"):
            raise ValueError("backup digest mismatch")
        prior = json.loads(backup)
        prior_events = prior.get("bounce_back_events", [])
        if not any(e.get("id") == event.get("id") and e.get("status") == "OPEN" and e.get("round_review_basis") == basis
                   for e in prior_events if isinstance(e, dict)):
            raise ValueError("event mismatch")
        prior_snapshot = _check_event(prior, event)
        if prior_snapshot.get("report_ref") != basis["source_report_ref"] or invocation == prior_snapshot.get("source_invocation_ref"):
            raise ValueError("review source result/invocation mismatch")
        from .rounds import validate_threshold_lineage

        validate_threshold_lineage(root, run, prior, prior_snapshot, prior["repair"]["rounds"][basis["round_number"] - 1]["result_verification"])
    except (ValueError, TypeError, AttributeError) as exc:
        raise InputError("process-review original state provenance is invalid") from exc
    if not historical:
        from .boundary import validate_boundary_pass

        ok, reason = validate_boundary_pass(root, run, role="independent_verifier", invocation_ref=invocation,
                                           evidence_ref=continuation["boundary_evidence_ref"])
        if not ok:
            raise InputError(reason)
        _current_inputs(root, run, state, assignment, invocation)
    _, approval = _object(root, continuation["approval_path"], continuation["approval_sha256"])
    expected_approval = {"schema_version": "1.0", "artifact_type": "iteration-continuation-approval",
                         "run_id": state.get("run", {}).get("run_id"), "user_role": "user", "decision": "APPROVE",
                         "review_path": continuation["review_path"], "review_sha256": continuation["review_sha256"],
                         "basis": basis, "additional_rounds": allowance,
                         "proposed_changed_approach": review["proposed_changed_approach"], "intent_impact": "UNCHANGED"}
    if any(approval.get(k) != v for k, v in expected_approval.items()) or not _text(approval.get("response")):
        raise InputError("approval must retain the actual user response and approve the exact review, allowance and approach")
    approved_at = _timestamp(approval.get("timestamp"))
    if approved_at < _timestamp(evidence.get("completed_at")) or approved_at > _timestamp(resolution.get("resolved_at")):
        raise InputError("approval must follow completed review and precede resolution")
    if continuation["approval_path"] not in resolution.get("decision_refs", []) or not all(
        ref in resolution.get("evidence_refs", []) for ref in (continuation["review_path"], continuation["boundary_evidence_ref"])
    ):
        raise InputError("resolution must cite the exact decision and review evidence")
    if event.get("retry", {}).get("allowed") is not True or "DECISION_CHANGED" not in event.get("retry", {}).get("change_basis", []):
        # State's resolve hook receives the proposed retry separately in some
        # callers; require it be installed on the copied event before admission.
        raise InputError("continuation requires an allowed retry with DECISION_CHANGED basis")
    return deepcopy(continuation)


def validate_continuation_metadata(state: dict[str, Any]) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    control, repair, events = (state.get(key) for key in ("control", "repair", "bounce_back_events"))
    if isinstance(control, dict) and control.get("semantic_role_boundary") in ("1.1", "1.2") and not isinstance(events, list):
        return [Diagnostic("CONTINUATION_METADATA", "bounce_back_events", "selected ceiling requires an explicit event ledger")]
    if not isinstance(control, dict) or not isinstance(repair, dict) or not isinstance(events, list):
        return diagnostics  # The existing outer-section validators own these errors.
    selected = control.get("semantic_role_boundary") in ("1.1", "1.2")
    ceiling = 4
    seen: set[int] = set()
    for index, event in enumerate(events):
        if not isinstance(event, dict):
            continue
        resolution = event.get("resolution")
        continuation = resolution.get("continuation") if isinstance(resolution, dict) else None
        has_continuation = isinstance(resolution, dict) and "continuation" in resolution
        has_basis = "round_review_basis" in event
        if not selected:
            if has_basis or has_continuation:
                diagnostics.append(Diagnostic("CONTINUATION_CONTROL", f"bounce_back_events[{index}]", "selected continuation metadata requires control revision 1.1"))
            continue
        threshold = event.get("classification") == "REPAIR_LIMIT_EXHAUSTED"
        try:
            if threshold:
                _check_event(state, event)
                retry = event.get("retry")
                if isinstance(retry, dict) and retry.get("allowed") is True and not has_continuation:
                    raise InputError("threshold retry requires explicit continuation authorization")
            elif has_basis or has_continuation:
                raise InputError("continuation metadata requires a threshold event")
            if has_continuation:
                if event.get("status") != "RESOLVED" or not isinstance(continuation, dict) or set(continuation) != CONTINUATION_FIELDS:
                    raise InputError("continuation requires a resolved event and exact fields")
                basis = event["round_review_basis"]
                allowance = continuation.get("additional_rounds")
                if not _positive(allowance) or basis["maximum_attempts"] != ceiling or basis["round_number"] in seen:
                    raise InputError("continuation increments must be unique, finite and sequential")
                if resolution.get("resolved_by") != "user" or resolution.get("resolution_type") != "USER_DECIDED":
                    raise InputError("continuation requires an attributed user decision")
                ceiling += allowance
                seen.add(basis["round_number"])
                if type(continuation.get("new_maximum_attempts")) is not int or continuation["new_maximum_attempts"] != ceiling:
                    raise InputError("continuation new maximum does not match approved increments")
                for name in ("review_path", "approval_path", "boundary_evidence_ref", "review_invocation_ref"):
                    if not _text(continuation.get(name)):
                        raise InputError("continuation references must be nonempty strings")
                if not all(_hash(continuation.get(n)) for n in ("review_sha256", "approval_sha256")):
                    raise InputError("continuation evidence digests are malformed")
        except (InputError, KeyError, TypeError, ValueError) as exc:
            diagnostics.append(Diagnostic("CONTINUATION_METADATA", f"bounce_back_events[{index}]", str(exc)))
    if selected and (type(repair.get("maximum_attempts")) is not int or repair.get("maximum_attempts") != ceiling):
        diagnostics.append(Diagnostic("CONTINUATION_CEILING", "repair.maximum_attempts", "must equal four plus all valid resolved continuation increments"))
    return diagnostics


def validate_continuation_history(root: Path, run: Path, state: dict[str, Any]) -> list[Diagnostic]:
    if state.get("control", {}).get("semantic_role_boundary") not in ("1.1", "1.2"):
        return []
    diagnostics = validate_continuation_metadata(state)
    if diagnostics:
        return diagnostics
    for index, event in enumerate(state.get("bounce_back_events", [])):
        resolution = event.get("resolution") if isinstance(event, dict) else None
        if not isinstance(resolution, dict) or "continuation" not in resolution:
            continue
        try:
            prepare_continuation(root, run, state, event, resolution, historical=True)
        except (InputError, OSError, ValueError, TypeError, KeyError) as exc:
            diagnostics.append(Diagnostic("CONTINUATION_EVIDENCE", f"bounce_back_events[{index}]", str(exc)))
    return diagnostics
