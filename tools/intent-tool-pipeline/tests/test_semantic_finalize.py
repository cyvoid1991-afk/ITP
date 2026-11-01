from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

import pipeline_control.artifacts as artifacts_module
from pipeline_control.artifacts import finalize_semantic_return, persist_semantic_artifact
from pipeline_control.boundary import finish_role_boundary, start_role_boundary
from pipeline_control.cli import main
from pipeline_control.io_utils import InputError, normalize_repository_reference, sha256_file
from pipeline_control.result import CommandResult
from pipeline_control.validation import PROBLEM_FRAME_HEADINGS, validate_run_directory, validate_run_state_data


STARTED_AT = "2026-09-01T09:00:00+09:00"
FINALIZED_AT = "2026-09-01T09:01:00+09:00"
STAGES = (
    "intake",
    "framing",
    "contract",
    "repository_analysis",
    "implementation",
    "verification",
    "repair",
    "release",
)


def _build_request() -> dict:
    return {
        "schema_version": "1.0",
        "artifact": {
            "artifact_id": "build-request",
            "version": 1,
            "lifecycle_status": "ACTIVE",
            "owner_role": "root_codex",
            "created_at": STARTED_AT,
            "updated_at": STARTED_AT,
        },
        "project": {
            "project_id": "semantic-finalize-fixture",
            "name": "Semantic finalize fixture",
            "request_kind": "NEW_PRODUCT",
            "summary": "Exercise guarded semantic activation.",
        },
        "requested_outcome": {
            "objective": "Exercise guarded semantic activation.",
            "deliverables": ["fixture.py"],
            "success_summary": "The transaction remains atomic.",
        },
        "source_context": [],
        "build_profile": {"profile_id": "test"},
        "target": {"repository_path": "source", "output_path": "deliverables/fixture.zip"},
        "constraints": [],
        "user_decisions": [],
        "assumptions": [],
        "blockers": [],
        "handoff": {
            "readiness": "PASS",
            "next_stage": "framing",
            "required_inputs": ["build-request@1"],
            "rationale": "The deterministic fixture is ready.",
        },
    }


def _state() -> dict:
    stages = [
        {
            "id": stage,
            "status": "PASSED" if stage == "intake" else "PENDING",
            "gate_id": f"GATE-{stage.upper()}",
        }
        for stage in STAGES
    ]
    return {
        "schema_version": "1.1",
        "artifact": {
            "artifact_id": "run-state",
            "version": 1,
            "lifecycle_status": "ACTIVE",
            "owner_role": "root_codex",
            "created_at": STARTED_AT,
            "updated_at": STARTED_AT,
        },
        "control": {
            "semantic_role_boundary": "1.0",
            "verification_validation_identity": None,
        },
        "run": {
            "run_id": "semantic-finalize-fixture-001",
            "project_id": "semantic-finalize-fixture",
            "current_stage": "intake",
            "next_allowed_action": "Finalize the problem frame.",
        },
        "stages": stages,
        "gates": [
            {
                "id": "GATE-INTAKE",
                "status": "PASSED",
                "evidence_refs": ["build-request@1"],
                "rationale": "The fixture intake is complete.",
            }
        ],
        "active_artifacts": {
            "build_request": {
                "artifact_id": "build-request",
                "version": 1,
                "path": "00_intake/build_request.yaml",
            },
            "problem_frame": None,
            "product_contract": None,
            "run_state": {
                "artifact_id": "run-state",
                "version": 1,
                "path": "30_execution/run_state.json",
            },
            "verification_report": None,
        },
        "repair": {"active_attempt": 0, "maximum_attempts": 2, "last_failure_ref": None},
        "bounce_back_events": [],
        "blockers": [],
        "required_approvals": [],
    }


def _problem_frame(
    version: int = 1,
    *,
    artifact_id: str = "problem-frame",
    owner: str = "problem_framer",
    omit_heading: str | None = None,
) -> str:
    sections: list[str] = []
    for heading in PROBLEM_FRAME_HEADINGS:
        if heading == omit_heading:
            continue
        if heading == "Contract Metadata":
            body = "\n".join(
                (
                    "- Schema version: `1.0`",
                    f"- Artifact ID: `{artifact_id}`",
                    f"- Version: `{version}`",
                    "- Lifecycle status: `ACTIVE`",
                    f"- Semantic owner: `{owner}`",
                )
            )
        elif heading == "Completion Status":
            body = "PASS — ready for contract authoring."
        else:
            body = "Complete deterministic fixture content."
        sections.append(f"## {heading}\n\n{body}")
    return "# Problem Frame\n\n" + "\n\n".join(sections) + "\n"


