from __future__ import annotations

import json
import subprocess
import sys
from copy import deepcopy
from pathlib import Path

import yaml
import pytest

from pipeline_control.io_utils import sha256_file
from pipeline_control.revision import requirement_bundle_sha256, resolve_revision_baseline, validate_revision_contract
from pipeline_control.state import _verified_candidate_binding, update_state
from pipeline_control.validation import (
    validate_build_request_data,
    validate_product_contract_data,
    validate_run_directory,
    validate_verification_reconciliation,
)


ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = ROOT.parents[1]
INITIALIZER = REPO_ROOT / ".agents" / "skills" / "build-tool-pipeline" / "scripts" / "initialize_run.py"
STAMP = "2026-09-01T00:00:00+09:00"


def _artifact(artifact_id: str, owner: str) -> dict:
    return {
        "artifact_id": artifact_id,
        "version": 1,
        "lifecycle_status": "ACTIVE",
        "owner_role": owner,
        "created_at": STAMP,
        "updated_at": STAMP,
    }


def _build_request(project_id: str = "baseline-tool", kind: str = "NEW_PRODUCT") -> dict:
    return {
        "schema_version": "1.0",
        "artifact": _artifact("build-request", "root_codex"),
        "project": {"project_id": project_id, "name": "Tool", "request_kind": kind, "summary": "A controlled tool."},
        "requested_outcome": {"objective": "Keep behavior deterministic.", "deliverables": ["source"], "success_summary": "All gates pass."},
        "source_context": [],
        "build_profile": {"profile_id": "test"},
        "target": {"repository_path": "codex_workspace/tool", "output_path": "deliverables/tool.zip"},
        "constraints": [],
        "user_decisions": [],
        "assumptions": [],
        "blockers": [],
        "handoff": {"readiness": "PASS", "next_stage": "framing", "required_inputs": ["build-request"], "rationale": "Ready."},
    }


def _contract() -> dict:
    return {
        "schema_version": "1.0",
        "artifact": _artifact("product-contract", "product_contract_agent"),
        "source_artifacts": [{"artifact_id": "build-request", "version": 1}, {"artifact_id": "problem-frame", "version": 1}],
        "readiness": {"status": "PASS", "rationale": "Complete."},
        "product": {"name": "Tool", "objective": "Deterministic output.", "primary_user": "Tester", "interface_summary": "CLI"},
        "scope": {"included": ["CLI"], "excluded": ["Network"]},
        "decisions": [],
        "assumptions": [],
        "blockers": [],
        "verification_policy": {
            "scope": "ALL_APPLICABLE_REQUIREMENTS",
            "default_nature": "DETERMINISTIC",
            "applicable_requirement_count": 1,
            "applicable_requirement_ids": ["REQ-001"],
            "llm_judgment_requirements": [],
        },
        "requirements": [{
            "id": "REQ-001",
            "category": "FUNCTIONAL",
            "title": "Stable output",
            "statement": "Output remains stable.",
            "source_refs": ["problem-frame@1"],
            "acceptance_refs": ["ACC-001"],
        }],
        "acceptance_methods": [{
            "id": "ACC-001",
            "requirement_refs": ["REQ-001"],
            "evidence_method": "TEST",
            "procedure": "Run twice.",
            "expected_result": "Outputs match.",
            "evidence_required": ["captured output"],
        }],
        "implementation_constraints": [],
        "documentation_obligations": [],
        "handoff": {"next_stage": "repository_analysis", "required_artifacts": ["product-contract@1"], "carried_assumptions": [], "open_blockers": [], "rationale": "Ready."},
    }


