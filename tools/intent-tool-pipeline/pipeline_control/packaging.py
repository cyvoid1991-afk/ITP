"""Deterministic release archive creation and independent inventory inspection."""

from __future__ import annotations

import fnmatch
import hashlib
import os
import re
import tempfile
import zipfile
from pathlib import Path, PurePosixPath
from typing import Any

from .evidence import passing_test_results
from .io_utils import InputError, atomic_write_json, read_structured, repository_relative, resolve_within, sha256_file
from .result import CommandResult
from .mutation_guard import run_forward_diagnostics


DEFAULT_PROHIBITED_PATTERNS = [
    "**/__pycache__/**",
    "**/.pytest_cache/**",
    "**/pytest-cache-files-*/**",
    "**/*.pyc",
    "**/*.xlsx",
    "**/*.xls",
    "**/*.xlsm",
    "**/*.tmp",
    "**/*.temp",
    "**/*~",
    "**/.DS_Store",
    "**/Thumbs.db",
]
REQUIRED_ARTIFACT_ROLES = {"readme", "source", "tests", "examples"}


def re_drive_path(path: str) -> bool:
    """Return true for ZIP names that resemble a Windows absolute drive path."""

    return re.match(r"^[A-Za-z]:/", path) is not None


def _matches_pattern(path: str, pattern: str) -> bool:
    normalized = path.replace("\\", "/").lstrip("./")
    candidates = {normalized, f"x/{normalized}"}
    return any(fnmatch.fnmatchcase(candidate, pattern) or PurePosixPath(candidate).match(pattern) for candidate in candidates)


def prohibited_reason(path: str, patterns: list[str]) -> str | None:
    normalized = path.replace("\\", "/").strip("/")
    parts = PurePosixPath(normalized).parts
    for part in parts:
        if part in {"__pycache__", ".pytest_cache"} or part.startswith("pytest-cache-files-"):
            return f"prohibited cache segment {part!r}"
    name = parts[-1] if parts else ""
    suffix = PurePosixPath(name).suffix.lower()
    if suffix in {".pyc", ".xlsx", ".xls", ".xlsm", ".tmp", ".temp"}:
        return f"prohibited suffix {suffix!r}"
    if name in {".DS_Store", "Thumbs.db"} or name.endswith("~"):
        return f"prohibited temporary/system file {name!r}"
    for pattern in patterns:
        if _matches_pattern(normalized, pattern):
            return f"matches prohibited pattern {pattern!r}"
    return None


