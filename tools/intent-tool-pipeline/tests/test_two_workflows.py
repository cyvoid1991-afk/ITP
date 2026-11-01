"""Behavioral control fixtures; simulated semantic returns are not native verdicts."""

from __future__ import annotations

import importlib.util
import json
import sys
from copy import deepcopy
from pathlib import Path

import pytest
import yaml

from pipeline_control.artifacts import finalize_semantic_return
from pipeline_control.boundary import start_role_boundary
from pipeline_control.io_utils import sha256_file
from pipeline_control.packaging import create_package, inspect_package
from pipeline_control.revision import resolve_revision_baseline
from pipeline_control.state import update_bounce_back, update_state
from pipeline_control.test_runner import run_test_plan
from pipeline_control.verifier_harness import prepare_verification
from pipeline_control.validation import validate_run_directory, validate_run_state_data
from pipeline_control.workflow import validate_contract_sources, validate_run_state_context
from test_build_tool_pipeline_skill import INITIALIZER, _request
from test_semantic_finalize import _contract, _problem_frame
from test_pipeline_control import _contract as _package_contract, _verification_report, _write_package_fixture_assets
from test_verifier_harness import _commands, _write_plan


STAMP = "2026-09-13T00:00:00+09:00"
spec = importlib.util.spec_from_file_location("tw_init", INITIALIZER)
initializer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(initializer)


def _state(run: Path) -> dict:
    return json.loads((run / "30_execution/run_state.json").read_text(encoding="utf-8"))


def _new(root: Path, *, direct: bool, source_snapshot: bool = False) -> Path:
    request = _request(STAMP)
    request["project"]["project_id"] = "t"
    request["source_context"] = []
    if source_snapshot:
        source = root / "intent.md"
        source.write_text("Bound original intent and delegated boundaries.\n", encoding="utf-8")
        request["source_context"] = [{"source_id": "SRC-001", "type": "FILE", "path": "intent.md",
            "authority": "USER_PROVIDED", "description": "Original intent snapshot.", "content_sha256": sha256_file(source)}]
    request["target"] = {"repository_path": "source", "output_path": "deliverables/fixture_tool.zip"}
    request["handoff"]["next_stage"] = "contract" if direct else "framing"
    path = root / "request.yaml"
    path.write_text(yaml.safe_dump(request), encoding="utf-8")
    # This suite exercises legacy complete-body transport and repair semantics.
    result = initializer.initialize(root, path, None, STAMP, control_revision="1.0")
    assert result["ok"], result
    return root / "workspace/build_runs/t"


def _step(root: Path, run: Path, stage: str, status: str = "PASSED", **kwargs):
    return update_state(run, project_root=root, to_stage=stage,
        stage_status=status, gate_status=status, evidence_refs=["fixture-evidence"],
        rationale="Controlled two-workflow fixture.", next_action="Evaluate the next gate.", **kwargs)


def _activate(root: Path, run: Path, key: str, body: str, invocation: str):
    role = "intent_realizer" if key == "problem_frame" else "product_contract_agent"
    if key == "verification_report":
        role = "independent_verifier"
    start = start_role_boundary(root, run, role=role, invocation_ref=invocation)
    assert start.ok, start.as_dict()
    source = root / (invocation + (".yaml" if key == "product_contract" else ".md"))
    source.write_text(body, encoding="utf-8", newline="\n")
    return finalize_semantic_return(root, run, artifact_key=key, role=role,
        invocation_ref=invocation, baseline_sha256=start.data["baseline_sha256"], source_path=source)


def _current_contract(run: Path, *, version: int = 1) -> dict:
    body = _contract(version)
    active = _state(run)["active_artifacts"]
    body["source_artifacts"] = [
        {k: active[key][k] for k in ("artifact_id", "version", "content_sha256")}
        for key in ("build_request", "problem_frame") if active[key] is not None
    ]
    body["requirements"][0]["source_refs"] = ["build-request@1"]
    return body


