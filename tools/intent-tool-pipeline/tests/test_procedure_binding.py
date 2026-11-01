"""S5 P1-P7: registry ownership, strict admission and retained recovery.

Threshold approvals in this module are synthetic test fixtures, not user authority.
"""

from copy import deepcopy
import json
import os
from pathlib import Path

import pytest
import yaml

import pipeline_control.artifacts as artifacts
import pipeline_control.procedures as procedures
from pipeline_control.boundary import start_role_boundary, finish_role_boundary
from pipeline_control.cli import _run, build_parser
from pipeline_control.io_utils import InputError, atomic_write_json, read_structured, sha256_file
from pipeline_control.mutation_guard import run_forward_diagnostics
from pipeline_control.submissions import submission_audit_id, validate_submission_assignment
from pipeline_control.validation import validate_control_metadata, validate_run_directory
from pipeline_control.workflow import validate_run_state_context
from test_agent_finalize import _selected, _call, _submission, _contract_submission
from test_semantic_finalize import STARTED_AT, FINALIZED_AT


@pytest.fixture
def root(tmp_path_factory):
    # Avoid per-test descriptive names exceeding the real Windows path budget.
    return tmp_path_factory.mktemp("p5")


def selected(root):
    run = _selected(root)
    path = run / "30_execution/run_state.json"
    state = read_structured(path)
    state["control"]["semantic_role_boundary"] = "1.2"
    atomic_write_json(path, state)
    assert validate_run_directory(root, run).ok
    return run


def bind(root, run, request):
    path = run / "30_execution/role_boundary/baselines" / f"{submission_audit_id(request['role'], request['invocation_ref'])}.json"
    baseline = read_structured(path)
    expected = procedures.result_binding(baseline, request["baseline_sha256"])
    source = request["source_path"]
    if source.suffix == ".md":
        source.write_bytes(source.read_bytes() + ("\n<!-- procedure-binding: " + json.dumps(expected) + " -->\n").encode())
    else:
        body = read_structured(source)
        body["procedure_binding"] = expected
        source.write_text(yaml.safe_dump(body), encoding="utf-8")
    request["expected_source_sha256"] = sha256_file(source)
    return request


def submitted(root, run, name="a", version=1):
    return bind(root, run, _submission(root, run, name, version))


def snapshot(run):
    return {p.relative_to(run).as_posix(): p.read_bytes() for p in run.rglob("*") if p.is_file()}


def loader(root, run, request):
    return procedures.load_role_assignment(root, run, role=request["role"], invocation_ref=request["invocation_ref"],
                                           baseline_sha256=request["baseline_sha256"])


def test_registry_loader_is_read_only_and_uses_installed_roots(root):
    run = selected(root)
    request = submitted(root, run)
    before = snapshot(run)
    loaded = loader(root, run, request)
    assert loaded.ok, loaded.as_dict()
    assert snapshot(run) == before


    assert loaded.data["assignment"]["artifact_key"] == "problem_frame"
    assert loaded.data["procedure_binding"]["workflow"] == "A"
    assert loaded.data["required_result_binding"]["assignment_sha256"] == request["baseline_sha256"]
    assert loaded.data["output_path"] == str(request["source_path"])
    for item in loaded.data["procedures"]:
        assert not Path(item["path"]).is_relative_to(root)
        assert item["body"] == Path(item["path"]).read_bytes().decode("utf-8")
    args = build_parser().parse_args(["--project-root", str(root), "load-role-assignment", "--run-dir", str(run),
        "--role", request["role"], "--invocation-ref", request["invocation_ref"], "--baseline-sha256", request["baseline_sha256"]])
    assert _run(args).ok
    assert snapshot(run) == before


def test_loader_before_producer_output_exists(root):
    run = selected(root)
    started = start_role_boundary(root, run, role="intent_realizer", invocation_ref="before", artifact_key="problem_frame")
    assert started.ok, started.as_dict()
    before = snapshot(run)
    loaded = procedures.load_role_assignment(root, run, role="intent_realizer", invocation_ref="before",
                                            baseline_sha256=started.data["baseline_sha256"])
    assert loaded.ok, loaded.as_dict()
    assert not Path(loaded.data["output_path"]).exists()
    assert snapshot(run) == before