def _validate_package_spec(data: Any, result: CommandResult) -> dict[str, Any] | None:
    if not isinstance(data, dict):
        result.add("PACKAGE_SPEC_TYPE", "$", "package spec must be an object/mapping")
        return None
    if str(data.get("schema_version", "")).split(".", 1)[0] != "1":
        result.add("SCHEMA_UNSUPPORTED", "$.schema_version", "package spec must use schema version 1.x")
    required_fields = ["source_root", "artifact_root", "archive_path", "manifest_path", "include", "required", "approval"]
    for field in required_fields:
        if field not in data:
            result.add("FIELD_REQUIRED", f"$.{field}", "required field is missing")
    artifact_root = data.get("artifact_root")
    if (
        not isinstance(artifact_root, str)
        or not artifact_root
        or "/" in artifact_root
        or "\\" in artifact_root
        or artifact_root in {".", ".."}
    ):
        result.add("ARTIFACT_ROOT", "$.artifact_root", "must be one non-empty archive-root name")
    for field in ("source_root", "archive_path", "manifest_path"):
        if not isinstance(data.get(field), str) or not data.get(field):
            result.add("PATH_VALUE", f"$.{field}", "must be a non-empty project-relative path")
        elif Path(data[field]).is_absolute():
            result.add("PATH_VALUE", f"$.{field}", "must be project-relative")
    for field in ("include", "required"):
        value = data.get(field)
        if not isinstance(value, list) or not value or any(not isinstance(item, str) or not item for item in value):
            result.add("PACKAGE_LIST", f"$.{field}", "must be a non-empty array of path strings")
    excludes = data.get("exclude", [])
    if not isinstance(excludes, list) or any(not isinstance(item, str) or not item for item in excludes):
        result.add("PACKAGE_LIST", "$.exclude", "must be an array of path patterns")
    approval = data.get("approval")
    if not isinstance(approval, dict):
        result.add("PACKAGE_APPROVAL", "$.approval", "must bind the package spec to an approved active contract decision")
    else:
        for field in ("contract_ref", "decision_refs", "required_roles"):
            if field not in approval:
                result.add("FIELD_REQUIRED", f"$.approval.{field}", "required field is missing")
        if not isinstance(approval.get("contract_ref"), str) or not approval.get("contract_ref"):
            result.add("PACKAGE_APPROVAL", "$.approval.contract_ref", "must be a non-empty artifact@version reference")
        decision_refs = approval.get("decision_refs")
        if not isinstance(decision_refs, list) or not decision_refs or any(not isinstance(item, str) or not item for item in decision_refs):
            result.add("PACKAGE_APPROVAL", "$.approval.decision_refs", "must contain at least one approved contract decision ID")
        roles = approval.get("required_roles")
        if not isinstance(roles, dict) or set(roles) != REQUIRED_ARTIFACT_ROLES:
            result.add("PACKAGE_ROLES", "$.approval.required_roles", f"must define exactly {sorted(REQUIRED_ARTIFACT_ROLES)}")
        else:
            role_paths: list[str] = []
            for role in sorted(REQUIRED_ARTIFACT_ROLES):
                paths = roles.get(role)
                if not isinstance(paths, list) or not paths or any(not isinstance(item, str) or not item for item in paths):
                    result.add("PACKAGE_ROLES", f"$.approval.required_roles.{role}", "must contain at least one source-relative path")
                    continue
                role_paths.extend(paths)
            if len(set(role_paths)) != len(role_paths):
                result.add("PACKAGE_ROLES", "$.approval.required_roles", "one path cannot satisfy multiple required artifact roles")
    return data


def _resolve_active_contract(project_root: Path, run_dir: Path, result: CommandResult) -> tuple[dict[str, Any], str] | None:
    state_path = run_dir / "30_execution" / "run_state.json"
    try:
        state = read_structured(state_path)
    except InputError as exc:
        result.add("PACKAGE_APPROVAL", str(state_path), str(exc))
        return None
    if not isinstance(state, dict) or not isinstance(state.get("active_artifacts"), dict):
        result.add("PACKAGE_APPROVAL", str(state_path), "run state lacks active artifact references")
        return None
    entry = state["active_artifacts"].get("product_contract")
    if not isinstance(entry, dict):
        result.add("PACKAGE_APPROVAL", "active_artifacts.product_contract", "an active product contract is required")
        return None
    raw_path = entry.get("path")
    if not isinstance(raw_path, str) or not raw_path:
        result.add("PACKAGE_APPROVAL", "active_artifacts.product_contract.path", "must be a non-empty path")
        return None
    contract_path = (project_root / raw_path).resolve(strict=False)
    if not contract_path.is_file():
        contract_path = (run_dir / raw_path).resolve(strict=False)
    try:
        contract_path.relative_to(run_dir.resolve())
    except ValueError:
        result.add("PACKAGE_APPROVAL", raw_path, "active product contract must remain inside the run directory")
        return None
    try:
        contract = read_structured(contract_path)
    except InputError as exc:
        result.add("PACKAGE_APPROVAL", str(contract_path), str(exc))
        return None
    if not isinstance(contract, dict) or not isinstance(contract.get("artifact"), dict):
        result.add("PACKAGE_APPROVAL", str(contract_path), "product contract metadata is invalid")
        return None
    artifact = contract["artifact"]
    if artifact.get("artifact_id") != entry.get("artifact_id") or artifact.get("version") != entry.get("version"):
        result.add("PACKAGE_APPROVAL", str(contract_path), "active product contract reference does not match its metadata")
        return None
    return contract, f"{artifact.get('artifact_id')}@{artifact.get('version')}"


