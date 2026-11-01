from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

import pipeline_control.boundary as boundary
from pipeline_control.boundary import BoundaryPolicy, finish_role_boundary, start_role_boundary
from pipeline_control.io_utils import InputError, sha256_file
from pipeline_control.submissions import (
    collect_submission_inputs, create_submission_assignment, submission_audit_id, validate_submission_assignment,
)
from test_boundary_optimization import TIMESTAMP, _state


@pytest.fixture
def project(tmp_path_factory) -> Path:
    # Selected allocation checks intentionally enforce the real Windows budget.
    return tmp_path_factory.mktemp("s2")


def selected_run(project: Path, *, direct: bool = True) -> tuple[Path, dict]:
    run = project / "r"
    for directory in ("00_intake", "10_framing", "20_contract", "30_execution", "40_verification", "50_release"):
        (run / directory).mkdir(parents=True)
    request_path = run / "00_intake/build_request.yaml"
    request_path.write_text(json.dumps({
        "handoff": {"next_stage": "contract" if direct else "framing"},
        "source_context": [], "target": {"output_path": "deliverables/tool.zip"},
    }))
    state = _state()
    state["control"].update(semantic_role_boundary="1.1", intent_realization="1.0",
                            semantic_registrations={}, latest_verification_result=None)
    state["repair"].update(maximum_attempts=4, rounds=[])
    state["active_artifacts"]["build_request"]["content_sha256"] = sha256_file(request_path)
    save_state(run, state)
    return run, state


def save_state(run: Path, state: dict) -> None:
    (run / "30_execution/run_state.json").write_text(json.dumps(state))


def start(project: Path, run: Path, *, key="product_contract", role="product_contract_agent", invocation="pc", **kwargs):
    return start_role_boundary(project, run, role=role, invocation_ref=invocation,
                               artifact_key=key, timestamp=TIMESTAMP, **kwargs)


def finish(project: Path, run: Path, started, *, role="product_contract_agent", invocation="pc"):
    return finish_role_boundary(project, run, role=role, invocation_ref=invocation,
                                baseline_sha256=started.data["baseline_sha256"], timestamp=TIMESTAMP)


def assignment_check(project: Path, run: Path, state: dict, started, **overrides):
    kwargs = dict(role="product_contract_agent", invocation_ref="pc", artifact_key="product_contract",
                  baseline_sha256=started.data["baseline_sha256"], source_path=project / started.data["submission_path"])
    kwargs.update(overrides)
    return validate_submission_assignment(project, run, state, **kwargs)


def test_exact_contract_assignment_allows_only_assigned_file(project: Path) -> None:
    run, state = selected_run(project)
    started = start(project, run)
    assert started.ok, started.as_dict()
    assignment = started.data["submission"]
    assert assignment["path"] == f"30_execution/sub/{started.data['audit_id']}/contract.yaml"
    assert assignment["artifact_version"] == 1
    assert assignment["round_number"] is None
    assert started.data["path_policy"]["allowed_durable_files"] == [assignment["path"]]
    assert started.data["allowed_write_roots"] == []
    source = project / started.data["submission_path"]
    source.write_text("specialist-authored bytes\n")
    baseline = assignment_check(project, run, state, started)
    assert baseline["control_revision"] == "1.1"
    assert [item["artifact_id"] for item in assignment["inputs"]] == ["build-request"]
    completed = finish(project, run, started)
    assert completed.ok, completed.as_dict()
    assert completed.data["status"] == "PASS"


@pytest.mark.parametrize("violation", ["sibling", "directory", "canonical", "hardlink"])
def test_assignment_rejects_siblings_directories_canonical_writes_and_aliases(project: Path, violation: str) -> None:
    run, _ = selected_run(project)
    canonical = run / "20_contract/product_contract.yaml"
    canonical.write_text("protected\n")
    started = start(project, run)
    assert started.ok, started.as_dict()
    source = project / started.data["submission_path"]
    if violation == "sibling":
        source.write_text("return\n")
        source.with_name("extra.txt").write_text("not assigned\n")
    elif violation == "directory":
        source.mkdir()
        (source / "child").write_text("not a file\n")
    elif violation == "canonical":
        source.write_text("return\n")
        canonical.write_text("unauthorized\n")
    else:
        os.link(canonical, source)
    completed = finish(project, run, started)
    assert not completed.ok, completed.as_dict()
    assert completed.data["status"] == "BOUNDARY_VIOLATION"


