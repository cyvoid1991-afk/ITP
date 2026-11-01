"""Selected-policy admission, durable interruption and receipt recovery."""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys

import pytest
import yaml

import pipeline_control.artifacts as artifacts
import pipeline_control.finalize_journal as journal
from pipeline_control.artifacts import finalize_semantic_return, persist_semantic_artifact
from pipeline_control.boundary import finish_role_boundary, start_role_boundary
from pipeline_control.io_utils import atomic_write_json, sha256_bytes, sha256_file
from pipeline_control.validation import validate_run_directory
from test_semantic_finalize import _write_run, _problem_frame, _contract, STARTED_AT, FINALIZED_AT
from test_pipeline_control import _verification_report


def _selected(root: Path) -> Path:
    run = _write_run(root)
    state_path = run / "30_execution/run_state.json"
    state = json.loads(state_path.read_bytes())
    state["control"].update(semantic_role_boundary="1.1", intent_realization="1.0", semantic_registrations={}, latest_verification_result=None)
    state["repair"].update(maximum_attempts=4, rounds=[])
    state["active_artifacts"]["build_request"]["content_sha256"] = sha256_file(run / "00_intake/build_request.yaml")
    atomic_write_json(state_path, state)
    assert validate_run_directory(root, run).ok
    return run


def _submission(root: Path, run: Path, name: str = "a", version: int = 1, *, input_refs: tuple = ()) -> dict:
    started = start_role_boundary(root, run, role="intent_realizer", invocation_ref=name,
                                 artifact_key="problem_frame", input_refs=input_refs, timestamp=STARTED_AT)
    assert started.ok, started.as_dict()
    tx_path = journal.transaction_path(run, "intent_realizer", name)
    baseline = json.loads((run / "30_execution/role_boundary/baselines" / tx_path.name).read_bytes())
    source = run / baseline["submission"]["path"]
    source.write_text(_problem_frame(version, owner="intent_realizer"), encoding="utf-8")
    return dict(artifact_key="problem_frame", role="intent_realizer", invocation_ref=name,
                baseline_sha256=started.data["baseline_sha256"], source_path=source,
                expected_source_sha256=sha256_file(source), timestamp=FINALIZED_AT)


def _call(root: Path, run: Path, request: dict):
    return finalize_semantic_return(root, run, **request)


def _tx(run: Path, request: dict) -> Path:
    return journal.transaction_path(run, request["role"], request["invocation_ref"])


def test_selected_receipt_and_read_only_replay(tmp_path: Path) -> None:
    run = _selected(tmp_path)
    request = _submission(tmp_path, run)
    result = _call(tmp_path, run, request)
    assert result.ok, result.as_dict()
    state = json.loads((run / "30_execution/run_state.json").read_bytes())
    receipt = state["control"]["semantic_registrations"][_tx(run, request).stem]
    assert result.data["receipt"] == receipt
    assert receipt["content_sha256"] == request["expected_source_sha256"]
    assert receipt["producer_role"] == "intent_realizer"
    before = {str(p.relative_to(run)): p.read_bytes() for p in run.rglob("*") if p.is_file()}
    replay = _call(tmp_path, run, request)
    assert replay.ok, replay.as_dict()
    assert replay.data["replayed"] is True and replay.data["is_current"] is True
    assert replay.data["receipt"] == receipt
    assert before == {str(p.relative_to(run)): p.read_bytes() for p in run.rglob("*") if p.is_file()}


def test_historical_replay_ignores_latest_and_live_inputs(tmp_path: Path) -> None:
    run = _selected(tmp_path)
    first = _submission(tmp_path, run, "v1")
    assert _call(tmp_path, run, first).ok
    second = _submission(tmp_path, run, "v2", 2)
    assert _call(tmp_path, run, second).ok
    # Today's request need not equal the original role's inputs for read-only
    # recovery. Consumers must validate the current run separately.
    (run / "00_intake/build_request.yaml").write_bytes(b"changed after registration\n")
    before = (run / "30_execution/run_state.json").read_bytes()
    result = _call(tmp_path, run, first)
    assert result.ok, result.as_dict()
    assert result.data["replayed"] and result.data["is_current"] is False
    assert (run / "30_execution/run_state.json").read_bytes() == before
    assert (run / "10_framing/problem_frame.md").read_bytes() == second["source_path"].read_bytes()


