"""Selected-policy threshold review and finite, attributed user decisions."""

from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import zipfile

import pytest

from pipeline_control.cli import build_parser
from pipeline_control.continuation import (
    threshold_basis, validate_continuation_metadata, prepare_continuation, validate_continuation_history,
)
from pipeline_control.boundary import start_role_boundary, finish_role_boundary
from pipeline_control.io_utils import InputError, sha256_file, atomic_write_json
from test_agent_rounds import completed_rounds, load, request_change, one_round, transition, report, resolve
from pipeline_control.state import update_bounce_back
from pipeline_control.rounds import capture_verification_result


NOW = "2026-10-30T00:00:00+00:00"


def subject(root: Path) -> tuple[Path, dict]:
    """An actual immutable archive with live source and completed round ledger.

    This fixture tests D6 eligibility/ceiling helpers, rather than bypassing
    product admission or claiming a product-verification lifecycle.
    """
    run = root / "r"
    (run / "20_contract").mkdir(parents=True)
    (run / "50_release").mkdir()
    (root / "src").mkdir()
    source = root / "src/a.py"
    source.write_text("print('original subject')\n", encoding="utf-8")
    contract = run / "20_contract/product_contract.yaml"
    contract.write_text("contract identity\n", encoding="utf-8")
    archive = root / "a.zip"
    with zipfile.ZipFile(archive, "w") as zipped:
        zipped.write(source, "tool/a.py")
    manifest = run / "50_release/release_manifest.json"
    manifest.write_text(json.dumps({"source_root": "src", "artifact_root": "tool", "archive_path": "a.zip",
                                    "archive_sha256": sha256_file(archive), "entries": [
                                        {"path": "tool/a.py", "sha256": sha256_file(source), "size_bytes": source.stat().st_size}]}))
    binding = {"product_contract_ref": "product-contract@1", "product_contract_path": "r/20_contract/product_contract.yaml",
               "product_contract_sha256": sha256_file(contract), "manifest_path": "r/50_release/release_manifest.json",
               "manifest_sha256": sha256_file(manifest), "inspection_path": None, "inspection_sha256": None,
               "archive_path": "a.zip", "archive_sha256": sha256_file(archive)}
    def result(number):
        return {"report_ref": f"verification-report@{number}", "report_sha256": str(number) * 64,
                "report_path": f"r/report{number}.md", "source_invocation_ref": f"v{number}",
                "boundary_evidence_ref": f"r/boundary{number}.json", "stage_status": "FAILED", "recorded_at": NOW,
                "candidate_binding": deepcopy(binding), "harness_attempt": None}
    rounds = [{"number": i, "started_at": NOW, "request_refs": [f"BB-{i:03d}"], "source_verification": result(i),
               "status": "COMPLETED", "result_verification": result(i + 1)} for i in range(1, 5)]
    state = {"control": {"semantic_role_boundary": "1.1", "latest_verification_result": result(5)},
             "repair": {"active_attempt": 4, "maximum_attempts": 4, "rounds": rounds},
             "active_artifacts": {"product_contract": {"artifact_id": "product-contract", "version": 1,
                                                       "path": binding["product_contract_path"], "content_sha256": sha256_file(contract)}},
             "bounce_back_events": []}
    return run, state


def event_for(root: Path, run: Path, state: dict) -> dict:
    latest = state["control"]["latest_verification_result"]
    return {"id": "BB-005", "classification": "REPAIR_LIMIT_EXHAUSTED", "status": "OPEN",
            "origin": {"role": "independent_verifier", "invocation_ref": latest["source_invocation_ref"],
                       "result_artifact_ref": latest["report_ref"], "result": "FAILED"},
            "round_review_basis": threshold_basis(root, run, state), "resolution": None}


def test_threshold_requires_exact_latest_completed_result_and_known_subject(tmp_path: Path) -> None:
    run, state = subject(tmp_path)
    basis = threshold_basis(tmp_path, run, state)
    assert basis["round_number"] == basis["maximum_attempts"] == 4
    assert basis["source_report_ref"] == "verification-report@5"
    for mutation in ("in_progress", "stale_result", "unknown_archive", "not_exhausted"):
        changed = deepcopy(state)
        if mutation == "in_progress":
            changed["repair"]["rounds"][-1]["status"] = "IN_PROGRESS"
        elif mutation == "stale_result":
            changed["control"]["latest_verification_result"]["report_sha256"] = "a" * 64
        elif mutation == "unknown_archive":
            changed["control"]["latest_verification_result"]["candidate_binding"]["archive_sha256"] = None
            changed["repair"]["rounds"][-1]["result_verification"] = deepcopy(changed["control"]["latest_verification_result"])
        else:
            changed["repair"]["active_attempt"] = 3
        with pytest.raises(InputError):
            threshold_basis(tmp_path, run, changed)


