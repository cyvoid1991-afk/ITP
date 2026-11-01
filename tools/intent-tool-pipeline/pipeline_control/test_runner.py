"""Shell-free deterministic test-plan execution and evidence capture."""

from __future__ import annotations

import subprocess
import hashlib
import json
import re
import secrets
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .io_utils import InputError, atomic_write_json, read_structured, repository_relative, resolve_within, sha256_file
from .result import CommandResult
from .mutation_guard import run_forward_diagnostics


ATTEMPT_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,95}$")


def _new_attempt_id() -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    return f"{stamp}-{secrets.token_hex(4)}"


def _validate_plan(data: Any, result: CommandResult, project_root: Path) -> list[dict[str, Any]]:
    if not isinstance(data, dict):
        result.add("TEST_PLAN_TYPE", "$", "test plan must be an object/mapping")
        return []
    if str(data.get("schema_version", "")).split(".", 1)[0] != "1":
        result.add("SCHEMA_UNSUPPORTED", "$.schema_version", "test plan must use schema version 1.x")
    commands = data.get("commands")
    if not isinstance(commands, list) or not commands:
        result.add("TEST_COMMANDS", "$.commands", "must contain at least one command")
        return []
    seen: set[str] = set()
    valid: list[dict[str, Any]] = []
    for index, value in enumerate(commands):
        path = f"$.commands[{index}]"
        if not isinstance(value, dict):
            result.add("TEST_COMMAND_TYPE", path, "must be an object/mapping")
            continue
        identifier = value.get("id")
        if not isinstance(identifier, str) or not identifier.strip():
            result.add("TEST_COMMAND_ID", f"{path}.id", "must be a non-empty string")
        elif identifier in seen:
            result.add("ID_DUPLICATE", f"{path}.id", f"duplicate command ID {identifier}")
        else:
            seen.add(identifier)
        argv = value.get("argv")
        if not isinstance(argv, list) or not argv or any(not isinstance(item, str) or not item for item in argv):
            result.add("TEST_ARGV", f"{path}.argv", "must be a non-empty array of non-empty strings")
        expected = value.get("expected_exit_codes", [0])
        if (
            not isinstance(expected, list)
            or not expected
            or any(not isinstance(item, int) or isinstance(item, bool) for item in expected)
        ):
            result.add("TEST_EXPECTED_EXIT", f"{path}.expected_exit_codes", "must be a non-empty array of integers")
        timeout = value.get("timeout_seconds", 300)
        if not isinstance(timeout, (int, float)) or isinstance(timeout, bool) or timeout <= 0 or timeout > 3600:
            result.add("TEST_TIMEOUT", f"{path}.timeout_seconds", "must be greater than 0 and at most 3600")
        cwd = value.get("cwd", ".")
        if not isinstance(cwd, str) or not cwd:
            result.add("TEST_CWD", f"{path}.cwd", "must be a non-empty project-relative path")
        elif Path(cwd).is_absolute():
            result.add("TEST_CWD", f"{path}.cwd", "must be project-relative")
        artifact_paths = value.get("artifact_paths")
        if not isinstance(artifact_paths, list) or any(not isinstance(item, str) or not item for item in artifact_paths):
            result.add("TEST_ARTIFACT_PATHS", f"{path}.artifact_paths", "must be an array of repository-relative path strings; use [] when none")
        else:
            for artifact_index, artifact_path in enumerate(artifact_paths):
                if Path(artifact_path).is_absolute():
                    result.add("TEST_ARTIFACT_PATHS", f"{path}.artifact_paths[{artifact_index}]", "must be project-relative")
                    continue
                try:
                    resolve_within(project_root, artifact_path)
                except InputError as exc:
                    result.add("TEST_ARTIFACT_PATHS", f"{path}.artifact_paths[{artifact_index}]", str(exc))
        valid.append(value)
    return valid


