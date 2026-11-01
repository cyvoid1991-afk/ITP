from __future__ import annotations

import json
import os
import sys
import zipfile
from pathlib import Path

import pytest
import yaml

from pipeline_control.artifacts import persist_semantic_artifact
from pipeline_control.boundary import finish_role_boundary, start_role_boundary
from pipeline_control.cli import build_parser, main
from pipeline_control.evidence import passing_test_results
from pipeline_control.io_utils import sha256_file
from pipeline_control.packaging import create_package, inspect_package
from pipeline_control.result import CommandResult
from pipeline_control.state import update_bounce_back, update_state
from pipeline_control.test_runner import run_test_plan
from pipeline_control.validation import validate_contract_file, validate_run_directory, validate_run_state_data


TIMESTAMP = "2026-08-15T12:00:00+09:00"
STAGES = [
    "intake",
    "framing",
    "contract",
    "repository_analysis",
    "implementation",
    "verification",
    "repair",
    "release",
]


def _contract() -> dict:
    return {
        "schema_version": "1.0",
        "artifact": {
            "artifact_id": "product-contract",
            "version": 1,
            "lifecycle_status": "ACTIVE",
            "owner_role": "product_contract_agent",
            "created_at": TIMESTAMP,
            "updated_at": TIMESTAMP,
        },
        "source_artifacts": [
            {"artifact_id": "build-request", "version": 1},
            {"artifact_id": "problem-frame", "version": 1},
        ],
        "readiness": {"status": "PASS", "rationale": "The observable contract is complete."},
        "product": {
            "name": "Fixture Tool",
            "objective": "Produce deterministic fixture output.",
            "primary_user": "Tester",
            "interface_summary": "A local CLI.",
        },
        "scope": {"included": ["CLI"], "excluded": ["Network access"]},
        "decisions": [
            {
                "id": "DEC-001",
                "statement": "Package the approved source, README, tests, and example.",
                "rationale": "Release inventory must be explicit.",
                "owner": "user",
                "status": "APPROVED",
                "source_ref": "build-request@1",
                "impact": "Defines the release inventory baseline.",
            }
        ],
        "assumptions": [],
        "blockers": [],
        "verification_policy": {
            "scope": "ALL_APPLICABLE_REQUIREMENTS",
            "default_nature": "DETERMINISTIC",
            "applicable_requirement_count": 1,
            "applicable_requirement_ids": ["REQ-001"],
            "llm_judgment_requirements": [],
        },
        "requirements": [
            {
                "id": "REQ-001",
                "category": "FUNCTIONAL",
                "title": "Stable output",
                "statement": "The command emits stable output.",
                "source_refs": ["problem-frame@1"],
                "acceptance_refs": ["ACC-001"],
            }
        ],
        "acceptance_methods": [
            {
                "id": "ACC-001",
                "requirement_refs": ["REQ-001"],
                "evidence_method": "TEST",
                "procedure": "Run the command twice.",
                "expected_result": "Both outputs match.",
                "evidence_required": ["captured output"],
            }
        ],
        "implementation_constraints": [],
        "documentation_obligations": [],
        "handoff": {
            "next_stage": "repository_analysis",
            "required_artifacts": ["product-contract@1"],
            "carried_assumptions": [],
            "open_blockers": [],
            "rationale": "The repository may be inspected.",
        },
    }


def _build_request() -> dict:
    return {
        "schema_version": "1.0",
        "artifact": {
            "artifact_id": "build-request",
            "version": 1,
            "lifecycle_status": "ACTIVE",
            "owner_role": "root_codex",
            "created_at": TIMESTAMP,
            "updated_at": TIMESTAMP,
        },
        "project": {"project_id": "fixture-run", "name": "Fixture", "request_kind": "NEW_PRODUCT", "summary": "Fixture run."},
        "requested_outcome": {"objective": "Validate the pipeline.", "deliverables": ["tool.py"], "success_summary": "All gates pass."},
        "source_context": [],
        "build_profile": {"profile_id": "test"},
        "target": {"repository_path": "source", "output_path": "deliverables/tool.zip"},
        "constraints": [],
        "user_decisions": [],
        "assumptions": [],
        "blockers": [],
        "handoff": {"readiness": "PASS", "next_stage": "framing", "required_inputs": ["build-request"], "rationale": "Ready."},
    }


def _problem_frame() -> str:
    headings = [
        "Contract Metadata",
        "Completion Status",
        "Input Reviewed",
        "Active Problem",
        "Objective and User Need",
        "Target UX Flow",
        "Scope",
        "Non-Scope",
        "Inputs and Outputs",
        "Failure Behavior",
        "Constraints",
        "Assumptions",
        "Decisions",
        "Open Issues and Blockers",
        "Validation Needs",
        "Handoff Readiness",
    ]
    sections = []
    for heading in headings:
        body = "Fixture content."
        if heading == "Contract Metadata":
            body = "\n".join(
                [
                    "- Schema version: `1.0`",
                    "- Artifact ID: `problem-frame`",
                    "- Version: `1`",
                    "- Lifecycle status: `ACTIVE`",
                    "- Semantic owner: `problem_framer`",
                ]
            )
        elif heading == "Completion Status":
            body = "PASS — The fixture is ready for contract authoring."
        sections.append(f"## {heading}\n\n{body}")
    return "# Problem Frame\n\n" + "\n\n".join(sections) + "\n"


def _verification_report() -> str:
    headings = [
        ("Contract Metadata", "\n".join(["- Schema version: `1.0`", "- Artifact ID: `verification-report`", "- Version: `1`", "- Lifecycle status: `ACTIVE`", "- Semantic owner: `independent_verifier`"])),
        ("Overall Assessment", "READY — All applicable requirements pass."),
        ("Inputs and Evidence Reviewed", "- Deterministic fixture output."),
        ("LLM Judgment Scope", "None."),
        (
            "Requirement Results",
            "| Requirement | Acceptance | Result | Evidence |\n| --- | --- | --- | --- |\n| REQ-001 | ACC-001 | PASS | Stable captured output. |",
        ),
        ("Missing or Unusable Evidence", "None."),
        ("Contract, Interface, and Documentation Drift", "None."),
        ("Repair Requests", "None."),
        ("Risks, Waivers, and Blockers", "None."),
        ("Revalidation Needs", "None."),
        ("Root Return", "- Overall assessment: `READY`"),
    ]
    return "# Verification Report\n\n" + "\n\n".join(f"## {heading}\n\n{body}" for heading, body in headings) + "\n"


