from __future__ import annotations

import json
import os
import stat
import sys
import zipfile
from pathlib import Path

import pytest
import yaml

from pipeline_control.io_utils import sha256_file
from pipeline_control.cli import build_parser, main
from pipeline_control.packaging import create_package, inspect_package
from pipeline_control.scratch import ScratchError
from pipeline_control.state import update_state
from pipeline_control.test_runner import run_test_plan
from pipeline_control.validation import validate_run_directory
from pipeline_control.verifier_harness import prepare_verification
from test_pipeline_control import (
    TIMESTAMP,
    _contract,
    _enable_boundary_control,
    _persist_fixture_artifact,
    _prepare_package_fixture,
    _problem_frame,
    _verification_report,
    _write_package_fixture_assets,
    _write_run,
    _write_test_plan,
)


def _commands() -> list[dict]:
    probe = (
        "import os,pathlib,tempfile; "
        "f=tempfile.NamedTemporaryFile(); f.close(); "
        "p=pathlib.Path(os.environ['CODEX_VERIFICATION_OUTPUT_ROOT'])/'probe.txt'; "
        "p.write_text(os.environ['TEMP'], encoding='utf-8'); print('suite')"
    )
    commands = [
        {"id": "suite-1", "scenario": "complete_suite", "argv": [sys.executable, "-c", probe], "outputs": ["probe.txt"]},
        {"id": "suite-2", "scenario": "complete_suite", "argv": [sys.executable, "-c", "print('suite-2')"], "outputs": []},
    ]
    for scenario in ("help", "import", "cli", "packaging_layout", "legacy_or_open_result"):
        commands.append({"id": scenario.replace("_", "-"), "scenario": scenario, "argv": [sys.executable, "-c", "print('ok')"], "outputs": []})
    return commands


def _write_plan(root: Path, run: Path, *, commands: list[dict] | None = None, minimums: dict | None = None) -> Path:
    manifest = run / "50_release" / "release_manifest.json"
    inspection = run / "50_release" / "package_inspection.json"
    archive = root / "deliverables" / "fixture_tool.zip"
    contract = run / "20_contract" / "product_contract.yaml"
    plan = {
        "schema_version": "1.0",
        "binding": {
            "contract_ref": "product-contract@1",
            "contract_path": contract.relative_to(root).as_posix(),
            "contract_sha256": sha256_file(contract),
            "manifest_path": manifest.relative_to(root).as_posix(),
            "manifest_sha256": sha256_file(manifest),
            "inspection_path": inspection.relative_to(root).as_posix(),
            "inspection_sha256": sha256_file(inspection),
            "archive_path": archive.relative_to(root).as_posix(),
            "archive_sha256": sha256_file(archive),
        },
        "scenario_minimums": minimums or {
            "complete_suite": 2,
            "help": 1,
            "import": 1,
            "cli": 1,
            "packaging_layout": 1,
            "legacy_or_open_result": 1,
        },
        "commands": commands or _commands(),
    }
    path = root / "verifier_plan.yaml"
    path.write_text(yaml.safe_dump(plan, sort_keys=False), encoding="utf-8")
    return path


def _fixture(root: Path) -> tuple[Path, Path]:
    run, spec = _prepare_package_fixture(root)
    assert create_package(root, run, spec).ok
    assert inspect_package(root, run, run / "50_release" / "release_manifest.json").ok
    return run, _write_plan(root, run)


def _pre_verifier_fixture(root: Path) -> tuple[Path, Path]:
    run, spec = _prepare_package_fixture(
        root,
        current_stage="implementation",
        current_status="PASSED",
        include_verification_report=False,
    )
    state = json.loads((run / "30_execution" / "run_state.json").read_text(encoding="utf-8"))
    assert state["active_artifacts"]["verification_report"] is None
    assert not (run / "40_verification" / "verification_report.md").exists()
    assert create_package(root, run, spec).ok
    assert inspect_package(root, run, run / "50_release" / "release_manifest.json").ok
    return run, _write_plan(root, run)


def _rebind_candidate_sha(root: Path, run: Path, plan: Path) -> None:
    archive = root / "deliverables" / "fixture_tool.zip"
    archive_sha = sha256_file(archive)
    manifest_path = run / "50_release" / "release_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["archive_sha256"] = archive_sha
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    inspection_path = run / "50_release" / "package_inspection.json"
    inspection = json.loads(inspection_path.read_text(encoding="utf-8"))
    inspection["archive_sha256"] = archive_sha
    inspection_path.write_text(json.dumps(inspection, indent=2) + "\n", encoding="utf-8")
    data = yaml.safe_load(plan.read_text(encoding="utf-8"))
    data["binding"]["archive_sha256"] = archive_sha
    data["binding"]["manifest_sha256"] = sha256_file(manifest_path)
    data["binding"]["inspection_sha256"] = sha256_file(inspection_path)
    plan.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")