def _artifact_snapshot(project_root: Path, raw_path: str) -> dict[str, Any]:
    path = resolve_within(project_root, raw_path)
    record: dict[str, Any] = {
        "path": repository_relative(project_root, path),
        "exists": path.exists(),
    }
    if not path.exists():
        record["kind"] = "MISSING"
        return record
    if path.is_file():
        record.update({"kind": "FILE", "size_bytes": path.stat().st_size, "sha256": sha256_file(path)})
        return record
    if path.is_dir():
        entries = []
        for child in sorted((item for item in path.rglob("*") if item.is_file() and not item.is_symlink()), key=lambda item: item.relative_to(path).as_posix()):
            entries.append(
                {
                    "path": child.relative_to(path).as_posix(),
                    "size_bytes": child.stat().st_size,
                    "sha256": sha256_file(child),
                }
            )
        encoded = json.dumps(entries, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode("utf-8")
        record.update(
            {
                "kind": "DIRECTORY",
                "entry_count": len(entries),
                "tree_sha256": hashlib.sha256(encoded).hexdigest(),
            }
        )
        return record
    record["kind"] = "OTHER"
    return record


def run_test_plan(
    project_root: Path,
    run_dir: Path,
    plan_path: Path,
    *,
    output_path: Path | None = None,
    timestamp: str | None = None,
    attempt_id: str | None = None,
) -> CommandResult:
    result = CommandResult(command="run-tests")
    result.extend(run_forward_diagnostics(project_root, run_dir, allow_missing_state=True))
    if not result.ok:
        return result
    if not plan_path.is_file():
        result.add("TEST_PLAN_MISSING", str(plan_path), "test plan file does not exist")
        return result
    try:
        data = read_structured(plan_path)
    except InputError as exc:
        result.add("PARSE_ERROR", str(plan_path), str(exc))
        return result
    commands = _validate_plan(data, result, project_root)
    if not result.ok:
        return result

    records: list[dict[str, Any]] = []
    for index, command in enumerate(commands):
        identifier = command["id"]
        try:
            cwd = resolve_within(project_root, command.get("cwd", "."), must_exist=True)
        except InputError as exc:
            result.add("TEST_CWD", f"$.commands[{index}].cwd", str(exc))
            records.append(
                {
                    "id": identifier,
                    "argv": command["argv"],
                    "cwd": command.get("cwd", "."),
                    "expected_exit_codes": command.get("expected_exit_codes", [0]),
                    "return_code": None,
                    "stdout": "",
                    "stderr": str(exc),
                    "status": "FAIL",
                    "timed_out": False,
                }
            )
            continue
        if not cwd.is_dir():
            result.add("TEST_CWD", f"$.commands[{index}].cwd", "working directory is not a directory")
            continue
        try:
            process = subprocess.run(
                command["argv"],
                cwd=cwd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=command.get("timeout_seconds", 300),
                shell=False,
                check=False,
            )
            expected_codes = command.get("expected_exit_codes", [0])
            passed = process.returncode in expected_codes
            record = {
                "id": identifier,
                "argv": command["argv"],
                "cwd": repository_relative(project_root, cwd),
                "expected_exit_codes": expected_codes,
                "return_code": process.returncode,
                "stdout": process.stdout,
                "stderr": process.stderr,
                "status": "PASS" if passed else "FAIL",
                "timed_out": False,
            }
            if not passed:
                result.add(
                    "TEST_COMMAND_FAILED",
                    identifier,
                    f"returned {process.returncode}; expected one of {expected_codes}",
                )
        except subprocess.TimeoutExpired as exc:
            stdout = exc.stdout.decode("utf-8", errors="replace") if isinstance(exc.stdout, bytes) else (exc.stdout or "")
            stderr = exc.stderr.decode("utf-8", errors="replace") if isinstance(exc.stderr, bytes) else (exc.stderr or "")
            record = {
                "id": identifier,
                "argv": command["argv"],
                "cwd": repository_relative(project_root, cwd),
                "expected_exit_codes": command.get("expected_exit_codes", [0]),
                "return_code": None,
                "stdout": stdout,
                "stderr": stderr,
                "status": "FAIL",
                "timed_out": True,
            }
            result.add("TEST_TIMEOUT", identifier, f"exceeded {command.get('timeout_seconds', 300)} seconds")
        except OSError as exc:
            record = {
                "id": identifier,
                "argv": command["argv"],
                "cwd": repository_relative(project_root, cwd),
                "expected_exit_codes": command.get("expected_exit_codes", [0]),
                "return_code": None,
                "stdout": "",
                "stderr": str(exc),
                "status": "FAIL",
                "timed_out": False,
            }
            result.add("TEST_EXECUTION", identifier, str(exc))
        try:
            record["artifact_paths"] = [
                _artifact_snapshot(project_root, raw_path)
                for raw_path in command.get("artifact_paths", [])
            ]
        except (InputError, OSError) as exc:
            record["artifact_paths"] = []
            record["status"] = "FAIL"
            result.add("TEST_ARTIFACT_CAPTURE", identifier, str(exc))
        records.append(record)

    evidence_path = output_path or (run_dir / "30_execution" / "test_results.json")
    attempt_id = attempt_id or _new_attempt_id()
    if ATTEMPT_ID_PATTERN.fullmatch(attempt_id) is None:
        result.add("TEST_ATTEMPT_ID", "attempt_id", "must be a safe 1-96 character identifier")
        return result
    attempt_dir = run_dir / "30_execution" / "test_attempts" / attempt_id
    attempt_path = attempt_dir / "test_results.json"
    attempts_root = attempt_dir.parent.resolve(strict=False)
    try:
        evidence_path.resolve(strict=False).relative_to(attempts_root)
    except ValueError:
        pass
    else:
        result.add("TEST_RESULT_PATH", str(evidence_path), "canonical result output must remain outside immutable attempt history")
        return result
    if attempt_dir.exists():
        result.add("TEST_ATTEMPT_EXISTS", attempt_id, "test attempt history is immutable and cannot be reused")
        return result
    payload = {
        "schema_version": "1.0",
        "artifact_type": "deterministic-test-results",
        "status": "PASS" if records and all(item["status"] == "PASS" for item in records) else "FAIL",
        "executed_at": timestamp or datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "plan_path": repository_relative(project_root, plan_path),
        "plan_sha256": sha256_file(plan_path),
        "result_path": repository_relative(project_root, evidence_path),
        "attempt_id": attempt_id,
        "attempt_path": repository_relative(project_root, attempt_path),
        "command_count": len(records),
        "passed_count": sum(item["status"] == "PASS" for item in records),
        "failed_count": sum(item["status"] == "FAIL" for item in records),
        "commands": records,
    }
    attempt_dir.parent.mkdir(parents=True, exist_ok=True)
    try:
        attempt_dir.mkdir()
        atomic_write_json(attempt_path, payload)
        attempt_sha256 = sha256_file(attempt_path)
        canonical = dict(payload)
        canonical["attempt_sha256"] = attempt_sha256
        atomic_write_json(evidence_path, canonical)
    except OSError as exc:
        result.add("TEST_RESULT_WRITE", str(evidence_path), str(exc))
        return result
    result.data = {
        "status": payload["status"],
        "result_path": str(evidence_path),
        "command_count": payload["command_count"],
        "passed_count": payload["passed_count"],
        "failed_count": payload["failed_count"],
        "attempt_id": attempt_id,
        "attempt_path": str(attempt_path),
        "attempt_sha256": attempt_sha256,
    }
    if payload["status"] != "PASS":
        result.ok = False
    return result