def _state(current_stage: str = "release", current_status: str = "PASSED") -> dict:
    stage_records = []
    gates = []
    current_index = STAGES.index(current_stage)
    for index, stage_id in enumerate(STAGES):
        if stage_id == "repair" and current_stage == "release":
            status = "PENDING"
        elif index < current_index:
            status = "PASSED"
        elif index == current_index:
            status = current_status
        else:
            status = "PENDING"
        gate_id = f"GATE-{stage_id.upper()}"
        stage_records.append({"id": stage_id, "status": status, "gate_id": gate_id})
        if status != "PENDING":
            gates.append(
                {
                    "id": gate_id,
                    "status": status,
                    "evidence_refs": [f"{stage_id}-evidence"] if status == "PASSED" else [],
                    "rationale": f"{stage_id} fixture gate.",
                }
            )
    active = {
        "build_request": {"artifact_id": "build-request", "version": 1, "path": "00_intake/build_request.yaml"},
        "problem_frame": None,
        "product_contract": None,
        "run_state": {"artifact_id": "run-state", "version": 1, "path": "30_execution/run_state.json"},
        "verification_report": None,
    }
    if current_index >= STAGES.index("framing"):
        active["problem_frame"] = {"artifact_id": "problem-frame", "version": 1, "path": "10_framing/problem_frame.md"}
    if current_index >= STAGES.index("contract"):
        active["product_contract"] = {"artifact_id": "product-contract", "version": 1, "path": "20_contract/product_contract.yaml"}
    if current_stage in {"verification", "repair", "release"}:
        active["verification_report"] = {"artifact_id": "verification-report", "version": 1, "path": "40_verification/verification_report.md"}
    return {
        "schema_version": "1.0",
        "artifact": {
            "artifact_id": "run-state",
            "version": 1,
            "lifecycle_status": "ACTIVE",
            "owner_role": "root_codex",
            "created_at": TIMESTAMP,
            "updated_at": TIMESTAMP,
        },
        "run": {"run_id": "fixture-run-001", "project_id": "fixture-run", "current_stage": current_stage, "next_allowed_action": "Follow the recorded gate."},
        "stages": stage_records,
        "gates": gates,
        "active_artifacts": active,
        "repair": {"active_attempt": 0, "maximum_attempts": 2, "last_failure_ref": None},
        "bounce_back_events": [],
        "blockers": [],
        "required_approvals": [],
    }


def _write_run(project_root: Path, *, current_stage: str = "release", current_status: str = "PASSED") -> Path:
    run = project_root / "run"
    for directory in ("00_intake", "10_framing", "20_contract", "30_execution", "40_verification", "50_release"):
        (run / directory).mkdir(parents=True, exist_ok=True)
    (run / "00_intake" / "build_request.yaml").write_text(yaml.safe_dump(_build_request(), sort_keys=False), encoding="utf-8")
    (run / "10_framing" / "problem_frame.md").write_text(_problem_frame(), encoding="utf-8")
    (run / "20_contract" / "product_contract.yaml").write_text(yaml.safe_dump(_contract(), sort_keys=False), encoding="utf-8")
    (run / "40_verification" / "verification_report.md").write_text(_verification_report(), encoding="utf-8")
    (run / "30_execution" / "run_state.json").write_text(json.dumps(_state(current_stage, current_status), indent=2) + "\n", encoding="utf-8")
    return run


def _write_test_plan(project_root: Path, exit_code: int = 0) -> Path:
    plan = {
        "schema_version": "1.0",
        "commands": [
            {
                "id": "fixture-command",
                "argv": [sys.executable, "-c", f"import sys; print('fixture-output'); sys.exit({exit_code})"],
                "cwd": ".",
                "timeout_seconds": 30,
                "expected_exit_codes": [0],
                "artifact_paths": ["test_plan.json"],
            }
        ],
    }
    path = project_root / "test_plan.json"
    path.write_text(json.dumps(plan), encoding="utf-8")
    return path


def _enable_boundary_control(run: Path) -> dict:
    state_path = run / "30_execution" / "run_state.json"
    state = json.loads(state_path.read_text(encoding="utf-8"))
    state["schema_version"] = "1.1"
    state["control"] = {
        "semantic_role_boundary": "1.0",
        "verification_validation_identity": None,
    }
    state_path.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
    return state


def _clean_boundary(
    project_root: Path,
    run: Path,
    *,
    role: str,
    invocation_ref: str,
) -> str:
    started = start_role_boundary(
        project_root,
        run,
        role=role,
        invocation_ref=invocation_ref,
        timestamp=TIMESTAMP,
    )
    assert started.ok, started.as_dict()
    finished = finish_role_boundary(
        project_root,
        run,
        role=role,
        invocation_ref=invocation_ref,
        baseline_sha256=started.data["baseline_sha256"],
        timestamp="2026-08-15T12:01:00+09:00",
    )
    assert finished.ok, finished.as_dict()
    return str(finished.data["evidence_ref"])


def _persist_fixture_artifact(
    project_root: Path,
    run: Path,
    *,
    artifact_key: str,
    role: str,
    invocation_ref: str,
    body: str,
    suffix: str,
) -> CommandResult:
    evidence_ref = _clean_boundary(
        project_root,
        run,
        role=role,
        invocation_ref=invocation_ref,
    )
    source = project_root / f"returned_{artifact_key}{suffix}"
    source.write_text(body, encoding="utf-8")
    return persist_semantic_artifact(
        project_root,
        run,
        artifact_key=artifact_key,
        source_path=source,
        source_invocation_ref=invocation_ref,
        boundary_evidence_ref=evidence_ref,
        timestamp="2026-08-15T12:02:00+09:00",
    )


@pytest.mark.parametrize(
    "command",
    [
        "validate-run",
        "validate-contract",
        "update-state",
        "update-bounce-back",
        "role-boundary",
        "persist-artifact",
        "finalize-semantic-return",
        "run-tests",
        "package",
        "inspect-package",
    ],
)
def test_every_subcommand_exposes_help(command: str) -> None:
    with pytest.raises(SystemExit) as exc:
        build_parser().parse_args([command, "--help"])
    assert exc.value.code == 0


def test_validate_contract_accepts_valid_and_rejects_duplicate_mapping(tmp_path: Path) -> None:
    valid_path = tmp_path / "valid.yaml"
    valid_path.write_text(yaml.safe_dump(_contract(), sort_keys=False), encoding="utf-8")
    assert validate_contract_file(valid_path).ok

    invalid = _contract()
    invalid["requirements"].append(dict(invalid["requirements"][0]))
    invalid_path = tmp_path / "invalid.yaml"
    invalid_path.write_text(yaml.safe_dump(invalid, sort_keys=False), encoding="utf-8")
    result = validate_contract_file(invalid_path)
    assert not result.ok
    assert "ID_DUPLICATE" in {item.code for item in result.diagnostics}


