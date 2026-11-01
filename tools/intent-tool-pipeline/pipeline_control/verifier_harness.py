"""Deterministic clean-package verification preparation.

The harness prepares evidence for an independent verifier.  It deliberately
does not make requirement-level or release-readiness judgments.
"""

from __future__ import annotations

import ast
import hashlib
import json
import os
import platform
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any, BinaryIO

from .evidence import reconcile_source as _reconcile_source
from .io_utils import InputError, atomic_write_bytes, atomic_write_json, read_structured, repository_relative, resolve_within, sha256_file
from .packaging import DEFAULT_PROHIBITED_PATTERNS, prohibited_reason
from .result import CommandResult
from .mutation_guard import run_forward_diagnostics
from .scratch import ScratchError, VerificationScratch, allocate_verification_scratch
from .workflow import entry_context


ATTEMPT_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,95}$")
COMMAND_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
WINDOWS_RESERVED_NAMES = {
    "CON",
    "PRN",
    "AUX",
    "NUL",
    *(f"COM{index}" for index in range(1, 10)),
    *(f"LPT{index}" for index in range(1, 10)),
}
REQUIRED_SCENARIO_MINIMUMS = {
    "complete_suite": 2,
    "help": 1,
    "import": 1,
    "cli": 1,
    "packaging_layout": 1,
    "legacy_or_open_result": 1,
}
_PYTHON_ENV_PREFIXES = ("PYTHON", "PIP_")
_TEMPLATE_NAMES = {"package_root", "temp_root", "output_root"}
_AUDIT_MARKER = b"CODEX_UNDECLARED_DEPENDENCY:"
_PYTHON_PATH_CALLS = {
    "Path",
    "PurePath",
    "chdir",
    "listdir",
    "open",
    "open_code",
    "scandir",
}


def _now(timestamp: str | None) -> str:
    return timestamp or datetime.now(timezone.utc).isoformat(timespec="seconds")


def _new_attempt_id() -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"{stamp}-{os.urandom(4).hex()}"


def _safe_relative(value: Any, *, label: str, result: CommandResult) -> str | None:
    if not isinstance(value, str) or not value:
        result.add("HARNESS_PATH", label, "must be a non-empty forward-slash relative path")
        return None
    if "\\" in value or value.startswith("/") or value.endswith("/") or "//" in value:
        result.add("HARNESS_PATH", label, "must be a normalized forward-slash file path")
        return None
    parts = value.split("/")
    if any(part in {"", ".", ".."} for part in parts) or re.match(r"^[A-Za-z]:", value):
        result.add("HARNESS_PATH", label, "must remain within its declared root")
        return None
    return PurePosixPath(*parts).as_posix()


def _validate_plan(data: Any, result: CommandResult) -> dict[str, Any] | None:
    if not isinstance(data, dict):
        result.add("HARNESS_PLAN_TYPE", "$", "verification plan must be an object/mapping")
        return None
    if str(data.get("schema_version", "")).split(".", 1)[0] != "1":
        result.add("SCHEMA_UNSUPPORTED", "$.schema_version", "verification plan must use schema version 1.x")
    binding = data.get("binding")
    required_binding = {
        "contract_ref",
        "contract_path",
        "contract_sha256",
        "manifest_path",
        "manifest_sha256",
        "inspection_path",
        "inspection_sha256",
        "archive_path",
        "archive_sha256",
    }
    if not isinstance(binding, dict):
        result.add("HARNESS_BINDING", "$.binding", "must bind every inspected input path and SHA-256")
    else:
        for key in sorted(required_binding):
            value = binding.get(key)
            if not isinstance(value, str) or not value:
                result.add("HARNESS_BINDING", f"$.binding.{key}", "is required and must be a non-empty string")
            elif key.endswith("_sha256") and not re.fullmatch(r"[0-9a-f]{64}", value):
                result.add("HARNESS_BINDING", f"$.binding.{key}", "must be a lowercase SHA-256 digest")
            elif key.endswith("_path"):
                _safe_relative(value, label=f"$.binding.{key}", result=result)

    minimums = data.get("scenario_minimums")
    if not isinstance(minimums, dict):
        result.add("SCENARIO_MINIMUMS", "$.scenario_minimums", "must be an object of scenario names to positive minimums")
        minimums = {}
    else:
        for name, count in minimums.items():
            if not isinstance(name, str) or not name or not isinstance(count, int) or isinstance(count, bool) or count < 1:
                result.add("SCENARIO_MINIMUMS", f"$.scenario_minimums.{name}", "minimum must be a positive integer")
    for name, floor in REQUIRED_SCENARIO_MINIMUMS.items():
        if minimums.get(name, 0) < floor:
            result.add("SCENARIO_MINIMUM", f"$.scenario_minimums.{name}", f"must be at least {floor}")

    commands = data.get("commands")
    if not isinstance(commands, list) or not commands:
        result.add("HARNESS_COMMANDS", "$.commands", "must contain at least one shell-free command")
        return data
    identifiers: set[str] = set()
    counts: dict[str, int] = {}
    for index, command in enumerate(commands):
        path = f"$.commands[{index}]"
        if not isinstance(command, dict):
            result.add("HARNESS_COMMAND_TYPE", path, "must be an object/mapping")
            continue
        identifier = command.get("id")
        folded = identifier.casefold() if isinstance(identifier, str) else ""
        if not isinstance(identifier, str) or COMMAND_ID_PATTERN.fullmatch(identifier) is None:
            result.add("HARNESS_COMMAND_ID", f"{path}.id", "must be a safe 1-64 character identifier")
        elif folded in identifiers:
            result.add("HARNESS_COMMAND_ID", f"{path}.id", "must be unique under case-insensitive filesystems")
        else:
            identifiers.add(folded)
        scenario = command.get("scenario")
        if not isinstance(scenario, str) or not scenario:
            result.add("HARNESS_SCENARIO", f"{path}.scenario", "must be a non-empty scenario name")
        else:
            counts[scenario] = counts.get(scenario, 0) + 1
        argv = command.get("argv")
        if not isinstance(argv, list) or not argv or any(not isinstance(item, str) or not item for item in argv):
            result.add("HARNESS_ARGV", f"{path}.argv", "must be a non-empty array of non-empty strings")
        expected = command.get("expected_exit_codes", [0])
        if not isinstance(expected, list) or not expected or any(not isinstance(item, int) or isinstance(item, bool) for item in expected):
            result.add("HARNESS_EXPECTED_EXIT", f"{path}.expected_exit_codes", "must be a non-empty array of integers")
        timeout = command.get("timeout_seconds", 300)
        if not isinstance(timeout, (int, float)) or isinstance(timeout, bool) or timeout <= 0 or timeout > 3600:
            result.add("HARNESS_TIMEOUT", f"{path}.timeout_seconds", "must be greater than 0 and at most 3600")
        cwd = command.get("cwd", ".")
        if not isinstance(cwd, str) or not cwd or Path(cwd).is_absolute() or "\\" in cwd or ".." in PurePosixPath(cwd).parts:
            result.add("HARNESS_CWD", f"{path}.cwd", "must remain relative to the extracted package root")
        outputs = command.get("outputs", [])
        if not isinstance(outputs, list):
            result.add("HARNESS_OUTPUTS", f"{path}.outputs", "must be an array of output paths")
        else:
            seen_outputs: set[str] = set()
            for output_index, output in enumerate(outputs):
                raw = output.get("path") if isinstance(output, dict) else output
                normalized = _safe_relative(raw, label=f"{path}.outputs[{output_index}]", result=result)
                if normalized is not None:
                    if normalized.casefold() in seen_outputs:
                        result.add("HARNESS_OUTPUTS", f"{path}.outputs[{output_index}]", "duplicates another declared output")
                    seen_outputs.add(normalized.casefold())
    for scenario, minimum in minimums.items():
        if isinstance(minimum, int) and counts.get(scenario, 0) < minimum:
            result.add("SCENARIO_MINIMUM", f"$.commands[{scenario}]", f"declares {counts.get(scenario, 0)} command(s); requires {minimum}")
    return data


