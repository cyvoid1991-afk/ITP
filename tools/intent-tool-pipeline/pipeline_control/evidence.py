"""Read-only integrity checks for deterministic gate-evidence files."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .result import CommandResult
from .io_utils import InputError, read_structured, resolve_within, sha256_file


def passing_test_results(
    path: Path,
    project_root: Path | None = None,
) -> tuple[bool, str, dict[str, Any] | None]:
    if not path.is_file():
        return False, f"required evidence file is missing: {path}", None
    try:
        data = read_structured(path)
    except InputError as exc:
        return False, str(exc), None
    if not isinstance(data, dict) or data.get("artifact_type") != "deterministic-test-results":
        return False, "test evidence must be a deterministic-test-results object", data if isinstance(data, dict) else None
    commands = data.get("commands")
    if not isinstance(commands, list) or not commands:
        return False, "test evidence must retain at least one command result", data
    if data.get("status") != "PASS":
        return False, f"test result status must be PASS; found {data.get('status')!r}", data
    if any(not isinstance(item, dict) or item.get("status") != "PASS" for item in commands):
        return False, "every retained command result must have status PASS", data
    if data.get("command_count") != len(commands):
        return False, "command_count does not match the retained command results", data
    if data.get("passed_count") != len(commands) or data.get("failed_count") != 0:
        return False, "passing and failing counts do not describe an all-PASS result", data
    if not isinstance(data.get("result_path"), str) or not data.get("result_path"):
        return False, "test evidence must preserve its repository-relative result_path", data
    if not isinstance(data.get("plan_path"), str) or not isinstance(data.get("plan_sha256"), str):
        return False, "test evidence must preserve plan_path and plan_sha256", data
    for command in commands:
        if not isinstance(command.get("artifact_paths"), list):
            return False, f"command {command.get('id')!r} must preserve artifact_paths, including an explicit empty list", data
    if project_root is not None:
        try:
            evidence_path = resolve_within(project_root, data["result_path"], must_exist=True)
            plan_path = resolve_within(project_root, data["plan_path"], must_exist=True)
        except InputError as exc:
            return False, str(exc), data
        if evidence_path.resolve() != path.resolve():
            return False, "persisted result_path does not identify this evidence file", data
        if sha256_file(plan_path) != data["plan_sha256"]:
            return False, "test plan changed after the retained execution", data
    return True, "", data


def passing_package_inspection(project_root: Path, path: Path) -> tuple[bool, str, dict[str, Any] | None]:
    if not path.is_file():
        return False, f"required evidence file is missing: {path}", None
    try:
        inspection = read_structured(path)
    except InputError as exc:
        return False, str(exc), None
    if not isinstance(inspection, dict) or inspection.get("artifact_type") != "package-inspection":
        return False, "inspection evidence must be a package-inspection object", inspection if isinstance(inspection, dict) else None
    if inspection.get("status") != "PASS":
        return False, f"package inspection status must be PASS; found {inspection.get('status')!r}", inspection
    if inspection.get("diagnostics") not in ([], None):
        return False, "passing package inspection must not retain diagnostics", inspection
    if inspection.get("prohibited_entry_count") != 0:
        return False, "passing package inspection must report zero prohibited entries", inspection
    archive_value = inspection.get("archive_path")
    manifest_value = inspection.get("manifest_path")
    if not isinstance(archive_value, str) or not isinstance(manifest_value, str):
        return False, "inspection must identify repository-relative archive and manifest paths", inspection
    try:
        archive_path = resolve_within(project_root, archive_value, must_exist=True)
        manifest_path = resolve_within(project_root, manifest_value, must_exist=True)
    except InputError as exc:
        return False, str(exc), inspection
    try:
        manifest = read_structured(manifest_path)
    except InputError as exc:
        return False, str(exc), inspection
    if not isinstance(manifest, dict) or manifest.get("artifact_type") != "release-manifest":
        return False, "inspection manifest must be a release-manifest object", inspection
    archive_hash = sha256_file(archive_path)
    if inspection.get("archive_sha256") != archive_hash or manifest.get("archive_sha256") != archive_hash:
        return False, "archive content changed after packaging or inspection", inspection
    if inspection.get("entry_count") != manifest.get("entry_count"):
        return False, "inspection and manifest entry counts differ", inspection
    return True, "", inspection


def reconcile_source(project_root: Path, manifest: dict[str, Any], inventory: list[dict[str, Any]], result: CommandResult) -> None:
    """Match canonical packaged entries to an already validated inventory."""
    raw_root = manifest.get("source_root")
    root_name = manifest.get("artifact_root")
    if not isinstance(raw_root, str) or not isinstance(root_name, str):
        result.add("SOURCE_BINDING", "manifest.source_root", "source_root and artifact_root must be strings")
        return
    try:
        source_root = resolve_within(project_root, raw_root, must_exist=True)
    except InputError as exc:
        result.add("SOURCE_BINDING", "manifest.source_root", str(exc))
        return
    if not source_root.is_dir() or source_root.is_symlink():
        result.add("SOURCE_BINDING", str(source_root), "canonical source root must be a non-symlink directory")
        return
    prefix = f"{root_name}/"
    if not isinstance(inventory, list) or not inventory:
        result.add("SOURCE_BINDING", "manifest.entries", "must contain a non-empty source inventory")
        return
    for item in inventory:
        if not isinstance(item, dict) or not isinstance(item.get("path"), str) or not isinstance(item.get("sha256"), str) or type(item.get("size_bytes")) is not int:
            result.add("SOURCE_BINDING", "manifest.entries", "entry must contain path, SHA-256 and integer size")
            continue
        name = item["path"]
        if not name.startswith(prefix):
            result.add("SOURCE_BINDING", name, "source entry must be within the artifact root")
            continue
        relative = name[len(prefix):]
        try:
            path = resolve_within(source_root, relative, must_exist=True)
            path.relative_to(source_root.resolve())
        except (InputError, ValueError) as exc:
            result.add("SOURCE_MISMATCH", name, str(exc))
            continue
        if not path.is_file() or path.is_symlink():
            result.add("SOURCE_MISMATCH", name, "canonical source entry is not a regular non-symlink file")
            continue
        try:
            source_hash = sha256_file(path)
            source_size = path.stat().st_size
        except OSError as exc:
            result.add("SOURCE_MISMATCH", name, str(exc))
            continue
        if source_hash != item["sha256"] or source_size != item["size_bytes"]:
            result.add("SOURCE_MISMATCH", name, "canonical source bytes differ from the inspected archive")