def _role_path_is_valid(role: str, path: str) -> bool:
    pure = PurePosixPath(path)
    lowered_parts = [part.lower() for part in pure.parts]
    name = pure.name.lower()
    if role == "readme":
        return name == "readme" or name.startswith("readme.")
    if role == "examples":
        return "examples" in lowered_parts or "example" in name
    if role == "tests":
        return "tests" in lowered_parts or name.startswith("test_") or "_test." in name
    if role == "source":
        return not _role_path_is_valid("readme", path) and not _role_path_is_valid("examples", path) and not _role_path_is_valid("tests", path)
    return False


def _validate_approval_binding(
    project_root: Path,
    run_dir: Path,
    approval: Any,
    required: list[str],
    result: CommandResult,
    *,
    path: str,
) -> None:
    if not isinstance(approval, dict):
        result.add("PACKAGE_APPROVAL", path, "approval binding is missing")
        return
    resolved = _resolve_active_contract(project_root, run_dir, result)
    if resolved is None:
        return
    contract, active_ref = resolved
    if approval.get("contract_ref") != active_ref:
        result.add("PACKAGE_APPROVAL", f"{path}.contract_ref", f"must equal active contract {active_ref!r}")
    decisions = {
        item.get("id"): item
        for item in contract.get("decisions", [])
        if isinstance(item, dict) and isinstance(item.get("id"), str)
    }
    for decision_ref in approval.get("decision_refs", []) if isinstance(approval.get("decision_refs"), list) else []:
        decision = decisions.get(decision_ref)
        if not isinstance(decision, dict) or decision.get("status") != "APPROVED":
            result.add("PACKAGE_APPROVAL", f"{path}.decision_refs", f"{decision_ref!r} is not an APPROVED active-contract decision")
    roles = approval.get("required_roles")
    if not isinstance(roles, dict):
        return
    required_set = set(required)
    for role in sorted(REQUIRED_ARTIFACT_ROLES):
        paths = roles.get(role)
        if not isinstance(paths, list):
            continue
        for role_path in paths:
            normalized = PurePosixPath(role_path).as_posix().lstrip("./")
            if normalized not in required_set:
                result.add("PACKAGE_ROLES", f"{path}.required_roles.{role}", f"{normalized!r} must also appear in required")
            if not _role_path_is_valid(role, normalized):
                result.add("PACKAGE_ROLES", f"{path}.required_roles.{role}", f"{normalized!r} does not match the declared artifact role")


def _collect_files(source_root: Path, includes: list[str], patterns: list[str], result: CommandResult) -> list[Path]:
    selected: dict[str, Path] = {}
    for include in includes:
        include_path = PurePosixPath(include)
        if include_path.is_absolute() or ".." in include_path.parts:
            result.add("INCLUDE_PATH", include, "include pattern must remain inside source_root")
            continue
        try:
            matches = list(source_root.glob(include))
        except (OSError, ValueError) as exc:
            result.add("INCLUDE_PATTERN", include, str(exc))
            continue
        if not matches:
            result.add("INCLUDE_EMPTY", include, "include pattern matched no files")
            continue
        for match in matches:
            if match.is_symlink():
                result.add("SYMLINK_PROHIBITED", str(match), "release packages do not follow or include symlinks")
                continue
            candidates = [match] if match.is_file() else list(match.rglob("*")) if match.is_dir() else []
            for candidate in candidates:
                if not candidate.is_file():
                    continue
                if candidate.is_symlink():
                    result.add("SYMLINK_PROHIBITED", str(candidate), "release packages do not follow or include symlinks")
                    continue
                relative = candidate.relative_to(source_root).as_posix()
                if prohibited_reason(relative, patterns) is not None:
                    continue
                selected[relative] = candidate
    return [selected[key] for key in sorted(selected)]