def test_submission_symlink_and_parent_alias_reject(project: Path) -> None:
    run, state = selected_run(project)
    target = project / "target.md"
    target.write_text("protected")
    started = start(project, run)
    source = project / started.data["submission_path"]
    try:
        source.symlink_to(target)
    except OSError:
        pytest.skip("host does not permit symlink creation")
    with pytest.raises(InputError, match="symlink|reparse"):
        assignment_check(project, run, state, started)
    assert not finish(project, run, started).ok


@pytest.mark.parametrize("change", ["hash", "version", "disappear", "source", "round"])
def test_input_and_assignment_drift_rejects_admission(project: Path, change: str) -> None:
    run, state = selected_run(project)
    extra = project / "context.txt"
    extra.write_text("bound input")
    started = start(project, run, input_refs=("context.txt",))
    assert started.ok, started.as_dict()
    source = project / started.data["submission_path"]
    source.write_text("return")
    overrides = {}
    if change == "hash":
        extra.write_text("new input")
    elif change == "version":
        state["active_artifacts"]["build_request"]["version"] += 1
    elif change == "disappear":
        extra.unlink()
    elif change == "round":
        state["repair"]["rounds"] = [{"number": 1, "status": "IN_PROGRESS"}]
    else:
        alias = source.with_name("other.yaml")
        alias.write_bytes(source.read_bytes())
        overrides["source_path"] = alias
    with pytest.raises(InputError):
        assignment_check(project, run, state, started, **overrides)


def test_path_budget_and_wrong_owner_fail_before_allocation(project: Path) -> None:
    run, _ = selected_run(project)
    before = {path.relative_to(run).as_posix() for path in run.rglob("*")}
    wrong = start(project, run, key="verification_report")
    assert not wrong.ok
    assert before == {path.relative_to(run).as_posix() for path in run.rglob("*")}
    long_project = project / ("long-" + "x" * 32)
    long_project.mkdir()
    long_run, _ = selected_run(long_project)
    denied = start(long_project, long_run)
    assert not denied.ok
    assert not (long_run / "30_execution/sub").exists()
    assert not (long_run / "30_execution/role_boundary").exists()


def test_missing_artifact_and_legacy_submission_flags_reject(project: Path) -> None:
    run, state = selected_run(project)
    assert not start(project, run, key=None).ok
    state["control"] = {"semantic_role_boundary": "1.0", "verification_validation_identity": None}
    state["repair"] = {"active_attempt": 0, "maximum_attempts": 2, "last_failure_ref": None}
    save_state(run, state)
    assert not start(project, run).ok
    legacy = start_role_boundary(project, run, role="product_contract_agent", invocation_ref="old")
    assert legacy.ok, legacy.as_dict()
    assert legacy.data["path_policy"]["allowed_durable_files"] == []
    old_policy = legacy.data["path_policy"].copy()
    old_policy.pop("allowed_durable_files")
    assert BoundaryPolicy.from_dict(old_policy).allowed_durable_files == ()


def test_realizer_and_prepared_contractor_capture_request_and_brief(project: Path) -> None:
    run, state = selected_run(project, direct=False)
    realized = create_submission_assignment(project, run, state, role="intent_realizer", invocation_ref="ir",
                                            artifact_key="problem_frame")
    assert realized["path"].endswith("/brief.md")
    frame = run / "10_framing/problem_frame.md"
    frame.write_text("registered brief")
    state["active_artifacts"]["problem_frame"] = {
        "artifact_id": "problem-frame", "version": 3, "path": "10_framing/problem_frame.md",
        "content_sha256": sha256_file(frame),
    }
    assignment = create_submission_assignment(project, run, state, role="product_contract_agent", invocation_ref="pc",
                                             artifact_key="product_contract")
    assert {(item["artifact_id"], item["version"]) for item in assignment["inputs"]} == {
        ("build-request", 1), ("problem-frame", 3),
    }