def test_valid_bound_registration_receipt_and_replay(root):
    run = selected(root)
    request = submitted(root, run)
    expected = loader(root, run, request).data["required_result_binding"]
    admitted = _call(root, run, request)
    assert admitted.ok, admitted.as_dict()
    assert admitted.data["receipt"]["procedure_binding"] == expected
    assert validate_run_directory(root, run).ok
    before = snapshot(run)
    replay = _call(root, run, request)
    assert replay.ok and replay.data["replayed"]
    assert replay.data["receipt"] == admitted.data["receipt"]
    assert snapshot(run) == before


@pytest.mark.parametrize("change", ["missing", "revision", "assignment", "procedure", "extra", "duplicate", "raw"])
def test_missing_wrong_or_duplicate_markdown_binding_rejects_before_activation(root, change):
    run = selected(root)
    request = _submission(root, run)
    if change != "raw":
        request = bind(root, run, request)
    path = request["source_path"]
    body = path.read_text(encoding="utf-8")
    if change == "missing":
        body = body[:body.index("<!-- procedure-binding:")]
    elif change == "duplicate":
        body += body[body.index("<!-- procedure-binding:"):]
    elif change != "raw":
        expected = loader(root, run, request).data["required_result_binding"]
        wrong = deepcopy(expected)
        if change == "extra":
            wrong["acknowledged"] = True
        else:
            wrong[{"revision": "control_revision", "assignment": "assignment_sha256", "procedure": "procedure_sha256"}[change]] = "bad"
        body = body.replace(json.dumps(expected), json.dumps(wrong))
    path.write_text(body, encoding="utf-8")
    request["expected_source_sha256"] = sha256_file(path)
    state = (run / "30_execution/run_state.json").read_bytes()
    result = _call(root, run, request)
    assert not result.ok
    assert (run / "30_execution/run_state.json").read_bytes() == state
    assert not (run / "10_framing/problem_frame.md").exists()


@pytest.mark.parametrize("suffix", [".yaml", ".json", ".md"])
def test_duplicate_structured_keys_are_rejected_at_any_depth(suffix):
    expected = {"control_revision": "1.2", "assignment_sha256": "a" * 64, "procedure_sha256": "b" * 64}
    encoded = json.dumps(expected)
    if suffix == ".yaml":
        payload = ("procedure_binding: " + encoded + "\nprocedure_binding: " + encoded).encode()
    elif suffix == ".json":
        payload = ('{"procedure_binding":' + encoded + ',"procedure_binding":' + encoded + '}').encode()
    else:
        payload = ('<!-- procedure-binding: ' + encoded.replace('"1.2"', '"1.2", "control_revision":"1.2"') + ' -->').encode()
    with pytest.raises(InputError, match="duplicate"):
        procedures.validate_result_binding(payload, Path("result" + suffix), expected)


@pytest.mark.parametrize("suffix", [".yaml", ".json", ".md"])
def test_result_encoding_positive(suffix):
    expected = {"control_revision": "1.2", "assignment_sha256": "a" * 64, "procedure_sha256": "b" * 64}
    payload = ('<!-- procedure-binding: ' + json.dumps(expected) + ' -->') if suffix == ".md" else json.dumps({"procedure_binding": expected})
    assert procedures.validate_result_binding(payload.encode(), Path("result" + suffix), expected) == expected


@pytest.mark.parametrize("field", ["workflow", "step", "run_id", "run_dir", "role", "invocation_ref", "registry_revision", "protocol"])
def test_assignment_identity_and_registry_reject_substitution(root, field):
    run = selected(root)
    request = submitted(root, run)
    loaded = loader(root, run, request)
    baseline = read_structured(root / loaded.data["baseline_path"])
    baseline["procedure_binding"][field] = "substituted"
    with pytest.raises(InputError, match="mismatch"):
        procedures.validate_procedure_binding(root, run, procedures._original_state(baseline), baseline, current=False)


@pytest.mark.parametrize("change", ["order", "omit", "replace", "bytes", "duplicate"])
def test_mandatory_procedure_membership_order_and_retained_bytes(root, change):
    run = selected(root)
    request = submitted(root, run)
    baseline = read_structured(root / loader(root, run, request).data["baseline_path"])
    assets = baseline["procedure_binding"]["assets"]
    if change == "order":
        assets.reverse()
    elif change == "omit":
        assets.pop()
    elif change == "duplicate":
        assets[-1] = assets[0]
    elif change == "replace":
        assets[0]["path"] = "../unapproved.md"
    else:
        assets[0]["content_base64"] = "Y2hhbmdlZA=="
    with pytest.raises(InputError):
        procedures.validate_procedure_binding(root, run, procedures._original_state(baseline), baseline, current=False)


