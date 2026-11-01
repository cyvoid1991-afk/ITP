"""Repository-level mutation audits around semantic-agent invocations."""

from __future__ import annotations

import base64
import json
import os
import stat
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .io_utils import (
    InputError,
    atomic_write_bytes,
    atomic_write_json,
    normalize_repository_reference,
    read_structured,
    repository_relative,
    sha256_bytes,
    sha256_file,
)
from .result import CommandResult
from .validation import semantic_artifact_owner
from .submissions import assert_plain_path, create_submission_assignment, preflight_submission_path
from .workflow import validate_run_state_context

BOUNDARY_DIRECTORY = "30_execution/role_boundary"
SEMANTIC_FINALIZE_DIRECTORY = "30_execution/semantic_finalize"


def _normalize_relative_reference(value: str) -> str:
    """Backward-compatible wrapper for the public reference normalizer."""

    return normalize_repository_reference(value, allow_empty=True)


def _normalize_roots(values: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(_normalize_relative_reference(value) for value in values))


@dataclass(frozen=True)
class BoundaryPolicy:
    """Explicit path treatment for one audited role.

    The empty protected root represents the complete run tree. More-specific
    durable, ephemeral, and excluded roots take precedence over it.
    """

    protected_roots: tuple[str, ...] = ("",)
    allowed_durable_roots: tuple[str, ...] = ()
    allowed_durable_files: tuple[str, ...] = ()
    allowed_ephemeral_roots: tuple[str, ...] = ()
    excluded_roots: tuple[str, ...] = (BOUNDARY_DIRECTORY, SEMANTIC_FINALIZE_DIRECTORY)

    def __post_init__(self) -> None:
        for field_name in (
            "protected_roots",
            "allowed_durable_roots",
            "allowed_durable_files",
            "allowed_ephemeral_roots",
            "excluded_roots",
        ):
            object.__setattr__(self, field_name, _normalize_roots(getattr(self, field_name)))
        categories = (
            self.allowed_durable_roots,
            self.allowed_ephemeral_roots,
            self.excluded_roots,
        )
        for index, roots in enumerate(categories):
            for other in categories[index + 1 :]:
                overlap = set(roots) & set(other)
                if overlap:
                    raise InputError(f"boundary policy roots overlap across categories: {sorted(overlap)}")

    @property
    def allowed_write_roots(self) -> tuple[str, ...]:
        return self.allowed_durable_roots + self.allowed_ephemeral_roots

    def as_dict(self) -> dict[str, list[str]]:
        def displayed(values: tuple[str, ...]) -> list[str]:
            return [value or "." for value in values]

        return {
            "protected_roots": displayed(self.protected_roots),
            "allowed_durable_roots": displayed(self.allowed_durable_roots),
            "allowed_durable_files": displayed(self.allowed_durable_files),
            "allowed_ephemeral_roots": displayed(self.allowed_ephemeral_roots),
            "excluded_roots": displayed(self.excluded_roots),
        }

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> BoundaryPolicy:
        fields: dict[str, tuple[str, ...]] = {}
        for field_name in (
            "protected_roots",
            "allowed_durable_roots",
            "allowed_durable_files",
            "allowed_ephemeral_roots",
            "excluded_roots",
        ):
            if field_name == "allowed_durable_files" and field_name not in value:
                fields[field_name] = ()
                continue
            if field_name not in value:
                raise InputError(f"boundary policy is missing {field_name}")
            raw = value[field_name]
            if not isinstance(raw, list) or not all(isinstance(item, str) for item in raw):
                raise InputError(f"boundary policy {field_name} must be a list of relative paths")
            fields[field_name] = tuple(raw)
        return cls(**fields)


ROLE_BOUNDARY_POLICIES: dict[str, BoundaryPolicy] = {
    "problem_framer": BoundaryPolicy(),
    "intent_realizer": BoundaryPolicy(),
    "product_contract_agent": BoundaryPolicy(),
    "independent_verifier": BoundaryPolicy(allowed_ephemeral_roots=("40_verification/probes",)),
    "explorer": BoundaryPolicy(),
}

# Backward-compatible public projection used by the CLI and existing callers.
ROLE_POLICIES: dict[str, tuple[str, ...]] = {
    role: policy.allowed_write_roots for role, policy in ROLE_BOUNDARY_POLICIES.items()
}