@pytest.mark.parametrize("member", ["source", "contract", "archive", "manifest"])
def test_threshold_detects_subject_drift_before_any_new_round(tmp_path: Path, member: str) -> None:
    run, state = subject(tmp_path)
    path = {"source": tmp_path / "src/a.py", "contract": run / "20_contract/product_contract.yaml",
            "archive": tmp_path / "a.zip", "manifest": run / "50_release/release_manifest.json"}[member]
    path.write_bytes(b"changed subject")
    with pytest.raises((InputError, OSError)):
        threshold_basis(tmp_path, run, state)


def test_review_and_artifact_cli_modes_are_mutually_exclusive() -> None:
    parser = build_parser()
    with pytest.raises(SystemExit):
        parser.parse_args(["role-boundary", "start", "--run-dir", "r", "--role", "independent_verifier",
                           "--invocation-ref", "v", "--artifact", "verification_report", "--review-event", "BB-001"])


@pytest.mark.parametrize("value", [None, [], True, {}, "4", 5])
def test_ceiling_cannot_be_raised_without_valid_increments(tmp_path: Path, value) -> None:
    _, state = subject(tmp_path)
    state["repair"]["maximum_attempts"] = value
    assert validate_continuation_metadata(state)


@pytest.mark.parametrize("outer", ["control", "repair", "bounce_back_events"])
@pytest.mark.parametrize("value", [None, [], "bad"])
def test_malformed_outer_sections_remain_owned_by_existing_validator(outer, value) -> None:
    state = {"control": {}, "repair": {}, "bounce_back_events": []}
    state[outer] = value
    assert validate_continuation_metadata(state) == []


def test_legacy_and_nonthreshold_continuation_metadata_rejects(tmp_path: Path) -> None:
    run, state = subject(tmp_path)
    event = event_for(tmp_path, run, state)
    state["bounce_back_events"] = [event]
    assert validate_continuation_metadata(state) == []
    state["control"]["semantic_role_boundary"] = "1.0"
    assert validate_continuation_metadata(state)
    state["control"]["semantic_role_boundary"] = "1.1"
    event["classification"] = "IMPLEMENTATION_DEFECT"
    assert validate_continuation_metadata(state)


def review_fixture(root: Path, *, review_change=None, unauthorized=False, run=None, allowance=2, invocation="process1"):
    run = run or completed_rounds(root)
    event_id = request_change(root, run, classification="REPAIR_LIMIT_EXHAUSTED")
    state = load(run)
    latest = state["control"]["latest_verification_result"]
    event = next(e for e in state["bounce_back_events"] if e["id"] == event_id)
    started = start_role_boundary(root, run, role="independent_verifier", invocation_ref=invocation,
                                 review_event_id=event["id"], timestamp=NOW)
    assert started.ok, started.as_dict()
    review = {"schema_version": "1.0", "artifact_type": "iteration-threshold-review", "run_id": state["run"]["run_id"],
              "reviewer_role": "independent_verifier", "reviewer_invocation_ref": invocation, "basis": event["round_review_basis"],
              "recommendation": "BOUNDED_CONTINUATION", "additional_rounds": allowance, "unresolved_issues": ["A defect remains."],
              "observed_progress": ["Four attributable revisions are retained."], "likely_causes": ["The algorithm needs a narrower diagnostic."],
              "proposed_changed_approach": "Reproduce the remaining defect with a reduced input before editing.",
              "intent_impact": "UNCHANGED", "evidence_refs": [latest["report_ref"]]}
    if review_change:
        review.update(review_change)
    path = root / started.data["review_path"]
    atomic_write_json(path, review)
    if unauthorized:
        path.with_name("extra.json").write_text("{}")
    finished = finish_role_boundary(root, run, role="independent_verifier", invocation_ref=invocation,
                                    baseline_sha256=started.data["baseline_sha256"], timestamp=NOW)
    if not unauthorized:
        assert finished.ok, finished.as_dict()
    approval = {"schema_version": "1.0", "artifact_type": "iteration-continuation-approval", "run_id": state["run"]["run_id"],
                "user_role": "user", "response": f"I approve {allowance} additional rounds using the reduced-input diagnostic approach.",
                "decision": "APPROVE", "timestamp": NOW, "review_path": started.data["review_path"], "review_sha256": sha256_file(path),
                "basis": event["round_review_basis"], "additional_rounds": allowance,
                "proposed_changed_approach": review["proposed_changed_approach"], "intent_impact": "UNCHANGED"}
    approval_path = root / f"{invocation}-approval.json"
    atomic_write_json(approval_path, approval)
    continuation = {"review_path": started.data["review_path"], "review_sha256": sha256_file(path),
                    "review_invocation_ref": invocation, "boundary_evidence_ref": finished.data["evidence_ref"],
                    "approval_path": approval_path.relative_to(root).as_posix(), "approval_sha256": sha256_file(approval_path),
                    "additional_rounds": allowance, "new_maximum_attempts": state["repair"]["maximum_attempts"] + allowance}
    resolution = {"resolved_at": NOW, "resolved_by": "user", "resolution_type": "USER_DECIDED",
                  "summary": "The user approved the reviewed finite allowance and approach.", "changed_artifact_refs": [],
                  "decision_refs": [continuation["approval_path"]], "evidence_refs": [continuation["review_path"], continuation["boundary_evidence_ref"]],
                  "continuation": continuation}
    proposed = deepcopy(event)
    proposed["retry"].update(allowed=True, change_basis=["DECISION_CHANGED"])
    return run, proposed, resolution, started, finished


