"""Source-backed selected round lifecycles, recovery and rejection atomicity."""

from __future__ import annotations

import hashlib
import json
import zipfile
from copy import deepcopy
from pathlib import Path

import pytest
import yaml

from pipeline_control.artifacts import finalize_semantic_return
from pipeline_control.boundary import start_role_boundary
from pipeline_control.io_utils import InputError, atomic_write_json, sha256_file
from pipeline_control.rounds import assert_current_subject, validate_round_context, validate_round_metadata
from pipeline_control.state import update_bounce_back, update_state
from pipeline_control.test_runner import run_test_plan
from pipeline_control.validation import validate_run_directory
from test_agent_finalize import _selected, _call, _submission, _contract_submission
from test_pipeline_control import _verification_report, _write_test_plan
from test_semantic_finalize import STARTED_AT, FINALIZED_AT


def load(run: Path) -> dict:
    return json.loads((run / "30_execution/run_state.json").read_bytes())


def transition(root: Path, run: Path, stage: str, status: str = "IN_PROGRESS", *, refs=None, source=None):
    return update_state(run, project_root=root, to_stage=stage, stage_status=status, gate_status=status,
                        evidence_refs=refs or ["fixture"], failure_ref=source,
                        rationale="Retained fixture evidence.", next_action="Continue the declared lifecycle.", timestamp=FINALIZED_AT)


def subject(root: Path, run: Path, value: str = "initial") -> None:
    source = root / "source"
    source.mkdir(exist_ok=True)
    (source / "main.py").write_text(value, encoding="utf-8")
    archive = root / "deliverables/fixture.zip"
    archive.parent.mkdir(exist_ok=True)
    with zipfile.ZipFile(archive, "w") as output:
        output.writestr("fixture/main.py", value.encode())
    manifest = {"artifact_type": "release-manifest", "source_root": "source", "artifact_root": "fixture",
                "archive_path": "deliverables/fixture.zip", "archive_sha256": sha256_file(archive), "entry_count": 1,
                "entries": [{"path": "fixture/main.py", "sha256": hashlib.sha256(value.encode()).hexdigest(), "size_bytes": len(value.encode())}]}
    atomic_write_json(run / "50_release/release_manifest.json", manifest)
    atomic_write_json(run / "50_release/package_inspection.json", {
        "artifact_type": "package-inspection", "status": "PASS", "diagnostics": [], "prohibited_entry_count": 0,
        "manifest_path": (run / "50_release/release_manifest.json").relative_to(root).as_posix(),
        "archive_path": "deliverables/fixture.zip", "archive_sha256": sha256_file(archive), "entry_count": 1,
    })


def report(root: Path, run: Path, status: str = "FAILED") -> None:
    active = load(run)["active_artifacts"].get("verification_report")
    version = active["version"] + 1 if active else 1
    name = f"vr{version}"
    started = start_role_boundary(root, run, role="independent_verifier", invocation_ref=name,
                                 artifact_key="verification_report", timestamp=STARTED_AT)
    assert started.ok, started.as_dict()
    body = _verification_report().replace("- Version: `1`", f"- Version: `{version}`")
    contract = yaml.safe_load((run / "20_contract/product_contract.yaml").read_text(encoding="utf-8"))
    body = body.replace("REQ-001", contract["requirements"][0]["id"]).replace("ACC-001", contract["acceptance_methods"][0]["id"])
    if status != "PASSED":
        body = body.replace("READY", "UNVERIFIED").replace("| PASS |", "| UNVERIFIED |")
        body = body.replace("## Missing or Unusable Evidence\n\nNone.", "## Missing or Unusable Evidence\n\nNo harness was supplied; deterministic fixture only.")
    path = root / started.data["submission_path"]
    path.write_text(body, encoding="utf-8")
    result = finalize_semantic_return(root, run, artifact_key="verification_report", role="independent_verifier", invocation_ref=name,
                                     baseline_sha256=started.data["baseline_sha256"], source_path=path,
                                     expected_source_sha256=sha256_file(path), timestamp=FINALIZED_AT)
    assert result.ok, result.as_dict()


