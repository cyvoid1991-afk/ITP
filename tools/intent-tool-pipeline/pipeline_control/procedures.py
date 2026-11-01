"""Workflow-owned procedure assignments for explicitly selected control 1.2.

Snapshots authenticate original instructions; they do not attest model reading or
comprehension. Procedure roots belong to the installed control, never a product.
"""

from __future__ import annotations

import base64
import json
import re
from pathlib import Path
from typing import Any

import yaml

from .io_utils import InputError, read_structured, repository_relative, sha256_bytes, sha256_file
from .result import CommandResult, Diagnostic


REVISION = "1.2"
REGISTRY_REVISION = "ITP-20261030-ARTIFACT-S5-D1"
PROTOCOL = "itp-procedure-assignment/1.0"
TOOL_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = TOOL_ROOT.parents[1]
ENTRY = "skills/build-tool-pipeline/references/assignment-entry.md"
COMMON = (
    ("agents", ENTRY),
    ("agents", "skills/build-tool-pipeline/SKILL.md"),
    ("agents", "skills/build-tool-pipeline/references/invocation.md"),
    ("tool", "docs/contracts/README.md"),
    ("tool", "docs/contracts/agent-artifact-protocol.md"),
    ("tool", "docs/contracts/procedure-binding.md"),
    ("tool", "docs/contracts/round-recovery-clarification.md"),
    ("tool", "pipeline_control/procedures.py"),
    ("tool", "pipeline_control/validation.py"),
    ("tool", "pipeline_control/io_utils.py"),
)
# workflow, step, exact owner, ordered role-specific original procedures
REGISTRY = {
    "problem_frame": ("A", "intent_realization", "intent_realizer", (
        ("agents", "skills/intent-realization/SKILL.md"),
        ("tool", "docs/contracts/templates/problem_frame.md"),
    )),
    "product_contract": ("B", "product_contract", "product_contract_agent", (
        ("agents", "skills/author-product-contract/SKILL.md"),
        ("agents", "skills/build-tool-pipeline/references/contract-adapter.md"),
        ("tool", "docs/contracts/templates/product_contract.yaml"),
    )),
    "verification_report": ("B", "product_verification", "independent_verifier", (
        ("agents", "skills/independent-verification/SKILL.md"),
        ("agents", "skills/build-tool-pipeline/references/verification-adapter.md"),
        ("tool", "docs/contracts/templates/verification_report.md"),
    )),
    "round_review": ("B", "iteration_threshold_review", "independent_verifier", (
        ("agents", "skills/independent-verification/SKILL.md"),
        ("agents", "skills/build-tool-pipeline/references/verification-adapter.md"),
        ("tool", "pipeline_control/continuation.py"),
    )),
}


def selected(state: Any) -> bool:
    return isinstance(state, dict) and isinstance(state.get("control"), dict) and state["control"].get("semantic_role_boundary") == REVISION


def canonical_sha256(value: Any) -> str:
    return sha256_bytes(json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))


def procedure_path(namespace: str, relative: str) -> Path:
    """Resolve only exact registry spellings under the installed allowlist."""
    from .submissions import assert_plain_path

    roots = {"agents": REPOSITORY_ROOT / ".agents", "tool": TOOL_ROOT}
    allowed = set(COMMON) | {item for record in REGISTRY.values() for item in record[3]}
    if (namespace, relative) not in allowed or namespace not in roots:
        raise InputError("procedure is not in the mandatory registry allowlist")
    root = roots[namespace]
    path = root / relative
    assert_plain_path(REPOSITORY_ROOT, path, require_file=True)
    return path


def _identity(root: Path, run: Path, state: dict, baseline: dict) -> tuple[dict, tuple]:
    submission = baseline.get("submission")
    key = submission.get("artifact_key") if isinstance(submission, dict) else "round_review" if isinstance(baseline.get("round_review"), dict) else None
    if key not in REGISTRY:
        raise InputError("procedure assignment requires a registered artifact or threshold review")
    workflow, step, role, extra = REGISTRY[key]
    if baseline.get("role") != role or selected(state) is False or baseline.get("control_revision") != REVISION:
        raise InputError("procedure assignment role/control differs from the workflow registry")
    return {
        "protocol": PROTOCOL, "registry_revision": REGISTRY_REVISION,
        "workflow": workflow, "step": step, "artifact_key": key,
        "run_id": state.get("run", {}).get("run_id"),
        "run_dir": repository_relative(root, run), "role": role,
        "invocation_ref": baseline.get("invocation_ref"),
    }, COMMON + extra


def create_procedure_binding(root: Path, run: Path, state: dict, baseline: dict) -> dict:
    identity, assets = _identity(root, run, state, baseline)
    retained = []
    for namespace, relative in assets:
        payload = procedure_path(namespace, relative).read_bytes()
        # All assigned assets are original UTF-8 procedures/code, not opaque binaries.
        payload.decode("utf-8")
        retained.append({"namespace": namespace, "path": relative, "content_sha256": sha256_bytes(payload),
                         "content_base64": base64.b64encode(payload).decode("ascii")})
    return {**identity, "assets": retained}