def test_verifier_captures_current_missing_evidence(project: Path) -> None:
    run, state = selected_run(project)
    contract = run / "20_contract/product_contract.yaml"
    contract.write_text("registered contract")
    state["active_artifacts"]["product_contract"] = {
        "artifact_id": "product-contract", "version": 2, "path": "20_contract/product_contract.yaml",
        "content_sha256": sha256_file(contract),
    }
    state["control"]["verification_validation_identity"] = {"candidate_binding": {"archive_path": "old.zip"}}
    inputs = collect_submission_inputs(project, run, state, "verification_report")
    missing = {item["path"] for item in inputs if item["availability"] == "MISSING"}
    assert "r/50_release/release_manifest.json" in missing
    assert "r/40_verification/harness/latest.json" in missing
    assert "deliverables/tool.zip" in missing
    assert not any(item["path"] == "old.zip" for item in inputs)
    assert all("content_sha256" not in item for item in inputs if item["availability"] == "MISSING")


def test_selected_verifier_probe_policy_is_invocation_scoped(project: Path, monkeypatch) -> None:
    run, state = selected_run(project)
    contract = run / "20_contract/product_contract.yaml"
    contract.write_text("registered contract")
    state["active_artifacts"]["product_contract"] = {
        "artifact_id": "product-contract", "version": 1, "path": "20_contract/product_contract.yaml",
        "content_sha256": sha256_file(contract),
        "semantic_owner": "product_contract_agent", "persistence_owner": "root_codex",
        "source_invocation_ref": "fixture-contract", "boundary_evidence_ref": "fixture-boundary.json",
    }
    audit_id = submission_audit_id("product_contract_agent", "fixture-contract")
    state["control"]["semantic_registrations"][audit_id] = {
        "artifact_key": "product_contract", "artifact_ref": "product-contract@1",
        "path": "20_contract/product_contract.yaml", "content_sha256": sha256_file(contract),
        "producer_role": "product_contract_agent", "submission_path": f"30_execution/sub/{audit_id}/contract.yaml",
        "source_invocation_ref": "fixture-contract", "baseline_sha256": "a" * 64,
        "boundary_evidence_ref": "fixture-boundary.json", "registered_at": TIMESTAMP,
        "run_state_version": 1, "round_number": None,
    }
    # Probe scope is a boundary-unit concern; structural receipt admission is
    # exercised in finalizer integration tests, not forged by this fixture.
    save_state(run, state)
    monkeypatch.setattr(boundary, "validate_run_state_context", lambda *_: [])
    import pipeline_control.mutation_guard as guard
    monkeypatch.setattr(guard, "run_mutation_diagnostics", lambda *_: [])
    started = start(project, run, key="verification_report", role="independent_verifier", invocation="iv")
    assert started.ok, started.as_dict()
    expected = f"40_verification/probes/{started.data['audit_id']}"
    assert started.data["allowed_write_roots"] == [expected]
    (run / expected / "probe.txt").write_text("probe")
    (run / "40_verification/probes/other").mkdir()
    completed = finish(project, run, started, role="independent_verifier", invocation="iv")
    assert not completed.ok
    assert completed.data["status"] == "BOUNDARY_VIOLATION"


@pytest.mark.parametrize("selected", [False, True], ids=["legacy", "selected"])
@pytest.mark.parametrize("damage", ["delete", "json", "unknown-control", "receipts"])
def test_finish_recovers_role_damaged_state_from_authenticated_baseline(project: Path, selected: bool, damage: str) -> None:
    run, state = selected_run(project)
    if not selected:
        state["control"] = {"semantic_role_boundary": "1.0", "verification_validation_identity": None}
        state["repair"] = {"active_attempt": 0, "maximum_attempts": 2, "last_failure_ref": None}
        save_state(run, state)
        started = start_role_boundary(project, run, role="product_contract_agent", invocation_ref="pc")
    else:
        started = start(project, run)
    assert started.ok, started.as_dict()
    path = run / "30_execution/run_state.json"
    original = path.read_bytes()
    if damage == "delete":
        path.unlink()
    elif damage == "json":
        path.write_text("{broken")
    else:
        if damage == "unknown-control":
            state["control"]["semantic_role_boundary"] = "unsupported"
        else:
            state["control"]["semantic_registrations"] = {"invalid": None}
        save_state(run, state)
    completed = finish(project, run, started)
    assert not completed.ok, completed.as_dict()
    assert completed.data["status"] == "BOUNDARY_VIOLATION"
    assert completed.data["run_state_restored"]
    assert path.read_bytes() == original