def initial_result(root: Path, *, status: str = "FAILED", candidate: bool = True, record_terminal: bool = True) -> Path:
    run = _selected(root)
    assert _call(root, run, _submission(root, run, "brief")).ok
    assert _call(root, run, _contract_submission(root, run)).ok
    for stage in ("framing", "contract", "repository_analysis", "implementation"):
        result = transition(root, run, stage, "PASSED")
        assert result.ok, result.as_dict()
    assert transition(root, run, "verification").ok
    if candidate:
        subject(root, run)
    report(root, run, status)
    if record_terminal:
        result = transition(root, run, "verification", status)
        assert result.ok, result.as_dict()
    return run


def request_change(root: Path, run: Path, *, classification="IMPLEMENTATION_DEFECT", summary="Correct the subject.") -> str:
    latest = load(run)["control"]["latest_verification_result"]
    result = update_bounce_back(run, project_root=root, action="create", timestamp=FINALIZED_AT, payload={
        "origin": {"role": "independent_verifier", "invocation_ref": latest["source_invocation_ref"], "result_artifact_ref": latest["report_ref"], "result": latest["stage_status"]},
        "assigned_to": "root_codex", "classification": classification, "summary": summary,
        "affected_stages": ["repair", "verification"], "affected_refs": [latest["report_ref"]],
        "required_resolution": "Retain changed basis and reverify.",
        "retry": {"agent_role": "independent_verifier", "prior_invocation_ref": latest["source_invocation_ref"]},
    })
    assert result.ok, result.as_dict()
    return result.data["event_id"]


def resolve(root: Path, run: Path, event: str, *, basis="IMPLEMENTATION_CHANGED") -> None:
    result = update_bounce_back(run, project_root=root, action="resolve", timestamp=FINALIZED_AT, payload={
        "event_id": event, "resolved_by": "root_codex", "resolution_type": "IMPLEMENTATION_REPAIRED" if basis != "EVIDENCE_CHANGED" else "EVIDENCE_ADDED",
        "summary": "Changed basis retained.", "changed_artifact_refs": ["source/main.py"], "decision_refs": [], "evidence_refs": ["fixture"],
        "retry": {"allowed": True, "change_basis": [basis]},
    })
    assert result.ok, result.as_dict()


def one_round(root: Path, run: Path, *, status="FAILED", index=1) -> None:
    event = request_change(root, run)
    latest = load(run)["control"]["latest_verification_result"]
    result = transition(root, run, "repair", refs=[event], source=latest["report_ref"])
    assert result.ok, result.as_dict()
    subject(root, run, f"revision {index}")
    resolve(root, run, event)
    assert transition(root, run, "repair", "PASSED").ok
    result = transition(root, run, "verification")
    assert result.ok, result.as_dict()
    report(root, run, status)
    result = transition(root, run, "verification", status)
    assert result.ok, result.as_dict()


def completed_rounds(root: Path, count=4, *, status="FAILED") -> Path:
    run = initial_result(root)
    for index in range(1, count + 1):
        one_round(root, run, status=status, index=index)
    return run


@pytest.mark.parametrize("status", ["PASSED", "FAILED", "BLOCKED"])
def test_first_result_uses_audited_inputs_without_counting(tmp_path, status):
    run = initial_result(tmp_path, status=status)
    state = load(run)
    snapshot = state["control"]["latest_verification_result"]
    assert state["repair"]["active_attempt"] == 0
    assert snapshot["stage_status"] == status
    assert snapshot["candidate_binding"]["archive_sha256"] == sha256_file(tmp_path / "deliverables/fixture.zip")
    assert snapshot["harness_attempt"] is None
    assert not validate_round_metadata(state)
    assert not validate_round_context(tmp_path, run, state)
    before = (run / "30_execution/run_state.json").read_bytes()
    assert transition(tmp_path, run, "verification", status).data["replayed"]
    assert (run / "30_execution/run_state.json").read_bytes() == before