def _active_contract(project_root: Path, run_dir: Path, result: CommandResult) -> tuple[Path, dict[str, Any], str] | None:
    state_path = run_dir / "30_execution" / "run_state.json"
    try:
        state = read_structured(state_path)
    except InputError as exc:
        result.add("CONTRACT_BINDING", str(state_path), str(exc))
        return None
    entry = state.get("active_artifacts", {}).get("product_contract") if isinstance(state, dict) else None
    if not isinstance(entry, dict) or not isinstance(entry.get("path"), str):
        result.add("CONTRACT_BINDING", "active_artifacts.product_contract", "an active product contract is required")
        return None
    raw = entry["path"]
    candidates = [(project_root / raw).resolve(strict=False), (run_dir / raw).resolve(strict=False)]
    path = next((item for item in candidates if item.is_file()), candidates[0])
    try:
        path.relative_to(run_dir.resolve())
        contract = read_structured(path)
    except (ValueError, InputError) as exc:
        result.add("CONTRACT_BINDING", raw, f"active contract must be a readable file inside the run: {exc}")
        return None
    artifact = contract.get("artifact") if isinstance(contract, dict) else None
    if not isinstance(artifact, dict) or artifact.get("artifact_id") != entry.get("artifact_id") or artifact.get("version") != entry.get("version"):
        result.add("CONTRACT_BINDING", raw, "active contract metadata and run-state identity differ")
        return None
    if isinstance(entry.get("content_sha256"), str) and entry["content_sha256"] != sha256_file(path):
        result.add("CONTRACT_BINDING", raw, "run-state content identity differs from the active contract bytes")
        return None
    return path, contract, f"{artifact['artifact_id']}@{artifact['version']}"


def _binding_path(project_root: Path, binding: dict[str, Any], key: str, result: CommandResult) -> Path | None:
    try:
        return resolve_within(project_root, binding[key], must_exist=True)
    except (KeyError, InputError) as exc:
        result.add("HARNESS_BINDING", f"$.binding.{key}", str(exc))
        return None


def _check_file_binding(project_root: Path, path: Path, binding: dict[str, Any], prefix: str, result: CommandResult) -> None:
    actual_path = repository_relative(project_root, path)
    if binding.get(f"{prefix}_path") != actual_path:
        result.add("HARNESS_BINDING", f"$.binding.{prefix}_path", f"must equal {actual_path!r}")
    try:
        actual_hash = sha256_file(path)
    except OSError as exc:
        result.add("HARNESS_INPUT_READ", str(path), str(exc))
        return
    if binding.get(f"{prefix}_sha256") != actual_hash:
        result.add(f"{prefix.upper()}_DRIFT", str(path), "content SHA-256 no longer matches the verification plan")


def _zip_name_error(name: str) -> str | None:
    if not name:
        return "entry name is empty"
    if "\\" in name:
        return "backslashes are prohibited"
    if any(ord(character) < 32 for character in name):
        return "control characters are prohibited"
    if name.startswith("/") or name.startswith("//") or re.match(r"^[A-Za-z]:", name):
        return "absolute, drive, and UNC paths are prohibited"
    if name.endswith("/"):
        return "explicit directory entries are prohibited"
    parts = name.split("/")
    if any(part in {"", ".", ".."} for part in parts):
        return "empty, current, and parent path segments are prohibited"
    for part in parts:
        if ":" in part:
            return "drive and NTFS alternate-data-stream syntax is prohibited"
        if part.endswith((".", " ")):
            return "segments ending in dot or space are prohibited"
        base = part.split(".", 1)[0].upper()
        if base in WINDOWS_RESERVED_NAMES:
            return f"Windows reserved path segment {part!r} is prohibited"
    return None


def _zip_entry_is_regular(info: zipfile.ZipInfo) -> bool:
    if info.is_dir() or info.external_attr & 0x10:
        return False
    mode = (info.external_attr >> 16) & 0xFFFF
    return not mode or stat.S_IFMT(mode) in {0, stat.S_IFREG}


def _stream_digest(stream: BinaryIO, target: BinaryIO | None = None) -> tuple[str, int]:
    digest = hashlib.sha256()
    size = 0
    for chunk in iter(lambda: stream.read(1024 * 1024), b""):
        digest.update(chunk)
        size += len(chunk)
        if target is not None:
            target.write(chunk)
    return digest.hexdigest(), size


def _manifest_entries(manifest: dict[str, Any], result: CommandResult) -> dict[str, dict[str, Any]]:
    raw = manifest.get("entries")
    if not isinstance(raw, list):
        result.add("MANIFEST_ENTRIES", "manifest.entries", "must be an array")
        return {}
    entries: dict[str, dict[str, Any]] = {}
    folded: set[str] = set()
    for index, item in enumerate(raw):
        if not isinstance(item, dict) or not isinstance(item.get("path"), str):
            result.add("MANIFEST_ENTRIES", f"manifest.entries[{index}]", "must contain path, sha256, and size_bytes")
            continue
        name = item["path"]
        error = _zip_name_error(name)
        if error:
            result.add("MANIFEST_UNSAFE_PATH", name, error)
        if name in entries or name.casefold() in folded:
            result.add("MANIFEST_COLLISION", name, "duplicates or case-collides with another manifest entry")
        entries[name] = item
        folded.add(name.casefold())
        if not re.fullmatch(r"[0-9a-f]{64}", str(item.get("sha256", ""))) or not isinstance(item.get("size_bytes"), int):
            result.add("MANIFEST_ENTRIES", name, "must contain a lowercase SHA-256 and integer size_bytes")
    return entries


