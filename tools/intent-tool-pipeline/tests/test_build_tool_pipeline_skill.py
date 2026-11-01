from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import yaml

from pipeline_control.validation import validate_run_directory


ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = ROOT.parents[1]
SKILL_ROOT = REPO_ROOT / ".agents" / "skills" / "build-tool-pipeline"
MINOR_SKILL_ROOT = REPO_ROOT / ".agents" / "skills" / "minor-tool-revision"
INITIALIZER = SKILL_ROOT / "scripts" / "initialize_run.py"


def _request(timestamp: str = "2026-08-17T00:00:00+09:00") -> dict:
    return {
        "schema_version": "1.0",
        "artifact": {
            "artifact_id": "build-request",
            "version": 1,
            "lifecycle_status": "ACTIVE",
            "owner_role": "root_codex",
            "created_at": timestamp,
            "updated_at": timestamp,
        },
        "project": {
            "project_id": "phase5-skill-test",
            "name": "Phase 5 Skill Test",
            "request_kind": "NEW_PRODUCT",
            "summary": "Exercise the orchestration skill initializer and gate stop behavior.",
        },
        "requested_outcome": {
            "objective": "Create an isolated deterministic workflow fixture.",
            "deliverables": ["source", "tests", "README", "example", "release package"],
            "success_summary": "The fixed run is valid and invalid advancement is rejected.",
        },
        "source_context": [
            {
                "source_id": "SRC-001",
                "type": "FILE",
                "path": "request.yaml",
                "authority": "USER_PROVIDED",
                "description": "Controlled Phase 5 integration fixture.",
            }
        ],
        "build_profile": {
            "profile_id": "default_tool_profile",
            "path": "workspace/build_profiles/default_tool_profile.yaml",
        },
        "target": {
            "repository_path": "codex_workspace/phase5-skill-test",
            "output_path": "deliverables/phase5-skill-test.zip",
        },
        "constraints": ["Do not modify framework implementation files."],
        "user_decisions": [
            {
                "id": "DEC-001",
                "statement": "Use an isolated fixture.",
                "rationale": "Keep the test reversible.",
                "owner": "user",
                "status": "APPROVED",
                "source_ref": "SRC-001",
                "impact": "Constrains test paths.",
            }
        ],
        "assumptions": [],
        "blockers": [],
        "handoff": {
            "readiness": "PASS",
            "next_stage": "framing",
            "required_inputs": ["build-request"],
            "rationale": "The fixture is explicit enough for deterministic initialization.",
        },
    }


def test_skill_contract_and_repository_route_are_complete() -> None:
    skill = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
    gate_map = (SKILL_ROOT / "references" / "gate-map.md").read_text(encoding="utf-8")
    completion = (SKILL_ROOT / "references" / "completion-report.md").read_text(encoding="utf-8")
    agents = (SKILL_ROOT / "agents" / "openai.yaml").read_text(encoding="utf-8")
    repository_rules = (ROOT / "AGENTS.md").read_text(encoding="utf-8")

    assert "TODO" not in skill
    assert "name: build-tool-pipeline" in skill
    assert all(role in skill for role in ("intent_realizer", "product_contract_agent", "independent_verifier"))
    assert all(artifact in skill for artifact in ("build_request.yaml", "problem_frame.md", "product_contract.yaml", "run_state.json", "verification_report.md"))
    assert all(
        command in gate_map
        for command in (
            "validate-run",
            "validate-contract",
            "update-state",
            "role-boundary start",
            "role-boundary finish",
            "persist-artifact",
            "finalize-semantic-return",
            "run-tests",
            "package",
            "inspect-package",
            "prepare-verification",
        )
    )
    command_order = (
        "pipeline_ops.py --format json run-tests",
        "pipeline_ops.py --format json package",
        "pipeline_ops.py --format json inspect-package",
        "pipeline_ops.py --format json prepare-verification",
        "invoke `independent_verifier`",
    )
    positions = [gate_map.index(item) for item in command_order]
    assert positions == sorted(positions)
    assert gate_map.index("pipeline_ops.py --format json role-boundary start") < gate_map.index(
        "pipeline_ops.py --format json finalize-semantic-return"
    )
    assert "pre-verification candidate evidence" in gate_map
    assert "without rebuilding the archive" in gate_map
    assert "release stage `PENDING`" in skill
    assert "Reject a self-referential acceptance sequence" in skill
    assert "future final release-gate decision" in gate_map
    assert "enter verification as `IN_PROGRESS`" in gate_map
    assert "while verification remains `IN_PROGRESS`" in gate_map
    assert "Do not enter verification as `IN_PROGRESS`" not in gate_map
    assert "Never leave `run_state.json` pointing at a missing artifact" in skill
    assert "Stop and ask the user" in skill
    assert "AGENT_DECIDED" in skill
    assert "required_approvals" in skill
    legacy_routing = gate_map.split("## Failure Routing\n", 1)[1].split("\n## Release Sequence", 1)[0]
    assert "maximum is `2`" in legacy_routing
    assert "REPAIR_LIMIT_EXHAUSTED" in skill
    assert "DELIVERED_AWAITING_USER_APPROVAL" in completion
    assert "## User Approval" in completion
    assert "$build-tool-pipeline" in agents
    assert "### Build Tool Pipeline Routing" in repository_rules
    assert "$build-tool-pipeline" in repository_rules
    assert "### Module Responsibility and Boundaries" in repository_rules
    assert "three or more independently changing concerns" in repository_rules
    assert "do not split files solely to satisfy a line-count target" in repository_rules
    assert "choose cohesive module boundaries" in skill
    assert "implementation-quality check, not a product-contract requirement" in skill
    assert "open-ended theoretical experimentation" in skill
    assert "missing implementation conditions" in skill
    assert "new product objective" in skill