def test_multiple_requests_resume_contract_revisit_and_fresh_result_are_one_round(tmp_path):
    run = initial_result(tmp_path)
    events = [request_change(tmp_path, run), request_change(tmp_path, run, classification="CONTRACT_CONTRADICTION")]
    source = load(run)["control"]["latest_verification_result"]["report_ref"]
    assert transition(tmp_path, run, "repair", refs=events, source=source).ok
    before = (run / "30_execution/run_state.json").read_bytes()
    result = transition(tmp_path, run, "repair", refs=list(reversed(events)), source=source)
    assert result.ok and result.data["replayed"]
    assert (run / "30_execution/run_state.json").read_bytes() == before
    assert transition(tmp_path, run, "repair").ok
    contract = _contract_submission(tmp_path, run, "pc2", 2)
    # A real contract revisit changes requirement/acceptance identities. The
    # source report remains attributable to its old contract until reverified.
    path = contract["source_path"]
    path.write_text(path.read_text(encoding="utf-8").replace("REQ-001", "REQ-002").replace("ACC-001", "ACC-002"), encoding="utf-8")
    contract["expected_source_sha256"] = sha256_file(path)
    assert _call(tmp_path, run, contract).ok
    for event in events:
        resolve(tmp_path, run, event)
    subject(tmp_path, run, "combined contract and implementation")
    assert transition(tmp_path, run, "repair", "PASSED").ok
    assert transition(tmp_path, run, "verification").ok
    report(tmp_path, run)
    assert transition(tmp_path, run, "verification", "FAILED").ok
    state = load(run)
    assert state["repair"]["active_attempt"] == 1
    assert state["repair"]["rounds"][0]["status"] == "COMPLETED"
    assert validate_run_directory(tmp_path, run).ok


def test_fourth_pass_is_allowed_and_fifth_modification_is_atomic_stop(tmp_path):
    run = completed_rounds(tmp_path, 3)
    one_round(tmp_path, run, status="PASSED", index=4)
    assert load(run)["repair"]["rounds"][-1]["result_verification"]["stage_status"] == "PASSED"
    tests = run_test_plan(tmp_path, run, _write_test_plan(tmp_path))
    assert tests.ok, tests.as_dict()
    release = transition(tmp_path, run, "release")
    assert release.ok, release.as_dict()
    event = request_change(tmp_path, run, classification="NON_MATERIAL_CHOICE")
    before = (run / "30_execution/run_state.json").read_bytes()
    result = transition(tmp_path, run, "repair", refs=[event], source="verification-report@5")
    assert not result.ok and any(item.code == "REPAIR_LIMIT" for item in result.diagnostics), result.as_dict()
    assert (run / "30_execution/run_state.json").read_bytes() == before


def test_subject_artifact_assignment_requires_reserved_round(tmp_path):
    run = initial_result(tmp_path, status="PASSED")
    before = {p.relative_to(run): p.read_bytes() for p in run.rglob("*") if p.is_file()}
    denied = start_role_boundary(tmp_path, run, role="product_contract_agent", invocation_ref="outside", artifact_key="product_contract")
    assert not denied.ok
    assert before == {p.relative_to(run): p.read_bytes() for p in run.rglob("*") if p.is_file()}
    event = request_change(tmp_path, run, classification="NON_MATERIAL_CHOICE")
    assert transition(tmp_path, run, "repair", refs=[event], source="verification-report@1").ok
    assert start_role_boundary(tmp_path, run, role="product_contract_agent", invocation_ref="inside", artifact_key="product_contract").ok


def test_old_resolved_event_cannot_qualify_current_round_retry(tmp_path):
    run = completed_rounds(tmp_path, 1)
    event = request_change(tmp_path, run)
    assert transition(tmp_path, run, "repair", refs=[event], source="verification-report@2").ok
    resolve(tmp_path, run, event, basis="EVIDENCE_CHANGED")
    assert transition(tmp_path, run, "repair", "PASSED").ok
    before = (run / "30_execution/run_state.json").read_bytes()
    result = transition(tmp_path, run, "verification")
    assert not result.ok and any(d.code == "UNCHANGED_RETRY" for d in result.diagnostics)
    assert (run / "30_execution/run_state.json").read_bytes() == before


@pytest.mark.parametrize("drift", ["source", "archive", "contract", "manifest"])
def test_evidence_only_recovery_rejects_subject_drift(tmp_path, drift):
    run = initial_result(tmp_path)
    event = request_change(tmp_path, run, classification="EVIDENCE_GAP")
    resolve(tmp_path, run, event, basis="EVIDENCE_CHANGED")
    target = {"source": tmp_path / "source/main.py", "archive": tmp_path / "deliverables/fixture.zip", "contract": run / "20_contract/product_contract.yaml", "manifest": run / "50_release/release_manifest.json"}[drift]
    target.write_bytes(target.read_bytes() + b"drift")
    before = (run / "30_execution/run_state.json").read_bytes()
    result = transition(tmp_path, run, "verification", source="verification-report@1")
    assert not result.ok
    assert (run / "30_execution/run_state.json").read_bytes() == before