def test_independent_review_has_one_exact_durable_file_and_no_product_assignment(tmp_path: Path) -> None:
    run, event, resolution, started, _ = review_fixture(tmp_path)
    policy = started.data["path_policy"]
    assert policy["allowed_durable_roots"] == policy["allowed_ephemeral_roots"] == []
    assert len(policy["allowed_durable_files"]) == 1
    assert "submission" not in started.data and "submission_path" not in started.data
    before = (run / "30_execution/run_state.json").read_bytes()
    admitted = prepare_continuation(tmp_path, run, load(run), event, resolution)
    assert admitted["additional_rounds"] == 2 and admitted["new_maximum_attempts"] == 6
    assert (run / "30_execution/run_state.json").read_bytes() == before
    assert len(load(run)["control"]["semantic_registrations"]) == 7  # Brief, contract, five product reports.


def test_review_sibling_write_cannot_support_continuation(tmp_path: Path) -> None:
    run, event, resolution, _, finished = review_fixture(tmp_path, unauthorized=True)
    assert not finished.ok
    with pytest.raises(InputError, match="PASS"):
        prepare_continuation(tmp_path, run, load(run), event, resolution)


@pytest.mark.parametrize("change", [
    {"recommendation": "STOP"}, {"recommendation": "REQUEST_USER_DECISION"}, {"additional_rounds": True},
    {"additional_rounds": 0}, {"reviewer_role": "root_codex"}, {"intent_impact": "CHANGED"}, {"basis": {}},
])
def test_nonbounded_wrong_owner_changed_intent_or_wrong_basis_review_rejects(tmp_path: Path, change) -> None:
    run, event, resolution, _, _ = review_fixture(tmp_path, review_change=change)
    with pytest.raises(InputError):
        prepare_continuation(tmp_path, run, load(run), event, resolution)


@pytest.mark.parametrize("change", [
    {"response": ""}, {"user_role": "root_codex"}, {"decision": "DENY"}, {"additional_rounds": 3},
    {"proposed_changed_approach": "An unrelated approach"}, {"intent_impact": "CHANGED"}, {"basis": {}},
    {"timestamp": "2026-10-30T00:00:00"}, {"timestamp": "2026-01-01T00:00:00+00:00"},
])
def test_approval_must_quote_the_user_and_bind_exact_finite_allowance_approach_and_basis(tmp_path: Path, change) -> None:
    run, event, resolution, _, _ = review_fixture(tmp_path)
    path = tmp_path / resolution["continuation"]["approval_path"]
    approval = json.loads(path.read_bytes())
    approval.update(change)
    atomic_write_json(path, approval)
    resolution["continuation"]["approval_sha256"] = sha256_file(path)
    with pytest.raises(InputError):
        prepare_continuation(tmp_path, run, load(run), event, resolution)