def test_local_context_is_mandatory_without_optional_input_flag(project: Path) -> None:
    run, state = selected_run(project)
    context = project / "intent.md"
    context.write_text("original user intent")
    request_path = run / "00_intake/build_request.yaml"
    request = json.loads(request_path.read_text())
    request["source_context"] = [{"path": "intent.md", "type": "FILE", "authority": "USER_PROVIDED"}]
    request_path.write_text(json.dumps(request))
    state["active_artifacts"]["build_request"]["content_sha256"] = sha256_file(request_path)
    save_state(run, state)
    started = start(project, run)
    assert started.ok, started.as_dict()
    assert any(record["path"] == "intent.md" for record in started.data["submission"]["inputs"])
    (project / started.data["submission_path"]).write_text("return")
    context.write_text("changed original intent")
    with pytest.raises(InputError, match="input disappeared or changed"):
        assignment_check(project, run, state, started)


@pytest.mark.parametrize("appearance", ["file", "directory"])
def test_previously_missing_mandatory_evidence_appearance_rejects(project: Path, appearance: str) -> None:
    run, state = selected_run(project)
    started = start(project, run)
    assert started.ok, started.as_dict()
    source = project / started.data["submission_path"]
    source.write_text("return")
    baseline_path = project / started.data["baseline_path"]
    baseline = json.loads(baseline_path.read_text())
    baseline["submission"]["inputs"].append({"path": "later.txt", "availability": "MISSING"})
    baseline_path.write_text(json.dumps(baseline))
    # Hash-bound synthetic missing input isolates the appearance check; actual
    # verifier collection of mandatory missing files is tested above.
    digest = sha256_file(baseline_path)
    if appearance == "file":
        (project / "later.txt").write_text("now present")
    else:
        (project / "later.txt").mkdir()
    with pytest.raises(InputError, match="missing submission input appeared"):
        assignment_check(project, run, state, started, baseline_sha256=digest)


def test_audit_id_collision_rejects_without_replacing_assignment(project: Path, monkeypatch) -> None:
    run, _ = selected_run(project)
    started = start(project, run)
    assert started.ok, started.as_dict()
    baseline_path = project / started.data["baseline_path"]
    original = baseline_path.read_bytes()
    monkeypatch.setattr(boundary, "_audit_id", lambda *_: started.data["audit_id"])
    collided = start(project, run, invocation="different-full-identity")
    assert not collided.ok
    assert "BOUNDARY_EXISTS" in {item.code for item in collided.diagnostics}
    assert baseline_path.read_bytes() == original


def test_verifier_captures_supplied_custom_manifest_archive_and_harness(project: Path) -> None:
    run, state = selected_run(project)
    contract = run / "20_contract/product_contract.yaml"
    contract.write_text("registered contract")
    state["active_artifacts"]["product_contract"] = {
        "artifact_id": "product-contract", "version": 1, "path": "20_contract/product_contract.yaml",
        "content_sha256": sha256_file(contract),
    }
    custom = run / "50_release/custom.json"
    archive = project / "supplied.zip"
    archive.write_bytes(b"current candidate")
    custom.write_text(json.dumps({"archive_path": "supplied.zip"}))
    inspection = run / "50_release/package_inspection.json"
    inspection.write_text(json.dumps({"manifest_path": "r/50_release/custom.json"}))
    fixed_manifest = run / "50_release/release_manifest.json"
    fixed_manifest.write_text(json.dumps({"archive_path": "obsolete.zip"}))
    latest = run / "40_verification/harness/latest.json"
    latest.parent.mkdir()
    latest.write_text(json.dumps({
        "attempt_path": "r/40_verification/harness/attempts/current",
        "cleanup_path": "r/40_verification/harness/cleanup/current.json",
    }))
    summary = run / "40_verification/harness/attempts/current/summary.json"
    summary.parent.mkdir(parents=True)
    summary.write_text('{"attempt_id": "current"}')
    cleanup = run / "40_verification/harness/cleanup/current.json"
    cleanup.parent.mkdir()
    cleanup.write_text('{"status": "COMPLETE"}')
    state["control"]["verification_validation_identity"] = {
        "candidate_binding": {"manifest_path": "previous.json", "archive_path": "previous.zip"},
    }
    inputs = {item["path"]: item for item in collect_submission_inputs(project, run, state, "verification_report")}
    for path in (inspection, fixed_manifest, custom, archive, latest, summary, cleanup):
        reference = path.relative_to(project).as_posix()
        assert inputs[reference] == {"path": reference, "availability": "PRESENT", "content_sha256": sha256_file(path)}
    assert not {"obsolete.zip", "previous.zip", "previous.json", "deliverables/tool.zip"} & inputs.keys()