def test_evidence_recovery_preserves_completed_round_and_unknown_subject_rejects(tmp_path):
    run = completed_rounds(tmp_path, 1)
    prior = deepcopy(load(run)["repair"]["rounds"])
    event = request_change(tmp_path, run, classification="EVIDENCE_GAP")
    resolve(tmp_path, run, event, basis="EVIDENCE_CHANGED")
    assert transition(tmp_path, run, "verification", source="verification-report@2").ok
    manifest = run / "50_release/release_manifest.json"
    data = json.loads(manifest.read_bytes())
    data["note"] = "Evidence reconstructed without subject change."
    atomic_write_json(manifest, data)
    report(tmp_path, run)
    result = transition(tmp_path, run, "verification", "BLOCKED")
    assert result.ok, result.as_dict()
    state = load(run)
    assert state["repair"]["rounds"] == prior
    assert state["control"]["latest_verification_result"]["report_ref"] == "verification-report@3"
    assert not validate_round_metadata(state)
    assert not validate_round_context(tmp_path, run, state)


def test_missing_initial_candidate_cannot_claim_null_subject_equality(tmp_path):
    run = initial_result(tmp_path, candidate=False)
    event = request_change(tmp_path, run, classification="EVIDENCE_GAP")
    resolve(tmp_path, run, event, basis="EVIDENCE_CHANGED")
    before = (run / "30_execution/run_state.json").read_bytes()
    result = transition(tmp_path, run, "verification", source="verification-report@1")
    assert not result.ok and any(d.code == "RECOVERY_SUBJECT" for d in result.diagnostics)
    assert (run / "30_execution/run_state.json").read_bytes() == before


def test_incomplete_release_enters_counted_repair_and_completed_release_is_immutable(tmp_path):
    run = initial_result(tmp_path, status="PASSED")
    assert run_test_plan(tmp_path, run, _write_test_plan(tmp_path)).ok
    assert transition(tmp_path, run, "release").ok
    event = request_change(tmp_path, run, classification="NON_MATERIAL_CHOICE")
    source = deepcopy(load(run)["control"]["latest_verification_result"])
    result = transition(tmp_path, run, "repair", refs=[event], source=source["report_ref"])
    assert result.ok, result.as_dict()
    state = load(run)
    assert state["repair"]["active_attempt"] == 1
    assert state["control"]["latest_verification_result"] == source
    assert state["control"]["verification_validation_identity"] is None
    assert next(s for s in state["stages"] if s["id"] == "verification")["status"] == "IN_PROGRESS"
    assert next(s for s in state["stages"] if s["id"] == "release")["status"] == "PENDING"
    resolve(tmp_path, run, event, basis="DECISION_CHANGED")
    assert transition(tmp_path, run, "repair", "PASSED").ok
    assert transition(tmp_path, run, "verification").ok
    report(tmp_path, run, "PASSED")
    assert transition(tmp_path, run, "verification", "PASSED").ok
    result = transition(tmp_path, run, "release", "PASSED")
    assert result.ok, result.as_dict()
    before = (run / "30_execution/run_state.json").read_bytes()
    result = transition(tmp_path, run, "repair", refs=[event], source="verification-report@2")
    assert not result.ok and any(d.code == "COMPLETED_RELEASE" for d in result.diagnostics)
    assert (run / "30_execution/run_state.json").read_bytes() == before
    replay = transition(tmp_path, run, "repair", refs=[event], source=source["report_ref"])
    assert replay.ok and replay.data["replayed"] and replay.data["is_current"] is False
    assert transition(tmp_path, run, "verification", "PASSED").data["replayed"]
    assert (run / "30_execution/run_state.json").read_bytes() == before


def test_pre_round_report_cannot_complete_reserved_round(tmp_path):
    run = initial_result(tmp_path)
    recovery = request_change(tmp_path, run, classification="EVIDENCE_GAP")
    resolve(tmp_path, run, recovery, basis="EVIDENCE_CHANGED")
    # Admit a second report in an uncounted evidence invocation; do not mark it
    # terminal before reserving a separate subject modification.
    report(tmp_path, run)
    event = request_change(tmp_path, run)
    assert transition(tmp_path, run, "repair", refs=[event], source="verification-report@1").ok
    subject(tmp_path, run, "post-invocation correction")
    resolve(tmp_path, run, event)
    assert transition(tmp_path, run, "repair", "PASSED").ok
    assert transition(tmp_path, run, "verification").ok
    before = (run / "30_execution/run_state.json").read_bytes()
    result = transition(tmp_path, run, "verification", "FAILED")
    assert not result.ok and any(d.code == "ROUND_RESULT" for d in result.diagnostics)
    assert (run / "30_execution/run_state.json").read_bytes() == before