def test_happy_path_extracts_once_isolates_commands_hashes_outputs_and_cleans(tmp_path: Path) -> None:
    run, plan = _fixture(tmp_path)
    scratch_root = tmp_path / "s"
    result = prepare_verification(tmp_path, run, plan, scratch_root=scratch_root, attempt_id="happy", timestamp=TIMESTAMP)
    assert result.ok, result.as_dict()
    assert result.data["extraction_count"] == 1
    assert result.data["cleanup_status"] == "PASS"
    assert list(scratch_root.iterdir()) == []
    summary = json.loads(Path(result.data["summary_path"]).read_text(encoding="utf-8"))
    assert summary["extraction_count"] == 1
    assert summary["command_count"] == 7
    assert summary["independent_verifier_judgment"] == "NOT_PERFORMED"
    assert all(item["status"] == "PASS" for item in summary["commands"])
    first, second = summary["commands"][:2]
    assert first["isolated_temp_index"] != second["isolated_temp_index"]
    output = first["outputs"][0]
    promoted = Path(result.data["attempt_path"]) / output["evidence_path"]
    assert sha256_file(promoted) == output["sha256"]
    assert sha256_file(Path(result.data["attempt_path"]) / first["stdout"]["path"]) == first["stdout"]["sha256"]


def test_pre_verifier_harness_accepts_null_current_report(tmp_path: Path) -> None:
    run, plan = _pre_verifier_fixture(tmp_path)

    result = prepare_verification(
        tmp_path,
        run,
        plan,
        scratch_root=tmp_path / "s",
        attempt_id="pre-verifier-null-report",
        timestamp=TIMESTAMP,
    )

    assert result.ok, result.as_dict()
    assert result.data["status"] == "PASS"
    assert result.data["extraction_count"] == 1
    assert result.data["cleanup_status"] == "PASS"
    summary = json.loads(Path(result.data["summary_path"]).read_text(encoding="utf-8"))
    assert summary["independent_verifier_judgment"] == "NOT_PERFORMED"


def test_pre_verifier_harness_rejects_malformed_nonnull_report_entry(tmp_path: Path) -> None:
    run, plan = _pre_verifier_fixture(tmp_path)
    state_path = run / "30_execution" / "run_state.json"
    state = json.loads(state_path.read_text(encoding="utf-8"))
    state["active_artifacts"]["verification_report"] = {
        "artifact_id": "verification-report",
        "version": 1,
    }
    state_path.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")

    result = prepare_verification(
        tmp_path,
        run,
        plan,
        scratch_root=tmp_path / "s",
        attempt_id="malformed-report-entry",
        timestamp=TIMESTAMP,
    )

    assert not result.ok
    assert result.data["extraction_count"] == 0
    assert any(
        item.code == "HARNESS_GUARD" and item.path == "active_artifacts.verification_report"
        for item in result.diagnostics
    )


def test_public_fresh_sequence_prepares_before_report_then_passes_verification(tmp_path: Path) -> None:
    run = _write_run(tmp_path, current_stage="intake", current_status="PASSED")
    _enable_boundary_control(run)
    for relative in (
        "10_framing/problem_frame.md",
        "20_contract/product_contract.yaml",
        "40_verification/verification_report.md",
    ):
        (run / relative).unlink()

    def transition(
        stage: str,
        status: str,
        *,
        evidence: list[str] | None = None,
    ) -> None:
        result = update_state(
            run,
            project_root=tmp_path,
            to_stage=stage,
            stage_status=status,
            gate_status=status,
            evidence_refs=evidence or [],
            rationale=f"Exercise the public {stage} lifecycle.",
            next_action=f"Continue after {stage} {status}.",
            timestamp=TIMESTAMP,
        )
        assert result.ok, result.as_dict()

    transition("framing", "IN_PROGRESS")
    frame = _persist_fixture_artifact(
        tmp_path,
        run,
        artifact_key="problem_frame",
        role="problem_framer",
        invocation_ref="fresh-sequence-framer",
        body=_problem_frame(),
        suffix=".md",
    )
    assert frame.ok, frame.as_dict()
    transition("framing", "PASSED", evidence=["problem-frame@1"])

    transition("contract", "IN_PROGRESS")
    contract = _persist_fixture_artifact(
        tmp_path,
        run,
        artifact_key="product_contract",
        role="product_contract_agent",
        invocation_ref="fresh-sequence-contract",
        body=yaml.safe_dump(_contract(), sort_keys=False),
        suffix=".yaml",
    )
    assert contract.ok, contract.as_dict()
    transition("contract", "PASSED", evidence=["product-contract@1"])
    transition("repository_analysis", "IN_PROGRESS")
    transition("repository_analysis", "PASSED", evidence=["repository-analysis"])
    transition("implementation", "IN_PROGRESS")

    spec = _write_package_fixture_assets(tmp_path)
    tests = run_test_plan(
        tmp_path,
        run,
        _write_test_plan(tmp_path, 0),
        attempt_id="fresh-sequence-tests",
        timestamp=TIMESTAMP,
    )
    assert tests.ok, tests.as_dict()
    transition("implementation", "PASSED", evidence=["30_execution/test_results.json"])
    assert create_package(tmp_path, run, spec).ok
    assert inspect_package(tmp_path, run, run / "50_release" / "release_manifest.json").ok

    plan = _write_plan(tmp_path, run)
    harness = prepare_verification(
        tmp_path,
        run,
        plan,
        scratch_root=tmp_path / "s",
        attempt_id="fresh-sequence-harness",
        timestamp=TIMESTAMP,
    )
    assert harness.ok, harness.as_dict()
    assert harness.data["extraction_count"] == 1

    transition("verification", "IN_PROGRESS")
    state = json.loads((run / "30_execution" / "run_state.json").read_text(encoding="utf-8"))
    assert state["active_artifacts"]["verification_report"] is None

    report = _persist_fixture_artifact(
        tmp_path,
        run,
        artifact_key="verification_report",
        role="independent_verifier",
        invocation_ref="fresh-sequence-verifier",
        body=_verification_report(),
        suffix=".md",
    )
    assert report.ok, report.as_dict()
    transition("verification", "PASSED", evidence=["verification-report@1"])
    assert validate_run_directory(tmp_path, run).ok