def test_boosted_pipeline_documentation_matches_revision_and_verification_contract() -> None:
    skill = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
    gate_map = (SKILL_ROOT / "references" / "gate-map.md").read_text(encoding="utf-8")
    completion = (SKILL_ROOT / "references" / "completion-report.md").read_text(encoding="utf-8")

    assert all(
        phrase in skill
        for phrase in (
            "`NEW_PRODUCT`",
            "Exact-baseline `REVISION`",
            "`revision_of`",
            "`delta_request`",
            "`scope_classification: BOUNDED`",
            "`FRESH_REQUIRED`",
            "`revision_control.mode: DELTA`",
            "`SUPERSEDED_CONTEXT` is a migration label, not a new `source_context.authority` enum value",
            "legacy run without the fully captured\nverified-candidate binding is not eligible as a delta baseline",
        )
    )
    normalized_skill = " ".join(skill.split())
    assert "Legacy calls remain read-only and return the complete brief" in normalized_skill
    assert "one complete artifact-contract 1.0 contract" in normalized_skill
    assert all(
        phrase in gate_map
        for phrase in (
            "--attempt-id <unique-test-attempt-id>",
            "30_execution/test_attempts/<attempt-id>/test_results.json",
            "`independent_verifier_judgment: NOT_PERFORMED`",
            "not the verifier's semantic judgment or an OS sandbox",
            "complete captured candidate binding",
            "`REVISION_BASELINE_DRIFT`",
            "`SUPERSEDED_CONTEXT` is not an authority enum",
        )
    )
    assert "Legacy verification permits focused probes under `40_verification/probes/**`" in gate_map
    assert "selected verification permits them only in its assigned `40_verification/probes/<audit-id>/` directory" in gate_map
    assert "role-boundary finish` plus `persist-artifact` remains available only for migration-compatible" in gate_map
    assert "`finalize-semantic-return`" in skill
    assert "`run-tests --attempt-id <unique-id>`" in skill
    assert "complete fresh command repetition" in skill
    assert "exact `candidate_binding`" in gate_map
    for text in (skill, gate_map):
        assert "null current verification report" in text
        assert "already active verification report" in text

    assert all(
        phrase in completion
        for phrase in (
            "verification-harness plan/attempt/summary paths and hashes",
            "cleanup path/status and retained-scratch flag",
            "`independent_verifier_judgment: NOT_PERFORMED`",
            "additional verifier-owned probe locations",
            "exact release candidate binding captured at verification PASS",
            "not an OS sandbox",
            "requires `FRESH_REQUIRED` handling",
        )
    )


def test_selected_round_procedure_preserves_legacy_limit_and_requires_audited_user_continuation() -> None:
    skill = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
    gate = (SKILL_ROOT / "references/gate-map.md").read_text(encoding="utf-8")
    bound = " ".join(skill.split("## Enforce the Repair Bound\n", 1)[1].split("\n## ", 1)[0].split())
    assert "Legacy control retains at most two automatic repair attempts" in bound
    assert "repair.maximum_attempts: 4 and repair.active_attempt: 0" in bound
    assert "active_attempt counts rounds started" in bound
    selected = gate.split("## Selected four-round modification and threshold review\n", 1)[1].split("\n## Failure Routing", 1)[0]
    normalized = " ".join(selected.split())
    assert "Initial terminal verification records latest_verification_result with count zero" in normalized
    assert "in-progress fourth round may finish" in normalized
    assert "before reserving round five" in normalized
    reserve = next(line for line in selected.splitlines() if "pipeline_ops.py" in line and "update-state" in line)
    assert all(flag in reserve for flag in ("--to-stage repair", "--failure-ref verification-report@", "--evidence-ref <BB-ID>"))
    assert "pre-reservation report cannot complete" in normalized
    assert "known unchanged contract/archive/source" in normalized
    assert "two null values are not equality" in normalized
    # Review completion precedes a decision; a recommendation alone grants no
    # allowance and none of these procedure controls relaxes product gates.
    assert selected.index("--review-event") < selected.index("role-boundary finish") < selected.index("--action resolve")
    assert "actual response" in normalized and "positive finite additional_rounds" in normalized
    assert "recommendation or general approval of framework work is not approval" in normalized
    assert "Exact duplicate resolution returns the original outcome without another increment" in normalized
    assert "No allowance waives requirement coverage, tests, candidate or release gates" in normalized


