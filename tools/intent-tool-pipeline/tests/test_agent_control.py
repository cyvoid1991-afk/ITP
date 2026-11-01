"""Selected-policy admission and pre-side-effect compatibility checks."""

import json
from pathlib import Path
import subprocess
import sys

import pytest
import yaml

from pipeline_control.boundary import finish_role_boundary, start_role_boundary
from pipeline_control.cli import build_parser
from pipeline_control.io_utils import atomic_write_json
from pipeline_control.packaging import create_package, inspect_package
from pipeline_control.procedures import load_role_assignment
from pipeline_control.state import update_bounce_back, update_state
from pipeline_control.test_runner import run_test_plan
from pipeline_control.validation import validate_control_metadata, validate_run_directory
from pipeline_control.verifier_harness import prepare_verification
from test_build_tool_pipeline_skill import _request
from test_two_workflows import STAMP, initializer


def _request_source(root):
    request = _request(STAMP)
    request["project"]["project_id"] = "t"
    request["handoff"]["next_stage"] = "contract"
    request["source_context"] = []
    source = root / "request.yaml"
    source.write_text(yaml.safe_dump(request), encoding="utf-8")
    return source


def _initialize(root, revision="1.1"):
    source = _request_source(root)
    result = initializer.initialize(root, source, None, STAMP, control_revision=revision)
    if revision in ("1.0", "1.1", "1.2"):
        assert result["ok"], result
    return result, root / "workspace/build_runs/t"


@pytest.mark.parametrize("revision,maximum", [("1.0", 2), ("1.1", 4), ("1.2", 4)])
def test_explicit_initializer_preserves_each_control_revision(tmp_path, revision, maximum):
    result, run = _initialize(tmp_path, revision)
    assert result["ok"], result
    assert result["data"]["operational_status"] == {
        "1.0": "LEGACY", "1.1": "ARTIFACT_SUBMISSION", "1.2": "PROCEDURE_BOUND",
    }[revision]
    state = json.loads((run / "30_execution/run_state.json").read_text())
    assert state["control"]["semantic_role_boundary"] == revision
    assert state["repair"]["maximum_attempts"] == maximum
    assert ("semantic_registrations" in state["control"]) == (revision in {"1.1", "1.2"})
    assert ("rounds" in state["repair"]) == (revision in {"1.1", "1.2"})
    assert validate_run_directory(tmp_path, run).ok


def _initialize_default(root, entry):
    source = root / "request.yaml"
    if entry == "api":
        return initializer.initialize(root, source, None, STAMP)
    process = subprocess.run(
        [sys.executable, str(Path(initializer.__file__)), "--project-root", str(root),
         "--request", str(source), "--timestamp", STAMP, "--format", "json"],
        cwd=root, capture_output=True, text=True, timeout=60,
    )
    assert process.returncode in (0, 1), process.stdout + process.stderr
    result = json.loads(process.stdout)
    assert process.returncode == (0 if result["ok"] else 1), result
    return result


@pytest.mark.parametrize("entry", ["api", "cli"])
def test_default_initializer_creates_procedure_bound_four_round_run(tmp_path_factory, entry):
    root = tmp_path_factory.mktemp("d8")
    _request_source(root)
    result = _initialize_default(root, entry)
    assert result["ok"], result
    assert result["data"]["control_revision"] == "1.2"
    assert result["data"]["operational_status"] == "PROCEDURE_BOUND"
    assert result["data"]["repair_maximum_attempts"] == 4
    run = root / result["data"]["run_dir"]
    state = json.loads((run / "30_execution/run_state.json").read_bytes())
    assert state["control"]["semantic_role_boundary"] == "1.2"
    assert state["control"]["semantic_registrations"] == {}
    assert state["control"]["latest_verification_result"] is None
    assert state["repair"] == {
        "active_attempt": 0, "maximum_attempts": 4, "last_failure_ref": None, "rounds": [],
    }
    assert validate_run_directory(root, run).ok

    started = start_role_boundary(root, run, role="product_contract_agent", invocation_ref="c1",
                                  artifact_key="product_contract", timestamp=STAMP)
    assert started.ok, started.as_dict()
    loaded = load_role_assignment(root, run, role="product_contract_agent", invocation_ref="c1",
                                  baseline_sha256=started.data["baseline_sha256"])
    assert loaded.ok, loaded.as_dict()
    assert loaded.data["procedure_binding"]["workflow"] == "B"
    assert loaded.data["required_result_binding"]["control_revision"] == "1.2"
    assert loaded.data["required_result_binding"]["assignment_sha256"] == started.data["baseline_sha256"]
    assert loaded.data["procedures"]
    assert Path(loaded.data["output_path"]) == root / started.data["submission_path"]
    assert not Path(loaded.data["output_path"]).exists()


@pytest.mark.parametrize("entry", ["api", "cli"])
@pytest.mark.parametrize("revision", ["1.0", "1.1", "1.2"])
def test_default_initializer_refuses_existing_run_without_migration(tmp_path, entry, revision):
    _, run = _initialize(tmp_path, revision)
    (run / "30_execution/retained.txt").write_text("Retained run evidence.\n", encoding="utf-8")
    before = _snapshot(tmp_path)
    result = _initialize_default(tmp_path, entry)
    assert not result["ok"]
    assert [item["code"] for item in result["diagnostics"]] == ["RUN_EXISTS"]
    assert _snapshot(tmp_path) == before