def _contract(version: int = 1, *, owner: str = "product_contract_agent", backlink: bool = True) -> dict:
    return {
        "schema_version": "1.0",
        "artifact": {
            "artifact_id": "product-contract",
            "version": version,
            "lifecycle_status": "ACTIVE",
            "owner_role": owner,
            "created_at": STARTED_AT,
            "updated_at": FINALIZED_AT,
        },
        "source_artifacts": [
            {"artifact_id": "build-request", "version": 1},
            {"artifact_id": "problem-frame", "version": 1},
        ],
        "readiness": {"status": "PASS", "rationale": "The contract is complete."},
        "product": {
            "name": "Fixture",
            "objective": "Exercise finalize.",
            "primary_user": "Framework maintainer",
            "interface_summary": "A deterministic control-plane API.",
        },
        "scope": {"included": ["Finalize"], "excluded": ["Network"]},
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
        "requirements": [
            {
                "id": "REQ-001",
                "category": "FUNCTIONAL",
                "title": "Atomic finalize",
                "statement": "Finalize is atomic.",
                "source_refs": ["problem-frame@1"],
                "acceptance_refs": ["ACC-001"],
            }
        ],
        "acceptance_methods": [
            {
                "id": "ACC-001",
                "requirement_refs": ["REQ-001"] if backlink else [],
                "evidence_method": "TEST",
                "procedure": "Inject failures.",
                "expected_result": "Prior bytes remain exact.",
                "evidence_required": ["hashes"],
            }
        ],
        "implementation_constraints": [],
        "documentation_obligations": [],
        "handoff": {
            "next_stage": "repository_analysis",
            "required_artifacts": [f"product-contract@{version}"],
            "carried_assumptions": [],
            "open_blockers": [],
            "rationale": "The contract can be implemented.",
        },
    }


def _write_run(project_root: Path) -> Path:
    run = project_root / "run"
    for relative in ("00_intake", "10_framing", "20_contract", "30_execution", "40_verification", "50_release"):
        (run / relative).mkdir(parents=True, exist_ok=True)
    (run / "00_intake" / "build_request.yaml").write_text(
        yaml.safe_dump(_build_request(), sort_keys=False), encoding="utf-8"
    )
    (run / "30_execution" / "run_state.json").write_text(
        json.dumps(_state(), indent=2) + "\n", encoding="utf-8"
    )
    assert validate_run_directory(project_root, run).ok
    return run


def _intent_run(project_root: Path, marked: bool) -> Path:
    run = _write_run(project_root)
    if marked:
        state = _state()
        state["control"]["intent_realization"] = "1.0"
        (run / "30_execution/run_state.json").write_text(json.dumps(state), encoding="utf-8")
    return run


@pytest.mark.parametrize("marked", [False, True], ids=["legacy", "intent"])
@pytest.mark.parametrize("method", ["finalize", "persist"])
def test_run_selected_owner_activates_exact_body(tmp_path: Path, marked: bool, method: str) -> None:
    run = _intent_run(tmp_path, marked)
    owner = "intent_realizer" if marked else "problem_framer"
    source = tmp_path / "return.md"
    source.write_text(_problem_frame(owner=owner), encoding="utf-8")
    started = _start(tmp_path, run, role=owner, invocation="ir")
    if method == "finalize":
        result = finalize_semantic_return(tmp_path, run, artifact_key="problem_frame", role=owner,
            invocation_ref="ir", baseline_sha256=started["baseline_sha256"], source_path=source, timestamp=FINALIZED_AT)
    else:
        finished = finish_role_boundary(tmp_path, run, role=owner, invocation_ref="ir",
            baseline_sha256=started["baseline_sha256"], timestamp=FINALIZED_AT)
        assert finished.ok, finished.as_dict()
        result = persist_semantic_artifact(tmp_path, run, artifact_key="problem_frame", source_path=source,
            source_invocation_ref="ir", boundary_evidence_ref=finished.data["evidence_ref"], timestamp=FINALIZED_AT)
    assert result.ok, result.as_dict()
    state = json.loads((run / "30_execution/run_state.json").read_text(encoding="utf-8"))
    assert state["active_artifacts"]["problem_frame"]["semantic_owner"] == owner
    assert result.data["semantic_owner"] == owner
    assert (run / "10_framing/problem_frame.md").read_bytes() == source.read_bytes()
    assert validate_run_directory(tmp_path, run).ok
    # An active entry cannot switch identities merely by changing its recorded owner.
    state["active_artifacts"]["problem_frame"]["semantic_owner"] = "problem_framer" if marked else "intent_realizer"
    assert "SEMANTIC_OWNER" in {item.code for item in validate_run_state_data(state)}


@pytest.mark.parametrize("marked", [False, True], ids=["legacy", "intent"])
def test_cross_role_start_rejected_without_run_mutation(tmp_path: Path, marked: bool) -> None:
    run = _intent_run(tmp_path, marked)
    before = {str(path.relative_to(run)): path.read_bytes() for path in run.rglob("*") if path.is_file()}
    result = start_role_boundary(tmp_path, run, role="problem_framer" if marked else "intent_realizer",
        invocation_ref="wrong", timestamp=STARTED_AT)
    assert not result.ok and "SEMANTIC_ROLE" in {item.code for item in result.diagnostics}
    assert before == {str(path.relative_to(run)): path.read_bytes() for path in run.rglob("*") if path.is_file()}