@pytest.mark.parametrize("direct", [False, True], ids=["prepared", "direct"])
def test_intake_paths_preserve_contract_gate_and_semantic_owner(tmp_path: Path, direct: bool) -> None:
    run = _new(tmp_path, direct=direct)
    assert _state(run)["active_artifacts"]["build_request"]["content_sha256"] == sha256_file(run / "00_intake/build_request.yaml")
    rejected = _step(tmp_path, run, "contract", "IN_PROGRESS")
    assert not rejected.ok
    assert _step(tmp_path, run, "intake").ok
    if direct:
        assert not _step(tmp_path, run, "framing", "IN_PROGRESS").ok
    else:
        assert not _step(tmp_path, run, "contract", "IN_PROGRESS").ok
        assert _step(tmp_path, run, "framing", "IN_PROGRESS").ok
        activated = _activate(tmp_path, run, "problem_frame", _problem_frame(owner="intent_realizer"), "a1")
        assert activated.ok, activated.as_dict()
        assert _step(tmp_path, run, "framing").ok
    assert _step(tmp_path, run, "contract", "IN_PROGRESS").ok
    assert not _step(tmp_path, run, "contract").ok
    result = _activate(tmp_path, run, "product_contract", yaml.safe_dump(_current_contract(run)), "c1")
    assert result.ok, result.as_dict()
    assert _step(tmp_path, run, "contract").ok
    assert _step(tmp_path, run, "repository_analysis", "IN_PROGRESS").ok
    state = _state(run)
    assert state["active_artifacts"]["product_contract"]["semantic_owner"] == "product_contract_agent"
    assert state["repair"]["maximum_attempts"] == 2
    assert validate_run_directory(tmp_path, run).ok
    if direct:
        assert state["active_artifacts"]["problem_frame"] is None
        assert next(s for s in state["stages"] if s["id"] == "framing")["status"] == "PENDING"


def test_route_tampering_and_fabricated_framing_fail_without_mutation(tmp_path: Path) -> None:
    run = _new(tmp_path, direct=False)
    request_path = run / "00_intake/build_request.yaml"
    request = yaml.safe_load(request_path.read_text(encoding="utf-8"))
    request["handoff"]["next_stage"] = "contract"
    request_path.write_text(yaml.safe_dump(request), encoding="utf-8")
    before = (run / "30_execution/run_state.json").read_bytes()
    result = _step(tmp_path, run, "intake")
    assert not result.ok and "INTAKE_IDENTITY" in {d.code for d in result.diagnostics}
    assert (run / "30_execution/run_state.json").read_bytes() == before
    state = _state(run)
    state["active_artifacts"]["build_request"]["content_sha256"] = sha256_file(request_path)
    next(s for s in state["stages"] if s["id"] == "framing")["status"] = "PASSED"
    assert "DIRECT_INTAKE_STATE" in {d.code for d in validate_run_state_context(tmp_path, run, state)}


@pytest.mark.parametrize("key,value", [("stages", None), ("gates", None), ("run", None), ("active_artifacts", None), ("stages", [{"id": []}])])
def test_malformed_direct_state_returns_diagnostics(tmp_path: Path, key: str, value) -> None:
    run = _new(tmp_path, direct=True)
    state = _state(run)
    state[key] = value
    assert validate_run_state_context(tmp_path, run, state)


@pytest.mark.parametrize("version", [True, 1.0, 0, 2])
def test_wrong_source_identity_cannot_activate(tmp_path: Path, version) -> None:
    run = _new(tmp_path, direct=True)
    contract = _current_contract(run)
    contract["source_artifacts"][0]["version"] = version
    result = _activate(tmp_path, run, "product_contract", yaml.safe_dump(contract), "bad")
    assert not result.ok and "CONTRACT_SOURCE_IDENTITY" in {d.code for d in result.diagnostics}
    assert _state(run)["active_artifacts"]["product_contract"] is None


def test_prepared_delta_blocks_progress_but_owner_can_revise_contract(tmp_path: Path) -> None:
    run = _new(tmp_path, direct=False)
    assert _step(tmp_path, run, "intake").ok
    assert _activate(tmp_path, run, "problem_frame", _problem_frame(owner="intent_realizer"), "a1").ok
    assert _step(tmp_path, run, "framing").ok
    assert _activate(tmp_path, run, "product_contract", yaml.safe_dump(_current_contract(run)), "c1").ok
    assert _step(tmp_path, run, "contract").ok
    changed = _activate(tmp_path, run, "problem_frame", _problem_frame(2, owner="intent_realizer"), "a2")
    assert changed.ok, changed.as_dict()
    assert validate_run_directory(tmp_path, run).ok  # Repairable intermediate state.
    blocked = _step(tmp_path, run, "repository_analysis", "IN_PROGRESS")
    assert not blocked.ok and "CONTRACT_SOURCE_IDENTITY" in {d.code for d in blocked.diagnostics}
    current = _activate(tmp_path, run, "product_contract", yaml.safe_dump(_current_contract(run, version=2)), "c2")
    assert current.ok, current.as_dict()
    assert _step(tmp_path, run, "repository_analysis", "IN_PROGRESS").ok
    assert _state(run)["repair"]["active_attempt"] == 0


