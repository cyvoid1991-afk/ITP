"""Bounded write-ahead records for the existing semantic finalizer.

Terminal attempts remain evidence. A retry appends fresh before-images instead
of restoring a terminal attempt's old snapshot over intervening Root work.
"""

from __future__ import annotations

import base64
from copy import deepcopy
from pathlib import Path
from typing import Any

from .io_utils import InputError, atomic_write_json, read_structured, sha256_bytes
from .result import Diagnostic


DIRECTORY = "30_execution/semantic_finalize/tx"
STATUSES = {"PREPARED", "COMMITTED", "ROLLED_BACK"}


def transaction_path(run_dir: Path, role: str, invocation_ref: str) -> Path:
    audit_id = sha256_bytes(f"{role}\0{invocation_ref}".encode("utf-8"))[:24]
    return run_dir / DIRECTORY / f"{audit_id}.json"


def byte_snapshot(payload: bytes | None) -> dict[str, Any]:
    return {
        "base64": base64.b64encode(payload).decode("ascii") if payload is not None else None,
        "sha256": sha256_bytes(payload) if payload is not None else None,
    }


def snapshot_bytes(snapshot: Any, *, nullable: bool = False) -> bytes | None:
    if not isinstance(snapshot, dict) or set(snapshot) != {"base64", "sha256"}:
        raise InputError("invalid finalization backup record")
    if snapshot["base64"] is None and snapshot["sha256"] is None and nullable:
        return None
    try:
        payload = base64.b64decode(snapshot["base64"], validate=True)
    except (ValueError, TypeError) as exc:
        raise InputError("invalid finalization backup encoding") from exc
    if sha256_bytes(payload) != snapshot["sha256"]:
        raise InputError("finalization backup digest mismatch")
    return payload


def read_transaction(path: Path) -> dict[str, Any]:
    record = read_structured(path)
    if not isinstance(record, dict) or record.get("schema_version") != "1.0" or record.get("artifact_type") != "semantic-finalize-transaction":
        raise InputError("invalid finalization transaction format")
    attempts = record.get("attempts")
    if not isinstance(attempts, list) or not attempts or not isinstance(record.get("status"), str) or record["status"] not in STATUSES:
        raise InputError("invalid finalization transaction status/attempts")
    for number, attempt in enumerate(attempts, 1):
        if not isinstance(attempt, dict) or attempt.get("number") != number or not isinstance(attempt.get("status"), str) or attempt["status"] not in STATUSES:
            raise InputError("invalid finalization attempt sequence")
        if number < len(attempts) and attempt["status"] != "ROLLED_BACK":
            raise InputError("only rolled-back attempts may precede another attempt")
        for field in ("prior_state", "intended_state", "intended_artifact"):
            snapshot_bytes(attempt.get(field))
        snapshot_bytes(attempt.get("prior_artifact"), nullable=True)
    if attempts[-1]["status"] != record["status"]:
        raise InputError("finalization transaction/attempt status mismatch")
    return record


def pending_transaction_diagnostics(run_dir: Path) -> list[Diagnostic]:
    """Read-only guard used before unrelated run-mutating entry points."""
    diagnostics = []
    for path in sorted((run_dir / DIRECTORY).glob("*.json")):
        try:
            record = read_transaction(path)
            if record["status"] == "PREPARED":
                diagnostics.append(Diagnostic("FINALIZE_TRANSACTION_PENDING", str(path), "finish the matching finalize-semantic-return recovery before other mutations"))
        except (InputError, OSError, ValueError) as exc:
            diagnostics.append(Diagnostic("FINALIZE_TRANSACTION_INVALID", str(path), str(exc)))
    return diagnostics


def prepare_transaction(path: Path, *, request: dict[str, Any], attempt: dict[str, Any]) -> dict[str, Any]:
    if path.exists():
        record = read_transaction(path)
        if record.get("request") != request or record["status"] != "ROLLED_BACK":
            raise InputError("conflicting finalization request or nonterminal transaction")
        record = deepcopy(record)
    else:
        record = {"schema_version": "1.0", "artifact_type": "semantic-finalize-transaction", "request": deepcopy(request), "attempts": []}
    attempt = deepcopy(attempt)
    attempt.update(number=len(record["attempts"]) + 1, status="PREPARED")
    record["attempts"].append(attempt)
    record["status"] = "PREPARED"
    atomic_write_json(path, record)
    return record


def finish_transaction(path: Path, record: dict[str, Any], status: str, **outcome: Any) -> None:
    if status not in {"COMMITTED", "ROLLED_BACK"}:
        raise InputError("invalid terminal finalization status")
    candidate = deepcopy(record)
    candidate["status"] = status
    candidate["attempts"][-1].update(status=status, **outcome)
    atomic_write_json(path, candidate)