@pytest.mark.parametrize("marked", [False, True], ids=["legacy", "intent"])
def test_cross_role_finalize_preserves_original_audit(tmp_path: Path, marked: bool) -> None:
    run = _intent_run(tmp_path, marked)
    owner = "intent_realizer" if marked else "problem_framer"
    source = tmp_path / "return.md"
    source.write_text(_problem_frame(owner=owner), encoding="utf-8")
    started = _start(tmp_path, run, role=owner, invocation="ir")
    before = (run / "30_execution/run_state.json").read_bytes()
    audit_before = {str(path.relative_to(run)): path.read_bytes()
        for path in (run / "30_execution/role_boundary").rglob("*") if path.is_file()}
    rejected = finalize_semantic_return(tmp_path, run, artifact_key="problem_frame",
        role="problem_framer" if marked else "intent_realizer", invocation_ref="ir",
        baseline_sha256=started["baseline_sha256"], source_path=source, timestamp=FINALIZED_AT)
    assert not rejected.ok
    assert (run / "30_execution/run_state.json").read_bytes() == before
    assert not (run / "10_framing/problem_frame.md").exists()
    assert audit_before == {str(path.relative_to(run)): path.read_bytes()
        for path in (run / "30_execution/role_boundary").rglob("*") if path.is_file()}
    accepted = finalize_semantic_return(tmp_path, run, artifact_key="problem_frame", role=owner,
        invocation_ref="ir", baseline_sha256=started["baseline_sha256"], source_path=source, timestamp=FINALIZED_AT)
    assert accepted.ok, accepted.as_dict()


@pytest.mark.parametrize("marker", [None, "2.0", 1, {}, []])
def test_invalid_intent_marker_is_rejected(marker: object) -> None:
    state = _state()
    state["control"]["intent_realization"] = marker
    assert "INTENT_REALIZATION_REVISION" in {item.code for item in validate_run_state_data(state)}


def test_intent_marker_requires_controlled_schema() -> None:
    state = _state()
    state["schema_version"] = "1.0"
    state["control"]["intent_realization"] = "1.0"
    assert "INTENT_REALIZATION_REVISION" in {item.code for item in validate_run_state_data(state)}


@pytest.mark.parametrize("marked", [False, True], ids=["legacy", "intent"])
@pytest.mark.parametrize("method", ["finalize", "persist"])
def test_other_owner_body_cannot_activate(tmp_path: Path, marked: bool, method: str) -> None:
    run = _intent_run(tmp_path, marked)
    owner = "intent_realizer" if marked else "problem_framer"
    source = tmp_path / "return.md"
    source.write_text(_problem_frame(owner="problem_framer" if marked else "intent_realizer"), encoding="utf-8")
    started = _start(tmp_path, run, role=owner, invocation="ir")
    before = (run / "30_execution/run_state.json").read_bytes()
    if method == "finalize":
        result = finalize_semantic_return(tmp_path, run, artifact_key="problem_frame", role=owner,
            invocation_ref="ir", baseline_sha256=started["baseline_sha256"], source_path=source, timestamp=FINALIZED_AT)
    else:
        finished = finish_role_boundary(tmp_path, run, role=owner, invocation_ref="ir",
            baseline_sha256=started["baseline_sha256"], timestamp=FINALIZED_AT)
        assert finished.ok, finished.as_dict()
        result = persist_semantic_artifact(tmp_path, run, artifact_key="problem_frame", source_path=source,
            source_invocation_ref="ir", boundary_evidence_ref=finished.data["evidence_ref"], timestamp=FINALIZED_AT)
    assert not result.ok and "SEMANTIC_OWNER" in {item.code for item in result.diagnostics}
    assert (run / "30_execution/run_state.json").read_bytes() == before
    assert not (run / "10_framing/problem_frame.md").exists()


def test_intent_marker_tamper_still_restores_original_state(tmp_path: Path) -> None:
    run = _intent_run(tmp_path, True)
    source = tmp_path / "return.md"
    source.write_text(_problem_frame(owner="intent_realizer"), encoding="utf-8")
    started = _start(tmp_path, run, role="intent_realizer", invocation="ir")
    state_path = run / "30_execution/run_state.json"
    before = state_path.read_bytes()
    state = json.loads(before)
    del state["control"]["intent_realization"]
    state_path.write_text(json.dumps(state), encoding="utf-8")
    result = finalize_semantic_return(tmp_path, run, artifact_key="problem_frame", role="intent_realizer",
        invocation_ref="ir", baseline_sha256=started["baseline_sha256"], source_path=source, timestamp=FINALIZED_AT)
    assert not result.ok and "BOUNDARY_VIOLATION" in {item.code for item in result.diagnostics}
    assert state_path.read_bytes() == before
    assert not (run / "10_framing/problem_frame.md").exists()