def test_expected_nonzero_exit_is_a_pass(tmp_path: Path) -> None:
    run, _ = _fixture(tmp_path)
    commands = _commands()
    commands[0]["argv"] = [sys.executable, "-c", "import sys; sys.exit(7)"]
    commands[0]["expected_exit_codes"] = [7]
    commands[0]["outputs"] = []
    plan = _write_plan(tmp_path, run, commands=commands)
    result = prepare_verification(tmp_path, run, plan, scratch_root=tmp_path / "s", attempt_id="expected-7")
    assert result.ok, result.as_dict()


def test_unexpected_nonzero_exit_is_retained_and_other_scenarios_still_run(tmp_path: Path) -> None:
    run, _ = _fixture(tmp_path)
    commands = _commands()
    commands[0]["argv"] = [sys.executable, "-c", "import sys; sys.exit(7)"]
    commands[0]["outputs"] = []
    plan = _write_plan(tmp_path, run, commands=commands)
    result = prepare_verification(tmp_path, run, plan, scratch_root=tmp_path / "s", attempt_id="unexpected-7")
    assert not result.ok
    assert "HARNESS_COMMAND_FAILED" in {item.code for item in result.diagnostics}
    summary = json.loads(Path(result.data["summary_path"]).read_text())
    assert summary["command_count"] == len(commands)
    assert summary["commands"][0]["status"] == "FAIL"
    assert all(item["status"] == "PASS" for item in summary["commands"][1:])


def test_scenario_minimum_failure_occurs_before_attempt(tmp_path: Path) -> None:
    run, _ = _fixture(tmp_path)
    commands = _commands()[1:]
    plan = _write_plan(tmp_path, run, commands=commands)
    result = prepare_verification(tmp_path, run, plan, scratch_root=tmp_path / "s", attempt_id="too-few")
    assert not result.ok
    assert "SCENARIO_MINIMUM" in {item.code for item in result.diagnostics}
    assert not (run / "40_verification" / "harness").exists()


def test_output_escape_is_rejected_during_plan_validation(tmp_path: Path) -> None:
    run, _ = _fixture(tmp_path)
    commands = _commands()
    commands[0]["outputs"] = ["../escape.txt"]
    plan = _write_plan(tmp_path, run, commands=commands)
    result = prepare_verification(tmp_path, run, plan, scratch_root=tmp_path / "s", attempt_id="output-escape")
    assert not result.ok
    assert "HARNESS_PATH" in {item.code for item in result.diagnostics}
    assert not (run / "40_verification" / "harness").exists()


@pytest.mark.parametrize(
    ("target", "code"),
    [
        ("contract", "CONTRACT_DRIFT"),
        ("manifest", "MANIFEST_DRIFT"),
        ("inspection", "INSPECTION_DRIFT"),
        ("archive", "ARCHIVE_DRIFT"),
    ],
)
def test_bound_input_drift_fails_before_extraction(tmp_path: Path, target: str, code: str) -> None:
    run, plan = _fixture(tmp_path)
    paths = {
        "contract": run / "20_contract" / "product_contract.yaml",
        "manifest": run / "50_release" / "release_manifest.json",
        "inspection": run / "50_release" / "package_inspection.json",
        "archive": tmp_path / "deliverables" / "fixture_tool.zip",
    }
    with paths[target].open("ab") as stream:
        stream.write(b"\n")
    result = prepare_verification(tmp_path, run, plan, scratch_root=tmp_path / "s", attempt_id=f"drift-{target}")
    assert not result.ok
    assert code in {item.code for item in result.diagnostics}
    summary = json.loads((run / "40_verification" / "harness" / "attempts" / f"drift-{target}" / "summary.json").read_text())
    assert summary["extraction_count"] == 0


def test_source_mismatch_fails_before_extraction(tmp_path: Path) -> None:
    run, plan = _fixture(tmp_path)
    (tmp_path / "source" / "tool.py").write_text("print('changed')\n", encoding="utf-8")
    result = prepare_verification(tmp_path, run, plan, scratch_root=tmp_path / "s", attempt_id="source-drift")
    assert not result.ok
    assert "SOURCE_MISMATCH" in {item.code for item in result.diagnostics}
    assert result.data["extraction_count"] == 0