@pytest.mark.parametrize("namespace,path", [("product", "docs/contracts/README.md"), ("tool", "../README.md"),
    ("tool", "docs/../docs/contracts/README.md"), ("agents", "skills/build-tool-pipeline/SKILL.MD")])
def test_procedure_allowlist_rejects_namespaces_aliases_and_escapes(namespace, path):
    with pytest.raises(InputError):
        procedures.procedure_path(namespace, path)


def test_missing_dependency_blocks_before_allocation(root, monkeypatch):
    run = selected(root)
    before = snapshot(run)
    monkeypatch.setattr(procedures, "REPOSITORY_ROOT", root)
    started = start_role_boundary(root, run, role="intent_realizer", invocation_ref="missing", artifact_key="problem_frame")
    assert not started.ok
    assert snapshot(run) == before
    assert not (run / "30_execution/sub").exists()


def test_current_drift_blocks_admission_and_forward_writers_but_allows_historical_replay(root, monkeypatch):
    run = selected(root)
    request = submitted(root, run)
    admitted = _call(root, run, request)
    assert admitted.ok, admitted.as_dict()
    # Substitute one same-path current procedure read with drift; never edit source.
    changed = root / "changed.md"
    changed.write_text("changed current mandatory procedure", encoding="utf-8")
    original = procedures.procedure_path
    monkeypatch.setattr(procedures, "procedure_path", lambda ns, path: changed if path == procedures.ENTRY else original(ns, path))
    assert not loader(root, run, request).ok
    state = read_structured(run / "30_execution/run_state.json")
    assert not validate_run_state_context(root, run, state)  # Retained provenance is readable.
    assert run_forward_diagnostics(root, run)
    before = snapshot(run)
    replay = _call(root, run, request)
    assert replay.ok and replay.data["receipt"] == admitted.data["receipt"]
    assert snapshot(run) == before
    # Stale active provenance can be replaced by a fresh registry assignment.
    replacement = submitted(root, run, "fresh", 2)
    assert _call(root, run, replacement).ok
    assert not run_forward_diagnostics(root, run)


def test_uncommitted_admission_requires_current_procedures(root, monkeypatch):
    run = selected(root)
    request = submitted(root, run)
    changed = root / "changed.md"
    changed.write_text("changed procedure", encoding="utf-8")
    original = procedures.procedure_path
    monkeypatch.setattr(procedures, "procedure_path", lambda ns, path: changed if path == procedures.ENTRY else original(ns, path))
    result = _call(root, run, request)
    assert not result.ok
    assert not (run / "10_framing/problem_frame.md").exists()


@pytest.mark.parametrize("field", ["procedure_binding", "baseline_sha256", "submission_path"])
def test_active_receipt_corruption_blocks_context_and_mutation(root, field):
    run = selected(root)
    request = submitted(root, run)
    assert _call(root, run, request).ok
    path = run / "30_execution/run_state.json"
    state = read_structured(path)
    receipt = next(iter(state["control"]["semantic_registrations"].values()))
    receipt[field] = {} if field == "procedure_binding" else "bad"
    assert validate_run_state_context(root, run, state)
    atomic_write_json(path, state)
    assert run_forward_diagnostics(root, run)


def test_historical_replay_after_supersession_is_read_only(root):
    run = selected(root)
    old = submitted(root, run, "old")
    assert _call(root, run, old).ok
    newer = submitted(root, run, "new", 2)
    assert _call(root, run, newer).ok
    before = snapshot(run)
    replay = _call(root, run, old)
    assert replay.ok and replay.data["replayed"] and not replay.data["is_current"]
    assert snapshot(run) == before


def test_interrupted_canonical_write_recovers_exact_prior_bytes(root, monkeypatch):
    run = selected(root)
    request = submitted(root, run)
    before = (run / "30_execution/run_state.json").read_bytes()
    original = artifacts.atomic_write_bytes
    target = run / "10_framing/problem_frame.md"
    def stopped(path, payload):
        result = original(path, payload)
        if path == target:
            raise KeyboardInterrupt()
        return result
    with monkeypatch.context() as patch:
        patch.setattr(artifacts, "atomic_write_bytes", stopped)
        with pytest.raises(KeyboardInterrupt):
            _call(root, run, request)
    recovery = _call(root, run, request)
    assert not recovery.ok and any(d.code == "FINALIZE_RECOVERED_ROLLBACK" for d in recovery.diagnostics)
    assert (run / "30_execution/run_state.json").read_bytes() == before
    assert not target.exists()
    assert _call(root, run, request).ok