def _policy_for_role(role: str) -> BoundaryPolicy:
    legacy_allowed = _normalize_roots(ROLE_POLICIES[role])
    explicit = ROLE_BOUNDARY_POLICIES.get(role)
    if explicit is not None and explicit.allowed_write_roots == legacy_allowed:
        return explicit
    return BoundaryPolicy(allowed_durable_roots=legacy_allowed)


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


def _audit_id(role: str, invocation_ref: str) -> str:
    return sha256_bytes(f"{role}\0{invocation_ref}".encode("utf-8"))[:24]


def _is_reparse(stat_result: os.stat_result) -> bool:
    attributes = getattr(stat_result, "st_file_attributes", 0)
    reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
    return bool(reparse_flag and attributes & reparse_flag)


def _filesystem_path(path: Path) -> str:
    """Return an OS path that keeps deep Windows scans long-path capable."""

    value = str(path.absolute())
    if os.name != "nt" or value.startswith("\\\\?\\"):
        return value
    if value.startswith("\\\\"):
        return f"\\\\?\\UNC\\{value[2:]}"
    return f"\\\\?\\{value}"


def _resolved_path_text(path: Path) -> str:
    value = str(Path(os.path.realpath(_filesystem_path(path))))
    if value.startswith("\\\\?\\UNC\\"):
        return f"\\\\{value[8:]}"
    if value.startswith("\\\\?\\"):
        return value[4:]
    return value


def _path_is_within(path: str, root: str) -> bool:
    return root == "" or path == root or path.startswith(f"{root}/")


def _matching_root(path: str, roots: tuple[str, ...]) -> str | None:
    matches = [root for root in roots if _path_is_within(path, root)]
    return max(matches, key=len) if matches else None


def _path_class(path: str, policy: BoundaryPolicy) -> tuple[str, str | None]:
    if path in policy.allowed_durable_files:
        return "allowed_durable", path
    for category, roots in (
        ("excluded", policy.excluded_roots),
        ("allowed_ephemeral", policy.allowed_ephemeral_roots),
        ("allowed_durable", policy.allowed_durable_roots),
        ("protected", policy.protected_roots),
    ):
        matching = _matching_root(path, roots)
        if matching is not None:
            return category, matching
    return "excluded", None


def _ephemeral_scan_error_is_churn(relative: str, root: str | None, exc: OSError) -> bool:
    if root is None:
        return False
    # Any descendant can be concurrently removed or made unreadable by its
    # owning verification process. The declared root itself must stay
    # inspectable, except when it disappears altogether.
    return relative != root or isinstance(exc, FileNotFoundError)


def _snapshot(
    run_dir: Path,
    policy: BoundaryPolicy | None = None,
) -> dict[str, dict[str, Any]]:
    """Inventory a run without following reparse points.

    Protected and allowed-durable regular files are content hashed. An
    allowed-ephemeral root is identified and traversed only far enough to
    inspect reparse boundaries; ordinary descendants are not recorded or
    hashed and may churn while the scan is in progress.
    """

    effective_policy = policy or BoundaryPolicy()
    records: dict[str, dict[str, Any]] = {}
    stack: list[tuple[Path, str, str | None]] = [(run_dir, "protected", None)]
    while stack:
        directory, directory_class, ephemeral_root = stack.pop()
        directory_relative = "" if directory == run_dir else directory.relative_to(run_dir).as_posix()
        try:
            entries = sorted(os.scandir(_filesystem_path(directory)), key=lambda item: item.name)
        except OSError as exc:
            if directory_class == "allowed_ephemeral" and _ephemeral_scan_error_is_churn(
                directory_relative, ephemeral_root, exc
            ):
                continue
            raise InputError(f"cannot scan {directory}: {exc}") from exc
        for entry in entries:
            path = directory / entry.name
            relative = path.relative_to(run_dir).as_posix()
            path_class, matching_root = _path_class(relative, effective_policy)
            if path_class == "excluded":
                continue
            try:
                metadata = entry.stat(follow_symlinks=False)
            except OSError as exc:
                if path_class == "allowed_ephemeral" and _ephemeral_scan_error_is_churn(
                    relative, matching_root, exc
                ):
                    continue
                raise InputError(f"cannot stat {path}: {exc}") from exc
            mode = stat.S_IMODE(metadata.st_mode)
            if entry.is_symlink() or _is_reparse(metadata):
                try:
                    resolved_path = _resolved_path_text(path)
                except OSError as exc:
                    raise InputError(f"cannot resolve reparse path {path}: {exc}") from exc
                records[relative] = {
                    "kind": "reparse",
                    "mode": mode,
                    "resolved_path": resolved_path,
                }
            elif stat.S_ISDIR(metadata.st_mode):
                if path_class != "allowed_ephemeral" or relative == matching_root:
                    records[relative] = {"kind": "directory", "mode": mode}
                stack.append((path, path_class, matching_root))
            elif stat.S_ISREG(metadata.st_mode):
                if path_class == "allowed_ephemeral":
                    if relative == matching_root:
                        records[relative] = {"kind": "file", "mode": mode, "size": metadata.st_size}
                    continue
                try:
                    digest = sha256_file(Path(_filesystem_path(path)))
                except OSError as exc:
                    raise InputError(f"cannot hash {path}: {exc}") from exc
                records[relative] = {
                    "kind": "file",
                    "mode": mode,
                    "size": metadata.st_size,
                    "sha256": digest,
                }
                if effective_policy.allowed_durable_files:
                    # Windows DirEntry.stat may report zero links from cached
                    # enumeration metadata; lstat obtains the actual count.
                    records[relative]["link_count"] = path.lstat().st_nlink
            elif path_class != "allowed_ephemeral" or relative == matching_root:
                records[relative] = {"kind": "other", "mode": mode, "size": metadata.st_size}
    return dict(sorted(records.items()))