@pytest.mark.parametrize("drift", ["source", "contract", "archive", "review", "approval", "input", "baseline", "boundary"])
def test_changed_subject_or_retained_evidence_rejects_approval(tmp_path: Path, drift: str) -> None:
    run, event, resolution, started, _ = review_fixture(tmp_path)
    path = {"source": tmp_path / "source/main.py", "contract": run / "20_contract/product_contract.yaml",
            "archive": tmp_path / "deliverables/fixture.zip", "review": tmp_path / resolution["continuation"]["review_path"],
            "approval": tmp_path / resolution["continuation"]["approval_path"], "input": run / "00_intake/build_request.yaml",
            "baseline": tmp_path / started.data["baseline_path"],
            "boundary": tmp_path / resolution["continuation"]["boundary_evidence_ref"]}[drift]
    path.write_bytes(path.read_bytes() + b"changed")
    with pytest.raises((InputError, OSError)):
        prepare_continuation(tmp_path, run, load(run), event, resolution)


def test_historical_authorization_survives_later_subject_revision(tmp_path: Path) -> None:
    run, event, resolution, _, _ = review_fixture(tmp_path)
    state = load(run)
    assert prepare_continuation(tmp_path, run, state, event, resolution)
    event.update(status="RESOLVED", resolution=resolution)
    state["bounce_back_events"][-1] = event
    state["repair"]["maximum_attempts"] = 6
    (tmp_path / "source/main.py").write_text("legitimate next round source")
    (tmp_path / "deliverables/fixture.zip").write_bytes(b"legitimate next round archive")
    assert not validate_continuation_history(tmp_path, run, state)
    assert prepare_continuation(tmp_path, run, state, event, resolution, historical=True)
    with pytest.raises(InputError):
        prepare_continuation(tmp_path, run, state, event, resolution)


def resolve_payload(event: dict, resolution: dict) -> dict:
    payload = deepcopy(resolution)
    payload.pop("resolved_at")
    payload["event_id"] = event["id"]
    payload["retry"] = {"allowed": True, "change_basis": ["DECISION_CHANGED"]}
    return payload


def test_command_approval_replay_resume_and_second_exhaustion_preserve_lifetime_history(tmp_path: Path) -> None:
    run, event, resolution, _, _ = review_fixture(tmp_path)
    payload = resolve_payload(event, resolution)
    result = update_bounce_back(run, project_root=tmp_path, action="resolve", payload=payload, timestamp=NOW)
    assert result.ok, result.as_dict()
    original_rounds = deepcopy(load(run)["repair"]["rounds"])
    assert load(run)["repair"]["maximum_attempts"] == 6
    before = (run / "30_execution/run_state.json").read_bytes()
    replay = update_bounce_back(run, project_root=tmp_path, action="resolve", payload=payload, timestamp="2026-10-31T00:00:00+00:00")
    assert replay.ok and replay.data["replayed"], replay.as_dict()
    assert (run / "30_execution/run_state.json").read_bytes() == before
    conflicting = deepcopy(payload)
    conflicting["continuation"]["additional_rounds"] = 3
    rejected = update_bounce_back(run, project_root=tmp_path, action="resolve", payload=conflicting, timestamp=NOW)
    assert not rejected.ok
    assert (run / "30_execution/run_state.json").read_bytes() == before
    one_round(tmp_path, run, index=5)
    one_round(tmp_path, run, index=6)
    assert load(run)["repair"]["rounds"][:4] == original_rounds
    # A second allowance requires a new independent review and exact user response.
    _, event2, resolution2, _, _ = review_fixture(tmp_path, run=run, allowance=1, invocation="process2")
    result2 = update_bounce_back(run, project_root=tmp_path, action="resolve", payload=resolve_payload(event2, resolution2), timestamp=NOW)
    assert result2.ok, result2.as_dict()
    state = load(run)
    assert state["repair"]["active_attempt"] == 6 and state["repair"]["maximum_attempts"] == 7
    assert not validate_continuation_history(tmp_path, run, state)
    # Earlier authorization remains recoverable after both subject and allowance advance.
    older = update_bounce_back(run, project_root=tmp_path, action="resolve", payload=payload, timestamp=NOW)
    assert older.ok and older.data["replayed"], older.as_dict()
    one_round(tmp_path, run, index=7)
    next_event = request_change(tmp_path, run)
    stopped = transition(tmp_path, run, "repair", refs=[next_event], source="verification-report@8")
    assert not stopped.ok and load(run)["repair"]["active_attempt"] == 7