def test_legacy_1_1_does_not_require_or_load_procedures(root, monkeypatch):
    run = _selected(root)
    monkeypatch.setattr(procedures, "procedure_path", lambda *args: (_ for _ in ()).throw(InputError("unavailable")))
    request = _submission(root, run)
    result = _call(root, run, request)
    assert result.ok, result.as_dict()
    assert "procedure_binding" not in result.data["receipt"]
    assert not loader(root, run, request).ok


def test_1_2_requires_receipt_binding_without_changing_state_schema(root):
    run = selected(root)
    request = submitted(root, run)
    assert _call(root, run, request).ok
    state = read_structured(run / "30_execution/run_state.json")
    assert state["schema_version"] == "1.1"
    receipt = next(iter(state["control"]["semantic_registrations"].values()))
    receipt.pop("procedure_binding")
    assert any(d.code == "REGISTRATION_PROCEDURE" for d in validate_control_metadata(state))


@pytest.fixture
def full_lifecycle(monkeypatch):
    """Reuse genuine lifecycle helpers while producers add selected bindings."""
    import test_agent_rounds as rounds
    import test_agent_continuation as continuation_tests

    monkeypatch.setattr(rounds, "_selected", selected)
    monkeypatch.setattr(rounds, "_call", lambda root, run, request: _call(root, run, bind(root, run, request)))
    original_finalize = artifacts.finalize_semantic_return
    def finalizer(root, run, **request):
        return original_finalize(root, run, **bind(root, run, request))
    monkeypatch.setattr(rounds, "finalize_semantic_return", finalizer)
    original_write = continuation_tests.atomic_write_json
    def write(path, value):
        if isinstance(value, dict) and value.get("artifact_type") == "iteration-threshold-review":
            run = path.parents[3]
            baseline_path = run / "30_execution/role_boundary/baselines" / f"{path.parent.name}.json"
            baseline = read_structured(baseline_path)
            value = {**value, "procedure_binding": procedures.result_binding(baseline, sha256_file(baseline_path))}
        original_write(path, value)
    monkeypatch.setattr(continuation_tests, "atomic_write_json", write)
    return rounds, continuation_tests


def test_bound_prepared_a_to_b_and_four_round_threshold_review(root, full_lifecycle):
    rounds, continuation_tests = full_lifecycle
    run, event, resolution, started, _ = continuation_tests.review_fixture(root)
    state = rounds.load(run)
    assert state["repair"]["active_attempt"] == 4
    from pipeline_control.continuation import prepare_continuation
    admitted = prepare_continuation(root, run, state, event, resolution)
    assert admitted == resolution["continuation"]
    loaded = procedures.load_role_assignment(root, run, role="independent_verifier", invocation_ref="process1",
                                            baseline_sha256=started.data["baseline_sha256"])
    assert loaded.ok, loaded.as_dict()
    assert loaded.data["procedure_binding"]["step"] == "iteration_threshold_review"
    assert loaded.data["assignment"]["event_id"] == event["id"]
    assert validate_run_directory(root, run).ok


def test_threshold_unbound_review_rejects_even_with_matching_audit(root, full_lifecycle):
    rounds, continuation_tests = full_lifecycle
    original_write = continuation_tests.atomic_write_json
    def write(path, value):
        original_write(path, value)
        if isinstance(value, dict) and value.get("artifact_type") == "iteration-threshold-review":
            # Simulate unbound raw-spawn output before the audit closes.
            body = read_structured(path)
            body.pop("procedure_binding")
            atomic_write_json(path, body)
    continuation_tests.atomic_write_json = write
    run, event, resolution, _, _ = continuation_tests.review_fixture(root)
    from pipeline_control.continuation import prepare_continuation
    with pytest.raises(InputError, match="binding"):
        prepare_continuation(root, run, rounds.load(run), event, resolution)