def _start(project_root: Path, run: Path, *, role: str, invocation: str) -> dict:
    result = start_role_boundary(
        project_root,
        run,
        role=role,
        invocation_ref=invocation,
        timestamp=STARTED_AT,
    )
    assert result.ok, result.as_dict()
    return result.data


def _finalize_problem(
    project_root: Path,
    run: Path,
    *,
    invocation: str,
    body: str | None = None,
) -> CommandResult:
    started = _start(project_root, run, role="problem_framer", invocation=invocation)
    source = project_root / f"{invocation}.md"
    source.write_text(body or _problem_frame(), encoding="utf-8", newline="\n")
    return finalize_semantic_return(
        project_root,
        run,
        artifact_key="problem_frame",
        role="problem_framer",
        invocation_ref=invocation,
        baseline_sha256=started["baseline_sha256"],
        source_path=source,
        timestamp=FINALIZED_AT,
    )


def _journal(result: CommandResult, project_root: Path) -> dict:
    assert result.data.get("failed_attempt_ref"), result.as_dict()
    return json.loads((project_root / result.data["failed_attempt_ref"]).read_text(encoding="utf-8"))


def test_success_matches_the_existing_manual_sequence(tmp_path: Path) -> None:
    manual_root = tmp_path / "manual"
    final_root = tmp_path / "final"
    manual_run = _write_run(manual_root)
    final_run = _write_run(final_root)
    manual_started = _start(manual_root, manual_run, role="problem_framer", invocation="equivalent")
    final_started = _start(final_root, final_run, role="problem_framer", invocation="equivalent")
    assert manual_started["baseline_sha256"] == final_started["baseline_sha256"]
    for root in (manual_root, final_root):
        (root / "return.md").write_text(_problem_frame(), encoding="utf-8", newline="\n")

    finished = finish_role_boundary(
        manual_root,
        manual_run,
        role="problem_framer",
        invocation_ref="equivalent",
        baseline_sha256=manual_started["baseline_sha256"],
        timestamp=FINALIZED_AT,
    )
    assert finished.ok, finished.as_dict()
    persisted = persist_semantic_artifact(
        manual_root,
        manual_run,
        artifact_key="problem_frame",
        source_path=manual_root / "return.md",
        source_invocation_ref="equivalent",
        boundary_evidence_ref=finished.data["evidence_ref"],
        timestamp=FINALIZED_AT,
    )
    finalized = finalize_semantic_return(
        final_root,
        final_run,
        artifact_key="problem_frame",
        role="problem_framer",
        invocation_ref="equivalent",
        baseline_sha256=final_started["baseline_sha256"],
        source_path=final_root / "return.md",
        timestamp=FINALIZED_AT,
    )

    assert persisted.ok and finalized.ok, (persisted.as_dict(), finalized.as_dict())
    assert (manual_run / "10_framing/problem_frame.md").read_bytes() == (
        final_run / "10_framing/problem_frame.md"
    ).read_bytes()
    assert (manual_run / "30_execution/run_state.json").read_bytes() == (
        final_run / "30_execution/run_state.json"
    ).read_bytes()
    assert finalized.data["artifact_ref"] == "problem-frame@1"
    assert finalized.data["content_sha256"] == sha256_file(final_run / "10_framing/problem_frame.md")
    assert finalized.data["boundary_evidence_ref"] == finished.data["evidence_ref"]
    assert finalized.data["run_state_version"] == 2
    assert validate_run_directory(final_root, final_run).ok