def _fingerprint(record: dict[str, Any]) -> tuple[Any, ...]:
    return (
        record.get("kind"),
        record.get("size"),
        record.get("sha256"),
        record.get("resolved_path"),
        record.get("mode"),
    )


def _diff(
    before: dict[str, dict[str, Any]],
    after: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    deleted = set(before) - set(after)
    created = set(after) - set(before)
    mutations: list[dict[str, Any]] = []

    created_by_identity: dict[tuple[Any, ...], list[str]] = {}
    for path in sorted(created):
        created_by_identity.setdefault(_fingerprint(after[path]), []).append(path)
    for old_path in sorted(tuple(deleted)):
        candidates = created_by_identity.get(_fingerprint(before[old_path]), [])
        if not candidates:
            continue
        new_path = candidates.pop(0)
        deleted.remove(old_path)
        created.remove(new_path)
        mutations.append({"operation": "rename", "path": old_path, "destination": new_path})

    for path in sorted(deleted):
        mutations.append({"operation": "delete", "path": path, "before": before[path]})
    for path in sorted(created):
        mutations.append({"operation": "create", "path": path, "after": after[path]})
    for path in sorted(set(before) & set(after)):
        old = before[path]
        new = after[path]
        if old == new:
            continue
        if old.get("kind") != new.get("kind"):
            operation = "overwrite"
        elif old.get("kind") == "file" and new.get("size", 0) < old.get("size", 0):
            operation = "truncate"
        else:
            operation = "modify"
        mutations.append({"operation": operation, "path": path, "before": old, "after": new})
    return sorted(mutations, key=lambda item: (item["path"], item["operation"], item.get("destination", "")))


def _path_is_allowed(path: str, allowed_roots: tuple[str, ...]) -> bool:
    try:
        normalized = _normalize_relative_reference(path)
        roots = _normalize_roots(allowed_roots)
    except InputError:
        return False
    return any(_path_is_within(normalized, root) for root in roots)


def _mutation_is_allowed(
    mutation: dict[str, Any], allowed_roots: tuple[str, ...], allowed_files: tuple[str, ...] = (),
) -> bool:
    def allowed(path: str) -> bool:
        return path in allowed_files or _path_is_allowed(path, allowed_roots)

    if not allowed(str(mutation.get("path", ""))):
        return False
    destination = mutation.get("destination")
    if isinstance(destination, str) and not allowed(destination):
        return False
    for record_name in ("before", "after"):
        record = mutation.get(record_name)
        if mutation.get("path") in allowed_files and isinstance(record, dict):
            if record.get("kind") != "file" or record.get("link_count", 1) != 1:
                return False
    return True


def _allowed_path_escapes(
    run_dir: Path,
    snapshot: dict[str, dict[str, Any]],
    allowed_roots: tuple[str, ...],
) -> list[dict[str, str]]:
    escapes: list[dict[str, str]] = []
    normalized_roots = _normalize_roots(allowed_roots)
    for path, record in snapshot.items():
        if record.get("kind") != "reparse" or not _path_is_allowed(path, normalized_roots):
            continue
        matching_root = _matching_root(_normalize_relative_reference(path), normalized_roots)
        if matching_root is None:
            continue
        # Keep the lexical allowed root anchored under the real run root. Resolving
        # the allowed root itself would let a junction at that exact path redefine
        # its own permission boundary.
        allowed_path = run_dir.resolve() / matching_root
        resolved = Path(str(record.get("resolved_path", ""))).resolve(strict=False)
        try:
            resolved.relative_to(allowed_path)
        except ValueError:
            escapes.append(
                {
                    "operation": "path_escape",
                    "path": path,
                    "resolved_path": str(resolved),
                    "allowed_root": matching_root,
                }
            )
    return escapes


def _policy_from_baseline(role: str, baseline: dict[str, Any]) -> BoundaryPolicy:
    raw_policy = baseline.get("path_policy")
    if isinstance(raw_policy, dict):
        return BoundaryPolicy.from_dict(raw_policy)
    if raw_policy is not None:
        raise InputError("boundary baseline path_policy must be an object")

    # Legacy baselines described only allowed roots and recursively hashed them.
    # Preserve that behavior so audits started before this revision can finish.
    raw_allowed = baseline.get("allowed_write_roots", ROLE_POLICIES[role])
    if not isinstance(raw_allowed, list) or not all(isinstance(item, str) for item in raw_allowed):
        raise InputError("boundary baseline allowed_write_roots must be a list of relative paths")
    return BoundaryPolicy(allowed_durable_roots=tuple(raw_allowed))


def _boundary_paths(run_dir: Path, audit_id: str) -> tuple[Path, Path, Path]:
    root = run_dir / BOUNDARY_DIRECTORY
    return (
        root / "baselines" / f"{audit_id}.json",
        root / "results" / f"{audit_id}.json",
        root / "latest.json",
    )


def boundary_initial_state(run_dir: Path, *, role: str, invocation_ref: str, baseline_sha256: str) -> dict[str, Any]:
    """Read the caller-bound original state without consuming or changing an audit."""
    baseline_path, _, _ = _boundary_paths(run_dir, _audit_id(role, invocation_ref))
    if sha256_file(baseline_path) != baseline_sha256:
        raise InputError("boundary baseline SHA-256 mismatch")
    baseline = read_structured(baseline_path)
    if not isinstance(baseline, dict) or baseline.get("role") != role or baseline.get("invocation_ref") != invocation_ref:
        raise InputError("boundary baseline role or invocation mismatch")
    backup = base64.b64decode(str(baseline.get("run_state_backup_base64", "")), validate=True)
    if sha256_bytes(backup) != baseline.get("run_state_sha256"):
        raise InputError("boundary backup SHA-256 mismatch")
    state = json.loads(backup)
    if not isinstance(state, dict):
        raise InputError("boundary backup must be a state object")
    return state


def start_role_boundary(
    project_root: Path,
    run_dir: Path,
    *,
    role: str,
    invocation_ref: str,
    artifact_key: str | None = None,
    review_event_id: str | None = None,
    input_refs: tuple[str | Path, ...] = (),
    timestamp: str | None = None,
) -> CommandResult:
    result = CommandResult(command="role-boundary start")
    from .mutation_guard import run_mutation_diagnostics

    result.extend(run_mutation_diagnostics(run_dir))
    if not result.ok:
        return result
    if role not in ROLE_POLICIES:
        result.add("BOUNDARY_ROLE", "role", f"must be one of {sorted(ROLE_POLICIES)}")
        return result
    if not invocation_ref.strip():
        result.add("INVOCATION_REF", "invocation_ref", "must be non-empty")
        return result
    state_path = run_dir / "30_execution" / "run_state.json"
    try:
        state = read_structured(state_path)
    except InputError as exc:
        result.add("STATE_READ", str(state_path), str(exc))
        return result
    diagnostics = validate_run_state_context(project_root, run_dir, state)
    if diagnostics:
        result.extend(diagnostics)
        return result
    selected = state.get("control", {}).get("semantic_role_boundary") in {"1.1", "1.2"}
    if artifact_key is not None and review_event_id is not None:
        result.add("REVIEW_ASSIGNMENT", "review_event_id", "review-event and artifact are mutually exclusive")
        return result
    if not selected and (artifact_key is not None or review_event_id is not None or input_refs):
        result.add("SUBMISSION_CONTROL", "artifact", "submission assignments require boundary control revision 1.1")
        return result
    if role in {"problem_framer", "intent_realizer"} and role != semantic_artifact_owner(state, "problem_frame"):
        result.add("SEMANTIC_ROLE", "role", "initial-stage role does not match this run's intent-realization marker")
        return result
    audit_id = _audit_id(role, invocation_ref)
    baseline_path, final_path, _ = _boundary_paths(run_dir, audit_id)
    if baseline_path.exists() or final_path.exists():
        result.add("BOUNDARY_EXISTS", audit_id, "invocation_ref has already been audited; use a unique reference")
        return result
    try:
        started_at = _timestamp(timestamp)
        policy = _policy_for_role(role)
        submission = None
        round_review = None
        procedure_binding = None
        if state.get("control", {}).get("semantic_role_boundary") == "1.2":
            from .procedures import create_procedure_binding

            # Resolve and retain mandatory procedures before any allocation.
            procedure_binding = create_procedure_binding(project_root, run_dir, state, {
                "control_revision": "1.2", "role": role, "invocation_ref": invocation_ref,
                **({"round_review": {}} if review_event_id is not None else {"submission": {"artifact_key": artifact_key}}),
            })
        if selected:
            if review_event_id is not None:
                from .continuation import create_review_assignment

                round_review = create_review_assignment(
                    project_root, run_dir, state, role=role, invocation_ref=invocation_ref,
                    event_id=review_event_id, input_refs=input_refs,
                )
                policy = BoundaryPolicy(allowed_durable_files=(round_review["path"],))
                assigned = preflight_submission_path(project_root, run_dir, round_review["path"])
                assigned.parent.mkdir(parents=True, exist_ok=True)
            elif role != "explorer" or artifact_key is not None:
                if artifact_key is None:
                    raise InputError("selected semantic role invocations require an artifact assignment")
                submission = create_submission_assignment(
                    project_root, run_dir, state, role=role, invocation_ref=invocation_ref,
                    artifact_key=artifact_key, input_refs=input_refs,
                )
                policy = BoundaryPolicy(
                    allowed_durable_files=(submission["path"],),
                    allowed_ephemeral_roots=(f"40_verification/probes/{audit_id}",)
                    if role == "independent_verifier" else (),
                )
                # Preflight every allocated parent before the first mkdir.
                assigned = preflight_submission_path(project_root, run_dir, submission["path"])
                for root in policy.allowed_ephemeral_roots:
                    preflight_submission_path(project_root, run_dir, f"{root}/probe")
                assigned.parent.mkdir(parents=True, exist_ok=True)
                for root in policy.allowed_ephemeral_roots:
                    (run_dir / root).mkdir(parents=True, exist_ok=True)
            elif input_refs:
                raise InputError("input references require an artifact assignment")
        snapshot = _snapshot(run_dir, policy)
        baseline_escapes = _allowed_path_escapes(run_dir, snapshot, policy.allowed_write_roots)
        if baseline_escapes:
            raise InputError(
                f"allowed write roots contain {len(baseline_escapes)} path escape(s); clean them before starting the audit"
            )
        state_bytes = state_path.read_bytes()
        payload = {
            "schema_version": "1.0",
            "artifact_type": "role-boundary-baseline",
            "audit_id": audit_id,
            "role": role,
            "invocation_ref": invocation_ref,
            "started_at": started_at,
            "run_dir": repository_relative(project_root, run_dir),
            "allowed_write_roots": list(policy.allowed_write_roots),
            "path_policy": policy.as_dict(),
            "snapshot": snapshot,
            "run_state_backup_base64": base64.b64encode(state_bytes).decode("ascii"),
            "run_state_sha256": sha256_bytes(state_bytes),
        }
        if selected:
            payload["control_revision"] = state["control"]["semantic_role_boundary"]
        if submission is not None:
            payload["submission"] = submission
        if round_review is not None:
            payload["round_review"] = round_review
        if procedure_binding is not None:
            payload["procedure_binding"] = procedure_binding
        atomic_write_json(baseline_path, payload)
        baseline_sha256 = sha256_file(baseline_path)
    except (InputError, OSError, UnicodeError) as exc:
        result.add("BOUNDARY_START", str(run_dir), str(exc))
        return result
    result.data = {
        "audit_id": audit_id,
        "role": role,
        "invocation_ref": invocation_ref,
        "baseline_path": repository_relative(project_root, baseline_path),
        "baseline_sha256": baseline_sha256,
        "allowed_write_roots": list(policy.allowed_write_roots),
        "path_policy": policy.as_dict(),
    }
    if submission is not None:
        result.data["submission"] = submission
        result.data["submission_path"] = repository_relative(project_root, run_dir / submission["path"])
    if round_review is not None:
        result.data["round_review"] = round_review
        result.data["review_path"] = repository_relative(project_root, run_dir / round_review["path"])
    return result


def _write_latest(latest_path: Path, role: str, record: dict[str, Any]) -> None:
    if latest_path.is_file():
        try:
            latest = read_structured(latest_path)
        except InputError as exc:
            raise InputError(f"cannot update malformed boundary latest index: {exc}") from exc
    else:
        latest = None
    if latest is not None and (not isinstance(latest, dict) or not isinstance(latest.get("roles"), dict)):
        raise InputError("cannot update malformed boundary latest index")
    if latest is None:
        latest = {"schema_version": "1.0", "artifact_type": "role-boundary-latest", "roles": {}}
    latest["roles"][role] = record
    atomic_write_json(latest_path, latest)


def finish_role_boundary(
    project_root: Path,
    run_dir: Path,
    *,
    role: str,
    invocation_ref: str,
    baseline_sha256: str,
    timestamp: str | None = None,
) -> CommandResult:
    result = CommandResult(command="role-boundary finish")
    from .finalize_journal import pending_transaction_diagnostics

    # Finishing an authenticated audit is also recovery from a role corrupting
    # or deleting state. Do not require the mutated current state to validate.
    # Unrelated unfinished registration transactions still block all writes.
    result.extend(pending_transaction_diagnostics(run_dir))
    if not result.ok:
        return result
    if role not in ROLE_POLICIES:
        result.add("BOUNDARY_ROLE", "role", f"must be one of {sorted(ROLE_POLICIES)}")
        return result
    audit_id = _audit_id(role, invocation_ref)
    baseline_path, final_path, latest_path = _boundary_paths(run_dir, audit_id)
    if not baseline_path.is_file():
        result.add("BOUNDARY_BASELINE", str(baseline_path), "baseline does not exist")
        return result
    try:
        actual_baseline_sha256 = sha256_file(baseline_path)
    except OSError as exc:
        result.add("BOUNDARY_BASELINE", str(baseline_path), str(exc))
        return result
    if actual_baseline_sha256 != baseline_sha256:
        result.add("BOUNDARY_BASELINE_IDENTITY", str(baseline_path), "baseline SHA-256 does not match the start result")
        return result
    try:
        baseline = read_structured(baseline_path)
        if not isinstance(baseline, dict):
            raise InputError("boundary baseline must be an object")
        if baseline.get("role") != role or baseline.get("invocation_ref") != invocation_ref:
            raise InputError("boundary baseline role/invocation does not match the finish request")
        if baseline.get("audit_id") != audit_id or baseline.get("run_dir") != repository_relative(project_root, run_dir):
            raise InputError("boundary baseline run/audit binding does not match the finish request")
        backup = base64.b64decode(str(baseline.get("run_state_backup_base64", "")), validate=True)
        if sha256_bytes(backup) != baseline.get("run_state_sha256"):
            raise InputError("run-state backup identity is invalid")
        initial_state = json.loads(backup)
        from .validation import validate_control_metadata

        initial_diagnostics = validate_control_metadata(initial_state)
        if initial_diagnostics:
            raise InputError("boundary original state uses unsupported or invalid control metadata")
        original_revision = initial_state.get("control", {}).get("semantic_role_boundary")
        if baseline.get("control_revision") not in {None, "1.1", "1.2"} or (
            original_revision if original_revision in {"1.1", "1.2"} else None
        ) != baseline.get("control_revision"):
            raise InputError("boundary baseline control revision does not match its original state")
        before = baseline.get("snapshot")
        if not isinstance(before, dict):
            raise InputError("boundary baseline lacks a snapshot")
        if final_path.exists():
            existing = read_structured(final_path)
            if (
                not isinstance(existing, dict)
                or existing.get("artifact_type") != "role-boundary-result"
                or existing.get("audit_id") != audit_id
                or existing.get("role") != role
                or existing.get("invocation_ref") != invocation_ref
                or existing.get("baseline_sha256") != actual_baseline_sha256
                or existing.get("status") not in {"PASS", "BOUNDARY_VIOLATION"}
            ):
                raise InputError("existing boundary result does not match the finish request")
            evidence_ref = repository_relative(project_root, final_path)
            record = {
                "audit_id": audit_id,
                "invocation_ref": invocation_ref,
                "status": existing["status"],
                "completed_at": existing.get("completed_at"),
                "evidence_ref": evidence_ref,
            }
            index_recovered = True
            if baseline.get("control_revision") in {"1.1", "1.2"} and latest_path.is_file():
                latest = read_structured(latest_path)
                if not isinstance(latest, dict) or not isinstance(latest.get("roles"), dict):
                    raise InputError("cannot update malformed boundary latest index")
                indexed = latest["roles"].get(role)
                if indexed is not None:
                    if not isinstance(indexed, dict):
                        raise InputError("cannot update malformed role record in boundary latest index")
                    # Replaying an immutable older result must never erase a
                    # later role violation (or replace another invocation).
                    index_recovered = indexed.get("audit_id") == audit_id and indexed.get("invocation_ref") == invocation_ref
            if index_recovered:
                _write_latest(latest_path, role, record)
            mutations = existing.get("mutations", [])
            unauthorized = existing.get("unauthorized_mutations", [])
            run_state_restored = existing.get("run_state_restored") is True
            status = str(existing["status"])
            result.data = {
                "audit_id": audit_id,
                "role": role,
                "invocation_ref": invocation_ref,
                "status": status,
                "evidence_ref": evidence_ref,
                "mutation_count": len(mutations) if isinstance(mutations, list) else 0,
                "unauthorized_mutation_count": len(unauthorized) if isinstance(unauthorized, list) else 0,
                "run_state_restored": run_state_restored,
                "index_recovered": index_recovered,
            }
            if not index_recovered:
                result.data["latest_index_preserved"] = True
            if status == "BOUNDARY_VIOLATION":
                result.add(
                    "BOUNDARY_VIOLATION",
                    evidence_ref,
                    f"semantic-agent invocation made {result.data['unauthorized_mutation_count']} unauthorized mutation(s)",
                )
            return result
        policy = _policy_from_baseline(role, baseline)
        completed_at = _timestamp(timestamp)
        after = _snapshot(run_dir, policy)
        mutations = _diff(before, after)
        allowed_roots = policy.allowed_write_roots
        allowed = [item for item in mutations if _mutation_is_allowed(item, allowed_roots, policy.allowed_durable_files)]
        unauthorized = [item for item in mutations if not _mutation_is_allowed(item, allowed_roots, policy.allowed_durable_files)]
        path_escapes = _allowed_path_escapes(run_dir, after, allowed_roots)
        unauthorized.extend(path_escapes)
        for relative in policy.allowed_durable_files:
            try:
                assert_plain_path(project_root, run_dir / relative)
                if (run_dir / relative).exists() and not (run_dir / relative).is_file():
                    raise InputError("assigned submission must be a regular file")
            except (InputError, OSError) as exc:
                unauthorized.append({"operation": "submission_alias", "path": relative, "reason": str(exc)})
        status = "PASS" if not unauthorized else "BOUNDARY_VIOLATION"

        state_path = run_dir / "30_execution" / "run_state.json"
        current_state_sha256 = sha256_file(state_path) if state_path.is_file() else None
        run_state_restored = False
        if status == "BOUNDARY_VIOLATION" and current_state_sha256 != baseline.get("run_state_sha256"):
            atomic_write_bytes(state_path, backup)
            run_state_restored = True

        payload = {
            "schema_version": "1.0",
            "artifact_type": "role-boundary-result",
            "audit_id": audit_id,
            "role": role,
            "invocation_ref": invocation_ref,
            "started_at": baseline.get("started_at"),
            "completed_at": completed_at,
            "status": status,
            "allowed_write_roots": list(allowed_roots),
            "path_policy": policy.as_dict(),
            "baseline_path": repository_relative(project_root, baseline_path),
            "baseline_sha256": actual_baseline_sha256,
            "mutations": mutations,
            "allowed_mutations": allowed,
            "unauthorized_mutations": unauthorized,
            "run_state_restored": run_state_restored,
        }
        atomic_write_json(final_path, payload)
        evidence_ref = repository_relative(project_root, final_path)
        result.data = {
            "audit_id": audit_id,
            "role": role,
            "invocation_ref": invocation_ref,
            "status": status,
            "evidence_ref": evidence_ref,
            "mutation_count": len(mutations),
            "unauthorized_mutation_count": len(unauthorized),
            "run_state_restored": run_state_restored,
        }
        try:
            _write_latest(
                latest_path,
                role,
                {
                    "audit_id": audit_id,
                    "invocation_ref": invocation_ref,
                    "status": status,
                    "completed_at": completed_at,
                    "evidence_ref": evidence_ref,
                },
            )
        except (InputError, OSError, UnicodeError, ValueError) as exc:
            result.add(
                "BOUNDARY_INDEX",
                str(latest_path),
                f"immutable boundary result was retained but latest index update failed: {exc}; retry finish to recover",
            )
            return result
    except (InputError, OSError, UnicodeError, ValueError) as exc:
        result.add("BOUNDARY_FINISH", str(run_dir), str(exc))
        return result

    if status == "BOUNDARY_VIOLATION":
        result.add(
            "BOUNDARY_VIOLATION",
            evidence_ref,
            f"semantic-agent invocation made {len(unauthorized)} unauthorized mutation(s)",
        )
    return result


def latest_boundary_violations(run_dir: Path) -> list[dict[str, Any]]:
    latest_path = run_dir / BOUNDARY_DIRECTORY / "latest.json"
    if not latest_path.is_file():
        return []
    try:
        latest = read_structured(latest_path)
    except InputError:
        return [{"role": "<unknown>", "status": "BOUNDARY_VIOLATION", "evidence_ref": str(latest_path)}]
    roles = latest.get("roles") if isinstance(latest, dict) else None
    if not isinstance(roles, dict):
        return [{"role": "<unknown>", "status": "BOUNDARY_VIOLATION", "evidence_ref": str(latest_path)}]
    return [dict(record, role=role) for role, record in roles.items() if isinstance(record, dict) and record.get("status") != "PASS"]


def validate_boundary_pass(
    project_root: Path,
    run_dir: Path,
    *,
    role: str,
    invocation_ref: str,
    evidence_ref: str,
) -> tuple[bool, str]:
    """Bind Root persistence to the latest successful audit for one semantic role."""

    latest_path = run_dir / BOUNDARY_DIRECTORY / "latest.json"
    try:
        latest = read_structured(latest_path)
    except InputError as exc:
        return False, str(exc)
    roles = latest.get("roles") if isinstance(latest, dict) else None
    record = roles.get(role) if isinstance(roles, dict) else None
    if not isinstance(record, dict):
        return False, f"no latest boundary result exists for {role}"
    if record.get("status") != "PASS" or record.get("invocation_ref") != invocation_ref:
        return False, "latest role-boundary result is not a matching PASS"
    recorded_ref = record.get("evidence_ref")
    if not isinstance(recorded_ref, str):
        return False, "latest boundary evidence reference is invalid"
    try:
        requested_path = Path(evidence_ref)
        requested_ref = (
            repository_relative(project_root, requested_path)
            if requested_path.is_absolute()
            else _normalize_relative_reference(evidence_ref)
        )
        canonical_recorded_ref = _normalize_relative_reference(recorded_ref)
    except (InputError, OSError, ValueError):
        return False, "boundary evidence reference must be a repository-relative path"
    if canonical_recorded_ref != requested_ref:
        return False, "boundary evidence reference does not match the latest PASS"
    candidate = project_root / requested_ref
    candidate = candidate.resolve(strict=False)
    try:
        candidate.relative_to(run_dir.resolve())
    except ValueError:
        return False, "boundary evidence escapes the run directory"
    try:
        evidence = read_structured(candidate)
    except InputError as exc:
        return False, str(exc)
    if not isinstance(evidence, dict):
        return False, "boundary evidence must be an object"
    if evidence.get("status") != "PASS" or evidence.get("role") != role or evidence.get("invocation_ref") != invocation_ref:
        return False, "boundary evidence content does not match role/invocation PASS"
    return True, "matching role-boundary PASS"
