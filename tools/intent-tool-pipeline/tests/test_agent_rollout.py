"""S6 operational freeze/recovery route through a side-by-side compatible CLI.

Root's freeze is procedural, not a runtime setting. These tests issue no new
selected assignments after the freeze point. Exit injection stops a real CLI
process after a durable write; no production result is replaced with a mock.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest
import yaml

from pipeline_control import procedures
from pipeline_control.io_utils import sha256_file
from pipeline_control.submissions import submission_audit_id
from test_semantic_finalize import _build_request, _problem_frame, STARTED_AT, FINALIZED_AT
from test_procedure_binding import full_lifecycle  # noqa: F401
import test_agent_rounds as rounds


TOOL = Path(__file__).resolve().parents[1]
REPO = TOOL.parents[1]
INITIALIZER = Path(".agents/skills/build-tool-pipeline/scripts/initialize_run.py")
ROLE = "intent_realizer"


@pytest.fixture
def root(tmp_path_factory):
    # Short generated names leave headroom for actual submission path checks.
    return tmp_path_factory.mktemp("r6")


def _env():
    return {**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONDONTWRITEBYTECODE": "1", "PYTHONPATH": ""}


def _process(argv, *, cwd):
    return subprocess.run([sys.executable, "-B", *map(str, argv)], cwd=cwd,
                          env=_env(), capture_output=True, text=True, encoding="utf-8", timeout=60)


def _json_process(argv, *, cwd, ok=True):
    result = _process(argv, cwd=cwd)
    assert result.returncode == (0 if ok else 1), result.stdout + result.stderr
    body = json.loads(result.stdout)
    assert body["ok"] is ok, body
    return body


def _cli(installation, project, *args, ok=True):
    return _json_process([installation / "tools/intent-tool-pipeline/pipeline_ops.py",
                          "--project-root", project, "--format", "json", *args], cwd=project, ok=ok)


def _snapshot(root):
    return {p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob("*") if p.is_file()}


def _compatible_copy(root):
    """Retain executable package and exact registry assets, not another product tree.

    This isolates reader/recovery compatibility from the separately tested full
    distribution inventory. No source imports can resolve via PYTHONPATH.
    """
    installed = root / "keep"
    target = installed / "tools/intent-tool-pipeline"
    target.mkdir(parents=True)
    shutil.copy2(TOOL / "pipeline_ops.py", target / "pipeline_ops.py")
    shutil.copytree(TOOL / "pipeline_control", target / "pipeline_control",
                    ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    assets = set(procedures.COMMON) | {item for record in procedures.REGISTRY.values() for item in record[3]}
    for namespace, relative in assets:
        source = procedures.procedure_path(namespace, relative)
        destination = (installed / ".agents" if namespace == "agents" else target) / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        if not destination.exists():
            shutil.copy2(source, destination)
        assert destination.read_bytes() == source.read_bytes()
    initializer = installed / INITIALIZER
    initializer.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(REPO / INITIALIZER, initializer)
    assert target.resolve() != TOOL.resolve()
    return installed


def _initialize(project, *, revision=None, installation=REPO):
    project.mkdir(exist_ok=True)
    request = _build_request()
    request["project"]["project_id"] = "s6"
    source = project / "request.yaml"
    source.write_text(yaml.safe_dump(request), encoding="utf-8")
    argv = [installation / INITIALIZER, "--project-root", project, "--request", source,
            "--timestamp", STARTED_AT, "--format", "json"]
    if revision is not None:
        argv.extend(["--control-revision", revision])
    result = _json_process(argv, cwd=project)
    run = project / result["data"]["run_dir"]
    assert run == project / "workspace/build_runs/s6"
    return run


def _submission(project, run, revision, *, name="a", version=1, installation=REPO):
    result = _cli(installation, project, "role-boundary", "start", "--run-dir", run,
                  "--role", ROLE, "--invocation-ref", name, "--artifact", "problem_frame",
                  "--timestamp", STARTED_AT)
    baseline = result["data"]["baseline_sha256"]
    source = project / result["data"]["submission_path"]
    body = _problem_frame(version, owner=ROLE)
    if revision == "1.2":
        loaded = _cli(installation, project, "load-role-assignment", "--run-dir", run,
                      "--role", ROLE, "--invocation-ref", name, "--baseline-sha256", baseline)
        assert Path(loaded["data"]["output_path"]) == source
        body += "\n<!-- procedure-binding: " + json.dumps(loaded["data"]["required_result_binding"]) + " -->\n"
    source.write_text(body, encoding="utf-8")
    return {"artifact_key": "problem_frame", "role": ROLE, "invocation_ref": name,
            "baseline_sha256": baseline, "source_path": source, "expected_source_sha256": sha256_file(source)}


def _finalize_args(run, request):
    return ["finalize-semantic-return", "--run-dir", run, "--artifact", request["artifact_key"],
            "--role", request["role"], "--invocation-ref", request["invocation_ref"],
            "--baseline-sha256", request["baseline_sha256"], "--source", request["source_path"],
            "--expected-source-sha256", request["expected_source_sha256"], "--timestamp", FINALIZED_AT]


def _state(run):
    return json.loads((run / "30_execution/run_state.json").read_bytes())


def test_frozen_route_retains_explicit_legacy_initialization_and_full_body(root):
    installed = _compatible_copy(root)
    project = root / "p"
    run = _initialize(project, revision="1.0", installation=installed)
    state = _state(run)
    assert state["control"]["semantic_role_boundary"] == "1.0"
    assert state["repair"]["maximum_attempts"] == 2
    assert "rounds" not in state["repair"] and "semantic_registrations" not in state["control"]
    # Legacy Root-held complete body transport, without selected artifact/digest.
    source = project / "body.md"
    source.write_text(_problem_frame(owner=ROLE), encoding="utf-8")
    started = _cli(installed, project, "role-boundary", "start", "--run-dir", run,
                   "--role", ROLE, "--invocation-ref", "legacy", "--timestamp", STARTED_AT)
    admitted = _cli(installed, project, "finalize-semantic-return", "--run-dir", run,
                    "--artifact", "problem_frame", "--role", ROLE, "--invocation-ref", "legacy",
                    "--baseline-sha256", started["data"]["baseline_sha256"], "--source", source,
                    "--timestamp", FINALIZED_AT)
    assert admitted["data"]["content_sha256"] == sha256_file(source)
    assert (run / "10_framing/problem_frame.md").read_bytes() == source.read_bytes()
    before = _snapshot(project)
    _cli(installed, project, "validate-run", "--run-dir", run)
    assert _snapshot(project) == before
    assert _state(run)["control"]["semantic_role_boundary"] == "1.0"


@pytest.mark.parametrize("revision", ["1.1", "1.2"])
def test_frozen_selected_historical_replay_uses_original_paths_and_bytes(root, revision):
    project = root / "p"
    run = _initialize(project, revision=revision)
    first = _submission(project, run, revision, name="a")
    receipt = _cli(REPO, project, *_finalize_args(run, first))["data"]["receipt"]
    second = _submission(project, run, revision, name="b", version=2)
    _cli(REPO, project, *_finalize_args(run, second))
    installed = _compatible_copy(root)
    # Freeze: no selected initializer/start/fresh-admission calls from here.
    before = _snapshot(project)
    _cli(installed, project, "validate-run", "--run-dir", run)
    replay = _cli(installed, project, *_finalize_args(run, first))
    assert replay["data"]["replayed"] is True and replay["data"]["is_current"] is False
    assert replay["data"]["receipt"] == receipt
    assert _snapshot(project) == before
    assert _state(run)["control"]["semantic_role_boundary"] == revision
    assert (run / "10_framing/problem_frame.md").read_bytes() == second["source_path"].read_bytes()
    assert not (installed / "tools/intent-tool-pipeline/workspace").exists()


@pytest.mark.parametrize("revision", ["1.1", "1.2"])
@pytest.mark.parametrize("point", ["artifact", "state"])
def test_frozen_prepared_transaction_recovers_with_compatible_cli(root, revision, point):
    project = root / "p"
    run = _initialize(project, revision=revision)
    request = _submission(project, run, revision)
    installed = _compatible_copy(root)
    state_path = run / "30_execution/run_state.json"
    prior = state_path.read_bytes()
    source_bytes = request["source_path"].read_bytes()
    # Exit the actual command after its artifact/state write and before the
    # COMMITTED journal update. Only the write-stop mechanism is injected.
    script = """