def test_public_threshold_resolution_missing_or_wrong_user_authority_is_atomic(tmp_path: Path) -> None:
    run, event, resolution, _, _ = review_fixture(tmp_path)
    payload = resolve_payload(event, resolution)
    before = (run / "30_execution/run_state.json").read_bytes()
    missing = deepcopy(payload)
    missing.pop("continuation")
    wrong_user = deepcopy(payload)
    wrong_user["resolved_by"] = "root_codex"
    wrong_kind = deepcopy(payload)
    wrong_kind["resolution_type"] = "ROOT_ANSWERED"
    wrong_basis = deepcopy(payload)
    wrong_basis["retry"]["change_basis"] = ["EVIDENCE_CHANGED"]
    for invalid in (missing, wrong_user, wrong_kind, wrong_basis):
        rejected = update_bounce_back(run, project_root=tmp_path, action="resolve", payload=invalid, timestamp=NOW)
        assert not rejected.ok, rejected.as_dict()
        assert (run / "30_execution/run_state.json").read_bytes() == before


def test_threshold_review_after_fourth_evidence_recovery_binds_latest_without_rewriting_round(tmp_path: Path) -> None:
    run = completed_rounds(tmp_path)
    original = deepcopy(load(run)["repair"]["rounds"][-1]["result_verification"])
    event = request_change(tmp_path, run, classification="EVIDENCE_GAP")
    resolve(tmp_path, run, event, basis="EVIDENCE_CHANGED")
    assert transition(tmp_path, run, "verification", source=original["report_ref"]).ok
    report(tmp_path, run)
    assert transition(tmp_path, run, "verification", "BLOCKED").ok
    _, event, resolution, started, _ = review_fixture(tmp_path, run=run)
    assert event["round_review_basis"]["source_report_ref"] == "verification-report@6"
    assert any(item["path"].endswith("verification_report.md") for item in started.data["round_review"]["inputs"])
    result = update_bounce_back(run, project_root=tmp_path, action="resolve", payload=resolve_payload(event, resolution), timestamp=NOW)
    assert result.ok, result.as_dict()
    assert load(run)["repair"]["rounds"][-1]["result_verification"] == original


def test_wrong_process_role_and_ambiguous_assignment_cannot_allocate_review_output(tmp_path: Path) -> None:
    run = completed_rounds(tmp_path)
    event = request_change(tmp_path, run, classification="REPAIR_LIMIT_EXHAUSTED")
    before = {p.relative_to(run): p.read_bytes() for p in run.rglob("*") if p.is_file()}
    for role, artifact in (("product_contract_agent", None), ("independent_verifier", "verification_report")):
        rejected = start_role_boundary(tmp_path, run, role=role, invocation_ref="invalid", artifact_key=artifact, review_event_id=event)
        assert not rejected.ok
        assert before == {p.relative_to(run): p.read_bytes() for p in run.rglob("*") if p.is_file()}


def test_authenticated_null_round_report_without_recovery_lineage_cannot_supply_threshold(tmp_path: Path) -> None:
    run = completed_rounds(tmp_path)
    original = deepcopy(load(run)["repair"]["rounds"][-1]["result_verification"])
    # A genuinely admitted report and unchanged archive are insufficient: no
    # EVIDENCE_GAP recovery was authorized in this invocation's original state.
    report(tmp_path, run)
    state = load(run)
    latest = capture_verification_result(tmp_path, run, state, "FAILED", NOW)
    state["control"]["latest_verification_result"] = latest
    assert latest["report_ref"] == "verification-report@6"
    with pytest.raises(InputError, match="evidence event"):
        threshold_basis(tmp_path, run, state)
    assert load(run)["repair"]["rounds"][-1]["result_verification"] == original


@pytest.mark.parametrize("value", [None, {}, "invalid"])
def test_selected_missing_or_malformed_event_ledger_cannot_prove_raised_ceiling(value) -> None:
    state = {"control": {"semantic_role_boundary": "1.1"}, "repair": {"maximum_attempts": 6}, "bounce_back_events": value}
    assert validate_continuation_metadata(state)
    state.pop("bounce_back_events")
    assert validate_continuation_metadata(state)


def test_unknown_threshold_source_cannot_be_invented_without_retained_registration(tmp_path: Path) -> None:
    run, state = subject(tmp_path)
    event = event_for(tmp_path, run, state)
    event["round_review_basis"]["source_report_ref"] = "verification-report@99"
    event["round_review_basis"]["source_report_sha256"] = "a" * 64
    event["origin"].update(invocation_ref="invented", result_artifact_ref="verification-report@99")
    state["bounce_back_events"] = [event]
    assert validate_continuation_metadata(state)