def test_declared_handoff_snapshot_drift_is_not_current(tmp_path: Path) -> None:
    run = _new(tmp_path, direct=True)
    source = tmp_path / "intent.md"
    source.write_text("Original user meaning", encoding="utf-8")
    request_path = run / "00_intake/build_request.yaml"
    request = yaml.safe_load(request_path.read_text(encoding="utf-8"))
    request["source_context"] = [{"source_id": "SRC-001", "type": "HANDOFF", "path": "intent.md", "content_sha256": sha256_file(source)}]
    request_path.write_text(yaml.safe_dump(request), encoding="utf-8")
    state = _state(run)
    state["active_artifacts"]["build_request"]["content_sha256"] = sha256_file(request_path)
    contract = _current_contract(run)
    contract["source_artifacts"][0]["content_sha256"] = sha256_file(request_path)
    assert not validate_contract_sources(tmp_path, run, state, contract)
    source.write_text("Root's unauthorized reinterpretation", encoding="utf-8")
    assert "HANDOFF_SOURCE_IDENTITY" in {d.code for d in validate_contract_sources(tmp_path, run, state, contract)}


def _verified(root: Path, *, direct: bool, source_snapshot: bool = False) -> Path:
    run = _new(root, direct=direct, source_snapshot=source_snapshot)
    assert _step(root, run, "intake").ok
    if not direct:
        assert _activate(root, run, "problem_frame", _problem_frame(owner="intent_realizer"), "a1").ok
        assert _step(root, run, "framing").ok
    contract = _package_contract()
    contract["source_artifacts"] = _current_contract(run)["source_artifacts"]
    contract["requirements"][0]["source_refs"] = ["build-request@1"]
    assert _activate(root, run, "product_contract", yaml.safe_dump(contract), "c1").ok
    for stage in ("contract", "repository_analysis"):
        assert _step(root, run, stage).ok
    assert _step(root, run, "implementation", "IN_PROGRESS").ok
    spec_path = _write_package_fixture_assets(root)
    package_spec = yaml.safe_load(spec_path.read_text(encoding="utf-8"))
    package_spec["manifest_path"] = (run / "50_release/release_manifest.json").relative_to(root).as_posix()
    spec_path.write_text(yaml.safe_dump(package_spec), encoding="utf-8")
    (root / "source/tests/test_tool.py").write_text(
        "import contextlib,io,runpy,unittest\n"
        "class Stable(unittest.TestCase):\n"
        " def test_output(self):\n"
        "  for _ in range(2):\n"
        "   out=io.StringIO()\n"
        "   with contextlib.redirect_stdout(out): runpy.run_path('tool.py')\n"
        "   self.assertEqual(out.getvalue(),'ok\\n')\n", encoding="utf-8")
    test_plan = root / "tests.json"
    test_plan.write_text(json.dumps({"schema_version": "1.0", "commands": [{
        "id": "suite", "argv": [sys.executable, "-m", "unittest", "discover", "-s", "tests"],
        "cwd": "source", "timeout_seconds": 30, "expected_exit_codes": [0], "artifact_paths": []}]}), encoding="utf-8")
    result = run_test_plan(root, run, test_plan, attempt_id="t1")
    assert result.ok, result.as_dict()
    assert _step(root, run, "implementation").ok
    assert create_package(root, run, spec_path).ok
    inspection = inspect_package(root, run, run / "50_release/release_manifest.json")
    assert inspection.ok, inspection.as_dict()
    commands = _commands()
    for cmd in commands:
        cmd["outputs"] = []
        if cmd["scenario"] == "complete_suite":
            cmd["argv"] = [sys.executable, "-m", "unittest", "discover", "-s", "tests"]
        elif cmd["scenario"] in {"help", "cli", "legacy_or_open_result"}:
            cmd["argv"] = [sys.executable, "tool.py"]
        elif cmd["scenario"] == "import":
            cmd["argv"] = [sys.executable, "-c", "import tool"]
        else:
            cmd["argv"] = [sys.executable, "-c", "from pathlib import Path; assert Path('README.md').is_file()"]
    plan = _write_plan(root, run, commands=commands)
    harness = prepare_verification(root, run, plan, scratch_root=root / "s", attempt_id="v1")
    assert harness.ok, harness.as_dict()
    assert harness.data["extraction_count"] == 1
    assert harness.data["cleanup_status"] == "PASS"
    assert _step(root, run, "verification", "IN_PROGRESS").ok
    verdict = _activate(root, run, "verification_report", _verification_report(), "iv1")
    assert verdict.ok, verdict.as_dict()
    result = _step(root, run, "verification")
    assert result.ok, result.as_dict()
    return run