def validate_procedure_binding(root: Path, run: Path, state: dict, baseline: dict, *, current: bool) -> dict:
    identity, assets = _identity(root, run, state, baseline)
    binding = baseline.get("procedure_binding")
    if not isinstance(binding, dict) or set(binding) != set(identity) | {"assets"} or any(binding.get(k) != v for k, v in identity.items()):
        raise InputError("procedure assignment protocol/registry/workflow/step/run/role/invocation mismatch")
    records = binding.get("assets")
    if not isinstance(records, list) or len(records) != len(assets):
        raise InputError("procedure assignment mandatory asset count mismatch")
    for record, (namespace, relative) in zip(records, assets):
        if not isinstance(record, dict) or set(record) != {"namespace", "path", "content_sha256", "content_base64"} or record.get("namespace") != namespace or record.get("path") != relative:
            raise InputError("procedure assignment mandatory asset membership/order mismatch")
        try:
            payload = base64.b64decode(record["content_base64"], validate=True)
            payload.decode("utf-8")
        except (ValueError, TypeError, UnicodeError) as exc:
            raise InputError("procedure assignment retained bytes are malformed") from exc
        if sha256_bytes(payload) != record.get("content_sha256"):
            raise InputError("procedure assignment retained bytes/hash mismatch")
        if current and sha256_file(procedure_path(namespace, relative)) != record["content_sha256"]:
            raise InputError(f"mandatory procedure changed; issue a fresh assignment: {namespace}:{relative}")
    return binding


def result_binding(baseline: dict, baseline_sha256: str) -> dict:
    return {"control_revision": REVISION, "assignment_sha256": baseline_sha256,
            "procedure_sha256": canonical_sha256(baseline["procedure_binding"])}


def _unique_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise InputError(f"duplicate structured key: {key}")
        result[key] = value
    return result


class _UniqueLoader(yaml.SafeLoader):
    pass


def _yaml_mapping(loader, node):
    loader.flatten_mapping(node)
    return _unique_pairs((loader.construct_object(k), loader.construct_object(v)) for k, v in node.value)


_UniqueLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _yaml_mapping)


def validate_result_binding(payload: bytes, path: Path, expected: dict) -> dict:
    """Parse captured bytes once for binding; reject all ambiguous metadata."""
    try:
        text = payload.decode("utf-8")
        if path.suffix.lower() == ".md":
            markers = re.findall(r"<!--\s*procedure-binding\s*:", text)
            comments = re.findall(r"<!--\s*procedure-binding\s*:\s*(.*?)-->", text, re.DOTALL)
            if len(markers) != 1 or len(comments) != 1:
                raise InputError("Markdown requires exactly one procedure-binding comment")
            binding = json.loads(comments[0], object_pairs_hook=_unique_pairs)
        else:
            data = json.loads(text, object_pairs_hook=_unique_pairs) if path.suffix.lower() == ".json" else yaml.load(text, Loader=_UniqueLoader)
            binding = data.get("procedure_binding") if isinstance(data, dict) else None
        if not isinstance(binding, dict) or binding != expected:
            raise InputError("result procedure_binding is missing, unsupported or differs from its assignment")
        return binding
    except (ValueError, TypeError, UnicodeError, yaml.YAMLError) as exc:
        raise InputError(f"invalid result procedure binding: {exc}") from exc


def _original_state(baseline: dict) -> dict:
    try:
        payload = base64.b64decode(baseline["run_state_backup_base64"], validate=True)
        if sha256_bytes(payload) != baseline.get("run_state_sha256"):
            raise InputError("procedure original state backup hash mismatch")
        state = json.loads(payload, object_pairs_hook=_unique_pairs)
        if not isinstance(state, dict):
            raise InputError("procedure original state backup must be an object")
        return state
    except (ValueError, KeyError, TypeError) as exc:
        raise InputError("procedure original state backup is invalid") from exc


