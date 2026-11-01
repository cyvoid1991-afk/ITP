"""Behavioral checks for evidence-bound local deliveries and later B intake."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import subprocess
import sys
import zipfile
from dataclasses import dataclass
from pathlib import Path

import pytest

from pipeline_control.io_utils import InputError
from pipeline_control.local_delivery import (
    collect_deliveries,
    snapshot_sha256,
    validate_delivery,
    validate_intake_deliveries,
)


DISPOSITION = "PRE_EXISTING_DELTA_NOT_VERIFIED_BASELINE"
SOURCE_CHECKS = ("source-focused", "source-suite")
PATCH_CHECKS = (
    "patch-preflight", "patch-rejection", "patch-reapply", "patch-recovery"
)
CLI = Path(__file__).resolve().parents[1] / "minor_delivery.py"


def _sha(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


@dataclass
class Delivery:
    root: Path
    source: Path
    record: Path
    manifest: dict
    members: dict[str, bytes]

    def save(self) -> None:
        _json(self.record, self.manifest)

    def rewrite_evidence(self, criterion: str, **changes: object) -> None:
        check = next(c for c in self.manifest["checks"] if c["criterion_id"] == criterion)
        path = self.root / check["evidence"]["path"]
        evidence = json.loads(path.read_text(encoding="utf-8"))
        evidence.update(changes)
        _json(path, evidence)
        check["evidence"]["sha256"] = _sha(path.read_bytes())
        self.save()

    def rewrite_package(self) -> None:
        """Rebind outer evidence so archive tests reach member validation."""
        package = self.manifest["package"]
        with zipfile.ZipFile(self.root / package["path"], "w") as archive:
            for name, payload in self.members.items():
                archive.writestr(name, payload)
        self.rebind_package_evidence()

    def rebind_package_evidence(self) -> None:
        package = self.manifest["package"]
        package["sha256"] = _sha((self.root / package["path"]).read_bytes())
        for check in self.manifest["checks"]:
            if check["criterion_id"] not in SOURCE_CHECKS:
                check["subject_sha256"] = package["sha256"]
                self.rewrite_evidence(check["criterion_id"], subject_sha256=package["sha256"])
        judgment = self.manifest["judgment"]
        judgment["subject_sha256"] = package["sha256"]
        evidence_path = self.root / judgment["evidence"]["path"]
        _json(evidence_path, {key: value for key, value in judgment.items() if key != "evidence"})
        judgment["evidence"]["sha256"] = _sha(evidence_path.read_bytes())
        self.save()

    def target(self, name: str = "target", *, current: bool = False) -> Path:
        target = self.root / name
        target.mkdir()
        (target / "app.py").write_bytes(b"print('new')\n" if current else b"print('old')\n")
        (target / "support.py").write_bytes(b"READY = True\n")
        if current:
            (target / "new.txt").write_bytes(b"new feature\n")
        else:
            (target / "obsolete.txt").write_bytes(b"old feature\n")
        return target


def _delivery(root: Path, kind: str = "patch", delivery_id: str = "widget-M1") -> Delivery:
    source = root / "develop/widget"
    source.mkdir(parents=True, exist_ok=True)
    source_bytes = {
        "app.py": b"print('new')\n",
        "new.txt": b"new feature\n",
        "support.py": b"READY = True\n",
    }
    for name, payload in source_bytes.items():
        (source / name).write_bytes(payload)
    files = [{"path": name, "sha256": _sha(payload)} for name, payload in source_bytes.items()]
    delivery_dir = root / "deliverables" / delivery_id
    delivery_dir.mkdir(parents=True)
    record = delivery_dir / "local-delivery.json"
    record_ref = record.relative_to(root).as_posix()
    (source / "CHANGELOG.md").write_text(
        f"# Widget history\n\n## M1\n\nLocal delivery record: `{record_ref}`\n", encoding="utf-8"
    )
    members = {
        (f"payload/{name}" if kind == "patch" else name): payload
        for name, payload in source_bytes.items()
        if kind == "full" or name != "support.py"
    }
    members["INSTALL.txt"] = b"Load app.py with Python.\n"
    package_path = delivery_dir / "widget.zip"
    with zipfile.ZipFile(package_path, "w") as archive:
        for name, payload in members.items():
            archive.writestr(name, payload)
    package_digest = _sha(package_path.read_bytes())
    source_digest = snapshot_sha256(files)
    manifest = {
        "schema_version": "1.0",
        "artifact_type": "local-tool-delivery",
        "delivery_id": delivery_id,
        "producer": "root_codex",
        "disposition": DISPOSITION,
        "baseline": "unknown",
        "source": {
            "root": "develop/widget", "revision_ids": ["M1"],
            "history_path": "develop/widget/CHANGELOG.md", "files": files,
            "snapshot_sha256": source_digest,
        },
        "package": {
            "kind": kind, "path": package_path.relative_to(root).as_posix(),
            "sha256": package_digest,
            "entries": [
                {"path": name, "sha256": _sha(payload),
                 "source_path": name.removeprefix("payload/") if name != "INSTALL.txt" else None}
                for name, payload in members.items()
            ],
        },
        "checks": [],
        "judgment": {
            "criterion": "Compatible bounded local revision",
            "subject_sha256": package_digest,
            "assessment": "ACCEPT", "assumptions": [], "uncertainties": [], "unresolved": [],
        },
    }
    if kind == "patch":
        manifest.update({
            "operations": [
                {"path": "app.py", "action": "replace", "payload": "payload/app.py"},
                {"path": "new.txt", "action": "add", "payload": "payload/new.txt"},
                {"path": "obsolete.txt", "action": "remove", "payload": None},
            ],
            "supported_states": [{"id": "previous-local", "files": [
                {"path": "app.py", "sha256": _sha(b"print('old')\n")},
                {"path": "new.txt", "sha256": None},
                {"path": "obsolete.txt", "sha256": _sha(b"old feature\n")},
                {"path": "support.py", "sha256": _sha(b"READY = True\n")},
            ]}],
        })
    criteria = (*SOURCE_CHECKS, "package-load", *(PATCH_CHECKS if kind == "patch" else ()))
    for criterion in criteria:
        subject = source_digest if criterion in SOURCE_CHECKS else package_digest
        evidence_path = delivery_dir / f"{criterion}.json"
        _json(evidence_path, {"status": "PASS", "subject_sha256": subject,
                              "observed": ["Executed fixture check with a passing result."]})
        manifest["checks"].append({
            "criterion_id": criterion, "method": "pytest fixture probe", "method_version": "1.0",
            "status": "PASS", "subject_sha256": subject,
            "evidence": {"path": evidence_path.relative_to(root).as_posix(),
                         "sha256": _sha(evidence_path.read_bytes())},
        })
    judgment_path = delivery_dir / "judgment.json"
    _json(judgment_path, manifest["judgment"])
    manifest["judgment"]["evidence"] = {
        "path": judgment_path.relative_to(root).as_posix(), "sha256": _sha(judgment_path.read_bytes())
    }
    result = Delivery(root, source, record, manifest, members)
    result.save()
    return result


@pytest.fixture
def delivery(tmp_path: Path) -> Delivery:
    return _delivery(tmp_path)


def _tree_bytes(path: Path) -> dict[str, bytes]:
    return {p.relative_to(path).as_posix(): p.read_bytes() for p in path.rglob("*") if p.is_file()}


def test_snapshot_identity_is_order_independent_and_content_sensitive() -> None:
    files = [{"path": "a.py", "sha256": "a" * 64}, {"path": "b.py", "sha256": "b" * 64}]
    assert snapshot_sha256(files) == snapshot_sha256(list(reversed(files)))
    changed = [dict(files[0]), {"path": "b.py", "sha256": "c" * 64}]
    assert snapshot_sha256(files) != snapshot_sha256(changed)


@pytest.mark.parametrize("kind", ["full", "patch"])
def test_valid_local_delivery_does_not_qualify_unknown_baseline(tmp_path: Path, kind: str) -> None:
    fixture = _delivery(tmp_path, kind)
    before = _tree_bytes(tmp_path)
    receipt = validate_delivery(tmp_path, fixture.record, check_source=True)
    assert isinstance(receipt, dict)
    assert receipt["eligible_baseline"] is False
    assert DISPOSITION in json.dumps(receipt)
    assert fixture.manifest["baseline"] == "unknown"
    assert _tree_bytes(tmp_path) == before


@pytest.mark.parametrize("current", [False, True])
def test_patch_accepts_coherent_base_and_reapply_without_writing(delivery: Delivery, current: bool) -> None:
    target = delivery.target(current=current)
    before = _tree_bytes(target)
    assert isinstance(validate_delivery(delivery.root, delivery.record, target=target), dict)
    assert _tree_bytes(target) == before


@pytest.mark.parametrize("mutation", ["unknown", "hybrid", "prerequisite", "current-prerequisite", "later-version"])
def test_patch_rejects_unsupported_targets_without_writing(delivery: Delivery, mutation: str) -> None:
    target = delivery.target(current=mutation in {"later-version", "current-prerequisite"})
    if mutation in {"unknown", "later-version"}:
        (target / "app.py").write_bytes(b"print('independent later edit')\n")
    elif mutation == "hybrid":
        (target / "app.py").write_bytes(b"print('new')\n")
    else:
        (target / "support.py").unlink()
    before = _tree_bytes(target)
    with pytest.raises(InputError):
        validate_delivery(delivery.root, delivery.record, target=target)
    assert _tree_bytes(target) == before


def test_patch_rejects_mixture_of_two_individually_supported_bases(delivery: Delivery) -> None:
    second = {
        "id": "another-prior-local",
        "files": [
            {"path": "app.py", "sha256": _sha(b"print('second old')\n")},
            {"path": "new.txt", "sha256": None},
            {"path": "obsolete.txt", "sha256": _sha(b"second old feature\n")},
            {"path": "support.py", "sha256": _sha(b"READY = True\n")},
        ],
    }
    delivery.manifest["supported_states"].append(second)
    delivery.save()
    target = delivery.target()
    (target / "obsolete.txt").write_bytes(b"second old feature\n")
    before = _tree_bytes(target)
    with pytest.raises(InputError):
        validate_delivery(delivery.root, delivery.record, target=target)
    assert _tree_bytes(target) == before


@pytest.mark.parametrize("mutation", ["missing-operation-state", "add-already-present", "replace-absent", "missing-payload", "payload-target-mismatch"])
def test_patch_contract_requires_complete_safe_operations(delivery: Delivery, mutation: str) -> None:
    state = delivery.manifest["supported_states"][0]["files"]
    if mutation == "missing-operation-state":
        state[:] = [item for item in state if item["path"] != "obsolete.txt"]
    elif mutation == "add-already-present":
        next(item for item in state if item["path"] == "new.txt")["sha256"] = _sha(b"existing\n")
    elif mutation == "replace-absent":
        state[0]["sha256"] = None
    elif mutation == "missing-payload":
        delivery.manifest["operations"][0]["payload"] = "payload/absent.py"
    else:
        delivery.manifest["operations"][0]["payload"] = "payload/new.txt"
    delivery.save()
    with pytest.raises(InputError):
        validate_delivery(delivery.root, delivery.record)


def test_complete_baseline_reference_remains_ineligible(delivery: Delivery) -> None:
    delivery.manifest["baseline"] = {
        "run_id": "historical-run",
        "archive_sha256": "1" * 64,
        "product_contract_ref": "history/product-contract.yaml",
        "product_contract_sha256": "2" * 64,
        "verification_report_ref": "history/verification-report.md",
        "verification_report_sha256": "3" * 64,
    }
    delivery.save()
    assert validate_delivery(delivery.root, delivery.record)["eligible_baseline"] is False


def test_incomplete_baseline_reference_is_rejected(delivery: Delivery) -> None:
    delivery.manifest["baseline"] = {"run_id": "historical-run", "archive_sha256": "1" * 64}
    delivery.save()
    with pytest.raises(InputError):
        validate_delivery(delivery.root, delivery.record)


def test_source_currency_is_explicitly_checked(delivery: Delivery) -> None:
    (delivery.source / "app.py").write_bytes(b"print('later source')\n")
    assert isinstance(validate_delivery(delivery.root, delivery.record), dict)
    with pytest.raises(InputError):
        validate_delivery(delivery.root, delivery.record, check_source=True)


def test_archive_bytes_are_hash_bound(delivery: Delivery) -> None:
    with (delivery.root / delivery.manifest["package"]["path"]).open("ab") as stream:
        stream.write(b"tampered archive bytes")
    with pytest.raises(InputError):
        validate_delivery(delivery.root, delivery.record)


@pytest.mark.parametrize("mutation", ["extra", "missing", "changed", "traversal", "source-substitution"])
def test_archive_inventory_and_source_mapping_are_enforced(delivery: Delivery, mutation: str) -> None:
    entries = delivery.manifest["package"]["entries"]
    if mutation == "extra":
        delivery.members["unreported.py"] = b"unexpected executable\n"
    elif mutation == "missing":
        del delivery.members["payload/app.py"]
    elif mutation == "changed":
        delivery.members["payload/app.py"] = b"different payload\n"
    elif mutation == "traversal":
        payload = b"outside target\n"
        delivery.members["../escape.py"] = payload
        entries.append({"path": "../escape.py", "sha256": _sha(payload), "source_path": None})
    else:
        entries[0]["source_path"] = "support.py"
    delivery.rewrite_package()
    with pytest.raises(InputError):
        validate_delivery(delivery.root, delivery.record)
    assert not (delivery.root / "escape.py").exists()


def test_duplicate_zip_members_are_rejected(delivery: Delivery) -> None:
    package = delivery.manifest["package"]
    path = delivery.root / package["path"]
    with pytest.warns(UserWarning, match="Duplicate name"):
        with zipfile.ZipFile(path, "a") as archive:
            archive.writestr("payload/app.py", delivery.members["payload/app.py"])
    delivery.rebind_package_evidence()
    with pytest.raises(InputError):
        validate_delivery(delivery.root, delivery.record)


@pytest.mark.parametrize("criterion", [*SOURCE_CHECKS, "package-load", *PATCH_CHECKS])
def test_every_applicable_check_is_required(delivery: Delivery, criterion: str) -> None:
    delivery.manifest["checks"] = [c for c in delivery.manifest["checks"] if c["criterion_id"] != criterion]
    delivery.save()
    with pytest.raises(InputError):
        validate_delivery(delivery.root, delivery.record)


@pytest.mark.parametrize("status", ["NOT_RUN", "FAIL", "BLOCKED"])
def test_nonpassing_check_cannot_be_declared_complete(delivery: Delivery, status: str) -> None:
    delivery.manifest["checks"][0]["status"] = status
    delivery.rewrite_evidence("source-focused", status=status)
    with pytest.raises(InputError):
        validate_delivery(delivery.root, delivery.record)


@pytest.mark.parametrize("layer", ["check", "evidence"])
def test_stale_subject_identity_is_rejected(delivery: Delivery, layer: str) -> None:
    if layer == "check":
        delivery.manifest["checks"][0]["subject_sha256"] = "0" * 64
        delivery.save()
    else:
        delivery.rewrite_evidence("package-load", subject_sha256="0" * 64)
    with pytest.raises(InputError):
        validate_delivery(delivery.root, delivery.record)


@pytest.mark.parametrize("mutation", ["missing", "tampered", "empty-observation", "status-conflict"])
def test_evidence_requires_actual_matching_observations(delivery: Delivery, mutation: str) -> None:
    check = delivery.manifest["checks"][0]
    evidence_path = delivery.root / check["evidence"]["path"]
    if mutation == "missing":
        evidence_path.unlink()
    elif mutation == "tampered":
        evidence_path.write_text('{"status": "PASS"}', encoding="utf-8")
    elif mutation == "empty-observation":
        delivery.rewrite_evidence("source-focused", observed=[])
    else:
        delivery.rewrite_evidence("source-focused", status="FAIL")
    with pytest.raises(InputError):
        validate_delivery(delivery.root, delivery.record)


@pytest.mark.parametrize("mutation", ["unresolved", "mismatched-evidence", "missing-evidence", "stale-subject"])
def test_semantic_acceptance_is_evidence_bound(delivery: Delivery, mutation: str) -> None:
    judgment = delivery.manifest["judgment"]
    path = delivery.root / judgment["evidence"]["path"]
    if mutation == "unresolved":
        judgment["unresolved"] = ["Compatibility remains undecided."]
        evidence = {k: v for k, v in judgment.items() if k != "evidence"}
        _json(path, evidence)
        judgment["evidence"]["sha256"] = _sha(path.read_bytes())
    elif mutation in {"mismatched-evidence", "stale-subject"}:
        evidence = json.loads(path.read_text(encoding="utf-8"))
        if mutation == "stale-subject":
            evidence["subject_sha256"] = judgment["subject_sha256"] = "0" * 64
        else:
            evidence["assessment"] = "REJECT"
        _json(path, evidence)
        judgment["evidence"]["sha256"] = _sha(path.read_bytes())
    else:
        path.unlink()
    delivery.save()
    with pytest.raises(InputError):
        validate_delivery(delivery.root, delivery.record)


@pytest.mark.parametrize("mutation", ["missing-record-marker", "wrong-revision", "source-traversal", "snapshot"])
def test_source_history_and_snapshot_identity_are_required(delivery: Delivery, mutation: str) -> None:
    if mutation == "missing-record-marker":
        (delivery.source / "CHANGELOG.md").write_text("# M1\n", encoding="utf-8")
    elif mutation == "wrong-revision":
        delivery.manifest["source"]["revision_ids"] = ["M2"]
    elif mutation == "source-traversal":
        delivery.manifest["source"]["files"][0]["path"] = "../other.py"
    else:
        delivery.manifest["source"]["snapshot_sha256"] = "0" * 64
    delivery.save()
    with pytest.raises(InputError):
        validate_delivery(delivery.root, delivery.record)


def test_collector_reads_history_and_carries_manifest_identity(delivery: Delivery) -> None:
    receipt = collect_deliveries(delivery.root, delivery.source)
    assert isinstance(receipt, dict)
    rendered = json.dumps(receipt)
    assert _sha(delivery.record.read_bytes()) in rendered
    assert DISPOSITION in rendered


def test_delivery_cannot_accept_a_history_path_the_collector_would_miss(delivery: Delivery) -> None:
    alternate = delivery.source / "docs/history.md"
    alternate.parent.mkdir()
    alternate.write_bytes((delivery.source / "CHANGELOG.md").read_bytes())
    delivery.manifest["source"]["history_path"] = alternate.relative_to(delivery.root).as_posix()
    delivery.save()
    with pytest.raises(InputError, match="discoverable"):
        validate_delivery(delivery.root, delivery.record)


@pytest.mark.parametrize("mutation", ["malformed-marker", "missing-record"])
def test_collector_does_not_silently_skip_broken_history_links(delivery: Delivery, mutation: str) -> None:
    history = delivery.source / "CHANGELOG.md"
    if mutation == "malformed-marker":
        history.write_text("# M1\n\nLocal delivery record: missing-backticks.json\n", encoding="utf-8")
    else:
        delivery.record.unlink()
    with pytest.raises(InputError):
        collect_deliveries(delivery.root, delivery.source)


def _intake(delivery: Delivery) -> tuple[Path, dict]:
    project = delivery.root / "tools/intent-tool-pipeline"
    project.mkdir(parents=True)
    source = project / "codex_workspace/widget"
    source.mkdir(parents=True)
    for path in delivery.source.iterdir():
        (source / path.name).write_bytes(path.read_bytes())
    delivery.source = source
    delivery.manifest["source"]["root"] = source.relative_to(delivery.root).as_posix()
    delivery.manifest["source"]["history_path"] = (source / "CHANGELOG.md").relative_to(delivery.root).as_posix()
    delivery.save()
    request = {"target": {"repository_path": "codex_workspace/widget"}, "source_context": []}
    return project, request


def test_intake_without_local_delivery_markers_preserves_existing_behavior(tmp_path: Path) -> None:
    project = tmp_path / "tools/intent-tool-pipeline"
    source = project / "source"
    source.mkdir(parents=True)
    (source / "README.md").write_text("Ordinary product without local deliveries.\n", encoding="utf-8")
    assert validate_intake_deliveries(project, {"target": {"repository_path": "source"}}) is None


@pytest.mark.parametrize("context_name,contents", [("missing.txt", None), ("stale.txt", b"changed"), ("broken.json", b"not JSON")])
def test_unrelated_legacy_source_context_keeps_its_previous_availability_rules(tmp_path: Path, context_name: str, contents: bytes | None) -> None:
    project = tmp_path / "tools/intent-tool-pipeline"
    project.mkdir(parents=True)
    if contents is not None:
        (project / context_name).write_bytes(contents)
    request = {"target": {"repository_path": "source"},
               "source_context": [{"path": context_name, "content_sha256": "0" * 64}]}
    assert validate_intake_deliveries(project, request) is None


def test_supplied_delivery_snapshot_cannot_lose_its_authoritative_history_link(delivery: Delivery) -> None:
    project, request = _intake(delivery)
    snapshot = project / "workspace/intake/local-delivery.json"
    snapshot.parent.mkdir(parents=True)
    snapshot.write_bytes(delivery.record.read_bytes())
    request["source_context"] = [{"path": snapshot.relative_to(project).as_posix(), "content_sha256": _sha(snapshot.read_bytes())}]
    (delivery.source / "CHANGELOG.md").write_text("# M1\nHistory link omitted\n", encoding="utf-8")
    with pytest.raises(InputError, match="not linked"):
        validate_intake_deliveries(project, request)


def test_supported_states_cannot_omit_each_others_prerequisites(delivery: Delivery) -> None:
    import copy
    state = copy.deepcopy(delivery.manifest["supported_states"][0])
    state["id"] = "incomplete-alternative"
    state["files"] = [item for item in state["files"] if item["path"] != "support.py"]
    delivery.manifest["supported_states"].append(state)
    delivery.save()
    with pytest.raises(InputError, match="same complete path set"):
        validate_delivery(delivery.root, delivery.record)


def test_intake_blocks_omitted_local_delivery_evidence(delivery: Delivery) -> None:
    project, request = _intake(delivery)
    with pytest.raises(InputError):
        validate_intake_deliveries(project, request)


def test_intake_requires_all_records_linked_from_authoritative_history(delivery: Delivery) -> None:
    project, request = _intake(delivery)
    second_path = delivery.record.with_name("second.json")
    second = json.loads(delivery.record.read_text(encoding="utf-8"))
    second["delivery_id"] = "widget-M2"
    second["source"]["revision_ids"] = ["M2"]
    _json(second_path, second)
    with (delivery.source / "CHANGELOG.md").open("a", encoding="utf-8") as history:
        history.write(f"\n## M2\n\nLocal delivery record: `{second_path.relative_to(delivery.root).as_posix()}`\n")
    first_snapshot = project / "workspace/intake/first.json"
    first_snapshot.parent.mkdir(parents=True)
    first_snapshot.write_bytes(delivery.record.read_bytes())
    request["source_context"] = [{
        "path": first_snapshot.relative_to(project).as_posix(),
        "content_sha256": _sha(first_snapshot.read_bytes()),
    }]
    with pytest.raises(InputError):
        validate_intake_deliveries(project, request)
    second_snapshot = first_snapshot.with_name("second.json")
    second_snapshot.write_bytes(second_path.read_bytes())
    request["source_context"].append({
        "path": second_snapshot.relative_to(project).as_posix(),
        "content_sha256": _sha(second_snapshot.read_bytes()),
    })
    receipt = validate_intake_deliveries(project, request)
    assert receipt is not None
    assert {record["delivery_id"] for record in receipt["records"]} == {"widget-M1", "widget-M2"}


def test_hash_bound_context_discovers_authoritative_source_outside_project(delivery: Delivery) -> None:
    project = delivery.root / "tools/intent-tool-pipeline"
    snapshot = project / "workspace/intake/local-delivery.json"
    snapshot.parent.mkdir(parents=True)
    snapshot.write_bytes(delivery.record.read_bytes())
    request = {
        "target": {"repository_path": "codex_workspace/future-widget"},
        "source_context": [{"path": snapshot.relative_to(project).as_posix(),
                            "content_sha256": _sha(snapshot.read_bytes())}],
    }
    receipt = validate_intake_deliveries(project, request)
    assert receipt is not None
    assert receipt["source_roots"] == ["develop/widget"]
    assert receipt["records"][0]["record_sha256"] == _sha(delivery.record.read_bytes())


@pytest.mark.parametrize("mutation", [None, "digest", "missing-file", "stale-content"])
def test_intake_requires_existing_snapshot_bound_to_discovered_record(delivery: Delivery, mutation: str | None) -> None:
    project, request = _intake(delivery)
    snapshot = project / "workspace/intake/local-delivery.json"
    snapshot.parent.mkdir(parents=True)
    snapshot.write_bytes(delivery.record.read_bytes())
    source = {"source_id": "local-delivery", "path": snapshot.relative_to(project).as_posix(),
              "content_sha256": _sha(snapshot.read_bytes()), "authority": "REFERENCE_ONLY"}
    request["source_context"] = [source]
    if mutation == "digest":
        source["content_sha256"] = "0" * 64
    elif mutation == "missing-file":
        snapshot.unlink()
    elif mutation == "stale-content":
        snapshot.write_text("{}\n", encoding="utf-8")
        source["content_sha256"] = _sha(snapshot.read_bytes())
    if mutation:
        with pytest.raises(InputError):
            validate_intake_deliveries(project, request)
    else:
        receipt = validate_intake_deliveries(project, request)
        assert isinstance(receipt, dict)
        assert DISPOSITION in json.dumps(receipt)


@pytest.mark.parametrize("include_context", [False, True])
def test_initializer_rejects_omission_or_retains_bound_intake_receipt(delivery: Delivery, include_context: bool) -> None:
    from test_build_tool_pipeline_skill import _request

    project, partial = _intake(delivery)
    request = _request()
    request["project"]["project_id"] = "widget-intake"
    request["target"]["repository_path"] = partial["target"]["repository_path"]
    request["source_context"] = []
    request["handoff"]["next_stage"] = "contract"
    if include_context:
        snapshot = project / "workspace/intake/local-delivery.json"
        snapshot.parent.mkdir(parents=True)
        snapshot.write_bytes(delivery.record.read_bytes())
        request["source_context"].append({
            "source_id": "SRC-LOCAL", "type": "FILE", "authority": "REFERENCE_ONLY",
            "description": "Pre-existing local delivery requiring governed verification.",
            "path": snapshot.relative_to(project).as_posix(),
            "content_sha256": _sha(snapshot.read_bytes()),
        })
    request_path = project / "request.json"
    _json(request_path, request)
    original_request = request_path.read_bytes()
    initializer_path = CLI.parents[2] / ".agents/skills/build-tool-pipeline/scripts/initialize_run.py"
    spec = importlib.util.spec_from_file_location("local_delivery_initializer", initializer_path)
    assert spec is not None and spec.loader is not None
    initializer = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(initializer)
    result = initializer.initialize(project, request_path, None, "2026-10-23T00:00:00+09:00")
    run = project / "workspace/build_runs/widget-intake"
    assert request_path.read_bytes() == original_request
    if not include_context:
        assert result["ok"] is False
        assert any(item["code"] == "LOCAL_DELIVERY_INTAKE" for item in result["diagnostics"])
        assert not run.exists()
        return
    assert result["ok"] is True, result
    assert (run / "00_intake/build_request.yaml").read_bytes() == original_request
    receipt = json.loads((run / "00_intake/minor_delivery_intake.json").read_text(encoding="utf-8"))
    assert receipt["records"][0]["record_sha256"] == _sha(delivery.record.read_bytes())
    assert receipt["records"][0]["eligible_baseline"] is False
    state = json.loads((run / "30_execution/run_state.json").read_text(encoding="utf-8"))
    assert "revision_baseline" not in state["control"]


def test_cli_check_and_intake_produce_reviewable_receipts(delivery: Delivery) -> None:
    check = subprocess.run(
        [sys.executable, str(CLI), "--repository-root", str(delivery.root), "check", "--record",
         delivery.record.relative_to(delivery.root).as_posix(), "--check-source"],
        capture_output=True, text=True, check=False,
    )
    assert check.returncode == 0, check.stdout + check.stderr
    assert DISPOSITION in check.stdout
    output_ref = "intake/receipt.json"
    intake = subprocess.run(
        [sys.executable, str(CLI), "--repository-root", str(delivery.root), "intake", "--source",
         "develop/widget", "--output", output_ref], capture_output=True, text=True, check=False,
    )
    assert intake.returncode == 0, intake.stdout + intake.stderr
    receipt_path = delivery.root / output_ref
    assert _sha(delivery.record.read_bytes()) in receipt_path.read_text(encoding="utf-8")
    before = receipt_path.read_bytes()
    repeated = subprocess.run(
        [sys.executable, str(CLI), "--repository-root", str(delivery.root), "intake", "--source",
         "develop/widget", "--output", output_ref], capture_output=True, text=True, check=False,
    )
    assert repeated.returncode != 0
    assert receipt_path.read_bytes() == before