def _report() -> str:
    sections = {
        "Contract Metadata": "\n".join(["- Schema version: `1.0`", "- Artifact ID: `verification-report`", "- Version: `1`", "- Lifecycle status: `ACTIVE`", "- Semantic owner: `independent_verifier`"]),
        "Overall Assessment": "READY — All applicable requirements pass.",
        "Inputs and Evidence Reviewed": "- Exact inspected archive.",
        "LLM Judgment Scope": "None.",
        "Requirement Results": "| Requirement | Acceptance | Result | Evidence |\n| --- | --- | --- | --- |\n| REQ-001 | ACC-001 | PASS | Exact candidate. |",
        "Missing or Unusable Evidence": "None.",
        "Contract, Interface, and Documentation Drift": "None.",
        "Repair Requests": "None.",
        "Risks, Waivers, and Blockers": "None.",
        "Revalidation Needs": "None.",
        "Root Return": "- Overall assessment: `READY`",
    }
    return "# Verification Report\n\n" + "\n\n".join(f"## {heading}\n\n{body}" for heading, body in sections.items()) + "\n"


def _problem_frame() -> str:
    headings = [
        "Contract Metadata", "Completion Status", "Input Reviewed", "Active Problem",
        "Objective and User Need", "Target UX Flow", "Scope", "Non-Scope",
        "Inputs and Outputs", "Failure Behavior", "Constraints", "Assumptions",
        "Decisions", "Open Issues and Blockers", "Validation Needs", "Handoff Readiness",
    ]
    sections = []
    for heading in headings:
        body = "Complete baseline framing evidence."
        if heading == "Contract Metadata":
            body = "\n".join([
                "- Schema version: `1.0`", "- Artifact ID: `problem-frame`",
                "- Version: `1`", "- Lifecycle status: `ACTIVE`",
                "- Semantic owner: `problem_framer`",
            ])
        elif heading == "Completion Status":
            body = "PASS — Baseline framing is complete."
        sections.append(f"## {heading}\n\n{body}")
    return "# Problem Frame\n\n" + "\n\n".join(sections) + "\n"


def _boundary_result(run: Path, role: str, invocation_ref: str) -> str:
    path = run / "30_execution" / "role_boundary" / "results" / role / invocation_ref / "result.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({
        "artifact_type": "role-boundary-result",
        "status": "PASS",
        "role": role,
        "invocation_ref": invocation_ref,
    }), encoding="utf-8")
    return path.relative_to(run).as_posix()