@pytest.mark.parametrize(
    "name",
    [
        "/absolute.txt",
        "fixture_tool/../escape.txt",
        "fixture_tool\\backslash.txt",
        "C:/drive.txt",
        "//server/share.txt",
        "fixture_tool//empty.txt",
        "fixture_tool/con.txt",
        "fixture_tool/trailing. ",
        "fixture_tool/file:stream",
    ],
)
def test_unsafe_zip_paths_fail_before_extraction(tmp_path: Path, name: str) -> None:
    run, plan = _fixture(tmp_path)
    archive = tmp_path / "deliverables" / "fixture_tool.zip"
    with zipfile.ZipFile(archive, "a") as handle:
        handle.writestr(name.replace("\\", "/"), b"unsafe")
    if "\\" in name:
        archive.write_bytes(archive.read_bytes().replace(name.replace("\\", "/").encode(), name.encode()))
    _rebind_candidate_sha(tmp_path, run, plan)
    result = prepare_verification(tmp_path, run, plan, scratch_root=tmp_path / "s", attempt_id="unsafe")
    assert not result.ok
    assert "ARCHIVE_UNSAFE_PATH" in {item.code for item in result.diagnostics}
    assert result.data["extraction_count"] == 0


@pytest.mark.parametrize(
    ("mutation", "expected_code"),
    [
        ("extra", "MANIFEST_INVENTORY"),
        ("missing", "MANIFEST_INVENTORY"),
        ("hash", "ENTRY_HASH"),
        ("prohibited", "PROHIBITED_ENTRY"),
        ("duplicate", "ARCHIVE_DUPLICATE"),
        ("case", "ARCHIVE_CASE_COLLISION"),
        ("ancestor", "ARCHIVE_ANCESTOR_COLLISION"),
        ("directory", "ARCHIVE_UNSAFE_PATH"),
        ("symlink", "ARCHIVE_SPECIAL_ENTRY"),
    ],
)
def test_archive_reconciliation_rejects_inventory_hash_policy_and_collisions(
    tmp_path: Path,
    mutation: str,
    expected_code: str,
) -> None:
    run, plan = _fixture(tmp_path)
    archive_path = tmp_path / "deliverables" / "fixture_tool.zip"
    if mutation in {"missing", "hash"}:
        replacement = tmp_path / "replacement.zip"
        with zipfile.ZipFile(archive_path, "r") as source, zipfile.ZipFile(replacement, "w") as target:
            for info in source.infolist():
                if mutation == "missing" and info.filename == "fixture_tool/tool.py":
                    continue
                payload = source.read(info)
                if mutation == "hash" and info.filename == "fixture_tool/tool.py":
                    payload = b"different bytes"
                target.writestr(info, payload)
        archive_path.write_bytes(replacement.read_bytes())
    else:
        with zipfile.ZipFile(archive_path, "a") as archive:
            if mutation == "extra":
                archive.writestr("fixture_tool/extra.txt", b"extra")
            elif mutation == "prohibited":
                archive.writestr("fixture_tool/__pycache__/bad.pyc", b"cache")
            elif mutation == "duplicate":
                archive.writestr("fixture_tool/tool.py", b"duplicate")
            elif mutation == "case":
                archive.writestr("fixture_tool/TOOL.py", b"case")
            elif mutation == "ancestor":
                archive.writestr("fixture_tool/node", b"file")
                archive.writestr("fixture_tool/node/child", b"child")
            elif mutation == "directory":
                archive.writestr("fixture_tool/explicit/", b"")
            elif mutation == "symlink":
                info = zipfile.ZipInfo("fixture_tool/link")
                info.create_system = 3
                info.external_attr = (stat.S_IFLNK | 0o777) << 16
                archive.writestr(info, b"tool.py")
    _rebind_candidate_sha(tmp_path, run, plan)
    result = prepare_verification(tmp_path, run, plan, scratch_root=tmp_path / "s", attempt_id=f"archive-{mutation}")
    assert not result.ok
    assert expected_code in {item.code for item in result.diagnostics}
    assert result.data["extraction_count"] == 0


def test_package_mutation_stops_reuse_of_changed_tree(tmp_path: Path) -> None:
    run, _ = _fixture(tmp_path)
    commands = _commands()
    commands[0]["argv"] = [sys.executable, "-c", "from pathlib import Path; Path('tool.py').write_text('mutated')"]
    commands[0]["outputs"] = []
    plan = _write_plan(tmp_path, run, commands=commands)
    result = prepare_verification(tmp_path, run, plan, scratch_root=tmp_path / "s", attempt_id="mutation")
    assert not result.ok
    assert "PACKAGE_MUTATION" in {item.code for item in result.diagnostics}
    summary = json.loads(Path(result.data["summary_path"]).read_text())
    assert summary["command_count"] == 1


def test_absolute_repository_dependency_is_rejected_before_any_command_runs(tmp_path: Path) -> None:
    run, _ = _fixture(tmp_path)
    commands = _commands()
    sentinel = tmp_path / "command-ran.txt"
    source = tmp_path / "source" / "tool.py"
    commands[0]["argv"] = [
        sys.executable,
        "-c",
        f"from pathlib import Path; Path({str(source)!r}).read_text(); Path({str(sentinel)!r}).write_text('ran')",
    ]
    commands[0]["outputs"] = []
    plan = _write_plan(tmp_path, run, commands=commands)

    result = prepare_verification(tmp_path, run, plan, scratch_root=tmp_path / "s", attempt_id="undeclared-absolute")

    assert not result.ok
    assert "UNDECLARED_DEPENDENCY" in {item.code for item in result.diagnostics}
    assert not sentinel.exists()
    summary = json.loads(Path(result.data["summary_path"]).read_text(encoding="utf-8"))
    assert summary["extraction_count"] == 1
    assert summary["command_count"] == 0