def test_finalize_cli_and_backslash_repository_references(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    run = _write_run(tmp_path)
    started = _start(tmp_path, run, role="problem_framer", invocation="cli-finalize")
    source = tmp_path / "returns" / "problem.md"
    source.parent.mkdir()
    source.write_text(_problem_frame(), encoding="utf-8")
    exit_code = main(
        [
            "--project-root",
            str(tmp_path),
            "--format",
            "json",
            "finalize-semantic-return",
            "--run-dir",
            "run",
            "--artifact",
            "problem_frame",
            "--role",
            "problem_framer",
            "--invocation-ref",
            "cli-finalize",
            "--baseline-sha256",
            started["baseline_sha256"],
            "--source",
            r"returns\problem.md",
            "--timestamp",
            FINALIZED_AT,
        ]
    )
    rendered = json.loads(capsys.readouterr().out)
    assert exit_code == 0, rendered
    assert rendered["data"]["artifact_ref"] == "problem-frame@1"

    state_path = run / "30_execution/run_state.json"
    state = json.loads(state_path.read_text(encoding="utf-8"))
    entry = state["active_artifacts"]["problem_frame"]
    entry["path"] = entry["path"].replace("/", "\\")
    entry["boundary_evidence_ref"] = entry["boundary_evidence_ref"].replace("/", "\\")
    state_path.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
    assert validate_run_directory(tmp_path, run).ok
    assert normalize_repository_reference(r"run\30_execution\run_state.json") == "run/30_execution/run_state.json"
    with pytest.raises(InputError):
        normalize_repository_reference(r"..\outside.txt")


@pytest.mark.parametrize(
    ("body", "code"),
    [
        (_problem_frame(artifact_id="wrong-frame"), "ARTIFACT_ID"),
        (_problem_frame(owner="explorer"), "SEMANTIC_OWNER"),
        (_problem_frame(version=2), "ARTIFACT_VERSION_SEQUENCE"),
        (_problem_frame(omit_heading="Failure Behavior"), "MARKDOWN_HEADING"),
    ],
)
def test_invalid_problem_body_is_rejected_after_boundary_and_journaled(
    tmp_path: Path,
    body: str,
    code: str,
) -> None:
    run = _write_run(tmp_path)
    state_before = (run / "30_execution/run_state.json").read_bytes()
    result = _finalize_problem(tmp_path, run, invocation=f"bad-{code.lower()}", body=body)
    assert not result.ok
    assert code in {item.code for item in result.diagnostics}
    assert (run / "30_execution/run_state.json").read_bytes() == state_before
    assert not (run / "10_framing/problem_frame.md").exists()
    evidence = _journal(result, tmp_path)
    assert evidence["failed_step"] == "body_validation"
    assert evidence["boundary"]["status"] == "PASS"
    assert evidence["rollback"]["status"] == "not_required"


@pytest.mark.parametrize(
    ("owner", "backlink", "expected_code"),
    [
        ("root_codex", True, "SEMANTIC_OWNER"),
        ("product_contract_agent", False, "MAPPING_EMPTY"),
    ],
)
def test_contract_owner_and_bidirectional_backlink_validation(
    tmp_path: Path,
    owner: str,
    backlink: bool,
    expected_code: str,
) -> None:
    run = _write_run(tmp_path)
    invocation = f"contract-{expected_code.lower()}"
    started = _start(tmp_path, run, role="product_contract_agent", invocation=invocation)
    source = tmp_path / f"{invocation}.yaml"
    source.write_text(yaml.safe_dump(_contract(owner=owner, backlink=backlink), sort_keys=False), encoding="utf-8")
    result = finalize_semantic_return(
        tmp_path,
        run,
        artifact_key="product_contract",
        role="product_contract_agent",
        invocation_ref=invocation,
        baseline_sha256=started["baseline_sha256"],
        source_path=source,
        timestamp=FINALIZED_AT,
    )
    assert not result.ok
    assert expected_code in {item.code for item in result.diagnostics}
    assert _journal(result, tmp_path)["failed_step"] == "body_validation"


def test_contract_yaml_parse_failure_is_not_reinterpreted_or_activated(tmp_path: Path) -> None:
    run = _write_run(tmp_path)
    invocation = "contract-yaml-parse-error"
    started = _start(tmp_path, run, role="product_contract_agent", invocation=invocation)
    source = tmp_path / f"{invocation}.yaml"
    valid_body = yaml.safe_dump(_contract(), sort_keys=False)
    invalid_body = valid_body.replace(
        "  statement: Finalize is atomic.\n",
        "  statement: : malformed plain scalar\n",
    )
    assert invalid_body != valid_body
    with pytest.raises(yaml.YAMLError):
        yaml.safe_load(invalid_body)
    source.write_text(invalid_body, encoding="utf-8", newline="\n")

    state_path = run / "30_execution/run_state.json"
    canonical_path = run / "20_contract/product_contract.yaml"
    history_path = run / "20_contract/history/product_contract.v1.yaml"
    state_before = state_path.read_bytes()
    source_before = source.read_bytes()

    result = finalize_semantic_return(
        tmp_path,
        run,
        artifact_key="product_contract",
        role="product_contract_agent",
        invocation_ref=invocation,
        baseline_sha256=started["baseline_sha256"],
        source_path=source,
        timestamp=FINALIZED_AT,
    )

    assert not result.ok
    assert "PARSE_ERROR" in {item.code for item in result.diagnostics}
    assert state_path.read_bytes() == state_before
    assert source.read_bytes() == source_before
    assert not canonical_path.exists()
    assert not history_path.exists()
    evidence = _journal(result, tmp_path)
    assert evidence["failed_step"] == "body_validation"
    assert evidence["boundary"]["status"] == "PASS"
    assert evidence["history"] == {"action": "not_attempted", "path": None, "sha256": None}
    assert evidence["rollback"]["status"] == "not_required"
    assert {item["code"] for item in evidence["diagnostics"]} == {"PARSE_ERROR"}
    assert evidence["request"]["source_sha256"] == sha256_file(source)


def test_wrong_role_is_preflighted_without_consuming_boundary(tmp_path: Path) -> None:
    run = _write_run(tmp_path)
    started = _start(tmp_path, run, role="problem_framer", invocation="role-preflight")
    source = tmp_path / "role-preflight.md"
    source.write_text(_problem_frame(), encoding="utf-8")
    rejected = finalize_semantic_return(
        tmp_path,
        run,
        artifact_key="problem_frame",
        role="explorer",
        invocation_ref="role-preflight",
        baseline_sha256=started["baseline_sha256"],
        source_path=source,
        timestamp=FINALIZED_AT,
    )
    assert not rejected.ok
    assert "SEMANTIC_ROLE" in {item.code for item in rejected.diagnostics}
    assert _journal(rejected, tmp_path)["failed_step"] == "preflight"

    accepted = finalize_semantic_return(
        tmp_path,
        run,
        artifact_key="problem_frame",
        role="problem_framer",
        invocation_ref="role-preflight",
        baseline_sha256=started["baseline_sha256"],
        source_path=source,
        timestamp="2026-09-01T09:02:00+09:00",
    )
    assert accepted.ok, accepted.as_dict()


@pytest.mark.parametrize("identity_kind", ["invocation", "baseline"])
def test_wrong_invocation_or_baseline_is_journaled(identity_kind: str, tmp_path: Path) -> None:
    run = _write_run(tmp_path)
    started = _start(tmp_path, run, role="problem_framer", invocation="identity")
    source = tmp_path / "identity.md"
    source.write_text(_problem_frame(), encoding="utf-8")
    result = finalize_semantic_return(
        tmp_path,
        run,
        artifact_key="problem_frame",
        role="problem_framer",
        invocation_ref="wrong-invocation" if identity_kind == "invocation" else "identity",
        baseline_sha256="0" * 64 if identity_kind == "baseline" else started["baseline_sha256"],
        source_path=source,
        timestamp=FINALIZED_AT,
    )
    assert not result.ok
    codes = {item.code for item in result.diagnostics}
    assert ("BOUNDARY_BASELINE" if identity_kind == "invocation" else "BOUNDARY_BASELINE_IDENTITY") in codes
    assert _journal(result, tmp_path)["failed_step"] == "boundary_finish"


def test_source_containment_is_preflighted_and_journaled(tmp_path: Path) -> None:
    project_root = tmp_path / "project"
    run = _write_run(project_root)
    started = _start(project_root, run, role="problem_framer", invocation="outside-source")
    outside = tmp_path / "outside.md"
    outside.write_text(_problem_frame(), encoding="utf-8")
    result = finalize_semantic_return(
        project_root,
        run,
        artifact_key="problem_frame",
        role="problem_framer",
        invocation_ref="outside-source",
        baseline_sha256=started["baseline_sha256"],
        source_path=outside,
        timestamp=FINALIZED_AT,
    )
    assert not result.ok
    assert "SOURCE_SCOPE" in {item.code for item in result.diagnostics}
    assert _journal(result, project_root)["failed_step"] == "preflight"


def test_boundary_violation_restores_state_retains_result_and_blocks_activation(tmp_path: Path) -> None:
    run = _write_run(tmp_path)
    state_path = run / "30_execution/run_state.json"
    prior_state = state_path.read_bytes()
    started = _start(tmp_path, run, role="problem_framer", invocation="boundary-violation")
    source = tmp_path / "boundary-violation.md"
    source.write_text(_problem_frame(), encoding="utf-8")
    state = json.loads(state_path.read_text(encoding="utf-8"))
    state["run"]["next_allowed_action"] = "Unauthorized semantic mutation."
    state.pop("stages")
    state_path.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")

    result = finalize_semantic_return(
        tmp_path,
        run,
        artifact_key="problem_frame",
        role="problem_framer",
        invocation_ref="boundary-violation",
        baseline_sha256=started["baseline_sha256"],
        source_path=source,
        timestamp=FINALIZED_AT,
    )
    assert not result.ok
    assert "BOUNDARY_VIOLATION" in {item.code for item in result.diagnostics}
    assert state_path.read_bytes() == prior_state
    evidence = _journal(result, tmp_path)
    assert evidence["failed_step"] == "boundary_pass"
    assert evidence["boundary"]["status"] == "BOUNDARY_VIOLATION"
    boundary_path = tmp_path / evidence["boundary"]["evidence_ref"]
    assert boundary_path.is_file()
    assert json.loads(boundary_path.read_text(encoding="utf-8"))["run_state_restored"] is True


def test_history_create_reuse_and_conflict_are_immutable(tmp_path: Path) -> None:
    create_root = tmp_path / "create"
    create_run = _write_run(create_root)
    assert _finalize_problem(create_root, create_run, invocation="create-v1").ok
    prior = (create_run / "10_framing/problem_frame.md").read_bytes()
    created = _finalize_problem(create_root, create_run, invocation="create-v2", body=_problem_frame(2))
    assert created.ok, created.as_dict()
    history = create_run / "10_framing/history/problem_frame.v1.md"
    assert created.data["history_action"] == "created"
    assert history.read_bytes() == prior

    reuse_root = tmp_path / "reuse"
    reuse_run = _write_run(reuse_root)
    assert _finalize_problem(reuse_root, reuse_run, invocation="reuse-v1").ok
    reuse_prior = (reuse_run / "10_framing/problem_frame.md").read_bytes()
    reuse_history = reuse_run / "10_framing/history/problem_frame.v1.md"
    reuse_history.parent.mkdir()
    reuse_history.write_bytes(reuse_prior)
    reused = _finalize_problem(reuse_root, reuse_run, invocation="reuse-v2", body=_problem_frame(2))
    assert reused.ok, reused.as_dict()
    assert reused.data["history_action"] == "reused"

    conflict_root = tmp_path / "conflict"
    conflict_run = _write_run(conflict_root)
    assert _finalize_problem(conflict_root, conflict_run, invocation="conflict-v1").ok
    conflict_state = (conflict_run / "30_execution/run_state.json").read_bytes()
    conflict_target = (conflict_run / "10_framing/problem_frame.md").read_bytes()
    conflict_history = conflict_run / "10_framing/history/problem_frame.v1.md"
    conflict_history.parent.mkdir()
    conflict_history.write_bytes(b"different immutable history\n")
    conflicted = _finalize_problem(conflict_root, conflict_run, invocation="conflict-v2", body=_problem_frame(2))
    assert not conflicted.ok
    assert "FINALIZE_HISTORY" in {item.code for item in conflicted.diagnostics}
    assert (conflict_run / "30_execution/run_state.json").read_bytes() == conflict_state
    assert (conflict_run / "10_framing/problem_frame.md").read_bytes() == conflict_target
    assert conflict_history.read_bytes() == b"different immutable history\n"
    evidence = _journal(conflicted, conflict_root)
    assert evidence["history"]["action"] == "conflict"


@pytest.mark.parametrize("failure_point", ["artifact", "state", "post_validation"])
def test_failure_injection_restores_exact_prior_bytes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    failure_point: str,
) -> None:
    run = _write_run(tmp_path)
    assert _finalize_problem(tmp_path, run, invocation=f"{failure_point}-v1").ok
    state_path = run / "30_execution/run_state.json"
    target = run / "10_framing/problem_frame.md"
    prior_state = state_path.read_bytes()
    prior_target = target.read_bytes()
    started = _start(tmp_path, run, role="problem_framer", invocation=f"{failure_point}-v2")
    source = tmp_path / f"{failure_point}-v2.md"
    source.write_text(_problem_frame(2), encoding="utf-8")

    if failure_point == "artifact":
        original_write_bytes = artifacts_module.atomic_write_bytes

        def fail_artifact(path: Path, payload: bytes) -> str:
            if path == target and payload != prior_target:
                raise OSError("injected canonical write failure")
            return original_write_bytes(path, payload)

        monkeypatch.setattr(artifacts_module, "atomic_write_bytes", fail_artifact)
    elif failure_point == "state":
        original_write_json = artifacts_module.atomic_write_json

        def fail_state(path: Path, value: object) -> None:
            if path == state_path:
                raise OSError("injected state activation failure")
            original_write_json(path, value)

        monkeypatch.setattr(artifacts_module, "atomic_write_json", fail_state)
    else:
        original_validate = artifacts_module.validate_run_directory
        calls = 0

        def fail_post(project_root: Path, candidate_run: Path) -> CommandResult:
            nonlocal calls
            calls += 1
            if calls == 2:
                injected = CommandResult(command="validate-run")
                injected.add("INJECTED_POST_VALIDATION", str(candidate_run), "injected post-validation failure")
                return injected
            return original_validate(project_root, candidate_run)

        monkeypatch.setattr(artifacts_module, "validate_run_directory", fail_post)

    result = finalize_semantic_return(
        tmp_path,
        run,
        artifact_key="problem_frame",
        role="problem_framer",
        invocation_ref=f"{failure_point}-v2",
        baseline_sha256=started["baseline_sha256"],
        source_path=source,
        timestamp=FINALIZED_AT,
    )
    assert not result.ok
    assert state_path.read_bytes() == prior_state
    assert target.read_bytes() == prior_target
    history = run / "10_framing/history/problem_frame.v1.md"
    assert history.read_bytes() == prior_target
    evidence = _journal(result, tmp_path)
    assert evidence["failed_step"] == {
        "artifact": "artifact_write",
        "state": "state_activation",
        "post_validation": "post_validation",
    }[failure_point]
    assert evidence["rollback"] == {
        "status": "restored",
        "state_restored": True,
        "artifact_restored": True,
        "errors": [],
    }
    assert evidence["prior"]["state_sha256"] == artifacts_module.sha256_bytes(prior_state)
    assert evidence["prior"]["artifact_sha256"] == artifacts_module.sha256_bytes(prior_target)