@pytest.mark.parametrize("revision", [None, "1.3", "", {}, 1.1])
def test_initializer_rejects_unknown_without_allocating(tmp_path, revision):
    result, run = _initialize(tmp_path, revision)
    assert not result["ok"]
    assert not run.exists()
    assert not (tmp_path / "workspace").exists()


@pytest.mark.parametrize("change", [
    lambda s: s["control"].pop("intent_realization"),
    lambda s: s["control"].pop("semantic_registrations"),
    lambda s: s["control"].pop("latest_verification_result"),
    lambda s: s["control"].update(semantic_registrations=[]),
    lambda s: s["control"].update(semantic_role_boundary=None),
    lambda s: s["control"].update(semantic_role_boundary=[]),
    lambda s: s["control"].update(semantic_role_boundary="1.0"),
    lambda s: s["repair"].update(active_attempt=True),
    lambda s: s["repair"].update(maximum_attempts=5),
    lambda s: s["repair"].update(rounds=[{"number": 1}]),
])
def test_incompatible_selected_metadata_rejects(change):
    state = initializer._state("t", "t", STAMP, control_revision="1.1")
    change(state)
    assert validate_control_metadata(state)


def _writers(root, run):
    absent = root / "not-read.json"
    return [
        lambda: run_test_plan(root, run, absent),
        lambda: create_package(root, run, absent),
        lambda: inspect_package(root, run, absent),
        lambda: prepare_verification(root, run, absent),
        lambda: update_state(run, project_root=root, to_stage="intake", stage_status="PASSED", gate_status="PASSED", evidence_refs=["test"], rationale="fixture", next_action="next"),
        lambda: update_bounce_back(run, project_root=root, action="create", payload={}),
        lambda: start_role_boundary(root, run, role="product_contract_agent", invocation_ref="x", artifact_key="product_contract"),
        lambda: finish_role_boundary(root, run, role="product_contract_agent", invocation_ref="x", baseline_sha256="0" * 64),
    ]


def _snapshot(root):
    return {str(p.relative_to(root)): p.read_bytes() for p in root.rglob("*") if p.is_file()}


@pytest.mark.parametrize("blocked_by", ["unknown", "pending"])
def test_all_run_writers_stop_before_side_effects(tmp_path, blocked_by):
    _, run = _initialize(tmp_path)
    if blocked_by == "unknown":
        path = run / "30_execution/run_state.json"
        state = json.loads(path.read_text())
        state["control"]["semantic_role_boundary"] = "future"
        atomic_write_json(path, state)
    else:
        # An unreadable/incomplete pending record must fail closed too.
        atomic_write_json(run / "30_execution/semantic_finalize/tx/x.json", {"status": "PREPARED"})
    before = _snapshot(tmp_path)
    for write in _writers(tmp_path, run):
        result = write()
        assert not result.ok, result.as_dict()
        assert any(d.code.startswith(("CONTROL", "FINALIZE", "TRANSACTION", "BOUNDARY_BASELINE")) for d in result.diagnostics), result.as_dict()
        assert _snapshot(tmp_path) == before


@pytest.mark.parametrize("stage,status", [("verification", "PASSED"), ("verification", "FAILED"), ("repair", "IN_PROGRESS"), ("release", "IN_PROGRESS")])
def test_selected_initial_state_cannot_skip_lifecycle_prerequisites(tmp_path, stage, status):
    _, run = _initialize(tmp_path)
    before = _snapshot(tmp_path)
    result = update_state(run, project_root=tmp_path, to_stage=stage, stage_status=status,
                          gate_status=status, evidence_refs=["test"], rationale="fixture", next_action="next")
    assert not result.ok, result.as_dict()
    assert any(d.code in {"TRANSITION_NOT_ALLOWED", "ROUND_RESULT"} for d in result.diagnostics), result.as_dict()
    assert all(d.code != "CONTROL_NOT_READY" for d in result.diagnostics), result.as_dict()
    assert _snapshot(tmp_path) == before


def test_cli_exposes_only_selected_artifact_interfaces():
    parser = build_parser()
    start = parser.parse_args(["role-boundary", "start", "--run-dir", "r", "--role", "product_contract_agent", "--invocation-ref", "x", "--artifact", "product_contract", "--input-ref", "i.md"])
    assert start.artifact == "product_contract" and start.input_ref == ["i.md"]
    finish = parser.parse_args(["finalize-semantic-return", "--run-dir", "r", "--artifact", "product_contract", "--role", "product_contract_agent", "--invocation-ref", "x", "--baseline-sha256", "a" * 64, "--source", "s", "--expected-source-sha256", "b" * 64])
    assert finish.expected_source_sha256 == "b" * 64


def test_uncontrolled_history_cannot_carry_selected_round_metadata():
    state = {"schema_version": "1.0", "repair": {"active_attempt": 0}}
    assert validate_control_metadata(state) == []
    state["repair"]["rounds"] = []
    assert any(d.code == "CONTROL_METADATA" for d in validate_control_metadata(state))