@pytest.mark.parametrize(
    "spelling",
    [
        "native",
        "forward-slash",
        pytest.param("case-variant", marks=pytest.mark.skipif(os.name != "nt", reason="case variants identify the same path only on Windows")),
    ],
)
def test_packaged_python_entrypoint_hardcoded_repository_read_is_rejected(
    tmp_path: Path,
    spelling: str,
) -> None:
    run, spec = _prepare_package_fixture(tmp_path)
    external = tmp_path / "undeclared-secret.txt"
    external.write_text("external dependency reached", encoding="utf-8")
    rendered = str(external)
    if spelling == "forward-slash":
        rendered = external.as_posix()
    elif spelling == "case-variant":
        rendered = rendered.swapcase()
    (tmp_path / "source" / "tool.py").write_text(
        "from pathlib import Path\n"
        f"print(Path({rendered!r}).read_text(encoding='utf-8'))\n",
        encoding="utf-8",
    )
    assert create_package(tmp_path, run, spec).ok
    assert inspect_package(tmp_path, run, run / "50_release" / "release_manifest.json").ok
    commands = _commands()
    commands[0]["argv"] = [sys.executable, "tool.py"]
    commands[0]["outputs"] = []
    plan = _write_plan(tmp_path, run, commands=commands)

    result = prepare_verification(
        tmp_path,
        run,
        plan,
        scratch_root=tmp_path / "s",
        attempt_id="entrypoint-" + spelling,
    )

    assert not result.ok
    assert "UNDECLARED_DEPENDENCY" in {item.code for item in result.diagnostics}
    summary = json.loads(Path(result.data["summary_path"]).read_text(encoding="utf-8"))
    assert summary["command_count"] == 0
    assert summary["independent_verifier_judgment"] == "NOT_PERFORMED"