@pytest.mark.parametrize("direct", [False, True], ids=["prepared", "direct"])
def test_full_candidate_lifecycle_and_exact_revision_baseline(tmp_path: Path, direct: bool) -> None:
    run = _verified(tmp_path, direct=direct)
    assert _step(tmp_path, run, "release", "IN_PROGRESS").ok
    result = _step(tmp_path, run, "release")
    assert result.ok, result.as_dict()
    assert validate_run_directory(tmp_path, run).ok
    state = _state(run)
    if direct:
        assert validate_run_state_data(state)  # State-only legacy defaults remain strict.
        assert not validate_run_state_context(tmp_path, run, state)
    binding = state["control"]["verification_validation_identity"]["candidate_binding"]
    revision = _request(STAMP)
    revision["project"]["request_kind"] = "REVISION"
    revision["target"]["repository_path"] = "source"
    revision["revision_of"] = {
        "run_id": "t", "archive_sha256": binding["archive_sha256"],
        "product_contract_ref": "product-contract@1", "product_contract_sha256": binding["product_contract_sha256"],
        "verification_report_ref": "verification-report@1",
        "verification_report_sha256": state["active_artifacts"]["verification_report"]["content_sha256"],
    }
    baseline = resolve_revision_baseline(tmp_path, revision)
    assert baseline.ok, baseline.as_dict()
    (tmp_path / "source/tool.py").write_text("print('pending revision')\n", encoding="utf-8")
    baseline = resolve_revision_baseline(tmp_path, revision)
    assert baseline.ok, baseline.as_dict()  # Live delta does not rewrite the released baseline.


def _review_event(root: Path, run: Path, classification: str = "EVIDENCE_GAP"):
    payload = {
        "origin": {"role": "independent_verifier", "result_artifact_ref": "verification-report@1", "invocation_ref": "iv1", "result": "READY"},
        "assigned_to": "root_codex", "classification": classification,
        "summary": "New intent evidence requires independent reassessment.",
        "affected_stages": ["verification", "release"], "affected_refs": ["verification-report@1"],
        "required_resolution": "Obtain a fresh verifier judgment against the current basis.",
        "retry": {"agent_role": "independent_verifier", "prior_invocation_ref": "iv1"},
    }
    result = update_bounce_back(run, project_root=root, action="create", payload=payload)
    assert result.ok, result.as_dict()
    return result.data["event_id"]


@pytest.mark.parametrize("from_release", [False, True])
def test_pass_reopens_only_with_recorded_basis_and_needs_new_verdict(tmp_path: Path, from_release: bool) -> None:
    run = _verified(tmp_path, direct=True)
    if from_release:
        assert _step(tmp_path, run, "release", "IN_PROGRESS").ok
    before = (run / "30_execution/run_state.json").read_bytes()
    assert not _step(tmp_path, run, "verification", "IN_PROGRESS", failure_ref="verification-report@1").ok
    assert (run / "30_execution/run_state.json").read_bytes() == before
    event_id = _review_event(tmp_path, run)
    result = _step(tmp_path, run, "verification", "IN_PROGRESS", failure_ref="verification-report@1")
    assert result.ok, result.as_dict()
    assert _state(run)["control"]["verification_validation_identity"] is not None
    assert next(s for s in _state(run)["stages"] if s["id"] == "release")["status"] == "PENDING"
    assert _state(run)["repair"]["active_attempt"] == 0
    resolved = update_bounce_back(run, project_root=tmp_path, action="resolve", payload={
        "event_id": event_id, "resolved_by": "root_codex", "resolution_type": "EVIDENCE_ADDED",
        "summary": "Added evidence; independent review is next.", "changed_artifact_refs": [],
        "decision_refs": [], "evidence_refs": ["new-evidence"],
        "retry": {"allowed": True, "change_basis": ["EVIDENCE_CHANGED"]},
    })
    assert resolved.ok, resolved.as_dict()
    refused = _step(tmp_path, run, "verification")
    assert not refused.ok and "UNCHANGED_VERIFIER_RETURN" in {d.code for d in refused.diagnostics}
    report = _verification_report().replace("- Version: `1`", "- Version: `2`")
    assert _activate(tmp_path, run, "verification_report", report, "iv2").ok
    assert _step(tmp_path, run, "verification").ok
    assert _step(tmp_path, run, "release", "IN_PROGRESS").ok
    assert _step(tmp_path, run, "release").ok
    _review_event(tmp_path, run)
    assert not _step(tmp_path, run, "verification", "IN_PROGRESS", failure_ref="verification-report@2").ok


