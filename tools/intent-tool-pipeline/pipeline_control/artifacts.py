"""Root-controlled persistence and activation for semantic artifacts."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

from .boundary import boundary_initial_state, finish_role_boundary, latest_boundary_violations, validate_boundary_pass
from .io_utils import (
    InputError,
    atomic_write_bytes,
    atomic_write_json,
    normalize_repository_reference,
    parse_structured_bytes,
    read_structured,
    repository_relative,
    resolve_within,
    sha256_bytes,
    sha256_file,
)
from .result import CommandResult, Diagnostic
from .finalize_journal import (
    byte_snapshot, finish_transaction, pending_transaction_diagnostics,
    prepare_transaction, read_transaction, snapshot_bytes, transaction_path,
)
from .workflow import validate_contract_sources, validate_run_state_context
from .validation import (
    PROBLEM_FRAME_HEADINGS,
    VERIFICATION_HEADINGS,
    is_controlled_run_state,
    is_agent_artifact_run,
    markdown_metadata,
    parse_verification_results,
    semantic_artifact_owner,
    validate_markdown_headings,
    validate_product_contract_data,
    validate_control_metadata,
    validate_run_directory,
)


SEMANTIC_ARTIFACTS: dict[str, dict[str, str]] = {
    "problem_frame": {
        "artifact_id": "problem-frame",
        "semantic_owner": "problem_framer",
        "path": "10_framing/problem_frame.md",
    },
    "product_contract": {
        "artifact_id": "product-contract",
        "semantic_owner": "product_contract_agent",
        "path": "20_contract/product_contract.yaml",
    },
    "verification_report": {
        "artifact_id": "verification-report",
        "semantic_owner": "independent_verifier",
        "path": "40_verification/verification_report.md",
    },
}


def _timestamp(value: str | None) -> str:
    if value is None:
        return datetime.now(timezone.utc).isoformat(timespec="seconds")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise InputError("timestamp must be ISO 8601 with an explicit timezone") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise InputError("timestamp must include an explicit timezone")
    return value


def _validate_body(source_path: Path, artifact_key: str, payload: bytes, expected_owner: str) -> tuple[int | None, list[Any]]:
    diagnostics: list[Any] = []
    config = SEMANTIC_ARTIFACTS[artifact_key]
    try:
        text = payload.decode("utf-8")
    except UnicodeError as exc:
        return None, [Diagnostic("ARTIFACT_ENCODING", str(source_path), str(exc))]

    if artifact_key == "product_contract":
        try:
            data = parse_structured_bytes(payload, source_path)
        except InputError as exc:
            return None, [Diagnostic("PARSE_ERROR", str(source_path), str(exc))]
        diagnostics.extend(validate_product_contract_data(data))
        artifact = data.get("artifact") if isinstance(data, dict) else None
        version = artifact.get("version") if isinstance(artifact, dict) else None
        artifact_id = artifact.get("artifact_id") if isinstance(artifact, dict) else None
        semantic_owner = artifact.get("owner_role") if isinstance(artifact, dict) else None
    else:
        headings = PROBLEM_FRAME_HEADINGS if artifact_key == "problem_frame" else VERIFICATION_HEADINGS
        diagnostics.extend(validate_markdown_headings(text, headings, str(source_path)))
        metadata = markdown_metadata(text)
        version = metadata.get("version")
        artifact_id = metadata.get("artifact_id")
        semantic_owner = metadata.get("semantic_owner")
        if artifact_key == "verification_report":
            _, _, parsed = parse_verification_results(text)
            diagnostics.extend(parsed)
    if artifact_id != config["artifact_id"]:
        diagnostics.append(
            Diagnostic(
                "ARTIFACT_ID",
                str(source_path),
                f"body artifact ID must equal {config['artifact_id']!r}",
            )
        )
    if semantic_owner != expected_owner:
        diagnostics.append(
            Diagnostic(
                "SEMANTIC_OWNER",
                str(source_path),
                f"body semantic owner must equal {expected_owner!r}",
            )
        )
    if not isinstance(version, int) or isinstance(version, bool) or version < 1:
        diagnostics.append(Diagnostic("ARTIFACT_VERSION", str(source_path), "body version must be a positive integer"))
        return None, diagnostics
    return version, diagnostics


def _history_path(target: Path, version: int) -> Path:
    return target.parent / "history" / f"{target.stem}.v{version}{target.suffix}"


def _state_candidate(
    state: dict[str, Any],
    *,
    artifact_key: str,
    version: int,
    content_sha256: str,
    source_invocation_ref: str,
    boundary_evidence_ref: str,
    persisted_at: str,
) -> dict[str, Any]:
    config = SEMANTIC_ARTIFACTS[artifact_key]
    candidate = deepcopy(state)
    candidate["active_artifacts"][artifact_key] = {
        "artifact_id": config["artifact_id"],
        "version": version,
        "path": config["path"],
        "content_sha256": content_sha256,
        "semantic_owner": semantic_artifact_owner(state, artifact_key),
        "persistence_owner": "root_codex",
        "source_invocation_ref": source_invocation_ref,
        "boundary_evidence_ref": boundary_evidence_ref,
    }
    # Keep a prior PASS candidate as the revalidation basis. Only formal repair
    # clears it; the next successful verification replaces it with a new verdict.
    candidate["artifact"]["version"] += 1
    candidate["artifact"]["updated_at"] = persisted_at
    candidate["active_artifacts"]["run_state"]["version"] = candidate["artifact"]["version"]
    return candidate


def _diagnostics_payload(result: CommandResult) -> list[dict[str, str]]:
    return [item.as_dict() for item in sorted(result.diagnostics)]


def _failed_attempt_id(
    *,
    artifact_key: str,
    role: str,
    invocation_ref: str,
    baseline_sha256: str,
    source_ref: str,
    source_sha256: str | None,
    attempted_at: str,
) -> str:
    identity = "\0".join(
        (artifact_key, role, invocation_ref, baseline_sha256, source_ref, source_sha256 or "", attempted_at)
    )
    return sha256_bytes(identity.encode("utf-8"))[:24]


def _record_finalize_failure(
    result: CommandResult,
    *,
    project_root: Path,
    run_dir: Path,
    failed_step: str,
    artifact_key: str,
    role: str,
    invocation_ref: str,
    baseline_sha256: str,
    source_ref: str,
    source_sha256: str | None,
    attempted_at: str,
    boundary_info: dict[str, Any] | None,
    prior_state_path: Path | None,
    prior_state_sha256: str | None,
    prior_artifact_path: Path | None,
    prior_artifact_sha256: str | None,
    history_action: dict[str, Any],
    rollback: dict[str, Any],
) -> None:
    """Retain one immutable, deterministic failed-finalize record."""

    attempt_id = _failed_attempt_id(
        artifact_key=artifact_key,
        role=role,
        invocation_ref=invocation_ref,
        baseline_sha256=baseline_sha256,
        source_ref=source_ref,
        source_sha256=source_sha256,
        attempted_at=attempted_at,
    )
    journal_path = run_dir / "30_execution" / "semantic_finalize" / "failed_attempts" / f"{attempt_id}.json"

    def safe_ref(path: Path | None) -> str | None:
        if path is None:
            return None
        try:
            return repository_relative(project_root, path)
        except (OSError, ValueError):
            return str(path)

    payload = {
        "schema_version": "1.0",
        "artifact_type": "semantic-finalize-failed-attempt",
        "attempt_id": attempt_id,
        "attempted_at": attempted_at,
        "failed_step": failed_step,
        "request": {
            "artifact_key": artifact_key,
            "role": role,
            "invocation_ref": invocation_ref,
            "baseline_sha256": baseline_sha256,
            "source_ref": source_ref,
            "source_sha256": source_sha256,
        },
        "diagnostics": _diagnostics_payload(result),
        "boundary": deepcopy(boundary_info),
        "prior": {
            "state_path": safe_ref(prior_state_path),
            "state_sha256": prior_state_sha256,
            "artifact_path": safe_ref(prior_artifact_path),
            "artifact_sha256": prior_artifact_sha256,
        },
        "history": deepcopy(history_action),
        "rollback": deepcopy(rollback),
    }
    try:
        if journal_path.exists():
            existing = read_structured(journal_path)
            if existing != payload:
                result.add(
                    "FINALIZE_JOURNAL_CONFLICT",
                    safe_ref(journal_path) or str(journal_path),
                    "failed-attempt evidence already exists with different content and was not overwritten",
                )
                return
            journal_action = "reused"
        else:
            atomic_write_json(journal_path, payload)
            journal_action = "created"
        result.data["failed_attempt_ref"] = safe_ref(journal_path)
        result.data["failed_attempt_id"] = attempt_id
        result.data["failed_attempt_action"] = journal_action
    except Exception as exc:
        result.add(
            "FINALIZE_JOURNAL",
            safe_ref(journal_path) or str(journal_path),
            f"failed-attempt evidence could not be retained: {exc}",
        )


def _transaction_file_bytes(project_root: Path, path: Path, *, nullable: bool = False) -> bytes | None:
    from .submissions import assert_plain_path
    assert_plain_path(project_root, path)
    try:
        path.lstat()
    except FileNotFoundError:
        if nullable:
            return None
        raise
    if not path.is_file():
        raise InputError("transaction target exists but is not a plain regular file")
    return path.read_bytes()


def _recognized_transaction_targets(project_root: Path, state_path: Path, target: Path, transaction: dict[str, Any]) -> bool:
    attempt = transaction["attempts"][-1]
    return _transaction_file_bytes(project_root, state_path) in (
        snapshot_bytes(attempt["prior_state"]), snapshot_bytes(attempt["intended_state"]),
    ) and _transaction_file_bytes(project_root, target, nullable=True) in (
        snapshot_bytes(attempt["prior_artifact"], nullable=True), snapshot_bytes(attempt["intended_artifact"]),
    )


def _audited_submission_matches(evidence: dict[str, Any], submission_path: str, digest: str) -> bool:
    mutations = evidence.get("allowed_mutations")
    if not isinstance(mutations, list):
        return False
    matches = [item.get("after") for item in mutations if isinstance(item, dict) and item.get("path") == submission_path]
    return len(matches) == 1 and isinstance(matches[0], dict) and matches[0].get("kind") == "file" and matches[0].get("sha256") == digest


def _recover_selected_transaction(
    project_root: Path, run_dir: Path, tx_path: Path,
    transaction: dict[str, Any], source_path: Path,
) -> CommandResult:
    """Resolve only recorded before/after identities; never overwrite drift."""
    result = CommandResult(command="finalize-semantic-return")
    try:
        from .submissions import validate_submission_assignment
        request = transaction["request"]
        attempt = transaction["attempts"][-1]
        state_path = run_dir / "30_execution/run_state.json"
        state = read_structured(state_path)
        # Retained provenance, including the baseline's original state backup,
        # is checked even on historical replay, without consulting latest.json.
        boundary_initial_state(run_dir, role=request["role"], invocation_ref=request["invocation_ref"], baseline_sha256=request["baseline_sha256"])
        baseline = validate_submission_assignment(
            project_root, run_dir, state, role=request["role"], invocation_ref=request["invocation_ref"],
            baseline_sha256=request["baseline_sha256"], artifact_key=request["artifact_key"],
            source_path=source_path, check_live_inputs=False,
        )
        receipt = attempt["receipt"]
        evidence_path = resolve_within(project_root, project_root / receipt["boundary_evidence_ref"], must_exist=True)
        expected_evidence = run_dir / "30_execution/role_boundary/results" / tx_path.name
        if evidence_path != expected_evidence.resolve() or sha256_file(evidence_path) != attempt["boundary_sha256"]:
            raise InputError("retained boundary evidence is missing or altered")
        evidence = read_structured(evidence_path)
        if any(evidence.get(key) != value for key, value in {
            "status": "PASS", "audit_id": tx_path.stem, "role": request["role"],
            "invocation_ref": request["invocation_ref"], "baseline_sha256": request["baseline_sha256"],
        }.items()) or evidence.get("unauthorized_mutations"):
            raise InputError("retained boundary result does not attest this assignment")
        if not _audited_submission_matches(evidence, baseline["submission"]["path"], request["source_sha256"]):
            raise InputError("retained boundary does not attest the submitted bytes")
        prior_state = snapshot_bytes(attempt["prior_state"])
        intended_state = snapshot_bytes(attempt["intended_state"])
        prior_artifact = snapshot_bytes(attempt["prior_artifact"], nullable=True)
        intended_artifact = snapshot_bytes(attempt["intended_artifact"])
        intended = json.loads(intended_state)
        if intended.get("control", {}).get("semantic_registrations", {}).get(tx_path.stem) != receipt:
            raise InputError("intended state does not embed the original receipt")
        config = SEMANTIC_ARTIFACTS[request["artifact_key"]]
        target = run_dir / config["path"]
        if attempt["target_path"] != repository_relative(project_root, target):
            raise InputError("transaction canonical target does not match artifact")
        if sha256_bytes(intended_artifact) != request["source_sha256"] or sha256_file(source_path) != request["source_sha256"]:
            raise InputError("retained submission bytes differ from the registration")
        version = baseline["submission"]["artifact_version"]
        expected_receipt = {
            "artifact_key": request["artifact_key"], "artifact_ref": f"{config['artifact_id']}@{version}",
            "path": config["path"], "content_sha256": request["source_sha256"],
            "producer_role": request["role"], "submission_path": request["source_ref"],
            "source_invocation_ref": request["invocation_ref"], "baseline_sha256": request["baseline_sha256"],
            "boundary_evidence_ref": repository_relative(project_root, expected_evidence),
            "registered_at": attempt["prepared_at"], "run_state_version": intended["artifact"]["version"],
            "round_number": baseline["submission"]["round_number"],
        }
        if baseline.get("control_revision") == "1.2":
            from .procedures import result_binding

            expected_receipt["procedure_binding"] = result_binding(baseline, request["baseline_sha256"])
        if receipt != expected_receipt:
            raise InputError("registration receipt does not match retained assignment")
        history = attempt["history"]
        if history["path"] is not None:
            previous = json.loads(prior_state)["active_artifacts"][request["artifact_key"]]
            expected_history = _history_path(target, previous["version"])
            if history["path"] != repository_relative(project_root, expected_history):
                raise InputError("transaction history path mismatch")
            if expected_history.exists() and expected_history.read_bytes() != prior_artifact:
                raise InputError("immutable history differs from recorded prior bytes")
            if transaction["status"] == "COMMITTED" and not expected_history.is_file():
                raise InputError("committed history evidence is missing")

        current_state_bytes = _transaction_file_bytes(project_root, state_path)
        current_artifact_bytes = _transaction_file_bytes(project_root, target, nullable=True)
        if transaction["status"] == "PREPARED":
            if current_state_bytes not in (prior_state, intended_state) or current_artifact_bytes not in (prior_artifact, intended_artifact):
                raise InputError("recovery conflict: current state/target is neither recorded prior nor intended identity")
            if current_state_bytes == intended_state and current_artifact_bytes == intended_artifact:
                procedure_errors = []
                if baseline.get("control_revision") == "1.2":
                    from .procedures import _original_state, validate_procedure_binding

                    try:
                        validate_procedure_binding(project_root, run_dir, _original_state(baseline), baseline, current=True)
                    except (InputError, OSError, ValueError, TypeError) as exc:
                        result.add("PROCEDURE_CURRENT", str(tx_path), str(exc))
                        procedure_errors = list(result.diagnostics)
                validation = validate_run_directory(project_root, run_dir)
                if validation.ok and not procedure_errors:
                    if history["path"] is not None and not expected_history.is_file():
                        raise InputError("installed transaction is missing immutable history")
                    finish_transaction(tx_path, transaction, "COMMITTED")
                else:
                    result.extend(validation.diagnostics)
            if current_state_bytes != intended_state or current_artifact_bytes != intended_artifact or not result.ok:
                # Check both before-images before the first restoration. A stop
                # during either write leaves a recognized PREPARED combination.
                atomic_write_bytes(state_path, prior_state)
                if prior_artifact is None:
                    if target.exists():
                        target.unlink()
                else:
                    atomic_write_bytes(target, prior_artifact)
                finish_transaction(tx_path, transaction, "ROLLED_BACK", recovery="exact prior bytes restored")
                result.add("FINALIZE_RECOVERED_ROLLBACK", str(tx_path), "prior bytes restored; reissue matching finalization for a freshly snapshotted attempt")
                return result
        if state.get("control", {}).get("semantic_registrations", {}).get(tx_path.stem) != receipt:
            raise InputError("current state is missing or altered immutable registration receipt")
        active = state.get("active_artifacts", {}).get(request["artifact_key"])
        expected_active = {
            "artifact_id": config["artifact_id"], "version": version, "path": config["path"],
            "content_sha256": receipt["content_sha256"], "semantic_owner": request["role"],
            "persistence_owner": "root_codex", "source_invocation_ref": request["invocation_ref"],
            "boundary_evidence_ref": receipt["boundary_evidence_ref"],
        }
        is_current = isinstance(active, dict) and all(active.get(key) == value for key, value in expected_active.items())
        if isinstance(active, dict) and active.get("version") == version and not is_current:
            raise InputError("current active identity contradicts the immutable registration receipt")
        retained = target if is_current else _history_path(target, version)
        if not retained.is_file() or sha256_file(retained) != receipt["content_sha256"]:
            raise InputError("registered canonical/historical bytes are missing or altered")
        result.data = {
            "artifact_key": request["artifact_key"], "artifact_ref": receipt["artifact_ref"],
            "path": repository_relative(project_root, target), "content_sha256": receipt["content_sha256"],
            "semantic_owner": request["role"], "persistence_owner": "root_codex",
            "source_invocation_ref": request["invocation_ref"], "boundary_evidence_ref": receipt["boundary_evidence_ref"],
            "history_path": history["path"], "history_action": history["action"],
            "run_state_version": receipt["run_state_version"], "receipt": receipt,
            "replayed": True, "is_current": is_current,
        }
    except (InputError, OSError, ValueError, KeyError, TypeError) as exc:
        result.add("FINALIZE_RECOVERY", str(tx_path), str(exc))
    return result


def finalize_semantic_return(
    project_root: Path,
    run_dir: Path,
    *,
    artifact_key: str,
    role: str,
    invocation_ref: str,
    baseline_sha256: str,
    source_path: Path,
    expected_source_sha256: str | None = None,
    timestamp: str | None = None,
) -> CommandResult:
    """Finish an audit and activate its semantic return as one guarded transaction."""

    result = CommandResult(command="finalize-semantic-return")
    raw_source_ref = str(source_path)
    source_ref = raw_source_ref
    source_sha256: str | None = None
    state_path = run_dir / "30_execution" / "run_state.json"
    target: Path | None = None
    prior_state_bytes: bytes | None = None
    prior_target_bytes: bytes | None = None
    prior_state_sha256: str | None = None
    prior_target_sha256: str | None = None
    boundary_info: dict[str, Any] | None = None
    history_action: dict[str, Any] = {"action": "not_attempted", "path": None, "sha256": None}
    rollback: dict[str, Any] = {
        "status": "not_required",
        "state_restored": None,
        "artifact_restored": None,
        "errors": [],
    }
    selected = False
    assignment: dict[str, Any] | None = None
    transaction: dict[str, Any] | None = None
    tx_path = transaction_path(run_dir, role, invocation_ref)
    try:
        attempted_at = _timestamp(timestamp)
    except InputError as exc:
        attempted_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
        result.add("TIMESTAMP", "timestamp", str(exc))
        from .mutation_guard import run_mutation_diagnostics
        guard = run_mutation_diagnostics(run_dir)
        if guard:
            result.extend(guard)
            return result
        _record_finalize_failure(
            result,
            project_root=project_root,
            run_dir=run_dir,
            failed_step="preflight",
            artifact_key=artifact_key,
            role=role,
            invocation_ref=invocation_ref,
            baseline_sha256=baseline_sha256,
            source_ref=source_ref,
            source_sha256=None,
            attempted_at=attempted_at,
            boundary_info=None,
            prior_state_path=None,
            prior_state_sha256=None,
            prior_artifact_path=None,
            prior_artifact_sha256=None,
            history_action=history_action,
            rollback=rollback,
        )
        return result

    def fail(step: str) -> CommandResult:
        _record_finalize_failure(
            result,
            project_root=project_root,
            run_dir=run_dir,
            failed_step=step,
            artifact_key=artifact_key,
            role=role,
            invocation_ref=invocation_ref,
            baseline_sha256=baseline_sha256,
            source_ref=source_ref,
            source_sha256=source_sha256,
            attempted_at=attempted_at,
            boundary_info=boundary_info,
            prior_state_path=state_path if prior_state_bytes is not None else None,
            prior_state_sha256=prior_state_sha256,
            prior_artifact_path=target,
            prior_artifact_sha256=prior_target_sha256,
            history_action=history_action,
            rollback=rollback,
        )
        return result

    # Recovery must precede live-input/next-version checks: a committed receipt
    # remains recoverable after newer artifacts and role invocations exist.
    try:
        try:
            initial_state = boundary_initial_state(run_dir, role=role, invocation_ref=invocation_ref, baseline_sha256=baseline_sha256)
        except (InputError, OSError, ValueError):
            initial_state = None
        if initial_state is not None:
            result.extend(validate_control_metadata(initial_state))
            if not result.ok:
                return result
        try:
            current_state = read_structured(state_path)
        except InputError:
            if initial_state is None or tx_path.exists():
                raise
            current_state = initial_state
        selected = is_agent_artifact_run(initial_state if initial_state is not None else current_state)
        if tx_path.exists():
            transaction = read_transaction(tx_path)
            if not selected:
                raise InputError("selected finalization journal requires boundary control 1.1")
        if selected and expected_source_sha256 is None:
            raise InputError("expected_source_sha256 is mandatory for selected finalization")
        if expected_source_sha256 is not None and (
            not isinstance(expected_source_sha256, str) or len(expected_source_sha256) != 64
            or any(character not in "0123456789abcdef" for character in expected_source_sha256)
        ):
            raise InputError("expected_source_sha256 must be a lowercase SHA-256 value")
        if transaction is not None:
            request = transaction["request"]
            source = resolve_within(project_root, source_path, must_exist=True)
            requested = {
                "run_id": current_state["run"]["run_id"],
                "run_path": repository_relative(project_root, run_dir),
                "artifact_key": artifact_key, "role": role, "invocation_ref": invocation_ref,
                "baseline_sha256": baseline_sha256,
                "source_ref": repository_relative(project_root, source),
                "source_sha256": expected_source_sha256,
            }
            if request != requested or sha256_file(source) != expected_source_sha256:
                raise InputError("finalization invocation was reused with conflicting digest or bindings")
            last_attempt = transaction["attempts"][-1]
            retained_boundary = run_dir / "30_execution/role_boundary/results" / tx_path.name
            if sha256_file(retained_boundary) != last_attempt["boundary_sha256"]:
                raise InputError("retained transaction boundary provenance is missing or altered")
            if transaction["status"] in {"PREPARED", "COMMITTED"}:
                return _recover_selected_transaction(project_root, run_dir, tx_path, transaction, source_path if source_path.is_absolute() else project_root / source_path)
        # A different PREPARED journal, or an unsupported selector, must block
        # before even failed-attempt evidence is written.
        from .mutation_guard import run_mutation_diagnostics
        if initial_state is not None:
            # An authenticated supported start snapshot permits boundary finish
            # to account for and restore unauthorized current-state damage.
            result.extend(pending_transaction_diagnostics(run_dir))
        else:
            result.extend(run_mutation_diagnostics(run_dir))
        if not result.ok:
            return result
    except (InputError, OSError, ValueError, KeyError, TypeError) as exc:
        result.add("FINALIZE_PREFLIGHT", str(tx_path if transaction else state_path), str(exc))
        return result

    # Preflight must not consume the audit.  In particular, the requested role
    # must own this exact artifact and the returned body must be repository-held.
    config = SEMANTIC_ARTIFACTS.get(artifact_key)
    if config is None:
        result.add("ARTIFACT_KEY", "artifact", f"must be one of {sorted(SEMANTIC_ARTIFACTS)}")
        return fail("preflight")
    allowed_roles = {"problem_framer", "intent_realizer"} if artifact_key == "problem_frame" else {config["semantic_owner"]}
    if role not in allowed_roles:
        result.add(
            "SEMANTIC_ROLE",
            "role",
            f"role must equal the owner {config['semantic_owner']!r} for {artifact_key}",
        )
        return fail("preflight")
    # Resolve against the hash-bound start snapshot, not possibly tampered
    # current state: boundary finish must still restore a damaged run state.
    try:
        initial_state = boundary_initial_state(run_dir, role=role, invocation_ref=invocation_ref, baseline_sha256=baseline_sha256)
    except (InputError, OSError, ValueError):
        initial_state = None  # finish_role_boundary diagnoses invalid audit identity.
    if initial_state is not None:
        try:
            expected_owner = semantic_artifact_owner(initial_state, artifact_key)
        except InputError as exc:
            result.add("INTENT_REALIZATION_REVISION", "$.control.intent_realization", str(exc))
            return fail("preflight")
        if role != expected_owner:
            result.add("SEMANTIC_ROLE", "role", f"role must equal the owner {expected_owner!r} for {artifact_key}")
            return fail("preflight")
    if not invocation_ref.strip():
        result.add("INVOCATION_REF", "invocation_ref", "must be non-empty")
        return fail("preflight")
    if not isinstance(baseline_sha256, str) or len(baseline_sha256) != 64 or any(
        character not in "0123456789abcdef" for character in baseline_sha256
    ):
        result.add("BOUNDARY_BASELINE_IDENTITY", "baseline_sha256", "must be a lowercase SHA-256 value")
        return fail("preflight")
    try:
        contained_source = resolve_within(project_root, source_path, must_exist=True)
        source_ref = repository_relative(project_root, contained_source)
    except (InputError, OSError, ValueError) as exc:
        result.add("SOURCE_SCOPE", raw_source_ref, str(exc))
        return fail("preflight")
    target = run_dir / config["path"]
    if contained_source.resolve(strict=False) == target.resolve(strict=False):
        result.add("SOURCE_IS_CANONICAL", source_ref, "source must be a separate Root-held returned-body draft")
        return fail("preflight")
    if not contained_source.is_file():
        result.add("SOURCE_MISSING", source_ref, "returned-body source does not exist or is not a regular file")
        return fail("preflight")
    try:
        payload = contained_source.read_bytes()
        source_sha256 = sha256_bytes(payload)
    except (OSError, UnicodeError) as exc:
        result.add("FINALIZE_PREFLIGHT", source_ref, str(exc))
        return fail("preflight")
    if expected_source_sha256 is not None and source_sha256 != expected_source_sha256:
        result.add("SOURCE_SHA256", source_ref, "captured source bytes do not match expected_source_sha256")
        return fail("preflight")
    if selected:
        try:
            from .submissions import validate_submission_assignment
            assignment = validate_submission_assignment(
                project_root, run_dir, initial_state if initial_state is not None else current_state, role=role, invocation_ref=invocation_ref,
                baseline_sha256=baseline_sha256, artifact_key=artifact_key, source_path=source_path,
            )
        except (InputError, OSError, ValueError) as exc:
            result.add("SUBMISSION_ASSIGNMENT", source_ref, str(exc))
            return fail("preflight")
    try:
        boundary_result = finish_role_boundary(
            project_root,
            run_dir,
            role=role,
            invocation_ref=invocation_ref,
            baseline_sha256=baseline_sha256,
            timestamp=timestamp,
        )
    except Exception as exc:
        result.add("FINALIZE_BOUNDARY", str(run_dir), f"boundary finish raised unexpectedly: {exc}")
        return fail("boundary_finish")
    boundary_info = deepcopy(boundary_result.data) if boundary_result.data else None
    if boundary_info is not None:
        try:
            prior_state_bytes = _transaction_file_bytes(project_root, state_path) if selected else state_path.read_bytes()
            prior_state_sha256 = sha256_bytes(prior_state_bytes)
            prior_target_bytes = _transaction_file_bytes(project_root, target, nullable=True) if selected else (target.read_bytes() if target.is_file() else None)
            prior_target_sha256 = sha256_bytes(prior_target_bytes) if prior_target_bytes is not None else None
        except (InputError, OSError) as exc:
            result.add("FINALIZE_PRIOR_CAPTURE", str(run_dir), str(exc))
            return fail("prior_capture")
    if not boundary_result.ok:
        result.extend(boundary_result.diagnostics)
        return fail(
            "boundary_pass"
            if boundary_result.data.get("status") == "BOUNDARY_VIOLATION"
            else "boundary_finish"
        )
    if boundary_result.data.get("status") != "PASS":
        result.add("BOUNDARY_PASS_REQUIRED", "role-boundary", "matching role-boundary result must be PASS")
        return fail("boundary_pass")
    boundary_evidence_ref = str(boundary_result.data.get("evidence_ref", ""))
    try:
        boundary_evidence_ref = normalize_repository_reference(boundary_evidence_ref)
    except InputError as exc:
        result.add("BOUNDARY_PASS_REQUIRED", boundary_evidence_ref, str(exc))
        return fail("boundary_pass")
    boundary_ok, boundary_message = validate_boundary_pass(
        project_root,
        run_dir,
        role=role,
        invocation_ref=invocation_ref,
        evidence_ref=boundary_evidence_ref,
    )
    if not boundary_ok:
        result.add("BOUNDARY_PASS_REQUIRED", boundary_evidence_ref, boundary_message)
        return fail("boundary_pass")
    if selected:
        try:
            evidence = read_structured(project_root / boundary_evidence_ref)
            if not _audited_submission_matches(evidence, assignment["submission"]["path"], source_sha256):
                raise InputError("captured submission differs from the immutable boundary audit; producer corrections require a new invocation")
        except (InputError, OSError, ValueError) as exc:
            result.add("SUBMISSION_AUDITED_SHA256", source_ref, str(exc))
            return fail("boundary_pass")

    try:
        state = read_structured(state_path)
    except InputError as exc:
        result.add("STATE_READ", str(state_path), str(exc))
        return fail("prior_run_validation")
    if not isinstance(state, dict):
        result.add("STATE_TYPE", str(state_path), "run state must be an object")
        return fail("prior_run_validation")
    result.extend(validate_run_state_context(project_root, run_dir, state))
    if not result.ok:
        return fail("prior_run_validation")
    if not is_controlled_run_state(state):
        result.add(
            "CONTROL_REVISION_REQUIRED",
            "$.control.semantic_role_boundary",
            "semantic finalize is available only for boundary-control runs",
        )
        return fail("prior_run_validation")
    config = {**config, "semantic_owner": semantic_artifact_owner(state, artifact_key)}
    if role != config["semantic_owner"]:
        result.add("SEMANTIC_ROLE", "role", "role does not match the run's semantic owner")
        return fail("prior_run_validation")

    try:
        current_validation = validate_run_directory(project_root, run_dir)
    except Exception as exc:
        result.add("FINALIZE_PRIOR_VALIDATION", str(run_dir), str(exc))
        return fail("prior_run_validation")
    if not current_validation.ok:
        result.extend(current_validation.diagnostics)
        return fail("prior_run_validation")

    try:
        version, body_diagnostics = _validate_body(contained_source, artifact_key, payload, config["semantic_owner"])
    except Exception as exc:
        result.add("FINALIZE_BODY", source_ref, str(exc))
        return fail("body_validation")
    result.extend(body_diagnostics)
    if artifact_key == "product_contract" and result.ok:
        result.extend(validate_contract_sources(project_root, run_dir, state, parse_structured_bytes(payload, contained_source)))
        if state.get("control", {}).get("verification_validation_identity") is not None:
            result.add("REPAIR_REQUIRED", "product_contract", "a contract change after verification PASS requires formal repair before adoption")
    if not result.ok or version is None:
        return fail("body_validation")
    active = state["active_artifacts"].get(artifact_key)
    expected_version = 1 if active is None else active.get("version", 0) + 1
    if version != expected_version:
        result.add(
            "ARTIFACT_VERSION_SEQUENCE",
            source_ref,
            f"body version must be {expected_version}; found {version}",
        )
        return fail("body_validation")
    if selected:
        try:
            assignment = validate_submission_assignment(
                project_root, run_dir, state, role=role, invocation_ref=invocation_ref,
                baseline_sha256=baseline_sha256, artifact_key=artifact_key,
                source_path=source_path, artifact_version=version,
            )
        except (InputError, OSError, ValueError) as exc:
            result.add("SUBMISSION_ASSIGNMENT", source_ref, str(exc))
            return fail("body_validation")
    unresolved_boundary = latest_boundary_violations(run_dir)
    if unresolved_boundary:
        refs = [str(item.get("evidence_ref", item.get("role", "<unknown>"))) for item in unresolved_boundary]
        result.add(
            "BOUNDARY_VIOLATION",
            "30_execution/role_boundary/latest.json",
            f"active artifact changes are blocked by latest role-boundary result(s): {refs}",
        )
        return fail("boundary_pass")

    content_sha256 = sha256_bytes(payload)
    candidate = _state_candidate(
        state,
        artifact_key=artifact_key,
        version=version,
        content_sha256=content_sha256,
        source_invocation_ref=invocation_ref,
        boundary_evidence_ref=boundary_evidence_ref,
        persisted_at=attempted_at,
    )
    receipt = None
    if selected:
        receipt = {
            "artifact_key": artifact_key, "artifact_ref": f"{config['artifact_id']}@{version}",
            "path": config["path"], "content_sha256": content_sha256,
            "producer_role": role, "submission_path": source_ref,
            "source_invocation_ref": invocation_ref, "baseline_sha256": baseline_sha256,
            "boundary_evidence_ref": boundary_evidence_ref, "registered_at": attempted_at,
            "run_state_version": candidate["artifact"]["version"],
            "round_number": assignment["submission"]["round_number"],
        }
        if assignment.get("control_revision") == "1.2":
            from .procedures import result_binding

            receipt["procedure_binding"] = result_binding(assignment, baseline_sha256)
        registrations = candidate["control"]["semantic_registrations"]
        if tx_path.stem in registrations:
            result.add("SEMANTIC_REGISTRATION_CONFLICT", tx_path.stem, "immutable registration already exists")
            return fail("state_candidate")
        registrations[tx_path.stem] = receipt
    candidate_diagnostics = validate_run_state_context(project_root, run_dir, candidate)
    if candidate_diagnostics:
        result.extend(candidate_diagnostics)
        return fail("state_candidate")

    history_path: Path | None = None
    if selected:
        # Determine the immutable history action without writing anything. The
        # durable PREPARED record must precede the first history/canonical write.
        if isinstance(active, dict):
            history_path = _history_path(target, int(active["version"]))
            if prior_target_bytes is None or (history_path.exists() and history_path.read_bytes() != prior_target_bytes):
                result.add("FINALIZE_HISTORY", str(history_path), "history conflicts with prior canonical bytes")
                return fail("history")
            history_action = {"action": "reused" if history_path.exists() else "created", "path": repository_relative(project_root, history_path), "sha256": prior_target_sha256}
        else:
            history_action = {"action": "not_applicable", "path": None, "sha256": None}
        try:
            transaction = prepare_transaction(tx_path, request={
                "run_id": state["run"]["run_id"], "run_path": repository_relative(project_root, run_dir),
                "artifact_key": artifact_key, "role": role, "invocation_ref": invocation_ref,
                "baseline_sha256": baseline_sha256, "source_ref": source_ref, "source_sha256": source_sha256,
            }, attempt={
                "prepared_at": attempted_at,
                "prior_state": byte_snapshot(prior_state_bytes), "prior_artifact": byte_snapshot(prior_target_bytes),
                "intended_state": byte_snapshot((json.dumps(candidate, indent=2, ensure_ascii=False, sort_keys=False) + "\n").encode("utf-8")),
                "intended_artifact": byte_snapshot(payload), "target_path": repository_relative(project_root, target),
                "boundary_sha256": sha256_file(project_root / boundary_evidence_ref),
                "history": deepcopy(history_action), "receipt": receipt,
            })
        except Exception as exc:
            result.add("FINALIZE_TRANSACTION", str(tx_path), str(exc))
            return fail("prepare")
    try:
        if isinstance(active, dict):
            if prior_target_bytes is None:
                raise OSError("active artifact has no canonical bytes to archive")
            history_path = _history_path(target, int(active["version"]))
            history_ref = repository_relative(project_root, history_path)
            if history_path.exists():
                if not history_path.is_file() or history_path.read_bytes() != prior_target_bytes:
                    history_action = {
                        "action": "conflict",
                        "path": history_ref,
                        "sha256": sha256_file(history_path) if history_path.is_file() else None,
                    }
                    raise OSError(f"history target already exists with different bytes: {history_path}")
                history_action = {"action": "reused", "path": history_ref, "sha256": prior_target_sha256}
            else:
                written_history_sha = atomic_write_bytes(history_path, prior_target_bytes)
                if written_history_sha != prior_target_sha256:
                    raise OSError("history identity differs from prior canonical bytes")
                history_action = {"action": "created", "path": history_ref, "sha256": written_history_sha}
        else:
            history_action = {"action": "not_applicable", "path": None, "sha256": None}
    except Exception as exc:
        result.add("FINALIZE_HISTORY", str(history_path or target), str(exc))
        if selected:
            try:
                if not _recognized_transaction_targets(project_root, state_path, target, transaction):
                    raise InputError("recovery conflict: history failure left unrecognized state/target; PREPARED journal retained")
                finish_transaction(tx_path, transaction, "ROLLED_BACK", failure=str(exc))
            except Exception as journal_exc:
                result.add("FINALIZE_TRANSACTION", str(tx_path), str(journal_exc))
        return fail("history")

    state_activation_attempted = False
    try:
        written_sha256 = atomic_write_bytes(target, payload)
        if written_sha256 != content_sha256:
            raise OSError("canonical artifact identity differs from the returned body")
        state_activation_attempted = True
        atomic_write_json(state_path, candidate)
        post_validation = validate_run_directory(project_root, run_dir)
        if not post_validation.ok:
            result.extend(post_validation.diagnostics)
            raise InputError("complete post-activation run validation failed")
    except Exception as exc:
        if not result.diagnostics:
            result.add(
                "FINALIZE_STATE" if state_activation_attempted else "FINALIZE_ARTIFACT",
                str(state_path if state_activation_attempted else target),
                str(exc),
            )
            failed_step = "state_activation" if state_activation_attempted else "artifact_write"
        else:
            result.add("FINALIZE_POST_VALIDATION", str(run_dir), str(exc))
            failed_step = "post_validation"
        if selected:
            try:
                if not _recognized_transaction_targets(project_root, state_path, target, transaction):
                    raise InputError("current state/target is neither recorded prior nor intended identity")
            except (InputError, OSError, ValueError) as conflict:
                result.add("FINALIZE_RECOVERY_CONFLICT", str(tx_path), f"rollback blocked without overwriting unrelated bytes: {conflict}")
                return fail(failed_step)
        rollback_errors: list[str] = []
        state_restored = False
        artifact_restored = False
        try:
            if prior_state_bytes is None:
                raise OSError("prior run-state bytes were not captured")
            atomic_write_bytes(state_path, prior_state_bytes)
            state_restored = state_path.read_bytes() == prior_state_bytes
            if not state_restored:
                raise OSError("state rollback bytes differ from the exact prior state")
        except Exception as rollback_exc:
            rollback_errors.append(f"state rollback failed: {rollback_exc}")
        try:
            if prior_target_bytes is None:
                if target.exists():
                    if target.is_file():
                        target.unlink()
                    else:
                        raise OSError("new canonical artifact rollback target is not a file")
                artifact_restored = not target.exists()
            else:
                atomic_write_bytes(target, prior_target_bytes)
                artifact_restored = target.read_bytes() == prior_target_bytes
                if not artifact_restored:
                    raise OSError("artifact rollback bytes differ from the exact prior artifact")
        except Exception as rollback_exc:
            rollback_errors.append(f"artifact rollback failed: {rollback_exc}")
        rollback = {
            "status": "failed" if rollback_errors else "restored",
            "state_restored": state_restored,
            "artifact_restored": artifact_restored,
            "errors": rollback_errors,
        }
        if rollback_errors:
            result.add("FINALIZE_ROLLBACK", str(run_dir), "; ".join(rollback_errors))
        elif selected:
            try:
                finish_transaction(tx_path, transaction, "ROLLED_BACK", failure=str(exc), rollback=rollback)
            except Exception as journal_exc:
                result.add("FINALIZE_TRANSACTION", str(tx_path), str(journal_exc))
        return fail(failed_step)

    result.data = {
        "artifact_key": artifact_key,
        "artifact_ref": f"{config['artifact_id']}@{version}",
        "path": repository_relative(project_root, target),
        "content_sha256": content_sha256,
        "semantic_owner": config["semantic_owner"],
        "persistence_owner": "root_codex",
        "source_invocation_ref": invocation_ref,
        "boundary_evidence_ref": boundary_evidence_ref,
        "history_path": repository_relative(project_root, history_path) if history_path else None,
        "history_action": history_action["action"],
        "run_state_version": candidate["artifact"]["version"],
    }
    if selected:
        result.data.update(receipt=receipt, replayed=False, is_current=True)
        try:
            finish_transaction(tx_path, transaction, "COMMITTED", result=deepcopy(result.data))
        except Exception as exc:
            result.add("FINALIZE_TRANSACTION", str(tx_path), f"registration installed; retry matching finalization to recover receipt: {exc}")
    return result


def persist_semantic_artifact(
    project_root: Path,
    run_dir: Path,
    *,
    artifact_key: str,
    source_path: Path,
    source_invocation_ref: str,
    boundary_evidence_ref: str,
    timestamp: str | None = None,
) -> CommandResult:
    """Persist complete returned bytes and activate their identity as one Root action."""

    result = CommandResult(command="persist-artifact")
    from .mutation_guard import run_mutation_diagnostics
    result.extend(run_mutation_diagnostics(run_dir))
    if not result.ok:
        return result
    try:
        if is_agent_artifact_run(read_structured(run_dir / "30_execution/run_state.json")):
            result.add("FINALIZE_REQUIRED", "$.control.semantic_role_boundary", "selected runs must use finalize-semantic-return with the assigned source and expected digest")
            return result
    except InputError as exc:
        result.add("STATE_READ", str(run_dir), str(exc))
        return result
    config = SEMANTIC_ARTIFACTS.get(artifact_key)
    if config is None:
        result.add("ARTIFACT_KEY", "artifact", f"must be one of {sorted(SEMANTIC_ARTIFACTS)}")
        return result
    if not source_invocation_ref.strip():
        result.add("INVOCATION_REF", "source_invocation_ref", "must be non-empty")
        return result
    state_path = run_dir / "30_execution" / "run_state.json"
    try:
        state = read_structured(state_path)
    except InputError as exc:
        result.add("STATE_READ", str(state_path), str(exc))
        return result
    if not isinstance(state, dict):
        result.add("STATE_TYPE", str(state_path), "run state must be an object")
        return result
    result.extend(validate_run_state_context(project_root, run_dir, state))
    if not result.ok:
        return result
    if not is_controlled_run_state(state):
        result.add(
            "CONTROL_REVISION_REQUIRED",
            "$.control.semantic_role_boundary",
            "Root-controlled activation is available only for new boundary-control runs",
        )
        return result

    current_validation = validate_run_directory(project_root, run_dir)
    if not current_validation.ok:
        result.extend(current_validation.diagnostics)
        return result
    config = {**config, "semantic_owner": semantic_artifact_owner(state, artifact_key)}
    target = run_dir / config["path"]
    if source_path.resolve(strict=False) == target.resolve(strict=False):
        result.add("SOURCE_IS_CANONICAL", str(source_path), "source must be a separate Root-held returned-body draft")
        return result
    if not source_path.is_file():
        result.add("SOURCE_MISSING", str(source_path), "returned-body source does not exist")
        return result
    try:
        payload = source_path.read_bytes()
    except OSError as exc:
        result.add("SOURCE_READ", str(source_path), str(exc))
        return result
    version, body_diagnostics = _validate_body(source_path, artifact_key, payload, config["semantic_owner"])
    result.extend(body_diagnostics)
    if artifact_key == "product_contract" and result.ok:
        result.extend(validate_contract_sources(project_root, run_dir, state, parse_structured_bytes(payload, source_path)))
        if state.get("control", {}).get("verification_validation_identity") is not None:
            result.add("REPAIR_REQUIRED", "product_contract", "a contract change after verification PASS requires formal repair before adoption")
    if not result.ok or version is None:
        return result

    active = state["active_artifacts"].get(artifact_key)
    expected_version = 1 if active is None else active.get("version", 0) + 1
    if version != expected_version:
        result.add(
            "ARTIFACT_VERSION_SEQUENCE",
            str(source_path),
            f"body version must be {expected_version}; found {version}",
        )
        return result
    unresolved_boundary = latest_boundary_violations(run_dir)
    if unresolved_boundary:
        refs = [str(item.get("evidence_ref", item.get("role", "<unknown>"))) for item in unresolved_boundary]
        result.add(
            "BOUNDARY_VIOLATION",
            "30_execution/role_boundary/latest.json",
            f"active artifact changes are blocked by latest role-boundary result(s): {refs}",
        )
        return result
    boundary_ok, boundary_message = validate_boundary_pass(
        project_root,
        run_dir,
        role=config["semantic_owner"],
        invocation_ref=source_invocation_ref,
        evidence_ref=boundary_evidence_ref,
    )
    if not boundary_ok:
        result.add("BOUNDARY_PASS_REQUIRED", boundary_evidence_ref, boundary_message)
        return result

    try:
        persisted_at = _timestamp(timestamp)
    except InputError as exc:
        result.add("TIMESTAMP", "timestamp", str(exc))
        return result
    content_sha256 = sha256_bytes(payload)
    candidate = _state_candidate(
        state,
        artifact_key=artifact_key,
        version=version,
        content_sha256=content_sha256,
        source_invocation_ref=source_invocation_ref,
        boundary_evidence_ref=boundary_evidence_ref,
        persisted_at=persisted_at,
    )
    result.extend(validate_run_state_context(project_root, run_dir, candidate))
    if not result.ok:
        return result

    old_state_bytes = state_path.read_bytes()
    old_target_bytes = target.read_bytes() if target.is_file() else None
    history_path: Path | None = None
    try:
        if isinstance(active, dict) and old_target_bytes is not None:
            history_path = _history_path(target, int(active["version"]))
            if history_path.exists() and history_path.read_bytes() != old_target_bytes:
                raise OSError(f"history target already exists with different bytes: {history_path}")
            if not history_path.exists():
                atomic_write_bytes(history_path, old_target_bytes)
        written_sha256 = atomic_write_bytes(target, payload)
        if written_sha256 != content_sha256:
            raise OSError("canonical artifact identity differs from the returned body")
        atomic_write_json(state_path, candidate)
        post_validation = validate_run_directory(project_root, run_dir)
        if not post_validation.ok:
            raise InputError(
                "; ".join(f"{item.code} {item.path}: {item.message}" for item in post_validation.diagnostics)
            )
    except (InputError, OSError, UnicodeError) as exc:
        rollback_errors: list[str] = []
        try:
            atomic_write_bytes(state_path, old_state_bytes)
        except OSError as rollback_exc:
            rollback_errors.append(f"state rollback failed: {rollback_exc}")
        try:
            if old_target_bytes is None:
                if target.exists():
                    target.unlink()
            else:
                atomic_write_bytes(target, old_target_bytes)
        except OSError as rollback_exc:
            rollback_errors.append(f"artifact rollback failed: {rollback_exc}")
        suffix = f"; {'; '.join(rollback_errors)}" if rollback_errors else ""
        result.add("ARTIFACT_PERSIST", str(target), f"persistence failed and bounded rollback was attempted: {exc}{suffix}")
        return result

    result.data = {
        "artifact_key": artifact_key,
        "artifact_ref": f"{config['artifact_id']}@{version}",
        "path": repository_relative(project_root, target),
        "content_sha256": content_sha256,
        "semantic_owner": config["semantic_owner"],
        "persistence_owner": "root_codex",
        "source_invocation_ref": source_invocation_ref,
        "boundary_evidence_ref": boundary_evidence_ref,
        "history_path": repository_relative(project_root, history_path) if history_path else None,
        "run_state_version": candidate["artifact"]["version"],
    }
    return result