def _reconcile_archive(
    project_root: Path,
    archive_path: Path,
    manifest: dict[str, Any],
    inspection: dict[str, Any],
    result: CommandResult,
) -> tuple[list[zipfile.ZipInfo], list[dict[str, Any]]]:
    expected = _manifest_entries(manifest, result)
    required = manifest.get("required_entries")
    if not isinstance(required, list) or any(not isinstance(item, str) for item in required):
        result.add("REQUIRED_ENTRY", "manifest.required_entries", "must be an array of paths")
        required = []
    declared_patterns = manifest.get("prohibited_patterns")
    if not isinstance(declared_patterns, list) or any(not isinstance(item, str) for item in declared_patterns):
        result.add("MANIFEST_POLICY", "manifest.prohibited_patterns", "must be an array of strings")
        declared_patterns = []
    patterns = list(dict.fromkeys([*DEFAULT_PROHIBITED_PATTERNS, *declared_patterns]))

    infos: list[zipfile.ZipInfo] = []
    inventory: list[dict[str, Any]] = []
    names: set[str] = set()
    folded: set[str] = set()
    try:
        with zipfile.ZipFile(archive_path, "r") as archive:
            for info in archive.infolist():
                # ZipInfo.filename is normalized with os.sep on Windows.  The
                # original spelling is required to reject backslash entries.
                name = info.orig_filename
                error = _zip_name_error(name)
                if error:
                    result.add("ARCHIVE_UNSAFE_PATH", name or "<empty>", error)
                if name in names:
                    result.add("ARCHIVE_DUPLICATE", name, "duplicate ZIP entry")
                if name.casefold() in folded:
                    result.add("ARCHIVE_CASE_COLLISION", name, "entry collides under Windows case folding")
                names.add(name)
                folded.add(name.casefold())
                if info.flag_bits & 0x1:
                    result.add("ARCHIVE_ENCRYPTED", name, "encrypted entries are prohibited")
                if not _zip_entry_is_regular(info):
                    result.add("ARCHIVE_SPECIAL_ENTRY", name, "only regular file entries are permitted")
                if prohibited_reason(name, patterns):
                    result.add("PROHIBITED_ENTRY", name, prohibited_reason(name, patterns) or "prohibited entry")
                infos.append(info)

            for name in sorted(names, key=lambda item: (item.casefold(), item)):
                parts = name.split("/")
                for end in range(1, len(parts)):
                    ancestor = "/".join(parts[:end])
                    if ancestor in names or ancestor.casefold() in folded:
                        result.add("ARCHIVE_ANCESTOR_COLLISION", name, f"file ancestor {ancestor!r} is also an entry")
                        break
            if not result.ok:
                return infos, inventory

            for info in infos:
                with archive.open(info, "r") as stream:
                    digest, size = _stream_digest(stream)
                inventory.append({"path": info.orig_filename, "sha256": digest, "size_bytes": size})
                if size != info.file_size:
                    result.add("ARCHIVE_SIZE", info.orig_filename, "streamed size differs from ZIP metadata")
    except (OSError, RuntimeError, zipfile.BadZipFile, zipfile.LargeZipFile) as exc:
        result.add("ARCHIVE_READ", str(archive_path), str(exc))
        return infos, inventory

    actual = {item["path"]: item for item in inventory}
    if set(expected) != set(actual):
        result.add("MANIFEST_INVENTORY", str(archive_path), f"missing={sorted(set(expected) - set(actual))}, extra={sorted(set(actual) - set(expected))}")
    for name in sorted(set(expected) & set(actual)):
        if expected[name].get("sha256") != actual[name]["sha256"] or expected[name].get("size_bytes") != actual[name]["size_bytes"]:
            result.add("ENTRY_HASH", name, "archive content hash or size differs from the manifest")
    missing_required = sorted(set(required) - set(actual))
    if missing_required:
        result.add("REQUIRED_ENTRY", "manifest.required_entries", f"missing required entries: {missing_required}")
    root = manifest.get("artifact_root")
    roots = {PurePosixPath(name).parts[0] for name in actual}
    if not isinstance(root, str) or roots != {root}:
        result.add("ARCHIVE_ROOT", str(archive_path), f"expected one root {root!r}; found {sorted(roots)}")
    if manifest.get("entry_count") != len(actual):
        result.add("ENTRY_COUNT", "manifest.entry_count", "does not match the archive inventory")

    inspected_raw = inspection.get("entries")
    inspected = {
        item.get("path"): item
        for item in inspected_raw
        if isinstance(item, dict) and isinstance(item.get("path"), str)
    } if isinstance(inspected_raw, list) else {}
    if inspected != actual:
        result.add("INSPECTION_DRIFT", "inspection.entries", "inspection inventory does not equal the streamed archive inventory")
    if inspection.get("entry_count") != len(actual):
        result.add("INSPECTION_DRIFT", "inspection.entry_count", "inspection entry count does not equal the streamed archive inventory")
    return infos, inventory


def _validate_inputs(
    project_root: Path,
    run_dir: Path,
    plan: dict[str, Any],
    result: CommandResult,
) -> tuple[Path, Path, Path, Path, dict[str, Any], list[zipfile.ZipInfo], list[dict[str, Any]]] | None:
    binding = plan["binding"]
    active = _active_contract(project_root, run_dir, result)
    contract_path = active[0] if active else None
    active_ref = active[2] if active else None
    manifest_path = _binding_path(project_root, binding, "manifest_path", result)
    inspection_path = _binding_path(project_root, binding, "inspection_path", result)
    archive_path = _binding_path(project_root, binding, "archive_path", result)
    if contract_path is not None:
        _check_file_binding(project_root, contract_path, binding, "contract", result)
        if binding.get("contract_ref") != active_ref:
            result.add("CONTRACT_DRIFT", "$.binding.contract_ref", f"must equal active contract {active_ref!r}")
    for prefix, path in (("manifest", manifest_path), ("inspection", inspection_path), ("archive", archive_path)):
        if path is not None:
            _check_file_binding(project_root, path, binding, prefix, result)
    if contract_path is None or manifest_path is None or inspection_path is None or archive_path is None:
        return None
    try:
        manifest = read_structured(manifest_path)
        inspection = read_structured(inspection_path)
    except InputError as exc:
        result.add("HARNESS_INPUT_READ", "$", str(exc))
        return None
    if not isinstance(manifest, dict) or manifest.get("artifact_type") != "release-manifest":
        result.add("MANIFEST_TYPE", str(manifest_path), "must be a release-manifest object")
        return None
    if not isinstance(inspection, dict) or inspection.get("artifact_type") != "package-inspection":
        result.add("INSPECTION_TYPE", str(inspection_path), "must be a package-inspection object")
        return None
    archive_hash = sha256_file(archive_path)
    manifest_rel = repository_relative(project_root, manifest_path)
    archive_rel = repository_relative(project_root, archive_path)
    if manifest.get("archive_path") != archive_rel or manifest.get("archive_sha256") != archive_hash:
        result.add("MANIFEST_DRIFT", str(manifest_path), "archive path or SHA-256 does not identify the bound archive")
    if manifest.get("approval", {}).get("contract_ref") != active_ref:
        result.add("CONTRACT_DRIFT", "manifest.approval.contract_ref", "manifest is not bound to the active contract")
    if inspection.get("status") != "PASS" or inspection.get("diagnostics") not in ([], None) or inspection.get("prohibited_entry_count") != 0:
        result.add("INSPECTION_NOT_PASSING", str(inspection_path), "bound package inspection must be a clean PASS")
    if inspection.get("archive_path") != archive_rel or inspection.get("manifest_path") != manifest_rel or inspection.get("archive_sha256") != archive_hash:
        result.add("INSPECTION_DRIFT", str(inspection_path), "inspection paths or archive SHA-256 do not identify the bound candidate")
    infos, inventory = _reconcile_archive(project_root, archive_path, manifest, inspection, result)
    if result.ok:
        _reconcile_source(project_root, manifest, inventory, result)
    if not result.ok:
        return contract_path, manifest_path, inspection_path, archive_path, manifest, infos, inventory
    return contract_path, manifest_path, inspection_path, archive_path, manifest, infos, inventory


def _extract_once(
    archive_path: Path,
    infos: list[zipfile.ZipInfo],
    inventory: list[dict[str, Any]],
    scratch: VerificationScratch,
) -> Path:
    extraction_root = scratch.path / "package"
    extraction_root.mkdir()
    expected = {item["path"]: item for item in inventory}
    with zipfile.ZipFile(archive_path, "r") as archive:
        for info in infos:
            target = extraction_root.joinpath(*info.filename.split("/"))
            target.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(info, "r") as source, target.open("xb") as destination:
                digest, size = _stream_digest(source, destination)
            identity = expected.get(info.orig_filename)
            if identity is None or digest != identity["sha256"] or size != identity["size_bytes"]:
                raise OSError(f"archive bytes changed between reconciliation and extraction for {info.orig_filename}")
    return extraction_root