def test_existing_evidence_directory_cannot_be_recorded_as_missing(project: Path) -> None:
    run, state = selected_run(project)
    contract = run / "20_contract/product_contract.yaml"
    contract.write_text("registered contract")
    state["active_artifacts"]["product_contract"] = {
        "artifact_id": "product-contract", "version": 1, "path": "20_contract/product_contract.yaml",
        "content_sha256": sha256_file(contract),
    }
    (run / "50_release/package_inspection.json").mkdir()
    with pytest.raises(InputError, match="must be a regular file"):
        collect_submission_inputs(project, run, state, "verification_report")


@pytest.mark.parametrize("selected", [False, True], ids=["legacy", "selected"])
def test_copied_cross_run_baseline_rejects_without_side_effects(project: Path, selected: bool) -> None:
    run, state = selected_run(project)
    if selected:
        started = start(project, run)
    else:
        state["control"] = {"semantic_role_boundary": "1.0", "verification_validation_identity": None}
        state["repair"] = {"active_attempt": 0, "maximum_attempts": 2, "last_failure_ref": None}
        save_state(run, state)
        started = start_role_boundary(project, run, role="product_contract_agent", invocation_ref="pc")
    assert started.ok, started.as_dict()
    other_project = project / "other"
    other_project.mkdir()
    other, _ = selected_run(other_project)
    copied_baseline = other / "30_execution/role_boundary/baselines" / f"{started.data['audit_id']}.json"
    copied_baseline.parent.mkdir(parents=True)
    copied_baseline.write_bytes((project / started.data["baseline_path"]).read_bytes())
    before = {path.relative_to(other).as_posix(): path.read_bytes() for path in other.rglob("*") if path.is_file()}
    completed = finish(project, other, started)
    assert not completed.ok
    assert "run/audit binding" in completed.diagnostics[0].message
    assert before == {path.relative_to(other).as_posix(): path.read_bytes() for path in other.rglob("*") if path.is_file()}
    assert not (other / "30_execution/role_boundary/results").exists()
    assert not (other / "30_execution/role_boundary/latest.json").exists()


def test_cached_selected_pass_preserves_newer_role_violation(project: Path) -> None:
    run, _ = selected_run(project)
    older = start(project, run)
    assert older.ok, older.as_dict()
    (project / older.data["submission_path"]).write_text("old assigned return")
    assert finish(project, run, older).ok
    newer = start(project, run, invocation="newer")
    assert newer.ok, newer.as_dict()
    newer_source = project / newer.data["submission_path"]
    newer_source.write_text("new assigned return")
    newer_source.with_name("unassigned.txt").write_text("violates exact scope")
    violation = finish(project, run, newer, invocation="newer")
    assert not violation.ok
    assert violation.data["status"] == "BOUNDARY_VIOLATION"
    latest_path = run / "30_execution/role_boundary/latest.json"
    latest_violation = latest_path.read_bytes()
    replay = finish(project, run, older)
    assert replay.ok, replay.as_dict()
    assert replay.data["status"] == "PASS"
    assert replay.data["index_recovered"] is False
    assert replay.data["latest_index_preserved"] is True
    assert latest_path.read_bytes() == latest_violation
    indexed = json.loads(latest_path.read_text())["roles"]["product_contract_agent"]
    assert indexed["invocation_ref"] == "newer"
    assert indexed["status"] == "BOUNDARY_VIOLATION"