@pytest.mark.parametrize("attempts", [0, 2])
def test_reopened_contract_change_requires_counted_repair(tmp_path: Path, attempts: int) -> None:
    run = _verified(tmp_path, direct=True)
    state_path = run / "30_execution/run_state.json"
    if attempts:
        state = _state(run)
        state["repair"].update(active_attempt=attempts, last_failure_ref="verification-report@1")
        state_path.write_text(json.dumps(state), encoding="utf-8")
    event_id = _review_event(tmp_path, run, "CONTRACT_CONTRADICTION")
    assert _step(tmp_path, run, "verification", "IN_PROGRESS", failure_ref="verification-report@1").ok
    contract = yaml.safe_load((run / "20_contract/product_contract.yaml").read_text(encoding="utf-8"))
    contract["artifact"]["version"] = 2
    contract["product"]["objective"] += " Source-authorized correction."
    refused = _activate(tmp_path, run, "product_contract", yaml.safe_dump(contract), "c2")
    assert not refused.ok and "REPAIR_REQUIRED" in {d.code for d in refused.diagnostics}
    failure = _verification_report().replace("- Version: `1`", "- Version: `2`").replace("READY", "NOT_READY").replace("| PASS |", "| FAIL |")
    assert _activate(tmp_path, run, "verification_report", failure, "iv2").ok
    assert _step(tmp_path, run, "verification", "FAILED").ok
    before = state_path.read_bytes()
    repair = _step(tmp_path, run, "repair", "IN_PROGRESS", failure_ref="verification-report@2")
    if attempts == 2:
        assert not repair.ok and "REPAIR_LIMIT" in {d.code for d in repair.diagnostics}
        assert state_path.read_bytes() == before
    else:
        assert repair.ok, repair.as_dict()
        assert _state(run)["repair"]["active_attempt"] == 1
        assert _state(run)["control"]["verification_validation_identity"] is None
        adopted = _activate(tmp_path, run, "product_contract", yaml.safe_dump(contract), "c3")
        assert adopted.ok, adopted.as_dict()
        spec_path = tmp_path / "package_spec.yaml"
        spec = yaml.safe_load(spec_path.read_text(encoding="utf-8"))
        spec["approval"]["contract_ref"] = "product-contract@2"
        spec_path.write_text(yaml.safe_dump(spec), encoding="utf-8")
        assert run_test_plan(tmp_path, run, tmp_path / "tests.json", attempt_id="t2").ok
        assert create_package(tmp_path, run, spec_path).ok
        assert inspect_package(tmp_path, run, run / "50_release/release_manifest.json").ok
        previous = yaml.safe_load((tmp_path / "verifier_plan.yaml").read_text(encoding="utf-8"))
        plan = _write_plan(tmp_path, run, commands=previous["commands"])
        rebound = yaml.safe_load(plan.read_text(encoding="utf-8"))
        rebound["binding"]["contract_ref"] = "product-contract@2"
        plan.write_text(yaml.safe_dump(rebound), encoding="utf-8")
        prepared = prepare_verification(tmp_path, run, plan, scratch_root=tmp_path / "s", attempt_id="v2")
        assert prepared.ok, prepared.as_dict()
        resolved = update_bounce_back(run, project_root=tmp_path, action="resolve", payload={
            "event_id": event_id, "resolved_by": "root_codex", "resolution_type": "CONTRACT_REVISED",
            "summary": "Owner corrected contract; fresh tests and candidate preparation passed.",
            "changed_artifact_refs": ["product-contract@2"], "decision_refs": [], "evidence_refs": ["t2", "v2"],
            "retry": {"allowed": True, "change_basis": ["INPUT_CHANGED", "EVIDENCE_CHANGED"]},
        })
        assert resolved.ok, resolved.as_dict()
        assert _step(tmp_path, run, "repair").ok
        assert _step(tmp_path, run, "verification", "IN_PROGRESS").ok
        report = _verification_report().replace("- Version: `1`", "- Version: `3`")
        assert _activate(tmp_path, run, "verification_report", report, "iv3").ok
        assert _step(tmp_path, run, "verification").ok
        assert _step(tmp_path, run, "release", "IN_PROGRESS").ok
        assert _step(tmp_path, run, "release").ok
        assert _state(run)["repair"]["active_attempt"] == 1