def test_rollback_and_journal_failures_are_surfaced(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    run = _write_run(tmp_path)
    assert _finalize_problem(tmp_path, run, invocation="surface-v1").ok
    state_path = run / "30_execution/run_state.json"
    target = run / "10_framing/problem_frame.md"
    prior_state = state_path.read_bytes()
    prior_target = target.read_bytes()
    started = _start(tmp_path, run, role="problem_framer", invocation="surface-v2")
    source = tmp_path / "surface-v2.md"
    source.write_text(_problem_frame(2), encoding="utf-8")
    original_json = artifacts_module.atomic_write_json
    original_bytes = artifacts_module.atomic_write_bytes

    def fail_state_and_journal(path: Path, value: object) -> None:
        if path == state_path or "failed_attempts" in path.parts:
            raise OSError("injected JSON write failure")
        original_json(path, value)

    def fail_state_rollback(path: Path, payload: bytes) -> str:
        if path == state_path:
            raise OSError("injected rollback failure")
        return original_bytes(path, payload)

    monkeypatch.setattr(artifacts_module, "atomic_write_json", fail_state_and_journal)
    monkeypatch.setattr(artifacts_module, "atomic_write_bytes", fail_state_rollback)
    result = finalize_semantic_return(
        tmp_path,
        run,
        artifact_key="problem_frame",
        role="problem_framer",
        invocation_ref="surface-v2",
        baseline_sha256=started["baseline_sha256"],
        source_path=source,
        timestamp=FINALIZED_AT,
    )
    codes = {item.code for item in result.diagnostics}
    assert {"FINALIZE_STATE", "FINALIZE_ROLLBACK", "FINALIZE_JOURNAL"} <= codes
    # The injected activation failed before replacing state, while artifact
    # rollback still succeeded; the error is surfaced even though bytes match.
    assert state_path.read_bytes() == prior_state
    assert target.read_bytes() == prior_target


def test_differing_failed_attempt_evidence_is_never_overwritten(tmp_path: Path) -> None:
    run = _write_run(tmp_path)
    started = _start(tmp_path, run, role="problem_framer", invocation="journal-conflict")
    source = tmp_path / "journal-conflict.md"
    source.write_text(_problem_frame(owner="explorer"), encoding="utf-8")
    first = finalize_semantic_return(
        tmp_path,
        run,
        artifact_key="problem_frame",
        role="problem_framer",
        invocation_ref="journal-conflict",
        baseline_sha256=started["baseline_sha256"],
        source_path=source,
        timestamp=FINALIZED_AT,
    )
    journal_path = tmp_path / first.data["failed_attempt_ref"]
    journal_path.write_text('{"different":true}\n', encoding="utf-8")
    before = journal_path.read_bytes()

    second = finalize_semantic_return(
        tmp_path,
        run,
        artifact_key="problem_frame",
        role="problem_framer",
        invocation_ref="journal-conflict",
        baseline_sha256=started["baseline_sha256"],
        source_path=source,
        timestamp=FINALIZED_AT,
    )
    assert not second.ok
    assert "FINALIZE_JOURNAL_CONFLICT" in {item.code for item in second.diagnostics}
    assert journal_path.read_bytes() == before


def test_boundary_result_can_recover_latest_index_without_losing_violation_evidence(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run = _write_run(tmp_path)
    started = _start(tmp_path, run, role="problem_framer", invocation="index-recovery")
    import pipeline_control.boundary as boundary_module

    original_boundary_json = boundary_module.atomic_write_json
    latest_path = run / "30_execution/role_boundary/latest.json"

    def fail_latest(path: Path, value: object) -> None:
        if path == latest_path:
            raise OSError("injected latest-index failure")
        original_boundary_json(path, value)

    monkeypatch.setattr(boundary_module, "atomic_write_json", fail_latest)
    first = finish_role_boundary(
        tmp_path,
        run,
        role="problem_framer",
        invocation_ref="index-recovery",
        baseline_sha256=started["baseline_sha256"],
        timestamp=FINALIZED_AT,
    )
    assert not first.ok
    assert "BOUNDARY_INDEX" in {item.code for item in first.diagnostics}
    result_path = tmp_path / first.data["evidence_ref"]
    immutable_result = result_path.read_bytes()

    monkeypatch.setattr(boundary_module, "atomic_write_json", original_boundary_json)
    recovered = finish_role_boundary(
        tmp_path,
        run,
        role="problem_framer",
        invocation_ref="index-recovery",
        baseline_sha256=started["baseline_sha256"],
        timestamp="2026-09-01T09:03:00+09:00",
    )
    assert recovered.ok, recovered.as_dict()
    assert recovered.data["index_recovered"] is True
    assert result_path.read_bytes() == immutable_result
    assert json.loads(latest_path.read_text(encoding="utf-8"))["roles"]["problem_framer"]["status"] == "PASS"