def _tree_snapshot(root: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for path in sorted(root.rglob("*"), key=lambda item: item.relative_to(root).as_posix().casefold()):
        relative = path.relative_to(root).as_posix()
        metadata = path.lstat()
        if path.is_symlink() or stat.S_IFMT(metadata.st_mode) not in {stat.S_IFDIR, stat.S_IFREG}:
            records.append({"path": relative, "kind": "SPECIAL"})
        elif path.is_dir():
            records.append({"path": relative, "kind": "DIRECTORY"})
        else:
            records.append({"path": relative, "kind": "FILE", "size_bytes": metadata.st_size, "sha256": sha256_file(path)})
    return records


def _path_identity(path: Path) -> dict[str, Any]:
    """Return a stable identity even when a guarded path disappears or changes kind."""

    try:
        metadata = path.lstat()
    except FileNotFoundError:
        return {"kind": "MISSING"}
    except OSError as exc:
        return {"kind": "UNREADABLE", "error": f"{type(exc).__name__}: {exc}"}
    if path.is_symlink() or stat.S_IFMT(metadata.st_mode) not in {stat.S_IFDIR, stat.S_IFREG}:
        return {"kind": "SPECIAL"}
    if path.is_dir():
        return {"kind": "DIRECTORY"}
    try:
        return {"kind": "FILE", "size_bytes": metadata.st_size, "sha256": sha256_file(path)}
    except OSError as exc:
        return {"kind": "UNREADABLE", "error": f"{type(exc).__name__}: {exc}"}


def _is_within(path: Path, root: Path) -> bool:
    try:
        path.resolve(strict=False).relative_to(root.resolve(strict=False))
        return True
    except ValueError:
        return False


def _source_snapshot(root: Path, *, excluded_roots: tuple[Path, ...]) -> list[dict[str, Any]]:
    """Hash the complete canonical source tree while excluding harness-owned evidence."""

    records: list[dict[str, Any]] = [{"path": ".", **_path_identity(root)}]
    try:
        paths = sorted(root.rglob("*"), key=lambda item: item.relative_to(root).as_posix().casefold())
    except OSError as exc:
        return [{"path": ".", "kind": "UNREADABLE", "error": f"{type(exc).__name__}: {exc}"}]
    for path in paths:
        if any(_is_within(path, excluded) for excluded in excluded_roots):
            continue
        relative = path.relative_to(root).as_posix()
        identity = _path_identity(path)
        records.append({"path": relative, **identity})
    return records


def _active_artifact_path(project_root: Path, run_dir: Path, raw: str) -> Path:
    candidates = ((project_root / raw).resolve(strict=False), (run_dir / raw).resolve(strict=False))
    for candidate in candidates:
        if candidate.exists() or candidate.is_symlink():
            candidate.relative_to(project_root.resolve(strict=False))
            return candidate
    candidates[0].relative_to(project_root.resolve(strict=False))
    return candidates[0]


def _guard_baseline(
    project_root: Path,
    run_dir: Path,
    manifest: dict[str, Any],
    *,
    contract_path: Path,
    manifest_path: Path,
    inspection_path: Path,
    archive_path: Path,
    harness_root: Path,
    result: CommandResult,
) -> dict[str, Any] | None:
    """Bind every canonical source byte and every gate-defining input."""

    state_path = run_dir / "30_execution" / "run_state.json"
    try:
        state = read_structured(state_path)
    except InputError as exc:
        result.add("HARNESS_GUARD", str(state_path), str(exc))
        return None
    active = state.get("active_artifacts") if isinstance(state, dict) else None
    if not isinstance(active, dict):
        result.add("HARNESS_GUARD", "active_artifacts", "run state must identify every semantic input")
        return None

    protected: dict[str, Path] = {
        "run_state": state_path,
        "product_contract": contract_path,
        "release_manifest": manifest_path,
        "package_inspection": inspection_path,
        "release_archive": archive_path,
    }
    def protect_active_artifact(key: str, *, required: bool) -> None:
        entry = active.get(key)
        if entry is None and not required:
            return
        raw = entry.get("path") if isinstance(entry, dict) else None
        if not isinstance(raw, str) or not raw:
            result.add("HARNESS_GUARD", f"active_artifacts.{key}", "must identify a guarded semantic input")
            return
        try:
            protected[key] = _active_artifact_path(project_root, run_dir, raw)
        except ValueError:
            result.add("HARNESS_GUARD", f"active_artifacts.{key}.path", "must remain inside the project root")

    direct, route_diagnostics = entry_context(project_root, run_dir, state)
    result.extend(route_diagnostics)
    protect_active_artifact("build_request", required=True)
    protect_active_artifact("problem_frame", required=not direct)
    protect_active_artifact("verification_report", required=False)

    raw_source = manifest.get("source_root")
    try:
        source_root = resolve_within(project_root, raw_source, must_exist=True)
    except (InputError, TypeError) as exc:
        result.add("HARNESS_GUARD", "manifest.source_root", str(exc))
        return None
    if not source_root.is_dir() or source_root.is_symlink():
        result.add("HARNESS_GUARD", str(source_root), "canonical source root must be a non-symlink directory")
        return None
    if not result.ok:
        return None

    protected_records: dict[str, dict[str, Any]] = {}
    for label, path in sorted(protected.items()):
        try:
            relative = repository_relative(project_root, path)
        except InputError as exc:
            result.add("HARNESS_GUARD", label, str(exc))
            continue
        identity = _path_identity(path)
        if identity["kind"] != "FILE":
            result.add("HARNESS_GUARD", relative, f"guarded {label} must be a readable regular file")
        protected_records[label] = {"path": relative, "identity": identity}
    if not result.ok:
        return None
    return {
        "source_root": repository_relative(project_root, source_root),
        "source_path": source_root,
        "source": _source_snapshot(source_root, excluded_roots=(harness_root,)),
        "protected": protected_records,
    }


def _guard_unchanged(
    project_root: Path,
    baseline: dict[str, Any],
    *,
    harness_root: Path,
    command_id: str,
    phase: str,
    result: CommandResult,
) -> bool:
    unchanged = True
    current_source = _source_snapshot(baseline["source_path"], excluded_roots=(harness_root,))
    if current_source != baseline["source"]:
        before = {item["path"]: item for item in baseline["source"]}
        after = {item["path"]: item for item in current_source}
        changed = sorted(path for path in set(before) | set(after) if before.get(path) != after.get(path))
        result.add(
            "CANONICAL_SOURCE_MUTATION",
            baseline["source_root"],
            f"{command_id} {phase} guard detected changed paths: {changed[:20]}",
        )
        unchanged = False
    for label, record in sorted(baseline["protected"].items()):
        path = project_root / Path(*record["path"].split("/"))
        current = _path_identity(path)
        if current != record["identity"]:
            result.add(
                "PROTECTED_INPUT_MUTATION",
                record["path"],
                f"{command_id} {phase} guard detected mutation of {label}",
            )
            unchanged = False
    return unchanged


def _scan_text(value: str) -> str:
    return value.replace("\\\\", "/").replace("\\", "/").casefold()


def _undeclared_dependency(
    argv: list[str],
    *,
    project_root: Path,
    package_root: Path,
    package_dir: Path,
    temp_root: Path,
    output_root: Path,
    command_index: int,
    result: CommandResult,
) -> bool:
    """Reject explicit repository dependencies outside the isolated roots.

    This is a deterministic argv preflight, not an OS sandbox.  Dynamic path
    construction remains covered only by the before/after mutation guards.
    """

    project_text = _scan_text(str(project_root.resolve(strict=False))).rstrip("/")
    allowed = sorted(
        (_scan_text(str(path.resolve(strict=False))).rstrip("/") for path in (package_root, temp_root, output_root)),
        key=len,
        reverse=True,
    )
    found = False
    for argument_index, value in enumerate(argv):
        scanned = _scan_text(value)
        censored = scanned
        for allowed_root in allowed:
            censored = censored.replace(allowed_root, "<isolated-root>")
        if argument_index > 0 and project_text and project_text in censored:
            result.add(
                "UNDECLARED_DEPENDENCY",
                f"$.commands[{command_index}].argv[{argument_index}]",
                "explicit repository path is outside the extracted package and isolated temp/output roots",
            )
            found = True
        for fragment in re.findall(r"[^\s\"'=(:,;\[\]{}]+", value):
            candidate = fragment.replace("\\", "/").rstrip(");,")
            if ".." not in candidate.split("/"):
                continue
            try:
                resolved = (package_dir / Path(*candidate.split("/"))).resolve(strict=False)
                resolved.relative_to(package_root.resolve(strict=False))
            except ValueError:
                result.add(
                    "UNDECLARED_DEPENDENCY",
                    f"$.commands[{command_index}].argv[{argument_index}]",
                    f"relative path {candidate!r} escapes the extracted package root",
                )
                found = True
                break
    return found


def _is_python_executor(value: str) -> bool:
    try:
        if Path(value).resolve(strict=False) == Path(sys.executable).resolve(strict=False):
            return True
    except OSError:
        pass
    return re.fullmatch(r"pythonw?(?:\d+(?:\.\d+)?)?(?:\.exe)?", Path(value).name, re.IGNORECASE) is not None


def _package_entrypoint(argv: list[str], *, package_dir: Path, package_root: Path) -> Path | None:
    candidates = [argv[0], *argv[1:]]
    for value in candidates:
        if not value or value.startswith("-") or "\x00" in value:
            continue
        try:
            candidate = Path(value)
            resolved = candidate.resolve(strict=False) if candidate.is_absolute() else (package_dir / candidate).resolve(strict=False)
            resolved.relative_to(package_root.resolve(strict=False))
        except (OSError, ValueError):
            continue
        if resolved.is_file() and not resolved.is_symlink():
            return resolved
    return None


def _decode_entrypoint(payload: bytes) -> str | None:
    encodings: tuple[str, ...]
    if payload.startswith((b"\xff\xfe", b"\xfe\xff")):
        encodings = ("utf-16",)
    elif payload[:64:2].count(0) > 8:
        encodings = ("utf-16-be",)
    elif payload[1:64:2].count(0) > 8:
        encodings = ("utf-16-le",)
    else:
        encodings = ("utf-8-sig",)
    for encoding in encodings:
        try:
            return payload.decode(encoding)
        except UnicodeError:
            continue
    return None


def _inspect_generic_entrypoint(
    entrypoint: Path | None,
    *,
    project_root: Path,
    package_root: Path,
    command_index: int,
    result: CommandResult,
) -> None:
    """Conservatively scan only the selected executable/script, never dormant files."""

    if entrypoint is None:
        return
    try:
        source = _decode_entrypoint(entrypoint.read_bytes())
    except OSError:
        return
    if source is None:
        return
    project_text = _scan_text(str(project_root.resolve(strict=False))).rstrip("/")
    if project_text and project_text in _scan_text(source):
        result.add(
            "UNDECLARED_DEPENDENCY",
            f"$.commands[{command_index}].entrypoint:{entrypoint.relative_to(package_root).as_posix()}",
            "executed package entrypoint contains an explicit repository path outside the isolated roots",
        )


def _sanitized_environment(project_root: Path) -> tuple[dict[str, str], list[str]]:
    project_text = _scan_text(str(project_root.resolve(strict=False))).rstrip("/")
    environment: dict[str, str] = {}
    scrubbed: list[str] = []
    for key, value in os.environ.items():
        upper = key.upper()
        if upper.startswith(_PYTHON_ENV_PREFIXES):
            continue
        if upper == "PATH":
            components = value.split(os.pathsep)
            retained = [component for component in components if project_text not in _scan_text(component)]
            if retained != components:
                scrubbed.append(key)
            environment[key] = os.pathsep.join(retained)
            continue
        if project_text and project_text in _scan_text(value):
            scrubbed.append(key)
            continue
        environment[key] = value
    return environment, sorted(scrubbed, key=str.casefold)


def _python_entrypoint(
    argv: list[str],
    *,
    package_dir: Path,
    package_root: Path,
    command_index: int,
    result: CommandResult,
) -> Path | None:
    index = 1
    mode: str | None = None
    target: str | None = None
    while index < len(argv):
        argument = argv[index]
        if argument == "--":
            target = argv[index + 1] if index + 1 < len(argv) else None
            break
        if argument in {"-c", "-m"}:
            mode = argument
            target = argv[index + 1] if index + 1 < len(argv) else None
            break
        if argument in {"-E", "-I", "-S", "--ignore-environment", "--isolated", "--no-site"} or (
            argument.startswith("-")
            and not argument.startswith("--")
            and any(flag in argument[1:] for flag in "EIS")
        ):
            result.add(
                "UNDECLARED_DEPENDENCY",
                f"$.commands[{command_index}].argv[{index}]",
                "Python option disables the verification filesystem audit guard",
            )
        if argument in {"-W", "-X"}:
            index += 2
            continue
        if argument.startswith("-"):
            index += 1
            continue
        target = argument
        break
    if not target or mode == "-c":
        return None
    if mode == "-m":
        relative = Path(*target.split("."))
        candidates = (package_dir / relative.with_suffix(".py"), package_dir / relative / "__main__.py")
    else:
        candidates = ((package_dir / target).resolve(strict=False),)
    for candidate in candidates:
        resolved = candidate.resolve(strict=False)
        try:
            resolved.relative_to(package_root.resolve(strict=False))
        except ValueError:
            continue
        if resolved.is_file() and not resolved.is_symlink():
            return resolved
    return None


def _literal_dependency_reason(value: str, *, project_root: Path, package_root: Path, package_dir: Path) -> str | None:
    scanned = _scan_text(value)
    project_text = _scan_text(str(project_root.resolve(strict=False))).rstrip("/")
    if project_text and project_text in scanned:
        return "Python entrypoint contains an explicit repository path outside the extracted package"
    normalized = value.replace("\\", "/")
    if ".." not in normalized.split("/"):
        return None
    try:
        (package_dir / Path(*normalized.split("/"))).resolve(strict=False).relative_to(package_root.resolve(strict=False))
    except ValueError:
        return f"Python entrypoint contains relative path {value!r} that escapes the extracted package"
    return None


def _inspect_python_entrypoint(
    entrypoint: Path | None,
    *,
    project_root: Path,
    package_root: Path,
    package_dir: Path,
    command_index: int,
    result: CommandResult,
) -> None:
    """Inspect only executed Python code, not documentation or dormant tests."""

    if entrypoint is None:
        return
    try:
        source = entrypoint.read_text(encoding="utf-8-sig")
        tree = ast.parse(source, filename=entrypoint.name)
    except (OSError, UnicodeError, SyntaxError):
        return
    seen: set[tuple[int, str]] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if isinstance(node.func, ast.Name):
            call_name = node.func.id
        elif isinstance(node.func, ast.Attribute):
            call_name = node.func.attr
        else:
            continue
        if call_name not in _PYTHON_PATH_CALLS:
            continue
        for argument in node.args:
            if not isinstance(argument, ast.Constant) or not isinstance(argument.value, str):
                continue
            reason = _literal_dependency_reason(
                argument.value,
                project_root=project_root,
                package_root=package_root,
                package_dir=package_dir,
            )
            key = (getattr(argument, "lineno", 0), argument.value)
            if reason is not None and key not in seen:
                result.add(
                    "UNDECLARED_DEPENDENCY",
                    f"$.commands[{command_index}].entrypoint:{entrypoint.relative_to(package_root).as_posix()}:{key[0]}",
                    reason,
                )
                seen.add(key)


def _write_python_audit_guard(
    temp_root: Path,
    *,
    project_root: Path,
    package_root: Path,
    output_root: Path,
    executable: str,
) -> dict[str, Any]:
    guard_root = temp_root / "python-audit"
    handshake_path = temp_root / "python-audit-active.txt"
    handshake_token = os.urandom(16).hex()
    toolchain_roots = {Path(sys.prefix).resolve(strict=False), Path(sys.base_prefix).resolve(strict=False)}
    executable_path = Path(executable)
    if executable_path.is_absolute():
        resolved_executable = executable_path.resolve(strict=False)
        toolchain_roots.update({resolved_executable.parent, resolved_executable.parent.parent})
    allowed_roots = [package_root, temp_root, output_root, *sorted(toolchain_roots, key=lambda item: str(item).casefold())]
    guard_source = f'''# Generated verification audit guard; scoped to this scratch command.\n\
import os\n\
import sys\n\
\n\
_PROJECT = os.path.normcase(os.path.realpath({str(project_root.resolve(strict=False))!r}))\n\
_ALLOWED = tuple(os.path.normcase(os.path.realpath(value)) for value in {tuple(str(path.resolve(strict=False)) for path in allowed_roots)!r})\n\
_MARKER = {_AUDIT_MARKER!r}\n\
_HANDSHAKE = {str(handshake_path)!r}\n\
_HANDSHAKE_TOKEN = {handshake_token!r}\n\
\n\
def _normalise(value):\n\
    if isinstance(value, bytes):\n\
        value = os.fsdecode(value)\n\
    if not isinstance(value, str):\n\
        return None\n\
    return os.path.normcase(os.path.realpath(os.path.abspath(value)))\n\
\n\
def _inside(path, root):\n\
    try:\n\
        return os.path.commonpath((path, root)) == root\n\
    except (OSError, ValueError):\n\
        return False\n\
\n\
def _blocked(value):\n\
    path = _normalise(value)\n\
    return path if path is not None and _inside(path, _PROJECT) and not any(_inside(path, root) for root in _ALLOWED) else None\n\
\n\
def _fail(event, path):\n\
    payload = _MARKER + event.encode("ascii", "replace") + b":" + os.fsencode(path) + b"\\n"\n\
    try:\n\
        os.write(2, payload)\n\
    finally:\n\
        os._exit(86)\n\
\n\
def _hook(event, args):\n\
    candidates = ()\n\
    if event == "open" and args:\n\
        mode = args[1] if len(args) > 1 else None\n\
        flags = args[2] if len(args) > 2 else None\n\
        reading = ("r" in mode or "+" in mode) if isinstance(mode, str) else not isinstance(flags, int) or (flags & getattr(os, "O_ACCMODE", os.O_WRONLY | os.O_RDWR)) != os.O_WRONLY\n\
        if reading:\n\
            candidates = (args[0],)\n\
    elif event in {{"os.listdir", "os.scandir", "os.chdir"}} and args:\n\
        candidates = (args[0],)\n\
    elif event == "import" and len(args) > 1 and args[1] is not None:\n\
        candidates = (args[1],)\n\
    for candidate in candidates:\n\
        blocked = _blocked(candidate)\n\
        if blocked is not None:\n\
            _fail(event, blocked)\n\
\n\
sys.addaudithook(_hook)\n\
with open(_HANDSHAKE, "w", encoding="utf-8") as _stream:\n\
    _stream.write(_HANDSHAKE_TOKEN)\n'''
    atomic_write_bytes(guard_root / "sitecustomize.py", guard_source.encode("utf-8"))
    return {"root": guard_root, "handshake_path": handshake_path, "handshake_token": handshake_token}


def _expand(value: str, values: dict[str, str], result: CommandResult, path: str) -> str:
    unknown = set(re.findall(r"\{([A-Za-z0-9_]+)\}", value)) - _TEMPLATE_NAMES
    if unknown:
        result.add("HARNESS_TEMPLATE", path, f"unknown template name(s): {sorted(unknown)}")
        return value
    try:
        return value.format_map(values)
    except (KeyError, ValueError) as exc:
        result.add("HARNESS_TEMPLATE", path, str(exc))
        return value


def _safe_output(output_root: Path, raw: str, result: CommandResult, label: str) -> Path | None:
    normalized = _safe_relative(raw, label=label, result=result)
    if normalized is None:
        return None
    current = output_root
    for part in normalized.split("/"):
        current = current / part
        if current.exists() or current.is_symlink():
            try:
                metadata = current.lstat()
            except OSError as exc:
                result.add("HARNESS_OUTPUT_READ", label, str(exc))
                return None
            if current.is_symlink() or stat.S_IFMT(metadata.st_mode) not in {stat.S_IFDIR, stat.S_IFREG}:
                result.add("HARNESS_OUTPUT_ESCAPE", label, "output or one of its ancestors is a symlink/special entry")
                return None
    try:
        current.resolve(strict=False).relative_to(output_root.resolve())
    except ValueError:
        result.add("HARNESS_OUTPUT_ESCAPE", label, "output escapes its isolated output root")
        return None
    return current


def _command_environment(
    project_root: Path,
    temp_root: Path,
    output_root: Path,
    python_guard: dict[str, Any] | None,
) -> tuple[dict[str, str], list[str]]:
    environment, scrubbed = _sanitized_environment(project_root)
    environment.update(
        {
            "TEMP": str(temp_root),
            "TMP": str(temp_root),
            "TMPDIR": str(temp_root),
            "PYTHONNOUSERSITE": "1",
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONPYCACHEPREFIX": str(temp_root / "pycache"),
            "CODEX_VERIFICATION_TEMP": str(temp_root),
            "CODEX_VERIFICATION_OUTPUT_ROOT": str(output_root),
        }
    )
    if python_guard is not None:
        environment["PYTHONPATH"] = str(python_guard["root"])
    return environment, scrubbed


def _run_commands(
    plan: dict[str, Any],
    package_root: Path,
    scratch: VerificationScratch,
    staging: Path,
    project_root: Path,
    harness_root: Path,
    guard_baseline: dict[str, Any],
    result: CommandResult,
) -> list[dict[str, Any]]:
    prepared: list[tuple[dict[str, Any], Path, Path, Path, list[str], dict[str, Any] | None]] = []
    for index, command in enumerate(plan["commands"]):
        identifier = command["id"]
        temp_root = scratch.path / "commands" / f"{index:03d}"
        output_root = temp_root / "outputs"
        package_dir = package_root / command.get("cwd", ".")
        try:
            package_dir = package_dir.resolve(strict=True)
            package_dir.relative_to(package_root.resolve())
        except (OSError, ValueError) as exc:
            result.add("HARNESS_CWD", identifier, str(exc))
            continue
        if not package_dir.is_dir():
            result.add("HARNESS_CWD", identifier, "cwd is not a directory")
            continue
        values = {"package_root": str(package_root), "temp_root": str(temp_root), "output_root": str(output_root)}
        diagnostic_count = len(result.diagnostics)
        argv = [_expand(item, values, result, f"$.commands[{index}].argv") for item in command["argv"]]
        if len(result.diagnostics) != diagnostic_count:
            continue
        _undeclared_dependency(
            argv,
            project_root=project_root,
            package_root=package_root,
            package_dir=package_dir,
            temp_root=temp_root,
            output_root=output_root,
            command_index=index,
            result=result,
        )
        entrypoint_diagnostic_count = len(result.diagnostics)
        generic_entrypoint = _package_entrypoint(argv, package_dir=package_dir, package_root=package_root)
        _inspect_generic_entrypoint(
            generic_entrypoint,
            project_root=project_root,
            package_root=package_root,
            command_index=index,
            result=result,
        )
        python_guard: dict[str, Any] | None = None
        if _is_python_executor(argv[0]):
            entrypoint = _python_entrypoint(
                argv,
                package_dir=package_dir,
                package_root=package_root,
                command_index=index,
                result=result,
            )
            if len(result.diagnostics) == entrypoint_diagnostic_count:
                _inspect_python_entrypoint(
                    entrypoint,
                    project_root=project_root,
                    package_root=package_root,
                    package_dir=package_dir,
                    command_index=index,
                    result=result,
                )
            if result.ok:
                try:
                    python_guard = _write_python_audit_guard(
                        temp_root,
                        project_root=project_root,
                        package_root=package_root,
                        output_root=output_root,
                        executable=argv[0],
                    )
                except OSError as exc:
                    result.add("HARNESS_EXECUTION", identifier, f"cannot create Python audit guard: {exc}")
        prepared.append((command, package_dir, temp_root, output_root, argv, python_guard))
    if not result.ok or len(prepared) != len(plan["commands"]):
        return []

    baseline = _tree_snapshot(package_root)
    records: list[dict[str, Any]] = []
    for index, (command, package_dir, temp_root, output_root, argv, python_guard) in enumerate(prepared):
        diagnostic_count = len(result.diagnostics)
        identifier = command["id"]
        if not _guard_unchanged(
            project_root,
            guard_baseline,
            harness_root=harness_root,
            command_id=identifier,
            phase="pre-command",
            result=result,
        ):
            break
        output_root.mkdir(parents=True)
        expected = command.get("expected_exit_codes", [0])
        timed_out = False
        command_environment, scrubbed_environment = _command_environment(
            project_root,
            temp_root,
            output_root,
            python_guard,
        )
        try:
            process = subprocess.run(
                argv,
                cwd=package_dir,
                env=command_environment,
                capture_output=True,
                timeout=command.get("timeout_seconds", 300),
                shell=False,
                check=False,
            )
            return_code = process.returncode
            stdout = process.stdout
            stderr = process.stderr
        except subprocess.TimeoutExpired as exc:
            return_code = None
            stdout = exc.stdout or b""
            stderr = exc.stderr or b""
            timed_out = True
        except OSError as exc:
            return_code = None
            stdout = b""
            stderr = str(exc).encode("utf-8", errors="replace")
        if isinstance(stdout, str):
            stdout = stdout.encode("utf-8", errors="replace")
        if isinstance(stderr, str):
            stderr = stderr.encode("utf-8", errors="replace")
        audit_violation = _AUDIT_MARKER in stderr
        if audit_violation:
            marker_line = next(
                (line.decode("utf-8", errors="replace") for line in stderr.splitlines() if line.startswith(_AUDIT_MARKER)),
                "Python audit guard blocked an undeclared repository dependency",
            )
            result.add("UNDECLARED_DEPENDENCY", identifier, marker_line)
        audit_active = python_guard is None
        if python_guard is not None:
            try:
                audit_active = python_guard["handshake_path"].read_text(encoding="utf-8") == python_guard["handshake_token"]
            except (OSError, UnicodeError):
                audit_active = False
            if not audit_active:
                result.add(
                    "PYTHON_AUDIT_INACTIVE",
                    identifier,
                    "recognized Python command did not activate its per-command filesystem audit guard",
                )
        guard_ok = _guard_unchanged(
            project_root,
            guard_baseline,
            harness_root=harness_root,
            command_id=identifier,
            phase="post-command",
            result=result,
        )
        command_dir = staging / "commands" / f"{index:03d}"
        stdout_hash = atomic_write_bytes(command_dir / "stdout.bin", stdout)
        stderr_hash = atomic_write_bytes(command_dir / "stderr.bin", stderr)
        captured: list[dict[str, Any]] = []
        for output_index, output in enumerate(command.get("outputs", [])):
            raw = output.get("path") if isinstance(output, dict) else output
            required = output.get("required", True) if isinstance(output, dict) else True
            source = _safe_output(output_root, raw, result, f"{identifier}.outputs[{output_index}]")
            if source is None:
                continue
            if not source.exists():
                if required:
                    result.add("HARNESS_OUTPUT_MISSING", raw, "required declared output was not produced")
                captured.append({"path": raw, "status": "MISSING"})
                continue
            if not source.is_file() or source.is_symlink():
                result.add("HARNESS_OUTPUT_ESCAPE", raw, "declared output must be a regular non-symlink file")
                continue
            target = command_dir / "outputs" / Path(*raw.split("/"))
            target.parent.mkdir(parents=True, exist_ok=True)
            with source.open("rb") as input_stream, target.open("xb") as output_stream:
                digest, size = _stream_digest(input_stream, output_stream)
            captured.append({
                "path": raw,
                "status": "CAPTURED",
                "size_bytes": size,
                "sha256": digest,
                "evidence_path": target.relative_to(staging).as_posix(),
            })
        mutation = _tree_snapshot(package_root) != baseline
        passed = not timed_out and return_code in expected and not audit_violation and audit_active and not mutation and guard_ok and len(result.diagnostics) == diagnostic_count
        record = {
            "id": identifier,
            "scenario": command["scenario"],
            "argv": command["argv"],
            "cwd": command.get("cwd", "."),
            "expected_exit_codes": expected,
            "return_code": return_code,
            "status": "PASS" if passed else "FAIL",
            "timed_out": timed_out,
            "isolated_temp_index": index,
            "stdout": {"path": (command_dir / "stdout.bin").relative_to(staging).as_posix(), "sha256": stdout_hash, "size_bytes": len(stdout)},
            "stderr": {"path": (command_dir / "stderr.bin").relative_to(staging).as_posix(), "sha256": stderr_hash, "size_bytes": len(stderr)},
            "outputs": captured,
            "package_tree_mutated": mutation,
            "canonical_guard_status": "PASS" if guard_ok else "FAIL",
            "python_audit_status": (
                "FAIL"
                if audit_violation or not audit_active
                else ("PASS" if python_guard is not None else "NOT_APPLICABLE")
            ),
            "scrubbed_environment_keys": scrubbed_environment,
        }
        records.append(record)
        if timed_out:
            result.add("HARNESS_TIMEOUT", identifier, f"exceeded {command.get('timeout_seconds', 300)} seconds")
        elif return_code not in expected:
            result.add("HARNESS_COMMAND_FAILED", identifier, f"returned {return_code}; expected one of {expected}")
        if mutation:
            result.add("PACKAGE_MUTATION", identifier, "command changed the extracted package tree; remaining commands were not run")
        if mutation or not guard_ok or audit_violation or not audit_active:
            break
    return records


def _toolchain_identity() -> dict[str, Any]:
    executable = Path(sys.executable)
    return {
        "python_version": platform.python_version(),
        "python_implementation": platform.python_implementation(),
        "platform": platform.platform(),
        "executable_name": executable.name,
        "executable_sha256": sha256_file(executable) if executable.is_file() else None,
        "isolation_scope": "clean extracted-package cwd plus per-command temp roots and scrubbed Python/PIP environment; not an OS sandbox",
    }


def _promote_attempt(staging: Path, attempt_path: Path) -> None:
    if attempt_path.exists():
        raise FileExistsError(f"verification attempt already exists: {attempt_path}")
    attempt_path.parent.mkdir(parents=True, exist_ok=True)
    os.replace(staging, attempt_path)


def prepare_verification(
    project_root: Path,
    run_dir: Path,
    plan_path: Path,
    *,
    contract_path: Path | None = None,
    manifest_path: Path | None = None,
    inspection_path: Path | None = None,
    archive_path: Path | None = None,
    scratch_root: Path | None = None,
    attempt_id: str | None = None,
    timestamp: str | None = None,
) -> CommandResult:
    """Prepare immutable deterministic evidence from one inspected archive.

    This supplies evidence to an independent verifier; it does not perform the
    verifier's semantic assessment.
    """

    result = CommandResult(command="prepare-verification")
    result.extend(run_forward_diagnostics(project_root, run_dir, allow_missing_state=True))
    if not result.ok:
        return result
    attempt_id = attempt_id or _new_attempt_id()
    if ATTEMPT_ID_PATTERN.fullmatch(attempt_id) is None:
        result.add("HARNESS_ATTEMPT_ID", "attempt_id", "must be a safe 1-96 character identifier")
        return result
    if not plan_path.is_file():
        result.add("HARNESS_PLAN_MISSING", str(plan_path), "verification plan does not exist")
        return result
    try:
        plan_data = read_structured(plan_path)
    except InputError as exc:
        result.add("PARSE_ERROR", str(plan_path), str(exc))
        return result
    plan = _validate_plan(plan_data, result)
    if plan is None or not result.ok:
        return result
    for prefix, explicit_path in (
        ("contract", contract_path),
        ("manifest", manifest_path),
        ("inspection", inspection_path),
        ("archive", archive_path),
    ):
        if explicit_path is None:
            continue
        try:
            explicit = resolve_within(project_root, explicit_path, must_exist=True)
            explicit_relative = repository_relative(project_root, explicit)
        except InputError as exc:
            result.add("HARNESS_BINDING", f"explicit.{prefix}_path", str(exc))
            continue
        if plan["binding"].get(f"{prefix}_path") != explicit_relative:
            result.add("HARNESS_BINDING", f"explicit.{prefix}_path", f"does not equal the plan binding {plan['binding'].get(f'{prefix}_path')!r}")
    if not result.ok:
        return result

    harness_root = run_dir / "40_verification" / "harness"
    attempt_path = harness_root / "attempts" / attempt_id
    cleanup_path = harness_root / "cleanup" / f"{attempt_id}.json"
    latest_path = harness_root / "latest.json"
    if attempt_path.exists() or cleanup_path.exists():
        result.add("HARNESS_ATTEMPT_EXISTS", attempt_id, "attempt IDs are immutable and cannot be reused")
        return result
    harness_root.mkdir(parents=True, exist_ok=True)
    atomic_write_json(
        latest_path,
        {
            "schema_version": "1.0",
            "artifact_type": "verification-harness-latest",
            "status": "PENDING",
            "attempt_id": attempt_id,
            "attempt_path": repository_relative(project_root, attempt_path),
            "archive_sha256": plan["binding"]["archive_sha256"],
        },
    )
    attempt_path.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{attempt_id}.", dir=attempt_path.parent))
    scratch: VerificationScratch | None = None
    records: list[dict[str, Any]] = []
    inventory: list[dict[str, Any]] = []
    extracted = False
    guard_baseline: dict[str, Any] | None = None
    inputs = _validate_inputs(project_root, run_dir, plan, result)
    if inputs is not None:
        contract_path, manifest_path, inspection_path, archive_path, manifest, infos, inventory = inputs
    else:
        contract_path = manifest_path = inspection_path = archive_path = None
        manifest = {}
        infos = []
    if result.ok and all(path is not None for path in (contract_path, manifest_path, inspection_path, archive_path)):
        guard_baseline = _guard_baseline(
            project_root,
            run_dir,
            manifest,
            contract_path=contract_path,
            manifest_path=manifest_path,
            inspection_path=inspection_path,
            archive_path=archive_path,
            harness_root=harness_root,
            result=result,
        )
    if result.ok and archive_path is not None:
        try:
            scratch = allocate_verification_scratch(scratch_root=scratch_root)
            if sha256_file(archive_path) != plan["binding"]["archive_sha256"]:
                raise OSError("archive SHA-256 changed between reconciliation and extraction")
            extraction_root = _extract_once(archive_path, infos, inventory, scratch)
            extracted = True
            package_root = extraction_root / manifest["artifact_root"]
            if not package_root.is_dir():
                result.add("ARCHIVE_ROOT", str(package_root), "declared package root was not extracted as a directory")
            else:
                records = _run_commands(
                    plan,
                    package_root,
                    scratch,
                    staging,
                    project_root,
                    harness_root,
                    guard_baseline,
                    result,
                )
        except (OSError, ScratchError, zipfile.BadZipFile) as exc:
            result.add("HARNESS_EXECUTION", attempt_id, str(exc))

    status = "PASS" if result.ok and len(records) == len(plan["commands"]) and all(item["status"] == "PASS" for item in records) else "FAIL"
    if status == "FAIL":
        result.ok = False
    summary = {
        "schema_version": "1.0",
        "artifact_type": "verification-harness-attempt",
        "attempt_id": attempt_id,
        "status": status,
        "prepared_at": _now(timestamp),
        "independent_verifier_judgment": "NOT_PERFORMED",
        "plan_path": repository_relative(project_root, plan_path),
        "plan_sha256": sha256_file(plan_path),
        "binding": plan["binding"],
        "archive_reconciliation": {
            "status": "PASS" if inputs is not None and not any(item.code.startswith(("ARCHIVE", "MANIFEST", "ENTRY", "REQUIRED", "PROHIBITED", "SOURCE", "INSPECTION", "CONTRACT")) for item in result.diagnostics) else "FAIL",
            "entry_count": len(inventory),
            "entries": inventory,
        },
        "extraction_count": 1 if extracted else 0,
        "command_count": len(records),
        "passed_count": sum(item["status"] == "PASS" for item in records),
        "failed_count": sum(item["status"] == "FAIL" for item in records),
        "commands": records,
        "toolchain": _toolchain_identity(),
        "diagnostics": [item.as_dict() for item in sorted(result.diagnostics)],
    }
    atomic_write_json(staging / "summary.json", summary)
    attempt_summary_sha = sha256_file(staging / "summary.json")
    promoted = False
    try:
        _promote_attempt(staging, attempt_path)
        promoted = True
    except OSError as exc:
        shutil.rmtree(staging, ignore_errors=True)
        result.add("HARNESS_PROMOTION", str(attempt_path), str(exc))

    cleanup_status = "NOT_ALLOCATED"
    cleanup_message = "No verification scratch was allocated."
    scratch_path = str(scratch.path) if scratch is not None else None
    if scratch is not None:
        try:
            scratch.cleanup()
            cleanup_status = "PASS"
            cleanup_message = "Owned verification scratch was removed."
        except ScratchError as exc:
            cleanup_status = "FAIL"
            cleanup_message = str(exc)
            result.add("HARNESS_CLEANUP", str(scratch.path), str(exc))
    atomic_write_json(
        cleanup_path,
        {
            "schema_version": "1.0",
            "artifact_type": "verification-harness-cleanup",
            "attempt_id": attempt_id,
            "status": cleanup_status,
            "message": cleanup_message,
            "scratch_path": scratch_path,
            "scratch_retained": scratch is not None and scratch.path.exists(),
            "attempt_promoted": promoted,
        },
    )
    final_status = "PASS" if status == "PASS" and promoted and cleanup_status == "PASS" else "FAIL"
    if final_status == "FAIL":
        result.ok = False
    atomic_write_json(
        latest_path,
        {
            "schema_version": "1.0",
            "artifact_type": "verification-harness-latest",
            "status": final_status,
            "attempt_id": attempt_id,
            "attempt_path": repository_relative(project_root, attempt_path),
            "attempt_promoted": promoted,
            "attempt_summary_sha256": attempt_summary_sha if promoted else None,
            "cleanup_path": repository_relative(project_root, cleanup_path),
            "cleanup_status": cleanup_status,
            "archive_sha256": plan["binding"]["archive_sha256"],
            "independent_verifier_judgment": "NOT_PERFORMED",
            "diagnostics": [item.as_dict() for item in sorted(result.diagnostics)],
        },
    )
    result.data = {
        "status": final_status,
        "attempt_id": attempt_id,
        "attempt_path": str(attempt_path),
        "attempt_promoted": promoted,
        "summary_path": str(attempt_path / "summary.json") if promoted else None,
        "cleanup_path": str(cleanup_path),
        "cleanup_status": cleanup_status,
        "latest_path": str(latest_path),
        "archive_sha256": plan["binding"]["archive_sha256"],
        "extraction_count": 1 if extracted else 0,
    }
    return result