@pytest.mark.parametrize("status", ["PASSED", "FAILED"])
def test_terminal_rejects_known_supplied_archive_drift_after_report_admission(tmp_path, status):
    run = initial_result(tmp_path, status=status, record_terminal=False)
    archive = tmp_path / "deliverables/fixture.zip"
    audited_hash = sha256_file(archive)
    archive.write_bytes(archive.read_bytes() + b"post-return subject drift")
    before = (run / "30_execution/run_state.json").read_bytes()
    result = transition(tmp_path, run, "verification", status)
    assert not result.ok and any(d.code == "ROUND_RESULT" for d in result.diagnostics), result.as_dict()
    assert (run / "30_execution/run_state.json").read_bytes() == before
    assert audited_hash != sha256_file(archive)


def test_start_replay_after_completion_recovers_history_without_mutation(tmp_path):
    run = completed_rounds(tmp_path, 1)
    first = load(run)["repair"]["rounds"][0]
    before = (run / "30_execution/run_state.json").read_bytes()
    replay = transition(tmp_path, run, "repair", refs=first["request_refs"], source=first["source_verification"]["report_ref"])
    assert replay.ok and replay.data["replayed"] and replay.data["is_current"] is False
    assert (run / "30_execution/run_state.json").read_bytes() == before


@pytest.mark.parametrize("drift", ["source", "archive", "contract"])
def test_known_subject_drift_before_reservation_rejects_atomically(tmp_path, drift):
    run = initial_result(tmp_path, status="PASSED")
    event = request_change(tmp_path, run)
    target = {"source": tmp_path / "source/main.py", "archive": tmp_path / "deliverables/fixture.zip", "contract": run / "20_contract/product_contract.yaml"}[drift]
    target.write_bytes(target.read_bytes() + b"changed before reserve")
    before = (run / "30_execution/run_state.json").read_bytes()
    result = transition(tmp_path, run, "repair", refs=[event], source="verification-report@1")
    assert not result.ok
    assert (run / "30_execution/run_state.json").read_bytes() == before


def test_incomplete_failed_subject_can_reserve_round_before_building_candidate(tmp_path):
    run = initial_result(tmp_path, candidate=False)
    event = request_change(tmp_path, run)
    result = transition(tmp_path, run, "repair", refs=[event], source="verification-report@1")
    assert result.ok, result.as_dict()
    assert load(run)["repair"]["active_attempt"] == 1


@pytest.mark.parametrize("defect", ["invalid_zip", "source_mismatch", "manifest_mismatch"])
def test_failed_inconsistent_candidate_can_reserve_counted_repair(tmp_path, defect):
    # Establish the defect before the report invocation so recorded hashes name
    # the actual failed candidate, rather than hiding post-verification drift.
    run = initial_result(tmp_path, candidate=False, record_terminal=False)
    subject(tmp_path, run)
    if defect == "invalid_zip":
        archive = tmp_path / "deliverables/fixture.zip"
        archive.write_bytes(b"This supplied candidate is not a ZIP archive.")
        for leaf in ("release_manifest.json", "package_inspection.json"):
            path = run / "50_release" / leaf
            data = json.loads(path.read_bytes())
            data["archive_sha256"] = sha256_file(archive)
            atomic_write_json(path, data)
    elif defect == "source_mismatch":
        (tmp_path / "source/main.py").write_text("Source does not match the supplied archive.", encoding="utf-8")
    else:
        path = run / "50_release/release_manifest.json"
        data = json.loads(path.read_bytes())
        data["entries"][0]["sha256"] = "0" * 64
        atomic_write_json(path, data)
    # The missing-evidence report from setup is superseded by a report assigned
    # after this candidate's actual bytes were supplied.
    report(tmp_path, run, "FAILED")
    terminal = transition(tmp_path, run, "verification", "FAILED")
    assert terminal.ok, terminal.as_dict()
    snapshot = load(run)["control"]["latest_verification_result"]
    with pytest.raises(InputError):
        assert_current_subject(tmp_path, run, load(run), snapshot)
    event = request_change(tmp_path, run)
    result = transition(tmp_path, run, "repair", refs=[event], source=snapshot["report_ref"])
    assert result.ok, result.as_dict()
    state = load(run)
    assert state["repair"]["active_attempt"] == 1
    assert state["repair"]["rounds"][-1]["status"] == "IN_PROGRESS"
    assert state["repair"]["rounds"][-1]["source_verification"] == snapshot