def test_minor_revision_skill_preserves_future_pipeline_delta_boundary() -> None:
    minor = (MINOR_SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
    metadata = (MINOR_SKILL_ROOT / "agents" / "openai.yaml").read_text(encoding="utf-8")
    pipeline = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")

    assert "TODO" not in minor
    assert "name: minor-tool-revision" in minor
    assert "PRE_EXISTING_DELTA_NOT_VERIFIED_BASELINE" in minor
    assert "exact baseline archive" in minor
    assert "FRESH_REQUIRED" in minor
    assert "independently verify the combined current behavior" in minor
    assert "$minor-tool-revision" in metadata
    assert "PRE_EXISTING_DELTA_NOT_VERIFIED_BASELINE" in pipeline
    assert "cumulative delta request" in pipeline
    assert "never eligible baselines by themselves" in pipeline


def test_explicit_legacy_initializer_creates_valid_run_and_refuses_overwrite(tmp_path: Path) -> None:
    request_path = tmp_path / "request.yaml"
    request_path.write_text(yaml.safe_dump(_request(), sort_keys=False), encoding="utf-8")
    command = [
        sys.executable,
        str(INITIALIZER),
        "--project-root",
        str(tmp_path),
        "--request",
        "request.yaml",
        "--control-revision",
        "1.0",
        "--timestamp",
        "2026-08-17T00:00:00+09:00",
        "--format",
        "json",
    ]

    first = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, check=False)
    assert first.returncode == 0, first.stderr or first.stdout
    payload = json.loads(first.stdout)
    assert payload["ok"] is True
    assert payload["data"]["repair_maximum_attempts"] == 2

    run_dir = tmp_path / "workspace" / "build_runs" / "phase5-skill-test"
    assert validate_run_directory(tmp_path, run_dir).ok
    state = json.loads((run_dir / "30_execution" / "run_state.json").read_text(encoding="utf-8"))
    assert state["schema_version"] == "1.1"
    assert state["control"] == {
        "semantic_role_boundary": "1.0",
        "intent_realization": "1.0",
        "verification_validation_identity": None,
    }
    assert state["run"]["current_stage"] == "intake"
    assert state["repair"] == {
        "active_attempt": 0,
        "maximum_attempts": 2,
        "last_failure_ref": None,
    }

    state_before = (run_dir / "30_execution" / "run_state.json").read_bytes()
    second = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, check=False)
    assert second.returncode == 1
    assert json.loads(second.stdout)["diagnostics"][0]["code"] == "RUN_EXISTS"
    assert (run_dir / "30_execution" / "run_state.json").read_bytes() == state_before


def test_invalid_gate_advancement_stops_without_state_change(tmp_path: Path) -> None:
    request_path = tmp_path / "request.yaml"
    request_path.write_text(yaml.safe_dump(_request(), sort_keys=False), encoding="utf-8")
    initialized = subprocess.run(
        [
            sys.executable,
            str(INITIALIZER),
            "--project-root",
            str(tmp_path),
            "--request",
            "request.yaml",
            "--format",
            "json",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert initialized.returncode == 0, initialized.stderr or initialized.stdout

    state_path = tmp_path / "workspace" / "build_runs" / "phase5-skill-test" / "30_execution" / "run_state.json"
    before = state_path.read_bytes()
    transition = subprocess.run(
        [
            sys.executable,
            str(ROOT / "pipeline_ops.py"),
            "--project-root",
            str(tmp_path),
            "--format",
            "json",
            "update-state",
            "--run-dir",
            "workspace/build_runs/phase5-skill-test",
            "--to-stage",
            "framing",
            "--stage-status",
            "IN_PROGRESS",
            "--gate-status",
            "IN_PROGRESS",
            "--rationale",
            "Attempt to skip the intake gate.",
            "--next-action",
            "This transition must be rejected.",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert transition.returncode == 1
    payload = json.loads(transition.stdout)
    assert payload["ok"] is False
    assert any(item["code"] == "TRANSITION_PRECONDITION" for item in payload["diagnostics"])
    assert state_path.read_bytes() == before


def test_initializer_help_is_available() -> None:
    result = subprocess.run(
        [sys.executable, str(INITIALIZER), "--help"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0
    assert "--project-root" in result.stdout
    assert "--request" in result.stdout