@pytest.mark.parametrize("digest", [None, "INVALID", "0" * 64])
def test_expected_digest_is_mandatory_and_checked(tmp_path: Path, digest: str | None) -> None:
    run = _selected(tmp_path)
    request = _submission(tmp_path, run)
    request["expected_source_sha256"] = digest
    before = (run / "30_execution/run_state.json").read_bytes()
    result = _call(tmp_path, run, request)
    assert not result.ok
    assert (run / "30_execution/run_state.json").read_bytes() == before
    assert not (run / "10_framing/problem_frame.md").exists()


@pytest.mark.parametrize("change", ["modify", "remove", "version"])
def test_stale_inputs_reject_before_activation(tmp_path: Path, change: str) -> None:
    run = _selected(tmp_path)
    extra = tmp_path / "input.txt"
    extra.write_text("supplied local context", encoding="utf-8")
    request = _submission(tmp_path, run, input_refs=(extra,))
    if change == "modify":
        extra.write_text("changed", encoding="utf-8")
    elif change == "remove":
        extra.unlink()
    else:
        path = run / "30_execution/run_state.json"
        state = json.loads(path.read_bytes())
        state["active_artifacts"]["build_request"]["version"] = 2
        atomic_write_json(path, state)
    result = _call(tmp_path, run, request)
    assert not result.ok
    assert ("BOUNDARY_VIOLATION" if change == "version" else "SUBMISSION_ASSIGNMENT") in {d.code for d in result.diagnostics}
    assert not (run / "10_framing/problem_frame.md").exists()


def test_unassigned_source_and_wrong_body_version_reject(tmp_path: Path) -> None:
    run = _selected(tmp_path)
    request = _submission(tmp_path, run)
    wrong_source = tmp_path / "returned.md"
    wrong_source.write_bytes(request["source_path"].read_bytes())
    result = _call(tmp_path, run, {**request, "source_path": wrong_source})
    assert not result.ok and "SUBMISSION_ASSIGNMENT" in {d.code for d in result.diagnostics}
    request["source_path"].write_text(_problem_frame(2, owner="intent_realizer"), encoding="utf-8")
    result = _call(tmp_path, run, {**request, "expected_source_sha256": sha256_file(request["source_path"])})
    assert not result.ok and "ARTIFACT_VERSION_SEQUENCE" in {d.code for d in result.diagnostics}


@pytest.mark.parametrize("alter", ["baseline", "boundary", "source", "receipt", "history"])
def test_replay_requires_retained_provenance(tmp_path: Path, alter: str) -> None:
    run = _selected(tmp_path)
    request = _submission(tmp_path, run)
    assert _call(tmp_path, run, request).ok
    tx_path = _tx(run, request)
    if alter == "baseline":
        path = run / "30_execution/role_boundary/baselines" / tx_path.name
    elif alter == "boundary":
        path = run / "30_execution/role_boundary/results" / tx_path.name
    elif alter == "source":
        path = request["source_path"]
    elif alter == "receipt":
        path = run / "30_execution/run_state.json"
        state = json.loads(path.read_bytes())
        state["control"]["semantic_registrations"][tx_path.stem]["registered_at"] = STARTED_AT
        atomic_write_json(path, state)
        path = None
    else:
        newer = _submission(tmp_path, run, "newer", 2)
        assert _call(tmp_path, run, newer).ok
        path = run / "10_framing/history/problem_frame.v1.md"
    if path is not None:
        path.write_bytes(b"altered retained evidence\n")
    before = (run / "30_execution/run_state.json").read_bytes()
    assert not _call(tmp_path, run, request).ok
    assert (run / "30_execution/run_state.json").read_bytes() == before