def test_validate_contract_json_errors_are_machine_readable(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    invalid_path = tmp_path / "invalid.yaml"
    invalid_path.write_text("schema_version: '2.0'\n", encoding="utf-8")
    exit_code = main(["--project-root", str(tmp_path), "--format", "json", "validate-contract", "--contract", "invalid.yaml"])
    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 1
    assert payload["ok"] is False
    assert all(set(item) == {"code", "path", "message"} for item in payload["diagnostics"])


def test_validate_run_accepts_complete_fixture_and_rejects_missing_stage_directory(tmp_path: Path) -> None:
    run = _write_run(tmp_path)
    first = validate_run_directory(tmp_path, run)
    second = validate_run_directory(tmp_path, run)
    assert first.ok, first.as_dict()
    assert first.as_dict() == second.as_dict()

    (run / "50_release").rmdir()
    invalid = validate_run_directory(tmp_path, run)
    assert not invalid.ok
    assert "RUN_DIRECTORY" in {item.code for item in invalid.diagnostics}


@pytest.mark.parametrize(
    ("role", "relative_path"),
    [
        ("problem_framer", "10_framing/problem_frame.md"),
        ("product_contract_agent", "20_contract/product_contract.yaml"),
    ],
)
def test_read_only_semantic_role_canonical_mutation_is_boundary_violation(
    tmp_path: Path,
    role: str,
    relative_path: str,
) -> None:
    run = _write_run(tmp_path, current_stage="intake", current_status="PASSED")
    _enable_boundary_control(run)
    invocation_ref = f"{role}-direct-write"
    started = start_role_boundary(tmp_path, run, role=role, invocation_ref=invocation_ref, timestamp=TIMESTAMP)
    assert started.ok, started.as_dict()

    target = run / relative_path
    target.write_bytes(target.read_bytes() + b"\nunauthorized mutation\n")
    finished = finish_role_boundary(
        tmp_path,
        run,
        role=role,
        invocation_ref=invocation_ref,
        baseline_sha256=started.data["baseline_sha256"],
        timestamp="2026-08-15T12:01:00+09:00",
    )
    assert not finished.ok
    assert finished.data["status"] == "BOUNDARY_VIOLATION"
    assert finished.data["unauthorized_mutation_count"] >= 1
    evidence = json.loads((tmp_path / finished.data["evidence_ref"]).read_text(encoding="utf-8"))
    assert any(item["path"] == relative_path for item in evidence["unauthorized_mutations"])


def test_verifier_probe_write_is_allowed_and_canonical_report_write_is_rejected(tmp_path: Path) -> None:
    run = _write_run(tmp_path, current_stage="intake", current_status="PASSED")
    _enable_boundary_control(run)

    allowed_start = start_role_boundary(
        tmp_path,
        run,
        role="independent_verifier",
        invocation_ref="verifier-probe-only",
        timestamp=TIMESTAMP,
    )
    assert allowed_start.ok
    probes = run / "40_verification" / "probes"
    probes.mkdir()
    (probes / "result.json").write_text('{"status":"PASS"}\n', encoding="utf-8")
    allowed_finish = finish_role_boundary(
        tmp_path,
        run,
        role="independent_verifier",
        invocation_ref="verifier-probe-only",
        baseline_sha256=allowed_start.data["baseline_sha256"],
        timestamp="2026-08-15T12:01:00+09:00",
    )
    assert allowed_finish.ok, allowed_finish.as_dict()
    assert allowed_finish.data["status"] == "PASS"

    rejected_start = start_role_boundary(
        tmp_path,
        run,
        role="independent_verifier",
        invocation_ref="verifier-direct-report",
        timestamp="2026-08-15T12:02:00+09:00",
    )
    assert rejected_start.ok
    report = run / "40_verification" / "verification_report.md"
    report.write_text(_verification_report() + "\nDirect write.\n", encoding="utf-8")
    rejected_finish = finish_role_boundary(
        tmp_path,
        run,
        role="independent_verifier",
        invocation_ref="verifier-direct-report",
        baseline_sha256=rejected_start.data["baseline_sha256"],
        timestamp="2026-08-15T12:03:00+09:00",
    )
    assert not rejected_finish.ok
    evidence = json.loads((tmp_path / rejected_finish.data["evidence_ref"]).read_text(encoding="utf-8"))
    assert any(item["path"] == "40_verification/verification_report.md" for item in evidence["unauthorized_mutations"])


@pytest.mark.parametrize("operation", ["delete", "rename"])
def test_boundary_detects_unauthorized_delete_and_rename(tmp_path: Path, operation: str) -> None:
    run = _write_run(tmp_path, current_stage="intake", current_status="PASSED")
    _enable_boundary_control(run)
    invocation_ref = f"framer-{operation}"
    started = start_role_boundary(
        tmp_path,
        run,
        role="problem_framer",
        invocation_ref=invocation_ref,
        timestamp=TIMESTAMP,
    )
    assert started.ok
    source = run / "10_framing" / "problem_frame.md"
    if operation == "delete":
        source.unlink()
    else:
        source.rename(source.with_name("problem_frame_moved.md"))
    finished = finish_role_boundary(
        tmp_path,
        run,
        role="problem_framer",
        invocation_ref=invocation_ref,
        baseline_sha256=started.data["baseline_sha256"],
        timestamp="2026-08-15T12:01:00+09:00",
    )
    assert not finished.ok
    evidence = json.loads((tmp_path / finished.data["evidence_ref"]).read_text(encoding="utf-8"))
    assert operation in {item["operation"] for item in evidence["unauthorized_mutations"]}


@pytest.mark.parametrize("operation", ["truncate", "overwrite"])
def test_boundary_detects_unauthorized_truncate_and_overwrite(tmp_path: Path, operation: str) -> None:
    run = _write_run(tmp_path, current_stage="intake", current_status="PASSED")
    _enable_boundary_control(run)
    started = start_role_boundary(
        tmp_path,
        run,
        role="problem_framer",
        invocation_ref=f"framer-{operation}",
        timestamp=TIMESTAMP,
    )
    assert started.ok
    target = run / "10_framing" / "problem_frame.md"
    if operation == "truncate":
        target.write_bytes(b"")
    else:
        target.unlink()
        target.mkdir()
    finished = finish_role_boundary(
        tmp_path,
        run,
        role="problem_framer",
        invocation_ref=f"framer-{operation}",
        baseline_sha256=started.data["baseline_sha256"],
        timestamp="2026-08-15T12:01:00+09:00",
    )
    assert not finished.ok
    evidence = json.loads((tmp_path / finished.data["evidence_ref"]).read_text(encoding="utf-8"))
    assert operation in {item["operation"] for item in evidence["unauthorized_mutations"]}


def test_boundary_failure_restores_run_state_and_blocks_progression(tmp_path: Path) -> None:
    run = _write_run(tmp_path, current_stage="intake", current_status="PASSED")
    original = _enable_boundary_control(run)
    state_path = run / "30_execution" / "run_state.json"
    started = start_role_boundary(
        tmp_path,
        run,
        role="problem_framer",
        invocation_ref="framer-mutates-state",
        timestamp=TIMESTAMP,
    )
    assert started.ok
    mutated = json.loads(state_path.read_text(encoding="utf-8"))
    mutated["active_artifacts"]["problem_frame"] = {
        "artifact_id": "problem-frame",
        "version": 1,
        "path": "10_framing/problem_frame.md",
    }
    mutated["stages"][1]["status"] = "PASSED"
    state_path.write_text(json.dumps(mutated, indent=2) + "\n", encoding="utf-8")

    finished = finish_role_boundary(
        tmp_path,
        run,
        role="problem_framer",
        invocation_ref="framer-mutates-state",
        baseline_sha256=started.data["baseline_sha256"],
        timestamp="2026-08-15T12:01:00+09:00",
    )
    assert not finished.ok
    assert finished.data["run_state_restored"] is True
    restored = json.loads(state_path.read_text(encoding="utf-8"))
    assert restored["active_artifacts"] == original["active_artifacts"]
    assert restored["stages"] == original["stages"]
    assert restored["gates"] == original["gates"]

    returned_body = tmp_path / "violated_problem_frame.md"
    returned_body.write_text(_problem_frame(), encoding="utf-8")
    rejected_persistence = persist_semantic_artifact(
        tmp_path,
        run,
        artifact_key="problem_frame",
        source_path=returned_body,
        source_invocation_ref="framer-mutates-state",
        boundary_evidence_ref=finished.data["evidence_ref"],
        timestamp="2026-08-15T12:02:00+09:00",
    )
    assert not rejected_persistence.ok
    assert "BOUNDARY_VIOLATION" in {item.code for item in rejected_persistence.diagnostics}
    assert json.loads(state_path.read_text(encoding="utf-8"))["active_artifacts"] == original["active_artifacts"]

    before = state_path.read_bytes()
    transition = update_state(
        run,
        project_root=tmp_path,
        to_stage="framing",
        stage_status="IN_PROGRESS",
        gate_status="IN_PROGRESS",
        evidence_refs=[],
        rationale="A violated invocation must not advance.",
        next_action="Contain the boundary violation.",
    )
    assert not transition.ok
    assert "BOUNDARY_VIOLATION" in {item.code for item in transition.diagnostics}
    assert state_path.read_bytes() == before


def test_root_persistence_records_hash_provenance_and_only_then_activates(tmp_path: Path) -> None:
    run = _write_run(tmp_path, current_stage="intake", current_status="PASSED")
    state_before = _enable_boundary_control(run)
    assert state_before["active_artifacts"]["problem_frame"] is None
    persisted = _persist_fixture_artifact(
        tmp_path,
        run,
        artifact_key="problem_frame",
        role="problem_framer",
        invocation_ref="framer-return-1",
        body=_problem_frame(),
        suffix=".md",
    )
    assert persisted.ok, persisted.as_dict()
    state = json.loads((run / "30_execution" / "run_state.json").read_text(encoding="utf-8"))
    entry = state["active_artifacts"]["problem_frame"]
    target = run / "10_framing" / "problem_frame.md"
    assert entry == {
        "artifact_id": "problem-frame",
        "version": 1,
        "path": "10_framing/problem_frame.md",
        "content_sha256": sha256_file(target),
        "semantic_owner": "problem_framer",
        "persistence_owner": "root_codex",
        "source_invocation_ref": "framer-return-1",
        "boundary_evidence_ref": persisted.data["boundary_evidence_ref"],
    }
    assert state["artifact"]["version"] == state_before["artifact"]["version"] + 1
    assert validate_run_directory(tmp_path, run).ok


@pytest.mark.parametrize(
    ("stage_id", "artifact_key", "relative_path"),
    [
        ("framing", "problem_frame", "10_framing/problem_frame.md"),
        ("contract", "product_contract", "20_contract/product_contract.yaml"),
        ("verification", "verification_report", "40_verification/verification_report.md"),
    ],
)
def test_in_progress_semantic_stage_may_await_document_registration(
    tmp_path: Path,
    stage_id: str,
    artifact_key: str,
    relative_path: str,
) -> None:
    run = _write_run(tmp_path, current_stage=stage_id, current_status="IN_PROGRESS")
    state_path = run / "30_execution" / "run_state.json"
    state = json.loads(state_path.read_text(encoding="utf-8"))
    state["active_artifacts"][artifact_key] = None
    state_path.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
    (run / relative_path).unlink()

    validation = validate_run_directory(tmp_path, run)

    assert validation.ok, validation.as_dict()


@pytest.mark.parametrize("status", ["PASSED", "FAILED", "BLOCKED"])
def test_terminal_verification_requires_current_report(tmp_path: Path, status: str) -> None:
    run = _write_run(tmp_path, current_stage="verification", current_status=status)
    state_path = run / "30_execution" / "run_state.json"
    state = json.loads(state_path.read_text(encoding="utf-8"))
    state["active_artifacts"]["verification_report"] = None
    state_path.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
    (run / "40_verification" / "verification_report.md").unlink()

    validation = validate_run_directory(tmp_path, run)

    assert not validation.ok
    assert any(
        item.code == "ACTIVE_ARTIFACT" and item.path == "$.active_artifacts.verification_report"
        for item in validation.diagnostics
    )


@pytest.mark.parametrize("status", ["PASSED", "FAILED", "BLOCKED"])
def test_terminal_verification_transition_without_report_is_atomic(tmp_path: Path, status: str) -> None:
    run = _write_run(tmp_path, current_stage="verification", current_status="IN_PROGRESS")
    state_path = run / "30_execution" / "run_state.json"
    state = json.loads(state_path.read_text(encoding="utf-8"))
    state["active_artifacts"]["verification_report"] = None
    state_path.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
    (run / "40_verification" / "verification_report.md").unlink()
    before = state_path.read_bytes()

    transition = update_state(
        run,
        project_root=tmp_path,
        to_stage="verification",
        stage_status=status,
        gate_status=status,
        evidence_refs=["verification-report@1"] if status == "PASSED" else [],
        rationale=f"Attempt terminal verification {status} without a report.",
        next_action="The invalid transition must not persist.",
        timestamp=TIMESTAMP,
    )

    assert not transition.ok
    assert state_path.read_bytes() == before
    assert any(
        item.code == "ACTIVE_ARTIFACT" and item.path == "$.active_artifacts.verification_report"
        for item in transition.diagnostics
    )


def test_problem_frame_registers_during_in_progress_framing(tmp_path: Path) -> None:
    run = _write_run(tmp_path, current_stage="intake", current_status="PASSED")
    _enable_boundary_control(run)
    (run / "10_framing" / "problem_frame.md").unlink()
    entered = update_state(
        run,
        project_root=tmp_path,
        to_stage="framing",
        stage_status="IN_PROGRESS",
        gate_status="IN_PROGRESS",
        evidence_refs=[],
        rationale="Framing started before its document is registered.",
        next_action="Register the audited problem frame.",
        timestamp="2026-08-15T12:00:30+09:00",
    )
    assert entered.ok, entered.as_dict()
    assert validate_run_directory(tmp_path, run).ok

    persisted = _persist_fixture_artifact(
        tmp_path,
        run,
        artifact_key="problem_frame",
        role="problem_framer",
        invocation_ref="framer-in-progress-registration",
        body=_problem_frame(),
        suffix=".md",
    )

    assert persisted.ok, persisted.as_dict()
    assert persisted.data["artifact_ref"] == "problem-frame@1"
    assert validate_run_directory(tmp_path, run).ok


@pytest.mark.parametrize("terminal_status", ["PASSED", "FAILED", "BLOCKED"])
def test_terminal_framing_requires_registered_problem_frame(
    tmp_path: Path,
    terminal_status: str,
) -> None:
    run = _write_run(tmp_path, current_stage="framing", current_status=terminal_status)
    state_path = run / "30_execution" / "run_state.json"
    state = json.loads(state_path.read_text(encoding="utf-8"))
    state["active_artifacts"]["problem_frame"] = None
    state_path.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
    (run / "10_framing" / "problem_frame.md").unlink()

    validation = validate_run_directory(tmp_path, run)

    assert not validation.ok
    assert "ACTIVE_ARTIFACT" in {item.code for item in validation.diagnostics}


def test_role_boundary_and_persistence_cli_round_trip(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    run = _write_run(tmp_path, current_stage="intake", current_status="PASSED")
    _enable_boundary_control(run)
    common = ["--project-root", str(tmp_path), "--format", "json"]
    assert main(
        common
        + [
            "role-boundary",
            "start",
            "--run-dir",
            "run",
            "--role",
            "problem_framer",
            "--invocation-ref",
            "cli-framer-return",
            "--timestamp",
            TIMESTAMP,
        ]
    ) == 0
    started = json.loads(capsys.readouterr().out)
    assert main(
        common
        + [
            "role-boundary",
            "finish",
            "--run-dir",
            "run",
            "--role",
            "problem_framer",
            "--invocation-ref",
            "cli-framer-return",
            "--baseline-sha256",
            started["data"]["baseline_sha256"],
            "--timestamp",
            "2026-08-15T12:01:00+09:00",
        ]
    ) == 0
    finished = json.loads(capsys.readouterr().out)
    source = tmp_path / "cli_problem_frame.md"
    source.write_text(_problem_frame(), encoding="utf-8")
    assert main(
        common
        + [
            "persist-artifact",
            "--run-dir",
            "run",
            "--artifact",
            "problem_frame",
            "--source",
            source.name,
            "--source-invocation-ref",
            "cli-framer-return",
            "--boundary-evidence-ref",
            finished["data"]["evidence_ref"],
            "--timestamp",
            "2026-08-15T12:02:00+09:00",
        ]
    ) == 0
    persisted = json.loads(capsys.readouterr().out)
    assert persisted["ok"] is True
    assert persisted["data"]["artifact_ref"] == "problem-frame@1"


def test_release_is_blocked_when_active_verification_hash_changes_after_validation(tmp_path: Path) -> None:
    run = _write_run(tmp_path, current_stage="intake", current_status="PASSED")
    _enable_boundary_control(run)
    assert _persist_fixture_artifact(
        tmp_path,
        run,
        artifact_key="problem_frame",
        role="problem_framer",
        invocation_ref="framer-return-release",
        body=_problem_frame(),
        suffix=".md",
    ).ok
    assert _persist_fixture_artifact(
        tmp_path,
        run,
        artifact_key="product_contract",
        role="product_contract_agent",
        invocation_ref="contract-return-release",
        body=yaml.safe_dump(_contract(), sort_keys=False),
        suffix=".yaml",
    ).ok
    report_persist = _persist_fixture_artifact(
        tmp_path,
        run,
        artifact_key="verification_report",
        role="independent_verifier",
        invocation_ref="verification-return-release",
        body=_verification_report(),
        suffix=".md",
    )
    assert report_persist.ok, report_persist.as_dict()

    state_path = run / "30_execution" / "run_state.json"
    state = json.loads(state_path.read_text(encoding="utf-8"))
    for stage in state["stages"]:
        stage["status"] = "PASSED" if stage["id"] in {"intake", "framing", "contract", "repository_analysis", "implementation"} else "PENDING"
    state["run"]["current_stage"] = "implementation"
    state["run"]["next_allowed_action"] = "Record the audited verification result."
    state["gates"] = [
        {
            "id": stage["gate_id"],
            "status": stage["status"],
            "evidence_refs": [f"{stage['id']}-evidence"] if stage["status"] == "PASSED" else [],
            "rationale": "Controlled release fixture.",
        }
        for stage in state["stages"]
    ]
    state_path.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
    verified = update_state(
        run,
        project_root=tmp_path,
        to_stage="verification",
        stage_status="PASSED",
        gate_status="PASSED",
        evidence_refs=["verification-report@1"],
        rationale="Audited verification report is READY.",
        next_action="Enter release after reconciliation.",
        timestamp="2026-08-15T12:10:00+09:00",
    )
    assert verified.ok, verified.as_dict()
    captured = json.loads(state_path.read_text(encoding="utf-8"))["control"]["verification_validation_identity"]
    assert captured["content_sha256"] == report_persist.data["content_sha256"]

    plan = _write_test_plan(tmp_path)
    assert run_test_plan(tmp_path, run, plan).ok
    report_path = run / "40_verification" / "verification_report.md"
    report_path.write_bytes(report_path.read_bytes() + b"\nchanged after validation\n")
    before = state_path.read_bytes()
    release = update_state(
        run,
        project_root=tmp_path,
        to_stage="release",
        stage_status="IN_PROGRESS",
        gate_status="IN_PROGRESS",
        evidence_refs=[],
        rationale="Attempt release with changed verification bytes.",
        next_action="This must be rejected.",
    )
    assert not release.ok
    assert {item.code for item in release.diagnostics} & {"ACTIVE_ARTIFACT_HASH", "RELEASE_RECONCILIATION"}
    assert state_path.read_bytes() == before


def test_legacy_completed_run_remains_read_compatible_without_boundary_metadata(tmp_path: Path) -> None:
    run = _write_run(tmp_path)
    state = json.loads((run / "30_execution" / "run_state.json").read_text(encoding="utf-8"))
    assert state["schema_version"] == "1.0"
    assert "control" not in state
    assert validate_run_directory(tmp_path, run).ok


def test_verifier_allowed_path_symlink_escape_is_rejected_when_supported(tmp_path: Path) -> None:
    run = _write_run(tmp_path, current_stage="intake", current_status="PASSED")
    _enable_boundary_control(run)
    started = start_role_boundary(
        tmp_path,
        run,
        role="independent_verifier",
        invocation_ref="verifier-path-escape",
        timestamp=TIMESTAMP,
    )
    assert started.ok
    probes = run / "40_verification" / "probes"
    probes.mkdir()
    outside = tmp_path / "outside.txt"
    outside.write_text("outside\n", encoding="utf-8")
    try:
        os.symlink(outside, probes / "escape.txt")
    except OSError as exc:
        pytest.skip(f"filesystem does not permit symlink creation: {exc}")
    finished = finish_role_boundary(
        tmp_path,
        run,
        role="independent_verifier",
        invocation_ref="verifier-path-escape",
        baseline_sha256=started.data["baseline_sha256"],
        timestamp="2026-08-15T12:01:00+09:00",
    )
    assert not finished.ok
    evidence = json.loads((tmp_path / finished.data["evidence_ref"]).read_text(encoding="utf-8"))
    assert "path_escape" in {item["operation"] for item in evidence["unauthorized_mutations"]}


def test_update_state_applies_allowed_transition_atomically_and_rejects_jump(tmp_path: Path) -> None:
    run = _write_run(tmp_path, current_stage="intake", current_status="PASSED")
    result = update_state(
        run,
        to_stage="framing",
        stage_status="IN_PROGRESS",
        gate_status="IN_PROGRESS",
        evidence_refs=[],
        rationale="Framing started.",
        next_action="Produce problem_frame.md.",
        timestamp="2026-08-15T13:00:00+09:00",
    )
    assert result.ok, result.as_dict()
    state_path = run / "30_execution" / "run_state.json"
    updated = json.loads(state_path.read_text(encoding="utf-8"))
    assert updated["run"]["current_stage"] == "framing"
    assert updated["artifact"]["version"] == 2
    assert updated["active_artifacts"]["run_state"]["version"] == 2

    before = state_path.read_bytes()
    rejected = update_state(
        run,
        to_stage="release",
        stage_status="IN_PROGRESS",
        gate_status="IN_PROGRESS",
        evidence_refs=[],
        rationale="Invalid jump.",
        next_action="This must not persist.",
    )
    assert not rejected.ok
    assert state_path.read_bytes() == before


def test_update_bounce_back_creates_and_resolves_only_in_event_namespace(tmp_path: Path) -> None:
    run = _write_run(tmp_path, current_stage="framing", current_status="IN_PROGRESS")
    state_path = run / "30_execution" / "run_state.json"
    original = json.loads(state_path.read_text(encoding="utf-8"))
    create_payload = {
        "origin": {
            "role": "problem_framer",
            "invocation_ref": "framing-attempt-1",
            "result_artifact_ref": "problem-frame@1",
            "result": "BLOCKED",
        },
        "assigned_to": "user",
        "classification": "MATERIAL_AMBIGUITY",
        "summary": "A product decision is required.",
        "affected_stages": ["framing", "contract"],
        "affected_refs": ["BLK-001"],
        "required_resolution": "Record the user's decision.",
        "retry": {
            "agent_role": "problem_framer",
            "prior_invocation_ref": "framing-attempt-1",
        },
    }

    created = update_bounce_back(run, action="create", payload=create_payload, timestamp=TIMESTAMP)
    assert created.ok, created.as_dict()
    state = json.loads(state_path.read_text(encoding="utf-8"))
    assert state["stages"] == original["stages"]
    assert state["artifact"]["version"] == 2
    assert state["active_artifacts"]["run_state"]["version"] == 2
    assert len(state["bounce_back_events"]) == 1
    event = state["bounce_back_events"][0]
    assert event["id"] == "BB-001"
    assert event["status"] == "OPEN"
    assert event["resolution"] is None
    assert event["retry"]["allowed"] is False
    assert event["retry"]["change_basis"] == []

    resolve_payload = {
        "event_id": "BB-001",
        "resolved_by": "user",
        "resolution_type": "USER_DECIDED",
        "summary": "The user selected the behavior.",
        "changed_artifact_refs": ["problem-frame@2"],
        "decision_refs": ["USER-DECISION-001"],
        "evidence_refs": ["user-message-1"],
        "retry": {"allowed": True, "change_basis": ["DECISION_CHANGED"]},
    }
    resolved = update_bounce_back(
        run,
        action="resolve",
        payload=resolve_payload,
        timestamp="2026-08-15T12:05:00+09:00",
    )
    assert resolved.ok, resolved.as_dict()
    state = json.loads(state_path.read_text(encoding="utf-8"))
    event = state["bounce_back_events"][0]
    assert state["stages"] == original["stages"]
    assert state["artifact"]["version"] == 3
    assert state["active_artifacts"]["run_state"]["version"] == 3
    assert event["status"] == "RESOLVED"
    assert event["resolution"]["resolved_at"] == "2026-08-15T12:05:00+09:00"
    assert event["retry"] == {
        "agent_role": "problem_framer",
        "allowed": True,
        "change_basis": ["DECISION_CHANGED"],
        "prior_invocation_ref": "framing-attempt-1",
    }


def test_update_bounce_back_rejects_invalid_candidate_without_changing_state(tmp_path: Path) -> None:
    run = _write_run(tmp_path, current_stage="framing", current_status="IN_PROGRESS")
    state_path = run / "30_execution" / "run_state.json"
    before = state_path.read_bytes()
    invalid_payload = {
        "origin": {
            "role": "problem_framer",
            "invocation_ref": "framing-attempt-1",
            "result_artifact_ref": "problem-frame@1",
            "result": "BLOCKED",
        },
        "assigned_to": "user",
        "classification": "NOT_A_CLASSIFICATION",
        "summary": "This candidate must not be persisted.",
        "affected_stages": ["framing"],
        "affected_refs": ["BLK-001"],
        "required_resolution": "Reject this payload.",
        "retry": {
            "agent_role": "problem_framer",
            "prior_invocation_ref": "framing-attempt-1",
        },
    }

    rejected = update_bounce_back(run, action="create", payload=invalid_payload, timestamp=TIMESTAMP)
    assert not rejected.ok
    assert "VALUE_ENUM" in {item.code for item in rejected.diagnostics}
    assert state_path.read_bytes() == before


def test_update_bounce_back_cli_reads_payload_and_reports_created_event(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    run = _write_run(tmp_path, current_stage="framing", current_status="IN_PROGRESS")
    payload_path = tmp_path / "create_bounce_back.yaml"
    payload_path.write_text(
        yaml.safe_dump(
            {
                "origin": {
                    "role": "problem_framer",
                    "invocation_ref": "framing-attempt-1",
                    "result_artifact_ref": "problem-frame@1",
                    "result": "BLOCKED",
                },
                "assigned_to": "user",
                "classification": "MATERIAL_AMBIGUITY",
                "summary": "A product decision is required.",
                "affected_stages": ["framing"],
                "affected_refs": ["BLK-001"],
                "required_resolution": "Record the user's decision.",
                "retry": {
                    "agent_role": "problem_framer",
                    "prior_invocation_ref": "framing-attempt-1",
                },
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    exit_code = main(
        [
            "--project-root",
            str(tmp_path),
            "--format",
            "json",
            "update-bounce-back",
            "--run-dir",
            "run",
            "--action",
            "create",
            "--payload",
            payload_path.name,
            "--timestamp",
            TIMESTAMP,
        ]
    )
    output = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert output["ok"] is True
    assert output["command"] == "update-bounce-back"
    assert output["data"]["event_id"] == "BB-001"
    state = json.loads((run / "30_execution" / "run_state.json").read_text(encoding="utf-8"))
    assert state["bounce_back_events"][0]["id"] == "BB-001"


def test_run_state_validator_rejects_bounce_back_inserted_into_stages() -> None:
    state = _state("framing", "IN_PROGRESS")
    state["stages"].append(
        {
            "id": "BB-001",
            "status": "OPEN",
            "summary": "A misplaced bounce-back event.",
        }
    )
    diagnostics = validate_run_state_data(state)
    codes = {item.code for item in diagnostics}
    assert "FIELD_REQUIRED" in codes
    assert "STAGE_SET" in codes


def test_blocked_contract_artifact_prevents_recorded_pass_transition(tmp_path: Path) -> None:
    run = _write_run(tmp_path, current_stage="contract", current_status="PASSED")
    contract_path = run / "20_contract" / "product_contract.yaml"
    contract = yaml.safe_load(contract_path.read_text(encoding="utf-8"))
    contract["readiness"] = {"status": "BLOCKED", "rationale": "Material ambiguity remains."}
    contract_path.write_text(yaml.safe_dump(contract, sort_keys=False), encoding="utf-8")

    validation = validate_run_directory(tmp_path, run)
    assert not validation.ok
    assert "STAGE_READINESS" in {item.code for item in validation.diagnostics}

    state_path = run / "30_execution" / "run_state.json"
    before = state_path.read_bytes()
    transition = update_state(
        run,
        project_root=tmp_path,
        to_stage="repository_analysis",
        stage_status="IN_PROGRESS",
        gate_status="IN_PROGRESS",
        evidence_refs=[],
        rationale="This transition must be rejected.",
        next_action="Resolve the contract blocker.",
    )
    assert not transition.ok
    assert "STAGE_READINESS" in {item.code for item in transition.diagnostics}
    assert state_path.read_bytes() == before


def test_failed_tests_prevent_release_transition(tmp_path: Path) -> None:
    run = _write_run(tmp_path, current_stage="verification", current_status="PASSED")
    (run / "30_execution" / "test_results.json").write_text('{"status":"FAIL"}\n', encoding="utf-8")
    result = update_state(
        run,
        to_stage="release",
        stage_status="IN_PROGRESS",
        gate_status="IN_PROGRESS",
        evidence_refs=[],
        rationale="Start release.",
        next_action="Package.",
    )
    assert not result.ok
    assert "TESTS_NOT_PASSING" in {item.code for item in result.diagnostics}


def test_repair_transition_counts_attempts_and_enforces_limit(tmp_path: Path) -> None:
    run = _write_run(tmp_path, current_stage="verification", current_status="FAILED")
    accepted = update_state(
        run,
        to_stage="repair",
        stage_status="IN_PROGRESS",
        gate_status="IN_PROGRESS",
        evidence_refs=[],
        rationale="Repair the failed requirement.",
        next_action="Apply the named repair.",
        failure_ref="verification-report@1",
        timestamp="2026-08-15T13:05:00+09:00",
    )
    assert accepted.ok, accepted.as_dict()
    state_path = run / "30_execution" / "run_state.json"
    assert json.loads(state_path.read_text(encoding="utf-8"))["repair"]["active_attempt"] == 1

    exhausted_state = _state("verification", "FAILED")
    exhausted_state["repair"]["active_attempt"] = 2
    exhausted_state["repair"]["last_failure_ref"] = "verification-report@0"
    state_path.write_text(json.dumps(exhausted_state, indent=2) + "\n", encoding="utf-8")
    before = state_path.read_bytes()
    rejected = update_state(
        run,
        to_stage="repair",
        stage_status="IN_PROGRESS",
        gate_status="IN_PROGRESS",
        evidence_refs=[],
        rationale="Attempt beyond the limit.",
        next_action="This must not persist.",
        failure_ref="verification-report@1",
    )
    assert not rejected.ok
    assert "REPAIR_LIMIT" in {item.code for item in rejected.diagnostics}
    assert state_path.read_bytes() == before


def test_repair_retry_requires_resolved_changed_basis(tmp_path: Path) -> None:
    run = _write_run(tmp_path, current_stage="repair", current_status="PASSED")
    state_path = run / "30_execution" / "run_state.json"
    state = json.loads(state_path.read_text(encoding="utf-8"))
    state["repair"] = {"active_attempt": 1, "maximum_attempts": 2, "last_failure_ref": "verification-report@1"}
    state_path.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
    result = update_state(
        run,
        to_stage="verification",
        stage_status="IN_PROGRESS",
        gate_status="IN_PROGRESS",
        evidence_refs=[],
        rationale="Retry verification.",
        next_action="Invoke the verifier.",
    )
    assert not result.ok
    assert "UNCHANGED_RETRY" in {item.code for item in result.diagnostics}


def test_run_tests_captures_pass_and_failure_outputs(tmp_path: Path) -> None:
    run = _write_run(tmp_path, current_stage="implementation", current_status="PASSED")
    passing = run_test_plan(tmp_path, run, _write_test_plan(tmp_path, 0), timestamp=TIMESTAMP)
    assert passing.ok
    evidence = json.loads((run / "30_execution" / "test_results.json").read_text(encoding="utf-8"))
    assert evidence["status"] == "PASS"
    assert evidence["commands"][0]["stdout"] == "fixture-output\n"
    assert evidence["commands"][0]["return_code"] == 0
    assert evidence["result_path"] == "run/30_execution/test_results.json"
    assert len(evidence["plan_sha256"]) == 64
    assert evidence["commands"][0]["artifact_paths"] == [
        {
            "path": "test_plan.json",
            "exists": True,
            "kind": "FILE",
            "size_bytes": (tmp_path / "test_plan.json").stat().st_size,
            "sha256": evidence["plan_sha256"],
        }
    ]

    failing = run_test_plan(tmp_path, run, _write_test_plan(tmp_path, 7), timestamp=TIMESTAMP)
    assert not failing.ok
    evidence = json.loads((run / "30_execution" / "test_results.json").read_text(encoding="utf-8"))
    assert evidence["status"] == "FAIL"
    assert evidence["commands"][0]["return_code"] == 7


def test_test_evidence_rejects_moved_result_and_changed_plan(tmp_path: Path) -> None:
    run = _write_run(tmp_path, current_stage="implementation", current_status="PASSED")
    plan_path = _write_test_plan(tmp_path, 0)
    passing = run_test_plan(tmp_path, run, plan_path, timestamp=TIMESTAMP)
    assert passing.ok
    evidence_path = run / "30_execution" / "test_results.json"

    accepted, reason, _ = passing_test_results(evidence_path, tmp_path)
    assert accepted, reason

    moved_path = tmp_path / "moved_test_results.json"
    moved_path.write_bytes(evidence_path.read_bytes())
    accepted, reason, _ = passing_test_results(moved_path, tmp_path)
    assert not accepted
    assert reason == "persisted result_path does not identify this evidence file"

    plan_path.write_text(plan_path.read_text(encoding="utf-8") + "\n", encoding="utf-8")
    accepted, reason, _ = passing_test_results(evidence_path, tmp_path)
    assert not accepted
    assert reason == "test plan changed after the retained execution"


def _write_package_fixture_assets(project_root: Path) -> Path:
    source = project_root / "source"
    (source / "tests").mkdir(parents=True)
    (source / "examples").mkdir(parents=True)
    (source / "tool.py").write_text("print('ok')\n", encoding="utf-8")
    (source / "README.md").write_text("# Tool\n", encoding="utf-8")
    (source / "tests" / "test_tool.py").write_text("def test_ok(): assert True\n", encoding="utf-8")
    (source / "examples" / "README.md").write_text("# Example\n", encoding="utf-8")
    (source / "__pycache__").mkdir()
    (source / "__pycache__" / "ignored.pyc").write_bytes(b"cache")
    spec = {
        "schema_version": "1.0",
        "source_root": "source",
        "artifact_root": "fixture_tool",
        "archive_path": "deliverables/fixture_tool.zip",
        "manifest_path": "run/50_release/release_manifest.json",
        "include": ["**/*"],
        "required": ["tool.py", "README.md", "tests/test_tool.py", "examples/README.md"],
        "approval": {
            "contract_ref": "product-contract@1",
            "decision_refs": ["DEC-001"],
            "required_roles": {
                "readme": ["README.md"],
                "source": ["tool.py"],
                "tests": ["tests/test_tool.py"],
                "examples": ["examples/README.md"],
            },
        },
        "exclude": [],
    }
    spec_path = project_root / "package_spec.yaml"
    spec_path.write_text(yaml.safe_dump(spec, sort_keys=False), encoding="utf-8")
    return spec_path


def _prepare_package_fixture(
    project_root: Path,
    *,
    current_stage: str = "verification",
    current_status: str = "PASSED",
    include_verification_report: bool = True,
) -> tuple[Path, Path]:
    run = _write_run(project_root, current_stage=current_stage, current_status=current_status)
    if not include_verification_report:
        (run / "40_verification" / "verification_report.md").unlink()
    passing = run_test_plan(project_root, run, _write_test_plan(project_root, 0), timestamp=TIMESTAMP)
    assert passing.ok
    spec_path = _write_package_fixture_assets(project_root)
    return run, spec_path


def test_package_is_repeatable_and_inspection_passes(tmp_path: Path) -> None:
    run, spec_path = _prepare_package_fixture(tmp_path)
    first = create_package(tmp_path, run, spec_path)
    assert first.ok, first.as_dict()
    first_bytes = (tmp_path / "deliverables" / "fixture_tool.zip").read_bytes()
    second = create_package(tmp_path, run, spec_path)
    assert second.ok, second.as_dict()
    assert (tmp_path / "deliverables" / "fixture_tool.zip").read_bytes() == first_bytes
    assert first.data["archive_sha256"] == second.data["archive_sha256"]

    inspection = inspect_package(tmp_path, run, run / "50_release" / "release_manifest.json")
    assert inspection.ok, inspection.as_dict()
    payload = json.loads((run / "50_release" / "package_inspection.json").read_text(encoding="utf-8"))
    assert payload["status"] == "PASS"
    assert payload["prohibited_entry_count"] == 0


def test_release_completion_requires_and_accepts_integrity_checked_evidence(tmp_path: Path) -> None:
    run, spec_path = _prepare_package_fixture(tmp_path)
    started = update_state(
        run,
        project_root=tmp_path,
        to_stage="release",
        stage_status="IN_PROGRESS",
        gate_status="IN_PROGRESS",
        evidence_refs=[],
        rationale="Verified candidate entered release packaging.",
        next_action="Package and inspect the candidate.",
    )
    assert started.ok, started.as_dict()
    assert create_package(tmp_path, run, spec_path).ok
    assert inspect_package(tmp_path, run, run / "50_release" / "release_manifest.json").ok
    completed = update_state(
        run,
        project_root=tmp_path,
        to_stage="release",
        stage_status="PASSED",
        gate_status="PASSED",
        evidence_refs=["test-results", "package-inspection"],
        rationale="Tests and the inspected manifest-attributed archive pass.",
        next_action="Await the user's phase decision.",
    )
    assert completed.ok, completed.as_dict()


def test_release_completion_rejects_archive_changed_after_inspection(tmp_path: Path) -> None:
    run, spec_path = _prepare_package_fixture(tmp_path)
    started = update_state(
        run,
        project_root=tmp_path,
        to_stage="release",
        stage_status="IN_PROGRESS",
        gate_status="IN_PROGRESS",
        evidence_refs=[],
        rationale="Verified candidate entered release packaging.",
        next_action="Package and inspect the candidate.",
    )
    assert started.ok
    assert create_package(tmp_path, run, spec_path).ok
    assert inspect_package(tmp_path, run, run / "50_release" / "release_manifest.json").ok
    archive_path = tmp_path / "deliverables" / "fixture_tool.zip"
    with zipfile.ZipFile(archive_path, "a") as archive:
        archive.writestr("fixture_tool/changed_after_inspection.txt", b"changed")
    state_path = run / "30_execution" / "run_state.json"
    before = state_path.read_bytes()
    rejected = update_state(
        run,
        project_root=tmp_path,
        to_stage="release",
        stage_status="PASSED",
        gate_status="PASSED",
        evidence_refs=["test-results", "package-inspection"],
        rationale="Attempt release with stale inspection.",
        next_action="This must not persist.",
    )
    assert not rejected.ok
    assert "PACKAGE_NOT_INSPECTED" in {item.code for item in rejected.diagnostics}
    assert state_path.read_bytes() == before


def test_package_rejects_failed_test_evidence(tmp_path: Path) -> None:
    run, spec_path = _prepare_package_fixture(tmp_path)
    (run / "30_execution" / "test_results.json").write_text('{"status":"FAIL"}\n', encoding="utf-8")
    result = create_package(tmp_path, run, spec_path)
    assert not result.ok
    assert not (tmp_path / "deliverables" / "fixture_tool.zip").exists()


def test_package_rejects_spec_that_omits_required_readme_role(tmp_path: Path) -> None:
    run, spec_path = _prepare_package_fixture(tmp_path)
    spec = yaml.safe_load(spec_path.read_text(encoding="utf-8"))
    spec["include"] = ["tool.py"]
    spec["required"] = ["tool.py"]
    spec["approval"]["required_roles"] = {
        "readme": [],
        "source": ["tool.py"],
        "tests": [],
        "examples": [],
    }
    spec_path.write_text(yaml.safe_dump(spec, sort_keys=False), encoding="utf-8")
    result = create_package(tmp_path, run, spec_path)
    assert not result.ok
    assert "PACKAGE_ROLES" in {item.code for item in result.diagnostics}
    assert not (tmp_path / "deliverables" / "fixture_tool.zip").exists()


def test_package_rejects_unapproved_contract_decision_binding(tmp_path: Path) -> None:
    run, spec_path = _prepare_package_fixture(tmp_path)
    spec = yaml.safe_load(spec_path.read_text(encoding="utf-8"))
    spec["approval"]["decision_refs"] = ["DEC-999"]
    spec_path.write_text(yaml.safe_dump(spec, sort_keys=False), encoding="utf-8")
    result = create_package(tmp_path, run, spec_path)
    assert not result.ok
    assert "PACKAGE_APPROVAL" in {item.code for item in result.diagnostics}


def test_inspection_catches_seeded_cache_content(tmp_path: Path) -> None:
    run, spec_path = _prepare_package_fixture(tmp_path)
    package = create_package(tmp_path, run, spec_path)
    assert package.ok
    archive_path = tmp_path / "deliverables" / "fixture_tool.zip"
    with zipfile.ZipFile(archive_path, "a") as archive:
        archive.writestr("fixture_tool/__pycache__/seeded.pyc", b"seed")
    inspection = inspect_package(tmp_path, run, run / "50_release" / "release_manifest.json")
    assert not inspection.ok
    codes = {item.code for item in inspection.diagnostics}
    assert {"PROHIBITED_ENTRY", "MANIFEST_INVENTORY"} <= codes
    payload = json.loads((run / "50_release" / "package_inspection.json").read_text(encoding="utf-8"))
    assert payload["status"] == "FAIL"


def test_control_plane_contains_no_llm_agent_invocation() -> None:
    root = Path(__file__).resolve().parents[1] / "pipeline_control"
    source = "\n".join(path.read_text(encoding="utf-8") for path in root.glob("*.py"))
    forbidden = ["import openai", "from openai", "import agents", "from agents", "Runner.run", "spawn_agent"]
    assert not [token for token in forbidden if token in source]