def test_packaged_python_environment_derived_repository_read_is_audit_blocked(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run, spec = _prepare_package_fixture(tmp_path)
    external = tmp_path / "undeclared-secret.txt"
    external.write_text("external dependency reached", encoding="utf-8")
    monkeypatch.setenv("CODEX_PROBE_EXTERNAL_PATH", str(external))
    (tmp_path / "source" / "tool.py").write_text(
        "import os\n"
        "from pathlib import Path\n"
        "print(Path(os.environ['CODEX_PROBE_EXTERNAL_PATH']).read_text(encoding='utf-8'))\n",
        encoding="utf-8",
    )
    assert create_package(tmp_path, run, spec).ok
    assert inspect_package(tmp_path, run, run / "50_release" / "release_manifest.json").ok
    commands = _commands()
    commands[0]["argv"] = [sys.executable, "tool.py"]
    commands[0]["outputs"] = []
    plan = _write_plan(tmp_path, run, commands=commands)

    result = prepare_verification(tmp_path, run, plan, scratch_root=tmp_path / "s", attempt_id="environment-read")

    assert not result.ok
    assert "HARNESS_COMMAND_FAILED" in {item.code for item in result.diagnostics}
    summary = json.loads(Path(result.data["summary_path"]).read_text(encoding="utf-8"))
    assert summary["command_count"] == len(commands)
    assert summary["commands"][0]["status"] == "FAIL"
    assert summary["commands"][0]["python_audit_status"] == "PASS"
    assert "CODEX_PROBE_EXTERNAL_PATH" in summary["commands"][0]["scrubbed_environment_keys"]
    stdout_path = Path(result.data["attempt_path"]) / summary["commands"][0]["stdout"]["path"]
    assert "external dependency reached" not in stdout_path.read_text(encoding="utf-8")


def test_packaged_python_runtime_constructed_repository_read_is_audit_blocked(tmp_path: Path) -> None:
    import base64

    run, spec = _prepare_package_fixture(tmp_path)
    external = tmp_path / "undeclared-secret.txt"
    external.write_text("external dependency reached", encoding="utf-8")
    encoded = base64.b64encode(str(external).encode("utf-8")).decode("ascii")
    (tmp_path / "source" / "tool.py").write_text(
        "import base64\n"
        "from pathlib import Path\n"
        f"path = base64.b64decode({encoded!r}).decode('utf-8')\n"
        "print(Path(path).read_text(encoding='utf-8'))\n",
        encoding="utf-8",
    )
    assert create_package(tmp_path, run, spec).ok
    assert inspect_package(tmp_path, run, run / "50_release" / "release_manifest.json").ok
    commands = _commands()
    commands[0]["argv"] = [sys.executable, "tool.py"]
    commands[0]["outputs"] = []
    plan = _write_plan(tmp_path, run, commands=commands)

    result = prepare_verification(tmp_path, run, plan, scratch_root=tmp_path / "s", attempt_id="runtime-read")

    assert not result.ok
    assert "UNDECLARED_DEPENDENCY" in {item.code for item in result.diagnostics}
    summary = json.loads(Path(result.data["summary_path"]).read_text(encoding="utf-8"))
    assert summary["command_count"] == 1
    assert summary["commands"][0]["python_audit_status"] == "FAIL"


def test_python_package_local_and_stdlib_reads_remain_allowed(tmp_path: Path) -> None:
    run, spec = _prepare_package_fixture(tmp_path)
    (tmp_path / "source" / "tool.py").write_text(
        "import json\n"
        "from pathlib import Path\n"
        "print(Path('README.md').read_text(encoding='utf-8'))\n"
        "print(Path(json.__file__).read_text(encoding='utf-8')[:1])\n",
        encoding="utf-8",
    )
    assert create_package(tmp_path, run, spec).ok
    assert inspect_package(tmp_path, run, run / "50_release" / "release_manifest.json").ok
    commands = _commands()
    commands[0]["argv"] = [sys.executable, "tool.py"]
    commands[0]["outputs"] = []
    plan = _write_plan(tmp_path, run, commands=commands)

    result = prepare_verification(tmp_path, run, plan, scratch_root=tmp_path / "s", attempt_id="allowed-python-reads")

    assert result.ok, result.as_dict()
    summary = json.loads(Path(result.data["summary_path"]).read_text(encoding="utf-8"))
    assert summary["commands"][0]["python_audit_status"] == "PASS"


def test_documentation_and_dormant_tests_may_discuss_external_paths(tmp_path: Path) -> None:
    run, spec = _prepare_package_fixture(tmp_path)
    external = tmp_path / "undeclared-secret.txt"
    (tmp_path / "source" / "README.md").write_text(
        f"Example only: {external}\nRelative notation: ../outside\n",
        encoding="utf-8",
    )
    (tmp_path / "source" / "tests" / "test_tool.py").write_text(
        f"EXAMPLE_ONLY = {str(external)!r}\ndef test_ok(): assert '../outside'\n",
        encoding="utf-8",
    )
    assert create_package(tmp_path, run, spec).ok
    assert inspect_package(tmp_path, run, run / "50_release" / "release_manifest.json").ok
    commands = _commands()
    commands[0]["argv"] = [sys.executable, "tool.py"]
    commands[0]["outputs"] = []
    plan = _write_plan(tmp_path, run, commands=commands)

    result = prepare_verification(tmp_path, run, plan, scratch_root=tmp_path / "s", attempt_id="discussion-only")

    assert result.ok, result.as_dict()


def test_python_isolation_flag_cannot_disable_audit_guard(tmp_path: Path) -> None:
    run, _ = _fixture(tmp_path)
    commands = _commands()
    commands[0]["argv"] = [sys.executable, "-S", "-c", "print('unguarded')"]
    commands[0]["outputs"] = []
    plan = _write_plan(tmp_path, run, commands=commands)

    result = prepare_verification(tmp_path, run, plan, scratch_root=tmp_path / "s", attempt_id="python-no-site")

    assert not result.ok
    assert "UNDECLARED_DEPENDENCY" in {item.code for item in result.diagnostics}
    summary = json.loads(Path(result.data["summary_path"]).read_text(encoding="utf-8"))
    assert summary["command_count"] == 0


def test_missing_python_audit_handshake_is_fail_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from pipeline_control import verifier_harness

    run, plan = _fixture(tmp_path)
    original = verifier_harness._write_python_audit_guard

    def omit_sitecustomize(*args, **kwargs):
        guard = original(*args, **kwargs)
        (guard["root"] / "sitecustomize.py").unlink()
        return guard

    monkeypatch.setattr(verifier_harness, "_write_python_audit_guard", omit_sitecustomize)
    result = prepare_verification(tmp_path, run, plan, scratch_root=tmp_path / "s", attempt_id="missing-handshake")

    assert not result.ok
    assert "PYTHON_AUDIT_INACTIVE" in {item.code for item in result.diagnostics}
    summary = json.loads(Path(result.data["summary_path"]).read_text(encoding="utf-8"))
    assert summary["command_count"] == 1
    assert summary["commands"][0]["python_audit_status"] == "FAIL"


@pytest.mark.parametrize("argument", ["../outside.py", "--input=../outside.txt", "nested/../../outside.txt"])
def test_relative_repository_escape_is_rejected_before_execution(tmp_path: Path, argument: str) -> None:
    run, _ = _fixture(tmp_path)
    commands = _commands()
    commands[0]["argv"] = [sys.executable, argument]
    commands[0]["outputs"] = []
    plan = _write_plan(tmp_path, run, commands=commands)

    result = prepare_verification(tmp_path, run, plan, scratch_root=tmp_path / "s", attempt_id="undeclared-relative")

    assert not result.ok
    assert "UNDECLARED_DEPENDENCY" in {item.code for item in result.diagnostics}
    summary = json.loads(Path(result.data["summary_path"]).read_text(encoding="utf-8"))
    assert summary["command_count"] == 0


def test_relative_dependency_that_stays_inside_package_is_allowed(tmp_path: Path) -> None:
    run, _ = _fixture(tmp_path)
    commands = _commands()
    commands[0]["argv"] = [sys.executable, "../tool.py"]
    commands[0]["cwd"] = "tests"
    commands[0]["outputs"] = []
    plan = _write_plan(tmp_path, run, commands=commands)

    result = prepare_verification(tmp_path, run, plan, scratch_root=tmp_path / "s", attempt_id="declared-relative")

    assert result.ok, result.as_dict()


def test_canonical_source_mutation_fails_and_stops_remaining_commands(tmp_path: Path) -> None:
    run, _ = _fixture(tmp_path)
    commands = _commands()
    commands[0]["argv"] = [
        sys.executable,
        "-c",
        "from pathlib import Path; p=Path.cwd().parents[3]/'source'/'tool.py'; p.write_text('mutated source')",
    ]
    commands[0]["outputs"] = []
    plan = _write_plan(tmp_path, run, commands=commands)

    result = prepare_verification(tmp_path, run, plan, scratch_root=tmp_path / "s", attempt_id="source-guard")

    assert not result.ok
    assert "CANONICAL_SOURCE_MUTATION" in {item.code for item in result.diagnostics}
    summary = json.loads(Path(result.data["summary_path"]).read_text(encoding="utf-8"))
    assert summary["command_count"] == 1
    assert summary["commands"][0]["status"] == "FAIL"
    assert summary["commands"][0]["canonical_guard_status"] == "FAIL"


@pytest.mark.parametrize(
    "relative_target",
    [
        "run/30_execution/run_state.json",
        "run/40_verification/verification_report.md",
        "run/50_release/release_manifest.json",
        "deliverables/fixture_tool.zip",
    ],
)
def test_protected_candidate_mutation_fails_and_stops_remaining_commands(
    tmp_path: Path,
    relative_target: str,
) -> None:
    run, _ = _fixture(tmp_path)
    commands = _commands()
    parts = relative_target.split("/")
    commands[0]["argv"] = [
        sys.executable,
        "-c",
        f"from pathlib import Path; p=Path.cwd().parents[3].joinpath(*{parts!r}); p.write_bytes(b'x')",
    ]
    commands[0]["outputs"] = []
    plan = _write_plan(tmp_path, run, commands=commands)

    result = prepare_verification(
        tmp_path,
        run,
        plan,
        scratch_root=tmp_path / "s",
        attempt_id="protected-" + Path(relative_target).name.replace(".", "-"),
    )

    assert not result.ok
    assert "PROTECTED_INPUT_MUTATION" in {item.code for item in result.diagnostics}
    summary = json.loads(Path(result.data["summary_path"]).read_text(encoding="utf-8"))
    assert summary["command_count"] == 1
    assert summary["commands"][0]["canonical_guard_status"] == "FAIL"


@pytest.mark.skipif(not hasattr(os, "symlink"), reason="symlinks unavailable")
def test_declared_output_symlink_is_rejected(tmp_path: Path) -> None:
    run, _ = _fixture(tmp_path)
    commands = _commands()
    script = "import os,pathlib; r=pathlib.Path(os.environ['CODEX_VERIFICATION_OUTPUT_ROOT']); os.symlink(pathlib.Path(__file__) if '__file__' in globals() else pathlib.Path.cwd()/'tool.py', r/'probe.txt')"
    commands[0]["argv"] = [sys.executable, "-c", script]
    commands[0]["outputs"] = ["probe.txt"]
    plan = _write_plan(tmp_path, run, commands=commands)
    result = prepare_verification(tmp_path, run, plan, scratch_root=tmp_path / "s", attempt_id="output-link")
    if sys.platform == "win32" and "HARNESS_COMMAND_FAILED" in {item.code for item in result.diagnostics}:
        pytest.skip("Windows symlink privilege unavailable")
    assert not result.ok
    assert "HARNESS_OUTPUT_ESCAPE" in {item.code for item in result.diagnostics}


def test_cleanup_failure_retains_promoted_evidence(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    run, plan = _fixture(tmp_path)

    def fail_cleanup(self):
        raise ScratchError("seeded cleanup failure")

    monkeypatch.setattr("pipeline_control.verifier_harness.VerificationScratch.cleanup", fail_cleanup)
    result = prepare_verification(tmp_path, run, plan, scratch_root=tmp_path / "s", attempt_id="cleanup-fail")
    assert not result.ok
    assert result.data["cleanup_status"] == "FAIL"
    assert Path(result.data["summary_path"]).is_file()
    cleanup = json.loads(Path(result.data["cleanup_path"]).read_text())
    assert cleanup["status"] == "FAIL"


def test_promotion_failure_still_cleans_scratch_and_records_cleanup(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run, plan = _fixture(tmp_path)
    scratch_root = tmp_path / "s"

    def fail_promotion(staging: Path, attempt_path: Path) -> None:
        raise OSError("seeded promotion failure")

    monkeypatch.setattr("pipeline_control.verifier_harness._promote_attempt", fail_promotion)
    result = prepare_verification(tmp_path, run, plan, scratch_root=scratch_root, attempt_id="promotion-fail")

    assert not result.ok
    assert {item.code for item in result.diagnostics} >= {"HARNESS_PROMOTION"}
    assert result.data["attempt_promoted"] is False
    assert result.data["cleanup_status"] == "PASS"
    assert list(scratch_root.iterdir()) == []
    cleanup = json.loads(Path(result.data["cleanup_path"]).read_text(encoding="utf-8"))
    latest = json.loads(Path(result.data["latest_path"]).read_text(encoding="utf-8"))
    assert cleanup["status"] == "PASS"
    assert cleanup["attempt_promoted"] is False
    assert latest["status"] == "FAIL"
    assert latest["cleanup_path"] == Path(result.data["cleanup_path"]).relative_to(tmp_path).as_posix()
    assert latest["cleanup_status"] == "PASS"


def test_promotion_and_cleanup_failures_retain_both_diagnostics(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run, plan = _fixture(tmp_path)

    def fail_promotion(staging: Path, attempt_path: Path) -> None:
        raise OSError("seeded promotion failure")

    def fail_cleanup(self) -> None:
        raise ScratchError("seeded cleanup failure")

    monkeypatch.setattr("pipeline_control.verifier_harness._promote_attempt", fail_promotion)
    monkeypatch.setattr("pipeline_control.verifier_harness.VerificationScratch.cleanup", fail_cleanup)
    result = prepare_verification(tmp_path, run, plan, scratch_root=tmp_path / "s", attempt_id="double-fail")

    assert not result.ok
    assert {item.code for item in result.diagnostics} >= {"HARNESS_PROMOTION", "HARNESS_CLEANUP"}
    assert result.data["attempt_promoted"] is False
    assert result.data["cleanup_status"] == "FAIL"
    cleanup = json.loads(Path(result.data["cleanup_path"]).read_text(encoding="utf-8"))
    latest = json.loads(Path(result.data["latest_path"]).read_text(encoding="utf-8"))
    assert cleanup["status"] == "FAIL"
    assert cleanup["scratch_retained"] is True
    assert latest["status"] == "FAIL"
    assert {item["code"] for item in latest["diagnostics"]} >= {"HARNESS_PROMOTION", "HARNESS_CLEANUP"}


def test_deep_project_path_uses_short_injected_scratch(tmp_path: Path) -> None:
    deep = tmp_path / ("deep-" + "x" * 12)
    deep.mkdir(parents=True)
    run, plan = _fixture(deep)
    result = prepare_verification(deep, run, plan, scratch_root=tmp_path / "short", attempt_id="deep")
    assert result.ok, result.as_dict()


def test_run_tests_retains_immutable_attempt_history(tmp_path: Path) -> None:
    from pipeline_control.test_runner import run_test_plan
    from test_pipeline_control import _write_run, _write_test_plan

    run = _write_run(tmp_path, current_stage="implementation", current_status="PASSED")
    first = run_test_plan(tmp_path, run, _write_test_plan(tmp_path, 7), attempt_id="failure")
    assert not first.ok
    failed_attempt = run / "30_execution" / "test_attempts" / "failure" / "test_results.json"
    failed_bytes = failed_attempt.read_bytes()
    second = run_test_plan(tmp_path, run, _write_test_plan(tmp_path, 0), attempt_id="pass")
    assert second.ok
    assert failed_attempt.read_bytes() == failed_bytes
    canonical = json.loads((run / "30_execution" / "test_results.json").read_text())
    assert canonical["status"] == "PASS"
    assert canonical["attempt_id"] == "pass"
    assert sha256_file(run / "30_execution" / "test_attempts" / "pass" / "test_results.json") == canonical["attempt_sha256"]
    reused = run_test_plan(tmp_path, run, _write_test_plan(tmp_path, 0), attempt_id="pass")
    assert not reused.ok
    assert "TEST_ATTEMPT_EXISTS" in {item.code for item in reused.diagnostics}


def test_prepare_verification_cli_help_is_registered() -> None:
    with pytest.raises(SystemExit) as exc:
        build_parser().parse_args(["prepare-verification", "--help"])
    assert exc.value.code == 0


def test_prepare_verification_cli_forwards_explicit_candidate_bindings(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    run, plan = _fixture(tmp_path)
    contract = run / "20_contract" / "product_contract.yaml"
    manifest = run / "50_release" / "release_manifest.json"
    inspection = run / "50_release" / "package_inspection.json"
    archive = tmp_path / "deliverables" / "fixture_tool.zip"

    exit_code = main(
        [
            "--project-root",
            str(tmp_path),
            "--format",
            "json",
            "prepare-verification",
            "--run-dir",
            run.relative_to(tmp_path).as_posix(),
            "--plan",
            plan.relative_to(tmp_path).as_posix(),
            "--contract",
            contract.relative_to(tmp_path).as_posix(),
            "--manifest",
            manifest.relative_to(tmp_path).as_posix(),
            "--inspection",
            inspection.relative_to(tmp_path).as_posix(),
            "--archive",
            archive.relative_to(tmp_path).as_posix(),
            "--scratch-root",
            "scratch",
            "--attempt-id",
            "cli-bindings",
        ]
    )

    assert exit_code == 0, capsys.readouterr().out


def test_run_tests_cli_remains_compatible_after_harness_integration(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    from test_pipeline_control import _write_run, _write_test_plan

    run = _write_run(tmp_path, current_stage="implementation", current_status="PASSED")
    plan = _write_test_plan(tmp_path, 0)

    exit_code = main(
        [
            "--project-root",
            str(tmp_path),
            "--format",
            "json",
            "run-tests",
            "--run-dir",
            run.relative_to(tmp_path).as_posix(),
            "--plan",
            plan.relative_to(tmp_path).as_posix(),
            "--attempt-id",
            "cli-compat",
        ]
    )

    assert exit_code == 0, capsys.readouterr().out