def _baseline(root: Path) -> tuple[Path, dict, dict]:
    run = root / "workspace" / "build_runs" / "baseline-release"
    for stage in ("00_intake", "10_framing", "20_contract", "30_execution", "40_verification", "50_release"):
        (run / stage).mkdir(parents=True, exist_ok=True)
    build = _build_request()
    contract = _contract()
    (run / "00_intake" / "build_request.yaml").write_text(yaml.safe_dump(build, sort_keys=False), encoding="utf-8")
    contract_path = run / "20_contract" / "product_contract.yaml"
    contract_path.write_text(yaml.safe_dump(contract, sort_keys=False), encoding="utf-8")
    frame_path = run / "10_framing" / "problem_frame.md"
    frame_path.write_text(_problem_frame(), encoding="utf-8")
    report_path = run / "40_verification" / "verification_report.md"
    report_path.write_text(_report(), encoding="utf-8")
    archive = root / "deliverables" / "tool.zip"
    archive.parent.mkdir(parents=True)
    archive.write_bytes(b"exact verified archive")
    archive_hash = sha256_file(archive)
    manifest_path = run / "50_release" / "release_manifest.json"
    manifest = {"artifact_type": "release-manifest", "archive_path": "deliverables/tool.zip", "archive_sha256": archive_hash, "entry_count": 1}
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    inspection_path = run / "50_release" / "package_inspection.json"
    inspection = {
        "artifact_type": "package-inspection",
        "status": "PASS",
        "diagnostics": [],
        "prohibited_entry_count": 0,
        "archive_path": "deliverables/tool.zip",
        "archive_sha256": archive_hash,
        "manifest_path": "workspace/build_runs/baseline-release/50_release/release_manifest.json",
        "entry_count": 1,
    }
    inspection_path.write_text(json.dumps(inspection), encoding="utf-8")
    contract_rel = "20_contract/product_contract.yaml"
    report_rel = "40_verification/verification_report.md"
    binding = {
        "product_contract_ref": "product-contract@1",
        "product_contract_path": contract_rel,
        "product_contract_sha256": sha256_file(contract_path),
        "manifest_path": "workspace/build_runs/baseline-release/50_release/release_manifest.json",
        "manifest_sha256": sha256_file(manifest_path),
        "inspection_path": "workspace/build_runs/baseline-release/50_release/package_inspection.json",
        "inspection_sha256": sha256_file(inspection_path),
        "archive_path": "deliverables/tool.zip",
        "archive_sha256": archive_hash,
    }
    stages = ["intake", "framing", "contract", "repository_analysis", "implementation", "verification", "repair", "release"]
    stage_records = [{"id": item, "status": "PENDING" if item == "repair" else "PASSED", "gate_id": f"GATE-{item.upper()}"} for item in stages]
    gates = [{"id": item["gate_id"], "status": item["status"], "evidence_refs": ["evidence"] if item["status"] == "PASSED" else [], "rationale": "Completed baseline."} for item in stage_records]
    state = {
        "schema_version": "1.1",
        "artifact": _artifact("run-state", "root_codex"),
        "run": {"run_id": "baseline-release", "project_id": "baseline-tool", "current_stage": "release", "next_allowed_action": "Released."},
        "stages": stage_records,
        "gates": gates,
        "active_artifacts": {
            "build_request": {"artifact_id": "build-request", "version": 1, "path": "00_intake/build_request.yaml"},
            "problem_frame": {"artifact_id": "problem-frame", "version": 1, "path": "10_framing/problem_frame.md", "content_sha256": sha256_file(frame_path), "semantic_owner": "problem_framer", "persistence_owner": "root_codex", "source_invocation_ref": "frame", "boundary_evidence_ref": _boundary_result(run, "problem_framer", "frame")},
            "product_contract": {"artifact_id": "product-contract", "version": 1, "path": contract_rel, "content_sha256": binding["product_contract_sha256"], "semantic_owner": "product_contract_agent", "persistence_owner": "root_codex", "source_invocation_ref": "contract", "boundary_evidence_ref": _boundary_result(run, "product_contract_agent", "contract")},
            "run_state": {"artifact_id": "run-state", "version": 1, "path": "30_execution/run_state.json"},
            "verification_report": {"artifact_id": "verification-report", "version": 1, "path": report_rel, "content_sha256": sha256_file(report_path), "semantic_owner": "independent_verifier", "persistence_owner": "root_codex", "source_invocation_ref": "verify", "boundary_evidence_ref": _boundary_result(run, "independent_verifier", "verify")},
        },
        "control": {
            "semantic_role_boundary": "1.0",
            "verification_validation_identity": {
                "artifact_id": "verification-report",
                "version": 1,
                "path": report_rel,
                "content_sha256": sha256_file(report_path),
                "validated_at": STAMP,
                "candidate_binding": binding,
            },
        },
        "repair": {"active_attempt": 0, "maximum_attempts": 2, "last_failure_ref": None},
        "bounce_back_events": [],
        "blockers": [],
        "required_approvals": [],
    }
    (run / "30_execution" / "run_state.json").write_text(json.dumps(state, indent=2), encoding="utf-8")
    plan_path = root / "baseline_test_plan.json"
    plan_path.write_text(json.dumps({"commands": [{"id": "baseline"}]}), encoding="utf-8")
    test_result_path = run / "30_execution" / "test_results.json"
    test_result_path.write_text(json.dumps({
        "artifact_type": "deterministic-test-results",
        "status": "PASS",
        "command_count": 1,
        "passed_count": 1,
        "failed_count": 0,
        "plan_path": "baseline_test_plan.json",
        "plan_sha256": sha256_file(plan_path),
        "result_path": "workspace/build_runs/baseline-release/30_execution/test_results.json",
        "commands": [{"id": "baseline", "status": "PASS", "artifact_paths": []}],
    }), encoding="utf-8")
    revision = _build_request("revision-tool", "REVISION")
    revision["revision_of"] = {
        "run_id": "baseline-release",
        "archive_sha256": archive_hash,
        "product_contract_ref": "product-contract@1",
        "product_contract_sha256": binding["product_contract_sha256"],
        "verification_report_ref": "verification-report@1",
        "verification_report_sha256": sha256_file(report_path),
    }
    revision["delta_request"] = {
        "scope_classification": "BOUNDED",
        "requested_changes": [{"id": "DELTA-001", "statement": "Adjust one bounded behavior."}],
        "explicit_non_changes": [],
        "feedback_evidence": [{"id": "FEEDBACK-001", "source_ref": "user-request", "summary": "A bounded change was requested."}],
    }
    return run, revision, contract


