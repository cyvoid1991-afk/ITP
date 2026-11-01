"""Deterministic file, path, hashing, and structured-data helpers."""

from __future__ import annotations

import hashlib
import json
import os
import posixpath
import re
import tempfile
from pathlib import Path
from typing import Any

import yaml


class InputError(ValueError):
    """Raised when a control-plane input cannot be read safely."""


def normalize_repository_reference(value: str | Path, *, allow_empty: bool = False) -> str:
    """Return a safe, slash-normalized repository-relative reference.

    Both Windows and POSIX separators are accepted as input so persisted
    references have one identity on every host.  Absolute, drive-qualified,
    UNC, and traversal references are rejected before they reach ``Path``.
    """

    raw = str(value).strip()
    if "\x00" in raw:
        raise InputError("path reference must not contain NUL bytes")
    slash_value = raw.replace("\\", "/")
    if slash_value.startswith("/") or re.match(r"^[A-Za-z]:", slash_value):
        raise InputError(f"path must be repository-relative: {value}")
    normalized = posixpath.normpath(slash_value)
    if normalized in {"", "."}:
        if allow_empty:
            return ""
        raise InputError("path reference must not be empty")
    if normalized == ".." or normalized.startswith("../"):
        raise InputError(f"path must be repository-relative: {value}")
    return normalized.strip("/")


def read_structured(path: Path) -> Any:
    """Read JSON or YAML based on the filename extension."""

    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise InputError(f"cannot read {path}: {exc}") from exc

    try:
        if path.suffix.lower() == ".json":
            return json.loads(text)
        if path.suffix.lower() in {".yaml", ".yml"}:
            return yaml.safe_load(text)
    except (json.JSONDecodeError, yaml.YAMLError) as exc:
        raise InputError(f"cannot parse {path}: {exc}") from exc
    raise InputError(f"unsupported structured-data extension: {path.suffix or '<none>'}")


def parse_structured_bytes(payload: bytes, path: Path) -> Any:
    """Parse the exact captured return bytes that will be hashed and persisted."""
    try:
        text = payload.decode("utf-8")
        if path.suffix.lower() == ".json":
            return json.loads(text)
        if path.suffix.lower() in {".yaml", ".yml"}:
            return yaml.safe_load(text)
    except (UnicodeError, json.JSONDecodeError, yaml.YAMLError) as exc:
        raise InputError(f"cannot parse captured {path}: {exc}") from exc
    raise InputError(f"unsupported structured-data extension: {path.suffix or '<none>'}")


def atomic_write_json(path: Path, value: Any) -> None:
    """Write canonical JSON using an atomic same-directory replacement."""

    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(value, indent=2, ensure_ascii=False, sort_keys=False) + "\n"
    handle = tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        newline="\n",
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".tmp",
        delete=False,
    )
    temporary_path = Path(handle.name)
    try:
        with handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_path, path)
    except Exception:
        temporary_path.unlink(missing_ok=True)
        raise


def sha256_bytes(payload: bytes) -> str:
    """Return the SHA-256 identity of an in-memory payload."""

    return hashlib.sha256(payload).hexdigest()


def atomic_write_bytes(path: Path, payload: bytes) -> str:
    """Persist complete bytes with an integrity check and same-directory replace."""

    path.parent.mkdir(parents=True, exist_ok=True)
    expected_sha256 = sha256_bytes(payload)
    handle = tempfile.NamedTemporaryFile(
        mode="wb",
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".tmp",
        delete=False,
    )
    temporary_path = Path(handle.name)
    try:
        with handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        if sha256_file(temporary_path) != expected_sha256:
            raise OSError("temporary payload failed its SHA-256 integrity check")
        os.replace(temporary_path, path)
    except Exception:
        temporary_path.unlink(missing_ok=True)
        raise
    return expected_sha256


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def resolve_within(project_root: Path, value: str | Path, *, must_exist: bool = False) -> Path:
    """Resolve a path while preventing traversal outside the project root."""

    root = project_root.resolve()
    candidate = Path(value)
    if not candidate.is_absolute():
        normalized = normalize_repository_reference(value, allow_empty=True)
        candidate = root / Path(normalized)
    candidate = candidate.resolve(strict=False)
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise InputError(f"path escapes project root: {value}") from exc
    if must_exist and not candidate.exists():
        raise InputError(f"path does not exist: {value}")
    return candidate


def repository_relative(project_root: Path, path: Path) -> str:
    return path.resolve(strict=False).relative_to(project_root.resolve()).as_posix()


def require_mapping(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise InputError(f"{label} must be an object/mapping")
    return value