def test_selected_persist_cannot_bypass_admission(tmp_path: Path) -> None:
    run = _selected(tmp_path)
    request = _submission(tmp_path, run)
    result = persist_semantic_artifact(tmp_path, run, artifact_key="problem_frame", source_path=request["source_path"],
                                      source_invocation_ref="a", boundary_evidence_ref="unused")
    assert not result.ok and "FINALIZE_REQUIRED" in {d.code for d in result.diagnostics}
    assert not (run / "10_framing/problem_frame.md").exists()


@pytest.mark.parametrize("point", ["before_prepare", "prepare", "history", "artifact", "state"])
def test_actual_process_exit_is_recoverable(tmp_path: Path, point: str) -> None:
    run = _selected(tmp_path)
    if point == "history":
        assert _call(tmp_path, run, _submission(tmp_path, run, "prior")).ok
    request = _submission(tmp_path, run, version=2 if point == "history" else 1)
    state_path = run / "30_execution/run_state.json"
    before = state_path.read_bytes()
    serializable = {key: str(value) if isinstance(value, Path) else value for key, value in request.items()}
    script = """
import json, os, sys
from pathlib import Path
import pipeline_control.artifacts as a
import pipeline_control.finalize_journal as j
root, run, request, point = Path(sys.argv[1]), Path(sys.argv[2]), json.loads(sys.argv[3]), sys.argv[4]
request['source_path'] = Path(request['source_path'])
if point in ('prepare', 'before_prepare'):
    original = j.atomic_write_json
    target = j.transaction_path(run, request['role'], request['invocation_ref'])
else:
    original = a.atomic_write_bytes if point in ('artifact', 'history') else a.atomic_write_json
    target = run / ({'artifact':'10_framing/problem_frame.md', 'history':'10_framing/history/problem_frame.v1.md', 'state':'30_execution/run_state.json'}[point])
def stopped(path, payload):
    if path == target and point == 'before_prepare':
        os._exit(71)
    result = original(path, payload)
    if path == target:
        os._exit(71)
    return result
if point in ('artifact', 'history'): a.atomic_write_bytes = stopped
elif point in ('prepare', 'before_prepare'): j.atomic_write_json = stopped
else: a.atomic_write_json = stopped
a.finalize_semantic_return(root, run, **request)
"""
    env = {**os.environ, "PYTHONPATH": str(Path(artifacts.__file__).resolve().parent.parent)}
    stopped = subprocess.run([sys.executable, "-c", script, str(tmp_path), str(run), json.dumps(serializable), point], env=env, capture_output=True, text=True)
    assert stopped.returncode == 71, stopped.stderr
    if point == "before_prepare":
        assert not _tx(run, request).exists()
        assert state_path.read_bytes() == before
        assert not (run / "10_framing/problem_frame.md").exists()
        assert _call(tmp_path, run, request).ok
        return
    assert journal.read_transaction(_tx(run, request))["status"] == "PREPARED"
    assert journal.pending_transaction_diagnostics(run)
    recovered = _call(tmp_path, run, request)
    if point == "state":
        assert recovered.ok and recovered.data["replayed"], recovered.as_dict()
    else:
        assert not recovered.ok
        assert state_path.read_bytes() == before
        assert journal.read_transaction(_tx(run, request))["status"] == "ROLLED_BACK"
        assert _call(tmp_path, run, request).ok
    assert not journal.pending_transaction_diagnostics(run)