@pytest.mark.parametrize("repackage", [False, True])
def test_reopened_code_and_repackaging_cannot_bypass_repair(tmp_path: Path, repackage: bool) -> None:
    run = _verified(tmp_path, direct=True)
    event = _review_event(tmp_path, run)
    assert _step(tmp_path, run, "verification", "IN_PROGRESS", failure_ref="verification-report@1").ok
    (tmp_path / "source/tool.py").write_text("print('changed')\n", encoding="utf-8")
    # Even replacing all deterministic candidate evidence cannot authorize the
    # changed candidate as evidence-only review against the previous PASS.
    if repackage:
        spec_path = tmp_path / "package_spec.yaml"
        assert create_package(tmp_path, run, spec_path).ok
        assert inspect_package(tmp_path, run, run / "50_release/release_manifest.json").ok
    resolved = update_bounce_back(run, project_root=tmp_path, action="resolve", payload={
        "event_id": event, "resolved_by": "root_codex", "resolution_type": "EVIDENCE_ADDED",
        "summary": "Attempt to reuse evidence review for a changed candidate.", "changed_artifact_refs": [],
        "decision_refs": [], "evidence_refs": ["changed-candidate"],
        "retry": {"allowed": True, "change_basis": ["EVIDENCE_CHANGED"]},
    })
    assert resolved.ok, resolved.as_dict()
    report = _verification_report().replace("- Version: `1`", "- Version: `2`")
    assert _activate(tmp_path, run, "verification_report", report, "iv2").ok
    blocked = _step(tmp_path, run, "verification")
    assert not blocked.ok and "RELEASE_RECONCILIATION" in {d.code for d in blocked.diagnostics}
    assert _state(run)["repair"]["active_attempt"] == 0


def test_changed_return_file_cannot_replace_captured_contract(tmp_path: Path, monkeypatch) -> None:
    import pipeline_control.artifacts as artifacts

    run = _new(tmp_path, direct=True)
    original = _current_contract(run)
    saved_validate = artifacts._validate_body

    def mutate_after_capture(path, key, payload, owner):
        if key == "product_contract":
            changed = deepcopy(original)
            changed["source_artifacts"][0]["content_sha256"] = "0" * 64
            path.write_text(yaml.safe_dump(changed), encoding="utf-8")
        return saved_validate(path, key, payload, owner)

    monkeypatch.setattr(artifacts, "_validate_body", mutate_after_capture)
    result = _activate(tmp_path, run, "product_contract", yaml.safe_dump(original), "c1")
    assert result.ok, result.as_dict()
    actual = yaml.safe_load((run / "20_contract/product_contract.yaml").read_text(encoding="utf-8"))
    assert actual == original


def test_declared_source_drift_blocks_actual_adoption(tmp_path: Path) -> None:
    run = _new(tmp_path, direct=True, source_snapshot=True)
    (tmp_path / "intent.md").write_text("Changed source without owner review.", encoding="utf-8")
    result = _activate(tmp_path, run, "product_contract", yaml.safe_dump(_current_contract(run)), "c1")
    assert not result.ok and "HANDOFF_SOURCE_IDENTITY" in {d.code for d in result.diagnostics}
    assert _state(run)["active_artifacts"]["product_contract"] is None


def test_declared_source_drift_blocks_release(tmp_path: Path) -> None:
    run = _verified(tmp_path, direct=True, source_snapshot=True)
    (tmp_path / "intent.md").write_text("Changed source without owner review.", encoding="utf-8")
    before = (run / "30_execution/run_state.json").read_bytes()
    result = _step(tmp_path, run, "release", "IN_PROGRESS")
    assert not result.ok and "HANDOFF_SOURCE_IDENTITY" in {d.code for d in result.diagnostics}
    assert (run / "30_execution/run_state.json").read_bytes() == before