def active_procedure_diagnostics(root: Path, run: Path, state: dict, *, current: bool = False) -> list[Diagnostic]:
    """Authenticate active provenance, including prospective pre-install state.

The exact producer submission remains available before canonical installation;
validate-run separately authenticates installed canonical bytes afterwards.
"""
    if not selected(state):
        return []
    from .submissions import validate_submission_assignment, submission_audit_id

    diagnostics = []
    for key in ("problem_frame", "product_contract", "verification_report"):
        entry = state.get("active_artifacts", {}).get(key)
        if not isinstance(entry, dict):
            continue
        latest = state.get("control", {}).get("latest_verification_result")
        current_for_entry = current
        pending_verification = any(s.get("id") == "verification" and s.get("status") == "IN_PROGRESS"
                                   for s in state.get("stages", []) if isinstance(s, dict))
        if current and key == "verification_report" and isinstance(latest, dict) and (
            state.get("run", {}).get("current_stage") == "repair" or pending_verification
        ) and latest.get("report_ref") == f"verification-report@{entry.get('version')}":
            # The previous verdict is retained evidence during reserved repair
            # and re-verification; only the fresh report grants verdict authority.
            current_for_entry = False
        try:
            audit = submission_audit_id(entry["semantic_owner"], entry["source_invocation_ref"])
            receipt = state["control"]["semantic_registrations"][audit]
            source = root / receipt["submission_path"]
            baseline = validate_submission_assignment(root, run, state, role=entry["semantic_owner"],
                invocation_ref=entry["source_invocation_ref"], baseline_sha256=receipt["baseline_sha256"],
                artifact_key=key, source_path=source, artifact_version=entry["version"], check_live_inputs=False)
            validate_procedure_binding(root, run, _original_state(baseline), baseline, current=current_for_entry)
            expected = result_binding(baseline, receipt["baseline_sha256"])
            if receipt.get("procedure_binding") != expected or sha256_file(source) != receipt["content_sha256"]:
                raise InputError("active receipt/submission procedure identity mismatch")
            validate_result_binding(source.read_bytes(), source, expected)
            evidence_path = run / "30_execution/role_boundary/results" / f"{audit}.json"
            if receipt["boundary_evidence_ref"] != repository_relative(root, evidence_path):
                raise InputError("active procedure boundary reference differs from its assigned audit")
            evidence = read_structured(evidence_path)
            if not isinstance(evidence, dict) or any(evidence.get(k) != v for k, v in {
                "audit_id": audit, "role": entry["semantic_owner"], "invocation_ref": entry["source_invocation_ref"],
                "baseline_sha256": receipt["baseline_sha256"], "status": "PASS",
            }.items()) or evidence.get("unauthorized_mutations") != []:
                raise InputError("active procedure audit does not bind its retained assignment")
            if not any(isinstance(m, dict) and m.get("path") == baseline["submission"]["path"]
                       and isinstance(m.get("after"), dict) and m["after"].get("sha256") == receipt["content_sha256"]
                       for m in evidence.get("allowed_mutations", [])):
                raise InputError("active procedure audit does not attest the submitted bytes")
        except (InputError, OSError, ValueError, KeyError, TypeError) as exc:
            diagnostics.append(Diagnostic("PROCEDURE_ACTIVE", f"active_artifacts.{key}", str(exc)))
    return diagnostics


def load_role_assignment(root: Path, run: Path, *, role: str, invocation_ref: str, baseline_sha256: str) -> CommandResult:
    """Read-only current bootstrap. Loading never creates boundary or output files."""
    from .submissions import submission_audit_id, validate_submission_assignment

    result = CommandResult(command="load-role-assignment")
    try:
        path = run / "30_execution/role_boundary/baselines" / f"{submission_audit_id(role, invocation_ref)}.json"
        if sha256_file(path) != baseline_sha256:
            raise InputError("assignment baseline SHA-256 mismatch")
        baseline = read_structured(path)
        state = read_structured(run / "30_execution/run_state.json")
        if not selected(state) or baseline.get("role") != role or baseline.get("invocation_ref") != invocation_ref or baseline.get("run_dir") != repository_relative(root, run):
            raise InputError("assignment run/role/invocation/control mismatch")
        binding = validate_procedure_binding(root, run, _original_state(baseline), baseline, current=True)
        assignment = baseline.get("submission") or baseline.get("round_review")
        if "submission" in baseline:
            validate_submission_assignment(root, run, state, role=role, invocation_ref=invocation_ref,
                baseline_sha256=baseline_sha256, artifact_key=assignment["artifact_key"],
                source_path=run / assignment["path"], require_result=False)
        else:
            from .continuation import _current_inputs
            from .boundary import BoundaryPolicy
            audit = submission_audit_id(role, invocation_ref)
            expected_path = f"40_verification/probes/{audit}/round-review.json"
            if assignment.get("path") != expected_path or baseline.get("path_policy") != BoundaryPolicy(allowed_durable_files=(expected_path,)).as_dict():
                raise InputError("review assignment must grant only its exact registered output")
            _current_inputs(root, run, state, assignment, invocation_ref)
        # Check every additional input as well as the derived mandatory set.
        from .submissions import assert_plain_path
        for record in assignment["inputs"]:
            source = root / record["path"]
            assert_plain_path(root, source)
            if record["availability"] == "PRESENT":
                if not source.is_file() or sha256_file(source) != record.get("content_sha256"):
                    raise InputError("assigned input changed")
            elif source.exists():
                raise InputError("assigned missing input appeared")
        result.data = {
            "baseline_path": repository_relative(root, path), "baseline_sha256": baseline_sha256,
            "procedure_binding": binding, "required_result_binding": result_binding(baseline, baseline_sha256),
            "assignment": assignment, "inputs": assignment["inputs"],
            "permitted_outputs": baseline["path_policy"],
            "output_path": str(run / assignment["path"]),
            "procedures": [{"namespace": r["namespace"], "path": str(procedure_path(r["namespace"], r["path"])),
                            "content_sha256": r["content_sha256"],
                            "body": base64.b64decode(r["content_base64"]).decode("utf-8")} for r in binding["assets"]],
            "evidence_level": "ASSIGNMENT_GENERATED; loading/comprehension require separate observed evidence",
        }
    except (InputError, OSError, ValueError, KeyError, TypeError) as exc:
        result.add("PROCEDURE_ASSIGNMENT", str(run), str(exc))
    return result