def test_recovery_conflict_does_not_overwrite_later_work(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    run = _selected(tmp_path)
    request = _submission(tmp_path, run)
    original = artifacts.atomic_write_bytes
    target = run / "10_framing/problem_frame.md"
    def stop(path, payload):
        result = original(path, payload)
        if path == target:
            raise KeyboardInterrupt()
        return result
    with monkeypatch.context() as patch:
        patch.setattr(artifacts, "atomic_write_bytes", stop)
        with pytest.raises(KeyboardInterrupt):
            _call(tmp_path, run, request)
    target.write_bytes(b"unrelated later work")
    before = (run / "30_execution/run_state.json").read_bytes()
    result = _call(tmp_path, run, request)
    assert not result.ok and "conflict" in result.diagnostics[0].message
    assert target.read_bytes() == b"unrelated later work"
    assert (run / "30_execution/run_state.json").read_bytes() == before


def test_second_attempt_prepare_and_rollback_interruptions(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    run = _selected(tmp_path)
    request = _submission(tmp_path, run)
    state_path = run / "30_execution/run_state.json"
    target = run / "10_framing/problem_frame.md"
    tx_path = _tx(run, request)
    original_bytes = artifacts.atomic_write_bytes
    def fail_first(path, payload):
        if path == target:
            raise OSError("ordinary first attempt write failure")
        return original_bytes(path, payload)
    with monkeypatch.context() as patch:
        patch.setattr(artifacts, "atomic_write_bytes", fail_first)
        assert not _call(tmp_path, run, request).ok
    terminal = journal.read_transaction(tx_path)
    assert terminal["status"] == "ROLLED_BACK"
    first_attempt = terminal["attempts"][0]
    # Intervening legitimate coordination work must survive second recovery.
    state = json.loads(state_path.read_bytes())
    state["run"]["next_allowed_action"] = "Root retained coordination decision."
    state["artifact"]["version"] += 1
    state["active_artifacts"]["run_state"]["version"] += 1
    atomic_write_json(state_path, state)
    fresh_prior = state_path.read_bytes()
    original_json = journal.atomic_write_json
    def stop_append(path, value):
        original_json(path, value)
        if path == tx_path and len(value["attempts"]) == 2 and value["status"] == "PREPARED":
            raise KeyboardInterrupt()
    with monkeypatch.context() as patch:
        patch.setattr(journal, "atomic_write_json", stop_append)
        with pytest.raises(KeyboardInterrupt):
            _call(tmp_path, run, request)
    prepared = journal.read_transaction(tx_path)
    assert prepared["attempts"][0] == first_attempt
    assert journal.snapshot_bytes(prepared["attempts"][1]["prior_state"]) == fresh_prior
    def stop_rollback(path, payload):
        result = original_bytes(path, payload)
        if path == state_path:
            raise KeyboardInterrupt()
        return result
    with monkeypatch.context() as patch:
        patch.setattr(artifacts, "atomic_write_bytes", stop_rollback)
        with pytest.raises(KeyboardInterrupt):
            _call(tmp_path, run, request)
    assert journal.read_transaction(tx_path)["status"] == "PREPARED"
    result = _call(tmp_path, run, request)
    assert not result.ok
    assert state_path.read_bytes() == fresh_prior
    assert not target.exists()
    rolled = journal.read_transaction(tx_path)
    assert rolled["status"] == "ROLLED_BACK" and len(rolled["attempts"]) == 2
    assert rolled["attempts"][0] == first_attempt
    assert _call(tmp_path, run, request).ok
    assert len(journal.read_transaction(tx_path)["attempts"]) == 3


def test_backup_corruption_blocks_recovery(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    run = _selected(tmp_path)
    request = _submission(tmp_path, run)
    original = artifacts.atomic_write_bytes
    target = run / "10_framing/problem_frame.md"
    def stop(path, payload):
        result = original(path, payload)
        if path == target:
            raise KeyboardInterrupt()
        return result
    with monkeypatch.context() as patch:
        patch.setattr(artifacts, "atomic_write_bytes", stop)
        with pytest.raises(KeyboardInterrupt):
            _call(tmp_path, run, request)
    path = _tx(run, request)
    value = json.loads(path.read_bytes())
    value["attempts"][0]["prior_state"]["sha256"] = "0" * 64
    atomic_write_json(path, value)
    before = target.read_bytes()
    assert not _call(tmp_path, run, request).ok
    assert target.read_bytes() == before


def test_legacy_explicit_digest_is_checked(tmp_path: Path) -> None:
    run = _write_run(tmp_path)
    start = start_role_boundary(tmp_path, run, role="problem_framer", invocation_ref="legacy", timestamp=STARTED_AT)
    assert start.ok
    source = tmp_path / "legacy.md"
    source.write_text(_problem_frame(), encoding="utf-8")
    request = dict(artifact_key="problem_frame", role="problem_framer", invocation_ref="legacy",
                   baseline_sha256=start.data["baseline_sha256"], source_path=source, timestamp=FINALIZED_AT)
    assert not _call(tmp_path, run, {**request, "expected_source_sha256": "0" * 64}).ok
    assert _call(tmp_path, run, {**request, "expected_source_sha256": sha256_bytes(source.read_bytes())}).ok


def _contract_submission(root: Path, run: Path, name="pc", version=1, *, blocked=False) -> dict:
    state = json.loads((run / "30_execution/run_state.json").read_bytes())
    body = _contract(version)
    entries = state["active_artifacts"]
    body["source_artifacts"] = [
        {"artifact_id": entries[key]["artifact_id"], "version": entries[key]["version"], "content_sha256": entries[key]["content_sha256"]}
        for key in ("build_request", "problem_frame") if entries[key] is not None
    ]
    if entries["problem_frame"] is None:
        body["requirements"][0]["source_refs"] = ["build-request@1"]
    if blocked:
        body["readiness"] = {"status": "BLOCKED", "rationale": "Owner reports unresolved intent ambiguity."}
    started = start_role_boundary(root, run, role="product_contract_agent", invocation_ref=name,
                                 artifact_key="product_contract", timestamp=STARTED_AT)
    assert started.ok, started.as_dict()
    source = root / started.data["submission_path"]
    source.write_text(yaml.safe_dump(body, sort_keys=False), encoding="utf-8")
    return dict(artifact_key="product_contract", role="product_contract_agent", invocation_ref=name,
                baseline_sha256=started.data["baseline_sha256"], source_path=source,
                expected_source_sha256=sha256_file(source), timestamp=FINALIZED_AT)


@pytest.mark.parametrize("direct", [False, True])
def test_contract_admission_consumes_actual_workflow_inputs(tmp_path: Path, direct: bool) -> None:
    run = _selected(tmp_path)
    if direct:
        path = run / "00_intake/build_request.yaml"
        request_body = yaml.safe_load(path.read_bytes())
        request_body["handoff"]["next_stage"] = "contract"
        path.write_text(yaml.safe_dump(request_body, sort_keys=False), encoding="utf-8")
        state_path = run / "30_execution/run_state.json"
        state = json.loads(state_path.read_bytes())
        state["active_artifacts"]["build_request"]["content_sha256"] = sha256_file(path)
        atomic_write_json(state_path, state)
    else:
        brief = _submission(tmp_path, run, "brief")
        assert _call(tmp_path, run, brief).ok
    request = _contract_submission(tmp_path, run)
    result = _call(tmp_path, run, request)
    assert result.ok, result.as_dict()
    baseline_path = run / "30_execution/role_boundary/baselines" / _tx(run, request).name
    inputs = json.loads(baseline_path.read_bytes())["submission"]["inputs"]
    assert {i["artifact_id"] for i in inputs} == ({"build-request"} if direct else {"build-request", "problem-frame"})
    prior = (run / "20_contract/product_contract.yaml").read_bytes()
    newer = _contract_submission(tmp_path, run, "pc2", 2)
    assert _call(tmp_path, run, newer).ok
    assert (run / "20_contract/history/product_contract.v1.yaml").read_bytes() == prior
    replay = _call(tmp_path, run, request)
    assert replay.ok and replay.data["is_current"] is False


def test_unverified_report_admission_retains_missing_evidence(tmp_path: Path) -> None:
    run = _selected(tmp_path)
    assert _call(tmp_path, run, _submission(tmp_path, run, "brief")).ok
    assert _call(tmp_path, run, _contract_submission(tmp_path, run)).ok
    for version in (1, 2):
        name = f"vr{version}"
        started = start_role_boundary(tmp_path, run, role="independent_verifier", invocation_ref=name,
                                     artifact_key="verification_report", timestamp=STARTED_AT)
        assert started.ok, started.as_dict()
        source = tmp_path / started.data["submission_path"]
        body = _verification_report().replace("READY", "UNVERIFIED").replace("| PASS |", "| UNVERIFIED |")
        body = body.replace("- Version: `1`", f"- Version: `{version}`")
        body = body.replace("## Missing or Unusable Evidence\n\nNone.", "## Missing or Unusable Evidence\n\nCandidate archive, manifest, inspection and harness were not supplied.")
        source.write_text(body, encoding="utf-8")
        request = dict(artifact_key="verification_report", role="independent_verifier", invocation_ref=name,
                       baseline_sha256=started.data["baseline_sha256"], source_path=source,
                       expected_source_sha256=sha256_file(source), timestamp=FINALIZED_AT)
        result = _call(tmp_path, run, request)
        assert result.ok, result.as_dict()
        inputs = started.data["submission"]["inputs"]
        missing = [i for i in inputs if i["availability"] == "MISSING"]
        assert missing and all("content_sha256" not in i for i in missing)
    state = json.loads((run / "30_execution/run_state.json").read_bytes())
    assert state["control"]["verification_validation_identity"] is None
    assert state["control"]["latest_verification_result"] is None
    assert not any(s["status"] == "PASSED" and s["id"] in {"verification", "release"} for s in state["stages"])
    assert (run / "40_verification/history/verification_report.v1.md").is_file()


def test_blocked_contract_replacement_restores_passed_active_contract(tmp_path: Path) -> None:
    run = _selected(tmp_path)
    assert _call(tmp_path, run, _submission(tmp_path, run, "brief")).ok
    assert _call(tmp_path, run, _contract_submission(tmp_path, run)).ok
    state_path = run / "30_execution/run_state.json"
    state = json.loads(state_path.read_bytes())
    for stage in state["stages"]:
        if stage["id"] in {"framing", "contract"}:
            stage["status"] = "PASSED"
            state["gates"].append({"id": stage["gate_id"], "status": "PASSED", "evidence_refs": ["owner-evidence"], "rationale": "Accepted owner artifact."})
    state["run"]["current_stage"] = "contract"
    atomic_write_json(state_path, state)
    assert validate_run_directory(tmp_path, run).ok
    request = _contract_submission(tmp_path, run, "blocked", 2, blocked=True)
    prior_state = state_path.read_bytes()
    canonical = run / "20_contract/product_contract.yaml"
    prior_contract = canonical.read_bytes()
    result = _call(tmp_path, run, request)
    assert not result.ok and "STAGE_READINESS" in {d.code for d in result.diagnostics}
    assert state_path.read_bytes() == prior_state and canonical.read_bytes() == prior_contract
    assert request["source_path"].is_file() and "failed_attempt_ref" in result.data
    assert journal.read_transaction(_tx(run, request))["status"] == "ROLLED_BACK"
    # A fresh, ready invocation can still use version 2 after rejection.
    ready = _contract_submission(tmp_path, run, "ready", 2)
    assert _call(tmp_path, run, ready).ok


@pytest.mark.parametrize("selected", [False, True])
@pytest.mark.parametrize("damage", ["corrupt", "delete", "selector"])
def test_finalize_accounts_for_damaged_state(tmp_path: Path, selected: bool, damage: str) -> None:
    if selected:
        run = _selected(tmp_path)
        request = _submission(tmp_path, run)
    else:
        run = _write_run(tmp_path)
        started = start_role_boundary(tmp_path, run, role="problem_framer", invocation_ref="x", timestamp=STARTED_AT)
        assert started.ok
        source = tmp_path / "return.md"
        source.write_text(_problem_frame(), encoding="utf-8")
        request = dict(artifact_key="problem_frame", role="problem_framer", invocation_ref="x",
                       baseline_sha256=started.data["baseline_sha256"], source_path=source, timestamp=FINALIZED_AT)
    path = run / "30_execution/run_state.json"
    before = path.read_bytes()
    if damage == "corrupt":
        path.write_bytes(b"{bad json")
    elif damage == "delete":
        path.unlink()
    else:
        state = json.loads(before)
        state["control"]["semantic_role_boundary"] = "unsupported"
        atomic_write_json(path, state)
    result = _call(tmp_path, run, request)
    assert not result.ok and "BOUNDARY_VIOLATION" in {d.code for d in result.diagnostics}, result.as_dict()
    assert path.read_bytes() == before


@pytest.mark.parametrize("drift", ["state", "artifact"])
def test_in_process_rollback_never_overwrites_unrecognized_bytes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, drift: str) -> None:
    run = _selected(tmp_path)
    request = _submission(tmp_path, run)
    original = artifacts.validate_run_directory
    calls = 0
    path = run / ("30_execution/run_state.json" if drift == "state" else "10_framing/problem_frame.md")
    def changed(root, candidate_run):
        nonlocal calls
        calls += 1
        if calls == 2:
            path.write_bytes(b"foreign concurrent bytes")
            raise OSError("injected post-validation conflict")
        return original(root, candidate_run)
    monkeypatch.setattr(artifacts, "validate_run_directory", changed)
    result = _call(tmp_path, run, request)
    assert not result.ok and "FINALIZE_RECOVERY_CONFLICT" in {d.code for d in result.diagnostics}
    assert path.read_bytes() == b"foreign concurrent bytes"
    assert journal.read_transaction(_tx(run, request))["status"] == "PREPARED"


def test_corrected_producer_bytes_require_fresh_invocation(tmp_path: Path) -> None:
    run = _selected(tmp_path)
    request = _submission(tmp_path, run)
    request["source_path"].write_text(_problem_frame(2, owner="intent_realizer"), encoding="utf-8")
    request["expected_source_sha256"] = sha256_file(request["source_path"])
    assert not _call(tmp_path, run, request).ok
    request["source_path"].write_text(_problem_frame(1, owner="intent_realizer"), encoding="utf-8")
    request["expected_source_sha256"] = sha256_file(request["source_path"])
    result = _call(tmp_path, run, request)
    assert not result.ok and "SUBMISSION_AUDITED_SHA256" in {d.code for d in result.diagnostics}
    assert _call(tmp_path, run, _submission(tmp_path, run, "fresh")).ok


@pytest.mark.parametrize("field", ["path", "boundary_evidence_ref", "artifact_id", "semantic_owner"])
def test_replay_rejects_contradictory_active_identity(tmp_path: Path, field: str) -> None:
    run = _selected(tmp_path)
    request = _submission(tmp_path, run)
    assert _call(tmp_path, run, request).ok
    path = run / "30_execution/run_state.json"
    state = json.loads(path.read_bytes())
    state["active_artifacts"]["problem_frame"][field] = "contradictory"
    atomic_write_json(path, state)
    result = _call(tmp_path, run, request)
    assert not result.ok


@pytest.mark.parametrize("status", [[], {}, None, 7])
def test_malformed_journal_status_fails_closed(tmp_path: Path, status) -> None:
    run = _selected(tmp_path)
    path = run / journal.DIRECTORY / "malformed.json"
    atomic_write_json(path, {"schema_version": "1.0", "artifact_type": "semantic-finalize-transaction", "status": status, "attempts": [{}]})
    assert journal.pending_transaction_diagnostics(run)[0].code == "FINALIZE_TRANSACTION_INVALID"


@pytest.mark.parametrize("condition", ["unsupported", "pending"])
def test_invalid_timestamp_respects_mutation_preflight(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, condition: str) -> None:
    run = _selected(tmp_path)
    request = _submission(tmp_path, run)
    if condition == "unsupported":
        path = run / "30_execution/run_state.json"
        state = json.loads(path.read_bytes())
        state["control"]["semantic_role_boundary"] = "unknown"
        atomic_write_json(path, state)
    else:
        original = artifacts.atomic_write_bytes
        target = run / "10_framing/problem_frame.md"
        def stop(path, payload):
            result = original(path, payload)
            if path == target:
                raise KeyboardInterrupt()
            return result
        with monkeypatch.context() as patch:
            patch.setattr(artifacts, "atomic_write_bytes", stop)
            with pytest.raises(KeyboardInterrupt):
                _call(tmp_path, run, request)
    before = {str(p.relative_to(run)): p.read_bytes() for p in run.rglob("*") if p.is_file()}
    result = _call(tmp_path, run, {**request, "timestamp": "invalid"})
    assert not result.ok
    assert before == {str(p.relative_to(run)): p.read_bytes() for p in run.rglob("*") if p.is_file()}


def test_nonregular_target_is_recovery_conflict(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    run = _selected(tmp_path)
    request = _submission(tmp_path, run)
    original = artifacts.atomic_write_bytes
    target = run / "10_framing/problem_frame.md"
    def stop(path, payload):
        result = original(path, payload)
        if path == target:
            raise KeyboardInterrupt()
        return result
    with monkeypatch.context() as patch:
        patch.setattr(artifacts, "atomic_write_bytes", stop)
        with pytest.raises(KeyboardInterrupt):
            _call(tmp_path, run, request)
    target.unlink()
    target.mkdir()
    before = (run / "30_execution/run_state.json").read_bytes()
    result = _call(tmp_path, run, request)
    assert not result.ok and "plain regular file" in result.diagnostics[0].message
    assert target.is_dir()
    assert (run / "30_execution/run_state.json").read_bytes() == before
    assert journal.read_transaction(_tx(run, request))["status"] == "PREPARED"


def test_rolled_back_retry_cannot_clear_later_boundary_violation(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    run = _selected(tmp_path)
    request = _submission(tmp_path, run, "old")
    original = artifacts.atomic_write_bytes
    target = run / "10_framing/problem_frame.md"
    def failed(path, payload):
        if path == target:
            raise OSError("first registration cannot be installed")
        return original(path, payload)
    with monkeypatch.context() as patch:
        patch.setattr(artifacts, "atomic_write_bytes", failed)
        assert not _call(tmp_path, run, request).ok
    assert journal.read_transaction(_tx(run, request))["status"] == "ROLLED_BACK"
    later = _submission(tmp_path, run, "later")
    state_path = run / "30_execution/run_state.json"
    state = json.loads(state_path.read_bytes())
    state["run"]["next_allowed_action"] = "Unauthorized role state change."
    atomic_write_json(state_path, state)
    violation = finish_role_boundary(tmp_path, run, role=later["role"], invocation_ref=later["invocation_ref"], baseline_sha256=later["baseline_sha256"], timestamp=FINALIZED_AT)
    assert not violation.ok and violation.data["status"] == "BOUNDARY_VIOLATION"
    latest = run / "30_execution/role_boundary/latest.json"
    before = latest.read_bytes()
    retry = _call(tmp_path, run, {**request, "timestamp": "2026-09-01T09:03:00+09:00"})
    assert not retry.ok
    assert latest.read_bytes() == before
    assert not target.exists()