def test_revision_request_pairing_and_scope_are_strict() -> None:
    fresh = _build_request()
    assert validate_build_request_data(fresh) == []
    fresh["revision_of"] = {}
    assert {item.code for item in validate_build_request_data(fresh)} == {"REVISION_FIELDS_FORBIDDEN"}
    revision = _build_request("revision", "REVISION")
    assert "FRESH_REQUIRED" in {item.code for item in validate_build_request_data(revision)}


def test_verified_transition_binding_captures_contract_and_package_bytes(tmp_path: Path) -> None:
    run, _, _ = _baseline(tmp_path)
    state = json.loads((run / "30_execution" / "run_state.json").read_text(encoding="utf-8"))
    binding = _verified_candidate_binding(tmp_path, run, state)
    assert binding is not None
    assert binding == state["control"]["verification_validation_identity"]["candidate_binding"]


def test_exact_verified_baseline_initializes_delta_state(tmp_path: Path) -> None:
    baseline_run, request, _ = _baseline(tmp_path)
    assert validate_build_request_data(request) == []
    assert validate_run_directory(tmp_path, baseline_run).ok
    state = json.loads((baseline_run / "30_execution" / "run_state.json").read_text(encoding="utf-8"))
    assert state["active_artifacts"]["product_contract"]["path"] == "20_contract/product_contract.yaml"
    assert state["control"]["verification_validation_identity"]["candidate_binding"]["product_contract_path"] == "20_contract/product_contract.yaml"
    resolved = resolve_revision_baseline(tmp_path, request)
    assert resolved.ok, resolved.as_dict()
    request_path = tmp_path / "revision.yaml"
    request_path.write_text(yaml.safe_dump(request, sort_keys=False), encoding="utf-8")
    process = subprocess.run(
        [sys.executable, str(INITIALIZER), "--project-root", str(tmp_path), "--request", "revision.yaml", "--timestamp", STAMP, "--format", "json"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert process.returncode == 0, process.stderr or process.stdout
    run = tmp_path / "workspace" / "build_runs" / "revision-tool"
    state = json.loads((run / "30_execution" / "run_state.json").read_text(encoding="utf-8"))
    assert state["control"]["revision_baseline"]["archive_sha256"] == request["revision_of"]["archive_sha256"]
    assert state["control"]["verification_validation_identity"] is None
    assert validate_run_directory(tmp_path, run).ok


def test_fabricated_completed_state_without_boundary_provenance_is_rejected(tmp_path: Path) -> None:
    run, request, _ = _baseline(tmp_path)
    state_path = run / "30_execution" / "run_state.json"
    state = json.loads(state_path.read_text(encoding="utf-8"))
    state["active_artifacts"]["product_contract"]["boundary_evidence_ref"] = "30_execution/role_boundary/missing.json"
    state_path.write_text(json.dumps(state), encoding="utf-8")

    invalid = validate_run_directory(tmp_path, run)
    assert not invalid.ok
    assert "BOUNDARY_EVIDENCE" in {item.code for item in invalid.diagnostics}
    rejected = resolve_revision_baseline(tmp_path, request)
    assert not rejected.ok
    assert {item.code for item in rejected.diagnostics} == {"FRESH_REQUIRED"}


def _rewrite_repackaged_candidate(root: Path, run: Path) -> None:
    archive_path = root / "deliverables" / "tool.zip"
    archive_path.write_bytes(b"new package bytes")
    digest = sha256_file(archive_path)
    manifest_path = run / "50_release" / "release_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["archive_sha256"] = digest
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    inspection_path = run / "50_release" / "package_inspection.json"
    inspection = json.loads(inspection_path.read_text(encoding="utf-8"))
    inspection["archive_sha256"] = digest
    inspection_path.write_text(json.dumps(inspection), encoding="utf-8")


@pytest.mark.parametrize("drift", ["archive", "manifest", "inspection", "contract", "repackage"])
def test_verified_candidate_drift_blocks_release_and_validate_run(tmp_path: Path, drift: str) -> None:
    run, _, _ = _baseline(tmp_path)
    if drift == "archive":
        (tmp_path / "deliverables" / "tool.zip").write_bytes(b"archive drift")
    elif drift == "manifest":
        path = run / "50_release" / "release_manifest.json"
        payload = json.loads(path.read_text(encoding="utf-8"))
        payload["post_verification_change"] = True
        path.write_text(json.dumps(payload), encoding="utf-8")
    elif drift == "inspection":
        path = run / "50_release" / "package_inspection.json"
        payload = json.loads(path.read_text(encoding="utf-8"))
        payload["post_verification_change"] = True
        path.write_text(json.dumps(payload), encoding="utf-8")
    elif drift == "contract":
        path = run / "20_contract" / "product_contract.yaml"
        path.write_text(path.read_text(encoding="utf-8") + "\n# post-verification drift\n", encoding="utf-8")
    else:
        _rewrite_repackaged_candidate(tmp_path, run)

    state = json.loads((run / "30_execution" / "run_state.json").read_text(encoding="utf-8"))
    reconciliation = validate_verification_reconciliation(tmp_path, run, state)
    assert "RELEASE_RECONCILIATION" in {item.code for item in reconciliation}
    invalid = validate_run_directory(tmp_path, run)
    assert not invalid.ok
    assert "RELEASE_RECONCILIATION" in {item.code for item in invalid.diagnostics}
    rejected = update_state(
        run,
        project_root=tmp_path,
        to_stage="release",
        stage_status="PASSED",
        gate_status="PASSED",
        evidence_refs=["test-results", "package-inspection"],
        rationale="Do not release a candidate changed after verification.",
        next_action="Reverify the exact candidate.",
        timestamp=STAMP,
    )
    assert not rejected.ok
    assert "RELEASE_RECONCILIATION" in {item.code for item in rejected.diagnostics}


def test_unchanged_bound_candidate_allows_release_reentry(tmp_path: Path) -> None:
    run, _, _ = _baseline(tmp_path)
    accepted = update_state(
        run,
        project_root=tmp_path,
        to_stage="release",
        stage_status="PASSED",
        gate_status="PASSED",
        evidence_refs=["test-results", "package-inspection"],
        rationale="The exact verified candidate remains unchanged.",
        next_action="Retain the completed release.",
        timestamp=STAMP,
    )
    assert accepted.ok, accepted.as_dict()
    assert validate_run_directory(tmp_path, run).ok


def test_legacy_verification_identity_without_candidate_binding_remains_readable(tmp_path: Path) -> None:
    run, request, _ = _baseline(tmp_path)
    state_path = run / "30_execution" / "run_state.json"
    state = json.loads(state_path.read_text(encoding="utf-8"))
    del state["control"]["verification_validation_identity"]["candidate_binding"]
    state_path.write_text(json.dumps(state), encoding="utf-8")

    assert validate_run_directory(tmp_path, run).ok
    rejected = resolve_revision_baseline(tmp_path, request)
    assert not rejected.ok
    assert {item.code for item in rejected.diagnostics} == {"FRESH_REQUIRED"}


def test_revision_lineage_cycle_is_rejected_without_recursive_validation(tmp_path: Path) -> None:
    run, request, _ = _baseline(tmp_path)
    baseline_request_path = run / "00_intake" / "build_request.yaml"
    baseline_request = deepcopy(request)
    baseline_request["project"]["project_id"] = "baseline-tool"
    baseline_request["revision_of"]["run_id"] = "baseline-release"
    baseline_request_path.write_text(yaml.safe_dump(baseline_request, sort_keys=False), encoding="utf-8")

    rejected = resolve_revision_baseline(tmp_path, request)
    assert not rejected.ok
    assert {item.code for item in rejected.diagnostics} == {"FRESH_REQUIRED"}
    assert "cycle" in rejected.diagnostics[0].message


def test_hash_drift_requires_fresh_before_and_after_initialization(tmp_path: Path) -> None:
    _, request, _ = _baseline(tmp_path)
    bad = deepcopy(request)
    bad["revision_of"]["archive_sha256"] = "0" * 64
    rejected = resolve_revision_baseline(tmp_path, bad)
    assert not rejected.ok
    assert {item.code for item in rejected.diagnostics} == {"FRESH_REQUIRED"}
    bad_path = tmp_path / "bad-revision.yaml"
    bad_path.write_text(yaml.safe_dump(bad, sort_keys=False), encoding="utf-8")
    bad_process = subprocess.run(
        [sys.executable, str(INITIALIZER), "--project-root", str(tmp_path), "--request", "bad-revision.yaml", "--timestamp", STAMP, "--format", "json"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert bad_process.returncode == 1
    assert {item["code"] for item in json.loads(bad_process.stdout)["diagnostics"]} == {"FRESH_REQUIRED"}
    assert not (tmp_path / "workspace" / "build_runs" / "revision-tool").exists()

    request_path = tmp_path / "revision.yaml"
    request_path.write_text(yaml.safe_dump(request, sort_keys=False), encoding="utf-8")
    process = subprocess.run(
        [sys.executable, str(INITIALIZER), "--project-root", str(tmp_path), "--request", "revision.yaml", "--timestamp", STAMP, "--format", "json"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert process.returncode == 0
    (tmp_path / "deliverables" / "tool.zip").write_bytes(b"drift")
    validation = validate_run_directory(tmp_path, tmp_path / "workspace" / "build_runs" / "revision-tool")
    assert not validation.ok
    assert "FRESH_REQUIRED" in {item.code for item in validation.diagnostics}


def test_complete_revision_contract_impact_map_and_exact_unchanged_hash(tmp_path: Path) -> None:
    _, request, baseline_contract = _baseline(tmp_path)
    resolved = resolve_revision_baseline(tmp_path, request)
    state = {"control": {"revision_baseline": {**resolved.data, "resolved_at": STAMP}}}
    current = deepcopy(baseline_contract)
    current["revision_control"] = {
        "mode": "DELTA",
        "baseline": deepcopy(request["revision_of"]),
        "unchanged_requirements": [],
        "impact_map": [{
            "delta_item_ref": "DELTA-001",
            "disposition": "IMPACTED",
            "baseline_requirement_refs": ["REQ-001"],
            "current_requirement_refs": ["REQ-001"],
            "source_refs": ["tool.py"],
            "test_refs": ["tests/test_tool.py"],
            "documentation_refs": ["README.md"],
            "packaging_refs": ["release-manifest"],
            "migration_impact": "No migration.",
            "reverification_scope": "ALL_APPLICABLE_REQUIREMENTS",
        }],
    }
    assert validate_product_contract_data(current) == []
    assert validate_revision_contract(tmp_path, request, state, current) == []

    current["revision_control"]["unchanged_requirements"] = [{
        "requirement_ref": "REQ-001",
        "baseline_bundle_sha256": requirement_bundle_sha256(baseline_contract, "REQ-001"),
    }]
    diagnostics = validate_revision_contract(tmp_path, request, state, current)
    assert {item.code for item in diagnostics} >= {"REVISION_CLASSIFICATION_OVERLAP"}


def test_shared_acceptance_change_cannot_hide_an_inherited_requirement(tmp_path: Path) -> None:
    _, request, baseline = _baseline(tmp_path)
    second = deepcopy(baseline["requirements"][0])
    second.update({"id": "REQ-002", "title": "Also stable"})
    second["acceptance_refs"] = ["ACC-001"]
    baseline["requirements"].append(second)
    baseline["acceptance_methods"][0]["requirement_refs"].append("REQ-002")
    baseline["verification_policy"]["applicable_requirement_count"] = 2
    baseline["verification_policy"]["applicable_requirement_ids"].append("REQ-002")
    current = deepcopy(baseline)
    current["acceptance_methods"][0]["expected_result"] = "Changed shared result."
    baseline_hash = requirement_bundle_sha256(baseline, "REQ-002")
    current["revision_control"] = {
        "mode": "DELTA",
        "baseline": request["revision_of"],
        "unchanged_requirements": [{"requirement_ref": "REQ-002", "baseline_bundle_sha256": baseline_hash}],
        "impact_map": [{
            "delta_item_ref": "DELTA-001",
            "disposition": "IMPACTED",
            "baseline_requirement_refs": ["REQ-001"],
            "current_requirement_refs": ["REQ-001"],
            "source_refs": [], "test_refs": [], "documentation_refs": [], "packaging_refs": [],
            "migration_impact": "No migration.",
            "reverification_scope": "ALL_APPLICABLE_REQUIREMENTS",
        }],
    }
    # Point the baseline contract bytes and identities at this two-requirement fixture.
    contract_path = tmp_path / "workspace" / "build_runs" / "baseline-release" / "20_contract" / "product_contract.yaml"
    contract_path.write_text(yaml.safe_dump(baseline, sort_keys=False), encoding="utf-8")
    request["revision_of"]["product_contract_sha256"] = sha256_file(contract_path)
    state_path = tmp_path / "workspace" / "build_runs" / "baseline-release" / "30_execution" / "run_state.json"
    baseline_state = json.loads(state_path.read_text(encoding="utf-8"))
    digest = sha256_file(contract_path)
    baseline_state["active_artifacts"]["product_contract"]["content_sha256"] = digest
    baseline_state["control"]["verification_validation_identity"]["candidate_binding"]["product_contract_sha256"] = digest
    report_path = tmp_path / "workspace" / "build_runs" / "baseline-release" / "40_verification" / "verification_report.md"
    report_path.write_text(
        report_path.read_text(encoding="utf-8").replace(
            "| REQ-001 | ACC-001 | PASS | Exact candidate. |",
            "| REQ-001 | ACC-001 | PASS | Exact candidate. |\n| REQ-002 | ACC-001 | PASS | Exact candidate. |",
        ),
        encoding="utf-8",
    )
    report_digest = sha256_file(report_path)
    request["revision_of"]["verification_report_sha256"] = report_digest
    baseline_state["active_artifacts"]["verification_report"]["content_sha256"] = report_digest
    baseline_state["control"]["verification_validation_identity"]["content_sha256"] = report_digest
    state_path.write_text(json.dumps(baseline_state), encoding="utf-8")
    resolved = resolve_revision_baseline(tmp_path, request)
    assert resolved.ok, resolved.as_dict()
    state = {"control": {"revision_baseline": {**resolved.data, "resolved_at": STAMP}}}
    diagnostics = validate_revision_contract(tmp_path, request, state, current)
    assert "REVISION_UNCHANGED_DRIFT" in {item.code for item in diagnostics}