@pytest.mark.parametrize("status", ["PASSED", "FAILED", "BLOCKED"])
def test_intervening_contract_revision_requires_fresh_report_before_terminal(tmp_path, status):
    run = initial_result(tmp_path)
    event = request_change(tmp_path, run)
    assert transition(tmp_path, run, "repair", refs=[event], source="verification-report@1").ok
    resolve(tmp_path, run, event)
    assert transition(tmp_path, run, "repair", "PASSED").ok
    assert transition(tmp_path, run, "verification").ok
    report(tmp_path, run, status)
    # Same requirement IDs still represent a different authoritative version.
    replacement = _contract_submission(tmp_path, run, "pc2", 2)
    admitted = _call(tmp_path, run, replacement)
    assert admitted.ok, admitted.as_dict()
    before = (run / "30_execution/run_state.json").read_bytes()
    result = transition(tmp_path, run, "verification", status)
    assert not result.ok and any(d.code == "ROUND_RESULT" for d in result.diagnostics), result.as_dict()
    assert (run / "30_execution/run_state.json").read_bytes() == before
    assert load(run)["repair"]["rounds"][-1]["status"] == "IN_PROGRESS"
    report(tmp_path, run, status)
    result = transition(tmp_path, run, "verification", status)
    assert result.ok, result.as_dict()


def test_pass_rejects_live_source_drift_after_report_admission(tmp_path):
    run = initial_result(tmp_path, status="PASSED", record_terminal=False)
    (tmp_path / "source/main.py").write_text("post-report source drift", encoding="utf-8")
    before = (run / "30_execution/run_state.json").read_bytes()
    result = transition(tmp_path, run, "verification", "PASSED")
    assert not result.ok and any(d.code == "ROUND_RESULT" for d in result.diagnostics), result.as_dict()
    assert (run / "30_execution/run_state.json").read_bytes() == before


def test_passed_evidence_recovery_rebuilds_metadata_and_preserves_zero_count(tmp_path):
    run = initial_result(tmp_path, status="PASSED")
    previous = deepcopy(load(run)["control"]["latest_verification_result"])
    event = request_change(tmp_path, run, classification="EVIDENCE_GAP")
    resolve(tmp_path, run, event, basis="EVIDENCE_CHANGED")
    assert transition(tmp_path, run, "verification", source=previous["report_ref"]).ok
    for leaf in ("release_manifest.json", "package_inspection.json"):
        path = run / "50_release" / leaf
        data = json.loads(path.read_bytes())
        data["recovery_note"] = "Rebuilt metadata with unchanged subject."
        atomic_write_json(path, data)
    report(tmp_path, run, "PASSED")
    result = transition(tmp_path, run, "verification", "PASSED")
    assert result.ok, result.as_dict()
    state = load(run)
    assert state["repair"]["active_attempt"] == 0
    assert state["repair"]["rounds"] == []
    assert state["control"]["latest_verification_result"]["report_ref"] == "verification-report@2"
    assert state["control"]["latest_verification_result"]["candidate_binding"]["archive_sha256"] == previous["candidate_binding"]["archive_sha256"]
    assert state["control"]["verification_validation_identity"]["candidate_binding"]["manifest_sha256"] != previous["candidate_binding"]["manifest_sha256"]
    assert validate_run_directory(tmp_path, run).ok


@pytest.mark.parametrize("change", [
    lambda s: s["control"]["latest_verification_result"].update(stage_status=[]),
    lambda s: s["control"]["latest_verification_result"].update(stage_status={}),
    lambda s: s["repair"]["rounds"][-1].update(source_verification=None),
    lambda s: s["control"]["latest_verification_result"].update(candidate_binding=None),
    lambda s: s["repair"]["rounds"][-1].update(request_refs=[{}]),
])
def test_malformed_nested_round_metadata_returns_diagnostics(tmp_path, change):
    run = completed_rounds(tmp_path, 1)
    state = load(run)
    change(state)
    assert validate_round_metadata(state)