import os, sys
from pathlib import Path
sys.path.insert(0, sys.argv[1])
import pipeline_control.artifacts as artifacts
from pipeline_control.cli import main
target, point = Path(sys.argv[2]), sys.argv[3]
attribute = 'atomic_write_bytes' if point == 'artifact' else 'atomic_write_json'
original = getattr(artifacts, attribute)
def stop(path, payload):
    result = original(path, payload)
    if path == target:
        os._exit(71)
    return result
setattr(artifacts, attribute, stop)
raise SystemExit(main(sys.argv[4:]))
"""
    target = run / "10_framing/problem_frame.md" if point == "artifact" else state_path
    stopped = _process(["-c", script, TOOL, target, point, "--project-root", project,
                        "--format", "json", *_finalize_args(run, request)], cwd=project)
    assert stopped.returncode == 71, stopped.stdout + stopped.stderr
    audit = submission_audit_id(ROLE, request["invocation_ref"])
    tx = run / f"30_execution/semantic_finalize/tx/{audit}.json"
    prepared = json.loads(tx.read_bytes())
    assert prepared["status"] == "PREPARED"
    installed_state = state_path.read_bytes()
    # Freeze and quiescence: reject unrelated supported mutation, then recover
    # only the existing request. Keep the original project/run paths throughout.
    before_block = _snapshot(project)
    # Supply an existing path so CLI path resolution reaches the transaction
    # guard before attempting to interpret its body as a test plan.
    rejected = _cli(installed, project, "run-tests", "--run-dir", run,
                    "--plan", "request.yaml", ok=False)
    assert any(d["code"] == "FINALIZE_TRANSACTION_PENDING" for d in rejected["diagnostics"])
    assert _snapshot(project) == before_block
    recovered = _cli(installed, project, *_finalize_args(run, request), ok=point == "state")
    final = json.loads(tx.read_bytes())
    assert final["request"] == prepared["request"]
    assert len(final["attempts"]) == 1
    assert request["source_path"].read_bytes() == source_bytes
    if point == "artifact":
        assert any(d["code"] == "FINALIZE_RECOVERED_ROLLBACK" for d in recovered["diagnostics"])
        assert state_path.read_bytes() == prior
        assert not target.exists()
        assert final["status"] == "ROLLED_BACK"
        # Do not turn a rollback into a fresh admission while frozen.
    else:
        assert recovered["data"]["replayed"] and recovered["data"]["is_current"]
        assert final["status"] == "COMMITTED"
        assert state_path.read_bytes() == installed_state
        assert (run / "10_framing/problem_frame.md").read_bytes() == source_bytes
        assert recovered["data"]["receipt"] == prepared["attempts"][0]["receipt"]
        assert _state(run)["control"]["semantic_registrations"][audit] == recovered["data"]["receipt"]
        before_replay = _snapshot(project)
        assert _cli(installed, project, *_finalize_args(run, request))["data"]["replayed"]
        assert _snapshot(project) == before_replay
    assert _state(run)["control"]["semantic_role_boundary"] == revision
    assert _state(run)["repair"] == json.loads(prior)["repair"]
    before_read = _snapshot(project)
    _cli(installed, project, "validate-run", "--run-dir", run)
    assert _snapshot(project) == before_read
    assert not (installed / "tools/intent-tool-pipeline/workspace").exists()


@pytest.mark.parametrize("revision", ["1.1", "1.2"])
def test_frozen_reader_preserves_completed_rounds_and_historical_report(root, revision, request):
    # Reuse real semantic/round fixture builders. The 1.2 producer fixture adds
    # required metadata before calling the unchanged production finalizer.
    if revision == "1.2":
        request.getfixturevalue("full_lifecycle")
    project = root / "p"
    project.mkdir()
    run = rounds.initial_result(project)
    rounds.one_round(project, run)
    state = _state(run)
    assert state["control"]["semantic_role_boundary"] == revision
    assert state["repair"]["active_attempt"] == 1
    assert state["repair"]["rounds"][0]["status"] == "COMPLETED"
    receipt = next(r for r in state["control"]["semantic_registrations"].values()
                   if r["artifact_ref"] == "verification-report@1")
    replay_request = {"artifact_key": "verification_report", "role": "independent_verifier",
                      "invocation_ref": receipt["source_invocation_ref"], "baseline_sha256": receipt["baseline_sha256"],
                      "source_path": project / receipt["submission_path"], "expected_source_sha256": receipt["content_sha256"]}
    installed = _compatible_copy(root)
    # Freeze: completed and historical rounds must remain exactly attributable.
    before = _snapshot(project)
    _cli(installed, project, "validate-run", "--run-dir", run)
    replay = _cli(installed, project, *_finalize_args(run, replay_request))
    assert replay["data"]["replayed"] and replay["data"]["is_current"] is False
    assert replay["data"]["receipt"] == receipt
    assert _snapshot(project) == before
    assert _state(run)["repair"] == state["repair"]
