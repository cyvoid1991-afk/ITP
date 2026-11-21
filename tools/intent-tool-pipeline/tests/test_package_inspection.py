from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from pipeline_control import packaging
from pipeline_control.cli import main
from pipeline_control.io_utils import sha256_file
from pipeline_control.result import CommandResult
from pipeline_control.state import update_state
from test_pipeline_control import _prepare_package_fixture


def _start_release(project_root: Path, run: Path) -> Path:
    started = update_state(
        run,
        project_root=project_root,
        to_stage="release",
        stage_status="IN_PROGRESS",
        gate_status="IN_PROGRESS",
        evidence_refs=[],
        rationale="Verified candidate entered release packaging.",
        next_action="Package and inspect the candidate.",
    )
    assert started.ok, started.as_dict()
    return run / "30_execution" / "run_state.json"


def test_combined_cli_matches_standalone_commands(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    run, spec = _prepare_package_fixture(tmp_path)
    state = _start_release(tmp_path, run)
    state_before = state.read_bytes()
    manifest = run / "50_release" / "custom_manifest.json"
    spec_data = yaml.safe_load(spec.read_text(encoding="utf-8"))
    spec_data["manifest_path"] = manifest.relative_to(tmp_path).as_posix()
    spec.write_text(yaml.safe_dump(spec_data), encoding="utf-8")
    arguments = ["--project-root", str(tmp_path), "--format", "json"]
    package = ["package", "--run-dir", str(run), "--spec", str(spec)]
    inspect = ["inspect-package", "--run-dir", str(run), "--manifest", str(manifest)]

    assert main(arguments + package) == 0
    standalone = json.loads(capsys.readouterr().out)
    assert standalone["data"]["inspection_status"] == "PENDING"
    assert "completed_steps" not in standalone["data"]
    assert main(arguments + inspect) == 0
    standalone_inspection = json.loads(capsys.readouterr().out)
    manifest_before = manifest.read_bytes()
    evidence = Path(standalone_inspection["data"]["inspection_path"])
    evidence_before = evidence.read_bytes()

    assert main(arguments + package + ["--inspect"]) == 0
    combined = json.loads(capsys.readouterr().out)
    assert combined["command"] == "package"
    assert combined["ok"]
    assert combined["data"] == {
        **standalone["data"],
        "inspection_status": "PASS",
        "completed_steps": ["package", "inspect-package"],
        "failed_step": None,
        "inspection": standalone_inspection,
    }
    assert sha256_file(Path(combined["data"]["archive_path"])) == standalone["data"]["archive_sha256"]
    assert manifest.read_bytes() == manifest_before
    assert evidence.read_bytes() == evidence_before
    assert state.read_bytes() == state_before

    assert main(arguments + inspect) == 0
    assert json.loads(capsys.readouterr().out) == standalone_inspection
    assert evidence.read_bytes() == evidence_before


@pytest.mark.parametrize("failure", ["missing-spec", "archive-output"])
def test_creation_failure_skips_inspection(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch, failure: str
) -> None:
    run, spec = _prepare_package_fixture(tmp_path)
    if failure == "missing-spec":
        spec = tmp_path / "missing.yaml"
        expected_code = "PACKAGE_SPEC_MISSING"
    else:
        (tmp_path / "deliverables").write_text("blocks archive directory", encoding="utf-8")
        expected_code = "PACKAGE_WRITE"

    def unexpected_inspection(*args: object) -> CommandResult:
        pytest.fail("creation failure reached the inspector")

    monkeypatch.setattr(packaging, "inspect_package", unexpected_inspection)
    assert main([
        "--project-root", str(tmp_path), "--format", "json",
        "package", "--run-dir", str(run), "--spec", str(spec), "--inspect",
    ]) == 1
    result = json.loads(capsys.readouterr().out)
    assert not result["ok"]
    assert [diagnostic["code"] for diagnostic in result["diagnostics"]] == [expected_code]
    assert result["data"] == {
        "status": "FAIL", "completed_steps": [], "failed_step": "package", "inspection": None,
    }


def test_inspection_failure_returns_failure_and_creation_details(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    run, spec = _prepare_package_fixture(tmp_path)
    inspect = packaging.inspect_package
    archive = tmp_path / "deliverables" / "fixture_tool.zip"

    def inspect_changed_archive(project_root: Path, run_dir: Path, manifest_path: Path) -> CommandResult:
        with archive.open("ab") as handle:
            handle.write(b"changed after creation")
        return inspect(project_root, run_dir, manifest_path)

    args = [
        "--project-root", str(tmp_path), "--format", "json",
        "package", "--run-dir", str(run), "--spec", str(spec), "--inspect",
    ]
    with monkeypatch.context() as patch:
        patch.setattr(packaging, "inspect_package", inspect_changed_archive)
        assert main(args) == 1
    result = json.loads(capsys.readouterr().out)
    assert not result["ok"]
    assert [diagnostic["code"] for diagnostic in result["diagnostics"]] == ["ARCHIVE_HASH"]
    data = result["data"]
    assert data["status"] == data["inspection_status"] == "FAIL"
    assert data["completed_steps"] == ["package"]
    assert data["failed_step"] == "inspect-package"
    assert data["archive_path"] == str(archive)
    assert archive.is_file() and Path(data["manifest_path"]).is_file()
    inspection = data["inspection"]
    assert not inspection["ok"]
    assert inspection["diagnostics"] == result["diagnostics"]
    evidence = Path(inspection["data"]["inspection_path"])
    assert json.loads(evidence.read_bytes())["status"] == "FAIL"

    assert main(args) == 0
    recovered = json.loads(capsys.readouterr().out)
    assert recovered["data"]["archive_sha256"] == data["archive_sha256"]
    assert json.loads(evidence.read_bytes())["status"] == "PASS"


def test_interrupted_replacement_cannot_reuse_prior_inspection(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    run, spec = _prepare_package_fixture(tmp_path)
    state = _start_release(tmp_path, run)
    state_before = state.read_bytes()
    first = packaging.create_and_inspect_package(tmp_path, run, spec)
    assert first.ok, first.as_dict()
    evidence = Path(first.data["inspection"]["data"]["inspection_path"])
    first_evidence = evidence.read_bytes()
    (tmp_path / "source" / "tool.py").write_text("print('replacement')\n", encoding="utf-8")

    def interrupt_at_inspection(*args: object) -> CommandResult:
        raise KeyboardInterrupt

    with monkeypatch.context() as patch:
        patch.setattr(packaging, "inspect_package", interrupt_at_inspection)
        with pytest.raises(KeyboardInterrupt):
            packaging.create_and_inspect_package(tmp_path, run, spec)

    archive = Path(first.data["archive_path"])
    replacement_hash = sha256_file(archive)
    assert replacement_hash != first.data["archive_sha256"]
    pending_evidence = evidence.read_bytes()
    assert json.loads(pending_evidence)["status"] == "PENDING"
    for saved_evidence in (pending_evidence, first_evidence):
        evidence.write_bytes(saved_evidence)
        denied = update_state(
            run,
            project_root=tmp_path,
            to_stage="release",
            stage_status="PASSED",
            gate_status="PASSED",
            evidence_refs=["test-results", "package-inspection"],
            rationale="Try to complete release with the saved inspection.",
            next_action="Await the user's phase decision.",
        )
        assert not denied.ok
        assert "PACKAGE_NOT_INSPECTED" in {item.code for item in denied.diagnostics}
        assert state.read_bytes() == state_before

    evidence.write_bytes(pending_evidence)
    recovered = packaging.inspect_package(tmp_path, run, Path(first.data["manifest_path"]))
    assert recovered.ok, recovered.as_dict()
    assert json.loads(evidence.read_bytes())["archive_sha256"] == replacement_hash
    assert state.read_bytes() == state_before
