"""Existing-artifact routing and consumed-input currency for the two workflows."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from .io_utils import InputError, normalize_repository_reference, parse_structured_bytes, read_structured, resolve_within, sha256_bytes, sha256_file
from .result import Diagnostic


def _mapping(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _records(value: Any) -> list[dict[str, Any]]:
    return [item for item in value if isinstance(item, dict)] if isinstance(value, list) else []


def entry_context(project_root: Path, run_dir: Path, state: Any) -> tuple[bool, list[Diagnostic]]:
    """Derive direct intake only from the canonical, identity-bound request."""
    diagnostics: list[Diagnostic] = []
    if not isinstance(state, dict):
        return False, diagnostics
    active = _mapping(state.get("active_artifacts"))
    entry = active.get("build_request")
    canonical = (run_dir / "00_intake/build_request.yaml").resolve()
    try:
        payload = canonical.read_bytes()
        request = parse_structured_bytes(payload, canonical)
    except (InputError, OSError) as exc:
        # Ordinary missing-file diagnostics belong to validate-run. Without
        # readable request context, the strict legacy prerequisites still apply.
        if isinstance(entry, dict) and "content_sha256" in entry:
            diagnostics.append(Diagnostic("INTAKE_IDENTITY", "active_artifacts.build_request", str(exc)))
        return False, diagnostics
    handoff = request.get("handoff") if isinstance(request, dict) else None
    direct = isinstance(handoff, dict) and handoff.get("next_stage") == "contract"
    digest = entry.get("content_sha256") if isinstance(entry, dict) else None
    bound = isinstance(digest, str) and re.fullmatch(r"[0-9a-f]{64}", digest) is not None
    if direct or (isinstance(entry, dict) and "content_sha256" in entry):
        if not bound:
            diagnostics.append(Diagnostic("INTAKE_IDENTITY", "active_artifacts.build_request", "direct intake requires a SHA-256-bound request"))
        else:
            try:
                raw = normalize_repository_reference(entry.get("path"))
                candidates = {(project_root / raw).resolve(), (run_dir / raw).resolve()}
                if canonical not in candidates or sha256_bytes(payload) != digest:
                    raise InputError("active request path or SHA-256 differs from the canonical intake")
            except (InputError, OSError, TypeError) as exc:
                diagnostics.append(Diagnostic("INTAKE_IDENTITY", "active_artifacts.build_request", str(exc)))
    if direct:
        from .validation import is_controlled_run_state

        stages = {s["id"]: s for s in _records(state.get("stages")) if isinstance(s.get("id"), str)}
        framing = stages.get("framing", {})
        gates = {g["id"]: g for g in _records(state.get("gates")) if isinstance(g.get("id"), str)}
        gate_id = framing.get("gate_id")
        gate = gates.get(gate_id, {}) if isinstance(gate_id, str) else {}
        if (
            not is_controlled_run_state(state)
            or framing.get("status") != "PENDING"
            or gate.get("status", "PENDING") != "PENDING"
            or active.get("problem_frame") is not None
            or _mapping(state.get("run")).get("current_stage") == "framing"
        ):
            diagnostics.append(Diagnostic("DIRECT_INTAKE_STATE", "stages.framing", "direct intake requires controlled provenance, unused PENDING framing and no active frame"))
    return direct, diagnostics


def validate_run_state_context(project_root: Path, run_dir: Path, state: Any) -> list[Diagnostic]:
    """Keep pure state validation strict unless authoritative context selects B."""
    from .validation import is_agent_artifact_run, validate_run_state_data

    direct, diagnostics = entry_context(project_root, run_dir, state)
    diagnostics += validate_run_state_data(state, direct_entry=direct)
    if not diagnostics and is_agent_artifact_run(state):
        from .rounds import validate_round_context
        from .continuation import validate_continuation_history

        diagnostics += validate_round_context(project_root, run_dir, state)
        if not diagnostics:
            diagnostics += validate_continuation_history(project_root, run_dir, state)
        if not diagnostics:
            from .procedures import active_procedure_diagnostics

            diagnostics += active_procedure_diagnostics(project_root, run_dir, state)
    return diagnostics


def validate_contract_sources(
    project_root: Path, run_dir: Path, state: dict[str, Any], contract: Any = None
) -> list[Diagnostic]:
    """Check consumed versions/hashes without making intermediate repair invalid.

    New identity-bound intakes require source identities. Historical unbound
    requests retain their original contract interface. Call on adoption and
    progression, not on every structurally valid intermediate state.
    """
    direct, diagnostics = entry_context(project_root, run_dir, state)
    if diagnostics:
        return diagnostics
    active = state.get("active_artifacts", {})
    request_entry = active.get("build_request")
    if not isinstance(request_entry, dict) or "content_sha256" not in request_entry:
        return []
    try:
        path = run_dir / "00_intake/build_request.yaml"
        payload = path.read_bytes()
        request = parse_structured_bytes(payload, path)
        if sha256_bytes(payload) != request_entry["content_sha256"]:
            raise InputError("request changed while checking consumed inputs")
    except (InputError, OSError) as exc:
        return [Diagnostic("INTAKE_IDENTITY", "active_artifacts.build_request", str(exc))]
    for source in _records(_mapping(request).get("source_context")):
        if "content_sha256" not in source:
            continue
        try:
            digest = source["content_sha256"]
            if not isinstance(digest, str) or re.fullmatch(r"[0-9a-f]{64}", digest) is None:
                raise InputError("snapshot must declare a lowercase SHA-256")
            path = resolve_within(project_root, source.get("path"), must_exist=True)
            if not path.is_file() or sha256_file(path) != digest:
                raise InputError("referenced intent/delegation snapshot differs from its declared identity")
        except (InputError, OSError, TypeError) as exc:
            diagnostics.append(Diagnostic("HANDOFF_SOURCE_IDENTITY", str(source.get("source_id", "source_context")), str(exc)))
    if contract is None:
        try:
            contract = read_structured(run_dir / "20_contract/product_contract.yaml")
        except InputError as exc:
            return [Diagnostic("CONTRACT_SOURCE_IDENTITY", "product_contract", str(exc))]
    sources = contract.get("source_artifacts") if isinstance(contract, dict) else None
    if not isinstance(sources, list):
        return [Diagnostic("CONTRACT_SOURCE_IDENTITY", "source_artifacts", "must list the current consumed input identities")]
    required = ["build_request"] if direct else ["build_request", "problem_frame"]
    for key in required:
        entry = active.get(key)
        artifact_id = key.replace("_", "-")
        matches = [s for s in sources if isinstance(s, dict) and s.get("artifact_id") == artifact_id]
        if len(matches) != 1 or not isinstance(entry, dict):
            diagnostics.append(Diagnostic("CONTRACT_SOURCE_IDENTITY", f"source_artifacts.{artifact_id}", "must identify the active input exactly once"))
            continue
        source = matches[0]
        version = source.get("version")
        if type(version) is not int or version < 1 or version != entry.get("version") or source.get("content_sha256") != entry.get("content_sha256") or not entry.get("content_sha256"):
            diagnostics.append(Diagnostic("CONTRACT_SOURCE_IDENTITY", f"source_artifacts.{artifact_id}", "consumed version/SHA-256 must match the active input"))
    if direct and any(isinstance(s, dict) and s.get("artifact_id") == "problem-frame" for s in sources):
        diagnostics.append(Diagnostic("CONTRACT_SOURCE_IDENTITY", "source_artifacts.problem-frame", "direct intake must not claim a nonexistent Realizer input"))
    return diagnostics