def test_post_verification_procedure_drift_has_a_legal_reserved_repair_route(root, full_lifecycle, monkeypatch):
    rounds, _ = full_lifecycle
    run = rounds.initial_result(root)
    changed = root / "changed.md"
    changed.write_text("changed role procedure", encoding="utf-8")
    original = procedures.procedure_path
    monkeypatch.setattr(procedures, "procedure_path", lambda ns, path: changed if path == procedures.ENTRY else original(ns, path))
    # Legal repair coordination must remain reachable despite stale procedures.
    event = rounds.request_change(root, run, classification="CONTRACT_CONTRADICTION")
    result = rounds.transition(root, run, "repair", refs=[event], source="verification-report@1")
    assert result.ok, result.as_dict()
    assert rounds.load(run)["repair"]["active_attempt"] == 1
    assert run_forward_diagnostics(root, run)
    brief = submitted(root, run, "brief2", 2)
    assert _call(root, run, brief).ok
    contract = bind(root, run, _contract_submission(root, run, "pc2", 2))
    assert _call(root, run, contract).ok
    # Old verification report stays attributable, but no longer grants current
    # verdict authority during repair or while a fresh report is pending.
    assert not run_forward_diagnostics(root, run)
    rounds.resolve(root, run, event)
    assert rounds.transition(root, run, "repair", "PASSED").ok
    assert rounds.transition(root, run, "verification").ok
    rounds.report(root, run)
    assert rounds.transition(root, run, "verification", "FAILED").ok
    assert rounds.load(run)["repair"]["rounds"][0]["status"] == "COMPLETED"
    assert validate_run_directory(root, run).ok


def test_installed_uncommitted_drift_rolls_back_and_unblocks_fresh_assignment(root, monkeypatch):
    run = selected(root)
    request = submitted(root, run)
    path = run / "30_execution/run_state.json"
    before = path.read_bytes()
    original_write = artifacts.atomic_write_json
    def stopped(target, value):
        original_write(target, value)
        if target == path:
            raise KeyboardInterrupt()
    with monkeypatch.context() as patch:
        patch.setattr(artifacts, "atomic_write_json", stopped)
        with pytest.raises(KeyboardInterrupt):
            _call(root, run, request)
    changed = root / "changed.md"
    changed.write_text("changed procedure", encoding="utf-8")
    original = procedures.procedure_path
    monkeypatch.setattr(procedures, "procedure_path", lambda ns, path: changed if path == procedures.ENTRY else original(ns, path))
    recovery = _call(root, run, request)
    assert not recovery.ok and any(d.code == "FINALIZE_RECOVERED_ROLLBACK" for d in recovery.diagnostics), recovery.as_dict()
    assert path.read_bytes() == before
    from pipeline_control.finalize_journal import pending_transaction_diagnostics
    assert not pending_transaction_diagnostics(run)
    replacement = submitted(root, run, "fresh")
    assert _call(root, run, replacement).ok


def test_previous_verdict_retains_provenance_checks_during_repair(root, full_lifecycle):
    rounds, _ = full_lifecycle
    run = rounds.initial_result(root)
    event = rounds.request_change(root, run)
    assert rounds.transition(root, run, "repair", refs=[event], source="verification-report@1").ok
    state = rounds.load(run)
    receipt = next(r for r in state["control"]["semantic_registrations"].values() if r["artifact_key"] == "verification_report")
    (root / receipt["submission_path"]).write_bytes(b"corrupted retained previous verdict")
    assert any(d.path == "active_artifacts.verification_report" for d in run_forward_diagnostics(root, run))


@pytest.mark.parametrize("output", ["sibling", "canonical", "hardlink"])
def test_selected_1_2_output_boundaries_reject_unauthorized_writes(root, output):
    run = selected(root)
    request = submitted(root, run)
    source = request["source_path"]
    canonical = run / "10_framing/problem_frame.md"
    if output == "sibling":
        source.with_name("sidecar.json").write_text("{}", encoding="utf-8")
    elif output == "canonical":
        canonical.write_bytes(source.read_bytes())
    else:
        alias = root / "alias.md"
        os.link(source, alias)
    result = _call(root, run, request)
    assert not result.ok
    assert read_structured(run / "30_execution/run_state.json")["active_artifacts"]["problem_frame"] is None


def test_bound_additional_input_drift_rejects_1_2_admission(root):
    run = selected(root)
    context = root / "context.txt"
    context.write_text("original", encoding="utf-8")
    request = bind(root, run, _submission(root, run, input_refs=(context,)))
    context.write_text("changed", encoding="utf-8")
    assert not loader(root, run, request).ok
    assert not _call(root, run, request).ok
    assert not (run / "10_framing/problem_frame.md").exists()
