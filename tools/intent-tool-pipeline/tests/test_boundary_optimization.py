from __future__ import annotations

import json
import os
import shutil
from pathlib import Path

import pytest

import pipeline_control.boundary as boundary
from pipeline_control.boundary import (
    ROLE_BOUNDARY_POLICIES,
    ROLE_POLICIES,
    finish_role_boundary,
    start_role_boundary,
    validate_boundary_pass,
)
from pipeline_control.io_utils import sha256_file
from pipeline_control.scratch import ScratchError, allocate_verification_scratch


TIMESTAMP = "2026-09-01T12:00:00+09:00"
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


def _state() -> dict:
    stages = []
    for stage_id in STAGES:
        stages.append(
            {
                "id": stage_id,
                "status": "PASSED" if stage_id == "intake" else "PENDING",
                "gate_id": f"GATE-{stage_id.upper()}",
            }
        )
    return {
        "schema_version": "1.1",
        "artifact": {
            "artifact_id": "run-state",
            "version": 1,
            "lifecycle_status": "ACTIVE",
            "owner_role": "root_codex",
            "created_at": TIMESTAMP,
            "updated_at": TIMESTAMP,
        },
        "run": {
            "run_id": "boundary-optimization-fixture",
            "project_id": "boundary-optimization",
            "current_stage": "intake",
            "next_allowed_action": "Audit the semantic role.",
        },
        "stages": stages,
        "gates": [
            {
                "id": "GATE-INTAKE",
                "status": "PASSED",
                "evidence_refs": ["00_intake/build_request.yaml"],
                "rationale": "Fixture intake is complete.",
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
        "control": {
            "semantic_role_boundary": "1.0",
            "verification_validation_identity": None,
        },
    }


def _write_run(project_root: Path) -> Path:
    run = project_root / "run"
    for directory in ("00_intake", "10_framing", "20_contract", "30_execution", "40_verification", "50_release"):
        (run / directory).mkdir(parents=True)
    (run / "00_intake" / "build_request.yaml").write_text("fixture: true\n", encoding="utf-8")
    (run / "10_framing" / "protected.txt").write_text("protected baseline\n", encoding="utf-8")
    (run / "30_execution" / "run_state.json").write_text(json.dumps(_state(), indent=2) + "\n", encoding="utf-8")
    return run


def _start(project_root: Path, run: Path, invocation_ref: str) -> dict:
    started = start_role_boundary(
        project_root,
        run,
        role="independent_verifier",
        invocation_ref=invocation_ref,
        timestamp=TIMESTAMP,
    )
    assert started.ok, started.as_dict()
    return started.data


def _finish(project_root: Path, run: Path, invocation_ref: str, started: dict):
    return finish_role_boundary(
        project_root,
        run,
        role="independent_verifier",
        invocation_ref=invocation_ref,
        baseline_sha256=started["baseline_sha256"],
        timestamp="2026-09-01T12:01:00+09:00",
    )


def test_explicit_policy_preserves_legacy_allowed_roots_and_baseline_fields(tmp_path: Path) -> None:
    run = _write_run(tmp_path)

    assert ROLE_POLICIES["independent_verifier"] == ("40_verification/probes",)
    policy = ROLE_BOUNDARY_POLICIES["independent_verifier"]
    assert policy.allowed_durable_roots == ()
    assert policy.allowed_ephemeral_roots == ("40_verification/probes",)
    assert policy.protected_roots == ("",)

    started = _start(tmp_path, run, "explicit-policy")
    baseline = json.loads((tmp_path / started["baseline_path"]).read_text(encoding="utf-8"))
    assert baseline["allowed_write_roots"] == ["40_verification/probes"]
    assert baseline["path_policy"] == {
        "protected_roots": ["."],
        "allowed_durable_roots": [],
        "allowed_durable_files": [],
        "allowed_ephemeral_roots": ["40_verification/probes"],
        "excluded_roots": ["30_execution/role_boundary", "30_execution/semantic_finalize"],
    }


def test_deep_ephemeral_probe_tree_is_not_regular_file_hashed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run = _write_run(tmp_path)
    probes = run / "40_verification" / "probes"
    deep = probes
    for index in range(18):
        deep = deep / f"d{index % 10}"
    deep.mkdir(parents=True)
    (deep / "before.bin").write_bytes(b"before")

    hashed: list[Path] = []
    real_sha256_file = boundary.sha256_file

    def recording_hash(path: Path) -> str:
        hashed.append(path)
        return real_sha256_file(path)

    monkeypatch.setattr(boundary, "sha256_file", recording_hash)
    started = _start(tmp_path, run, "deep-ephemeral")
    (deep / "after.bin").write_bytes(b"after")
    finished = _finish(tmp_path, run, "deep-ephemeral", started)

    assert finished.ok, finished.as_dict()
    assert finished.data["status"] == "PASS"
    assert not any(probes == item or probes in item.parents for item in hashed)
    baseline = json.loads((tmp_path / started["baseline_path"]).read_text(encoding="utf-8"))
    assert "40_verification/probes" in baseline["snapshot"]
    assert not any(path.endswith("before.bin") for path in baseline["snapshot"])


@pytest.mark.skipif(os.name != "nt", reason="Windows extended-path behavior")
def test_windows_long_ephemeral_tree_finishes_without_path_overflow(tmp_path: Path) -> None:
    run = _write_run(tmp_path)
    probes = run / "40_verification" / "probes"
    probes.mkdir()
    deep = probes
    try:
        while len(str(deep)) <= 285:
            deep = deep / "deep"
            os.mkdir(boundary._filesystem_path(deep))
        payload = deep / "payload.bin"
        with open(boundary._filesystem_path(payload), "wb") as stream:
            stream.write(b"ephemeral")

        started = _start(tmp_path, run, "windows-long-ephemeral")
        finished = _finish(tmp_path, run, "windows-long-ephemeral", started)

        assert finished.ok, finished.as_dict()
        assert finished.data["status"] == "PASS"
    finally:
        if probes.exists():
            shutil.rmtree(boundary._filesystem_path(probes))


@pytest.mark.parametrize(
    "error_type",
    [FileNotFoundError, PermissionError],
    ids=["disappeared", "unreadable"],
)
def test_ephemeral_descendant_scan_error_is_expected_churn(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    error_type: type[OSError],
) -> None:
    run = _write_run(tmp_path)
    volatile = run / "40_verification" / "probes" / "volatile"
    volatile.mkdir(parents=True)
    (volatile / "stale.txt").write_text("stale\n", encoding="utf-8")
    started = _start(tmp_path, run, "ephemeral-churn")
    real_scandir = boundary.os.scandir
    monkeypatch.setattr(boundary, "_filesystem_path", lambda path: str(path))

    def disappearing_scandir(path: str | os.PathLike[str]):
        if Path(path) == volatile:
            raise error_type("deterministic concurrent cleanup")
        return real_scandir(path)

    monkeypatch.setattr(boundary.os, "scandir", disappearing_scandir)
    finished = _finish(tmp_path, run, "ephemeral-churn", started)

    assert finished.ok, finished.as_dict()
    assert finished.data["status"] == "PASS"


def test_protected_unreadability_remains_a_boundary_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run = _write_run(tmp_path)
    protected_directory = run / "10_framing"
    started = _start(tmp_path, run, "protected-unreadable")
    real_scandir = boundary.os.scandir
    monkeypatch.setattr(boundary, "_filesystem_path", lambda path: str(path))

    def unreadable_scandir(path: str | os.PathLike[str]):
        if Path(path) == protected_directory:
            raise PermissionError("deterministic protected unreadability")
        return real_scandir(path)

    monkeypatch.setattr(boundary.os, "scandir", unreadable_scandir)
    finished = _finish(tmp_path, run, "protected-unreadable", started)

    assert not finished.ok
    assert {item.code for item in finished.diagnostics} == {"BOUNDARY_FINISH"}


def test_protected_overwrite_remains_a_violation(tmp_path: Path) -> None:
    run = _write_run(tmp_path)
    started = _start(tmp_path, run, "protected-overwrite")
    (run / "10_framing" / "protected.txt").write_text("changed bytes\n", encoding="utf-8")

    finished = _finish(tmp_path, run, "protected-overwrite", started)

    assert not finished.ok
    assert finished.data["status"] == "BOUNDARY_VIOLATION"
    evidence = json.loads((tmp_path / finished.data["evidence_ref"]).read_text(encoding="utf-8"))
    assert any(item["path"] == "10_framing/protected.txt" for item in evidence["unauthorized_mutations"])


def test_ephemeral_symlink_escape_is_rejected_when_supported(tmp_path: Path) -> None:
    run = _write_run(tmp_path)
    probes = run / "40_verification" / "probes"
    probes.mkdir()
    started = _start(tmp_path, run, "ephemeral-escape")
    outside = tmp_path / "outside"
    outside.mkdir()
    try:
        os.symlink(outside, probes / "escape", target_is_directory=True)
    except OSError as exc:
        pytest.skip(f"filesystem does not permit symlink creation: {exc}")

    finished = _finish(tmp_path, run, "ephemeral-escape", started)

    assert not finished.ok
    evidence = json.loads((tmp_path / finished.data["evidence_ref"]).read_text(encoding="utf-8"))
    assert any(item["operation"] == "path_escape" for item in evidence["unauthorized_mutations"])


def test_backslash_boundary_reference_has_the_same_repository_identity(tmp_path: Path) -> None:
    run = _write_run(tmp_path)
    started = _start(tmp_path, run, "backslash-reference")
    finished = _finish(tmp_path, run, "backslash-reference", started)
    assert finished.ok, finished.as_dict()

    valid, message = validate_boundary_pass(
        tmp_path,
        run,
        role="independent_verifier",
        invocation_ref="backslash-reference",
        evidence_ref=str(finished.data["evidence_ref"]).replace("/", "\\"),
    )

    assert valid, message


def test_legacy_baseline_without_explicit_policy_finishes_compatibly(tmp_path: Path) -> None:
    run = _write_run(tmp_path)
    probes = run / "40_verification" / "probes"
    probes.mkdir()
    started = _start(tmp_path, run, "legacy-baseline")
    baseline_path = tmp_path / started["baseline_path"]
    baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
    baseline.pop("path_policy")
    baseline_path.write_text(json.dumps(baseline, indent=2) + "\n", encoding="utf-8")
    started["baseline_sha256"] = sha256_file(baseline_path)
    (probes / "legacy-result.json").write_text('{"status":"PASS"}\n', encoding="utf-8")

    finished = _finish(tmp_path, run, "legacy-baseline", started)

    assert finished.ok, finished.as_dict()
    evidence = json.loads((tmp_path / finished.data["evidence_ref"]).read_text(encoding="utf-8"))
    assert evidence["allowed_write_roots"] == ["40_verification/probes"]
    assert any(item["path"].endswith("legacy-result.json") for item in evidence["allowed_mutations"])


def test_verification_scratch_cleanup_is_marker_bound_and_keeps_neighbors(tmp_path: Path) -> None:
    scratch_root = tmp_path / "s"
    scratch_root.mkdir()
    neighbor = scratch_root / "keep.txt"
    neighbor.write_text("keep\n", encoding="utf-8")
    scratch = allocate_verification_scratch(scratch_root=scratch_root)
    (scratch.path / "nested").mkdir()
    (scratch.path / "nested" / "output.txt").write_text("temporary\n", encoding="utf-8")

    scratch.cleanup()

    assert scratch_root.is_dir()
    assert neighbor.read_text(encoding="utf-8") == "keep\n"
    assert not scratch.path.exists()


def test_verification_scratch_refuses_cleanup_after_marker_tampering(tmp_path: Path) -> None:
    scratch = allocate_verification_scratch(scratch_root=tmp_path / "s")
    marker = scratch.path / ".codex-scratch.json"
    marker.write_text('{"token":"wrong"}\n', encoding="utf-8")

    with pytest.raises(ScratchError, match="does not match"):
        scratch.cleanup()

    assert scratch.path.is_dir()