def _write_deterministic_zip(archive_temp: Path, source_root: Path, artifact_root: str, files: list[Path]) -> None:
    with zipfile.ZipFile(
        archive_temp,
        mode="w",
        compression=zipfile.ZIP_DEFLATED,
        compresslevel=9,
        strict_timestamps=True,
    ) as archive:
        for path in files:
            relative = path.relative_to(source_root).as_posix()
            entry_name = f"{artifact_root}/{relative}"
            info = zipfile.ZipInfo(filename=entry_name, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            info.flag_bits |= 0x800
            archive.writestr(info, path.read_bytes(), compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)


def create_package(project_root: Path, run_dir: Path, spec_path: Path) -> CommandResult:
    result = CommandResult(command="package")
    result.extend(run_forward_diagnostics(project_root, run_dir, allow_missing_state=True))
    if not result.ok:
        return result
    tests_path = run_dir / "30_execution" / "test_results.json"
    tests_ok, tests_message, _ = passing_test_results(tests_path, project_root)
    if not tests_ok:
        result.add("TESTS_NOT_PASSING", str(tests_path), tests_message)
        return result
    if not spec_path.is_file():
        result.add("PACKAGE_SPEC_MISSING", str(spec_path), "package spec file does not exist")
        return result
    try:
        raw_spec = read_structured(spec_path)
    except InputError as exc:
        result.add("PARSE_ERROR", str(spec_path), str(exc))
        return result
    spec = _validate_package_spec(raw_spec, result)
    if spec is None or not result.ok:
        return result
    try:
        source_root = resolve_within(project_root, spec["source_root"], must_exist=True)
        archive_path = resolve_within(project_root, spec["archive_path"])
        manifest_path = resolve_within(project_root, spec["manifest_path"])
    except InputError as exc:
        result.add("PACKAGE_PATH", "$", str(exc))
        return result
    if not source_root.is_dir():
        result.add("SOURCE_ROOT", spec["source_root"], "source_root must be a directory")
        return result
    for output, label in ((archive_path, "archive_path"), (manifest_path, "manifest_path")):
        try:
            output.relative_to(source_root)
        except ValueError:
            pass
        else:
            result.add("OUTPUT_INSIDE_SOURCE", f"$.{label}", "package outputs must not be inside source_root")
    inspection_path = run_dir / "50_release" / "package_inspection.json"
    if len({archive_path, manifest_path, inspection_path}) != 3:
        result.add("OUTPUT_COLLISION", "$", "archive, manifest, and fixed inspection paths must be distinct")
    patterns = list(DEFAULT_PROHIBITED_PATTERNS) + list(spec.get("exclude", []))
    files = _collect_files(source_root, spec["include"], patterns, result)
    if not files:
        result.add("PACKAGE_EMPTY", "$.include", "no approved files remain after exclusions")
    selected_relatives = {path.relative_to(source_root).as_posix() for path in files}
    required = [PurePosixPath(item).as_posix().lstrip("./") for item in spec["required"]]
    for path in required:
        if path not in selected_relatives:
            result.add("REQUIRED_ENTRY", path, "required entry is not selected for packaging")
    _validate_approval_binding(
        project_root,
        run_dir,
        spec.get("approval"),
        required,
        result,
        path="$.approval",
    )
    if not result.ok:
        return result

    try:
        atomic_write_json(
            inspection_path,
            {
                "schema_version": "1.0",
                "artifact_type": "package-inspection",
                "status": "PENDING",
                "archive_path": repository_relative(project_root, archive_path),
                "manifest_path": repository_relative(project_root, manifest_path),
                "diagnostics": [],
            },
        )
    except OSError as exc:
        result.add("INSPECTION_INVALIDATION", str(inspection_path), f"cannot invalidate prior inspection: {exc}")
        return result

    archive_path.parent.mkdir(parents=True, exist_ok=True)
    handle = tempfile.NamedTemporaryFile(dir=archive_path.parent, prefix=f".{archive_path.name}.", suffix=".tmp", delete=False)
    archive_temp = Path(handle.name)
    handle.close()
    try:
        _write_deterministic_zip(archive_temp, source_root, spec["artifact_root"], files)
        archive_hash = sha256_file(archive_temp)
        entries = [
            {
                "path": f"{spec['artifact_root']}/{path.relative_to(source_root).as_posix()}",
                "sha256": sha256_file(path),
                "size_bytes": path.stat().st_size,
            }
            for path in files
        ]
        manifest = {
            "schema_version": "1.0",
            "artifact_type": "release-manifest",
            "artifact_root": spec["artifact_root"],
            "archive_path": repository_relative(project_root, archive_path),
            "source_root": repository_relative(project_root, source_root),
            "archive_sha256": archive_hash,
            "entry_count": len(entries),
            "entries": entries,
            "required_entries": [f"{spec['artifact_root']}/{path}" for path in required],
            "prohibited_patterns": patterns,
            "approval": spec["approval"],
        }
        os.replace(archive_temp, archive_path)
        atomic_write_json(manifest_path, manifest)
    except (OSError, ValueError, zipfile.BadZipFile) as exc:
        archive_temp.unlink(missing_ok=True)
        result.add("PACKAGE_WRITE", str(archive_path), str(exc))
        return result
    result.data = {
        "status": "PASS",
        "archive_path": str(archive_path),
        "manifest_path": str(manifest_path),
        "archive_sha256": archive_hash,
        "entry_count": len(entries),
        "inspection_status": "PENDING",
    }
    return result


def inspect_package(
    project_root: Path,
    run_dir: Path,
    manifest_path: Path,
    *,
    archive_path: Path | None = None,
    output_path: Path | None = None,
) -> CommandResult:
    result = CommandResult(command="inspect-package")
    result.extend(run_forward_diagnostics(project_root, run_dir, allow_missing_state=True))
    if not result.ok:
        return result
    if not manifest_path.is_file():
        result.add("MANIFEST_MISSING", str(manifest_path), "release manifest does not exist")
        return result
    try:
        manifest = read_structured(manifest_path)
    except InputError as exc:
        result.add("PARSE_ERROR", str(manifest_path), str(exc))
        return result
    if not isinstance(manifest, dict) or manifest.get("artifact_type") != "release-manifest":
        result.add("MANIFEST_TYPE", str(manifest_path), "manifest must be a release-manifest object")
        return result
    try:
        effective_archive = archive_path or resolve_within(project_root, manifest.get("archive_path", ""), must_exist=True)
    except InputError as exc:
        result.add("ARCHIVE_PATH", "manifest.archive_path", str(exc))
        return result
    if not effective_archive.is_file():
        result.add("ARCHIVE_MISSING", str(effective_archive), "release archive does not exist")
        return result

    expected_entries_raw = manifest.get("entries")
    if not isinstance(expected_entries_raw, list):
        result.add("MANIFEST_ENTRIES", "manifest.entries", "must be an array")
        return result
    expected_entries = {
        item.get("path"): item
        for item in expected_entries_raw
        if isinstance(item, dict) and isinstance(item.get("path"), str)
    }
    if len(expected_entries) != len(expected_entries_raw):
        result.add("MANIFEST_ENTRIES", "manifest.entries", "contains invalid or duplicate entry records")
    required_entries = manifest.get("required_entries")
    if not isinstance(required_entries, list) or any(not isinstance(item, str) for item in required_entries):
        result.add("REQUIRED_ENTRY", "manifest.required_entries", "must be an array of entry-path strings")
        required_entries = []
    artifact_root = manifest.get("artifact_root")
    prefix = f"{artifact_root}/" if isinstance(artifact_root, str) and artifact_root else ""
    source_required: list[str] = []
    for item in required_entries:
        if not prefix or not item.startswith(prefix):
            result.add("REQUIRED_ENTRY", "manifest.required_entries", f"{item!r} is outside the declared artifact root")
        else:
            source_required.append(item[len(prefix) :])
    _validate_approval_binding(
        project_root,
        run_dir,
        manifest.get("approval"),
        source_required,
        result,
        path="manifest.approval",
    )
    try:
        actual_hash = sha256_file(effective_archive)
    except OSError as exc:
        result.add("ARCHIVE_READ", str(effective_archive), str(exc))
        return result
    if actual_hash != manifest.get("archive_sha256"):
        result.add("ARCHIVE_HASH", str(effective_archive), "archive SHA-256 does not match the manifest")
    prohibited_patterns = manifest.get("prohibited_patterns")
    if not isinstance(prohibited_patterns, list) or any(not isinstance(item, str) for item in prohibited_patterns):
        result.add("MANIFEST_POLICY", "manifest.prohibited_patterns", "must be an array of path-pattern strings")
        prohibited_patterns = list(DEFAULT_PROHIBITED_PATTERNS)
    actual_entries: dict[str, dict[str, Any]] = {}
    prohibited: list[str] = []
    try:
        with zipfile.ZipFile(effective_archive, "r") as archive:
            for info in archive.infolist():
                raw_name = info.filename.replace("\\", "/")
                normalized = raw_name.strip("/")
                parts = PurePosixPath(normalized).parts
                if not normalized or info.is_dir():
                    continue
                if raw_name.startswith("/") or re_drive_path(raw_name) or ".." in parts:
                    result.add("ARCHIVE_UNSAFE_PATH", normalized, "entry is absolute or contains parent traversal")
                    continue
                if normalized in actual_entries:
                    result.add("ARCHIVE_DUPLICATE", normalized, "archive contains a duplicate entry")
                    continue
                payload = archive.read(info)
                actual_entries[normalized] = {
                    "path": normalized,
                    "sha256": hashlib.sha256(payload).hexdigest(),
                    "size_bytes": len(payload),
                }
                reason = prohibited_reason(normalized, prohibited_patterns)
                if reason:
                    prohibited.append(normalized)
                    result.add("PROHIBITED_ENTRY", normalized, reason)
    except (OSError, zipfile.BadZipFile, RuntimeError) as exc:
        result.add("ARCHIVE_READ", str(effective_archive), str(exc))

    expected_paths = set(expected_entries)
    actual_paths = set(actual_entries)
    if expected_paths != actual_paths:
        result.add(
            "MANIFEST_INVENTORY",
            str(effective_archive),
            f"archive and manifest inventories differ; missing={sorted(expected_paths - actual_paths)}, extra={sorted(actual_paths - expected_paths)}",
        )
    for path in sorted(expected_paths & actual_paths):
        expected = expected_entries[path]
        actual = actual_entries[path]
        if expected.get("sha256") != actual["sha256"] or expected.get("size_bytes") != actual["size_bytes"]:
            result.add("ENTRY_HASH", path, "entry content hash or size does not match the manifest")
    if any(item not in actual_paths for item in required_entries):
        missing = [item for item in required_entries if item not in actual_paths]
        result.add("REQUIRED_ENTRY", "manifest.required_entries", f"required archive entries are missing: {missing}")
    roots = {PurePosixPath(path).parts[0] for path in actual_paths if PurePosixPath(path).parts}
    if roots != {manifest.get("artifact_root")}:
        result.add("ARCHIVE_ROOT", str(effective_archive), f"expected one root {manifest.get('artifact_root')!r}; found {sorted(roots)}")
    if manifest.get("entry_count") != len(actual_entries):
        result.add("ENTRY_COUNT", "manifest.entry_count", "does not match the archive file-entry count")

    inspection_path = output_path or (run_dir / "50_release" / "package_inspection.json")
    payload = {
        "schema_version": "1.0",
        "artifact_type": "package-inspection",
        "status": "PASS" if result.ok else "FAIL",
        "archive_path": repository_relative(project_root, effective_archive),
        "manifest_path": repository_relative(project_root, manifest_path),
        "archive_sha256": actual_hash,
        "entry_count": len(actual_entries),
        "entries": [actual_entries[key] for key in sorted(actual_entries)],
        "prohibited_entry_count": len(prohibited),
        "diagnostics": [item.as_dict() for item in sorted(result.diagnostics)],
    }
    try:
        atomic_write_json(inspection_path, payload)
    except OSError as exc:
        result.add("INSPECTION_WRITE", str(inspection_path), str(exc))
        return result
    result.data = {
        "status": payload["status"],
        "inspection_path": str(inspection_path),
        "archive_path": str(effective_archive),
        "entry_count": len(actual_entries),
        "prohibited_entry_count": len(prohibited),
    }
    return result
