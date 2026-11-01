"""Read-only preflight of coherent local-patch installation states."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .io_utils import InputError, sha256_file


def validate_patch(data: dict[str, Any], entries: dict[str, dict], safe_path) -> None:
    operations, states = data.get("operations"), data.get("supported_states")
    if not isinstance(operations, list) or not operations or not isinstance(states, list) or not states:
        raise InputError("PATCH_CONTRACT: operations and supported_states must be nonempty arrays")
    paths: set[str] = set()
    used_payloads: set[str] = set()
    for operation in operations:
        if not isinstance(operation, dict):
            raise InputError("PATCH_OPERATION: expected an object")
        path = safe_path(operation.get("path"))
        if path.casefold() in paths:
            raise InputError("PATCH_OPERATION: duplicate target path")
        paths.add(path.casefold())
        action, payload = operation.get("action"), operation.get("payload")
        if not isinstance(action, str) or action not in {"add", "replace", "remove"}:
            raise InputError("PATCH_OPERATION: unsupported action")
        if action == "remove":
            if payload is not None:
                raise InputError("PATCH_OPERATION: removals must have null payload")
        elif not isinstance(payload, str) or payload not in entries or entries[payload].get("source_path") is None:
            raise InputError("PATCH_OPERATION: payload must identify packaged authoritative source")
        else:
            if payload in used_payloads:
                raise InputError("PATCH_OPERATION: a payload may only update one target")
            used_payloads.add(payload)
            if entries[payload]["source_path"] != path:
                raise InputError("PATCH_OPERATION: payload source and installation path must match")
    ids: set[str] = set()
    signatures: set[tuple] = set()
    state_paths: set[str] | None = None
    for state in states:
        if not isinstance(state, dict) or not isinstance(state.get("id"), str) or not state["id"].strip() or state["id"] in ids:
            raise InputError("PATCH_STATE: each state requires a unique nonempty id")
        ids.add(state["id"])
        inventory = state.get("files")
        if not isinstance(inventory, list) or not inventory:
            raise InputError("PATCH_STATE: files must be a nonempty inventory")
        mapping: dict[str, str | None] = {}
        for item in inventory:
            if not isinstance(item, dict):
                raise InputError("PATCH_STATE: expected file identity")
            path, digest = safe_path(item.get("path")), item.get("sha256")
            if path.casefold() in {p.casefold() for p in mapping}:
                raise InputError("PATCH_STATE: duplicate file path")
            if digest is not None and (not isinstance(digest, str) or len(digest) != 64 or any(c not in '0123456789abcdef' for c in digest)):
                raise InputError("PATCH_STATE: digest must be SHA-256 or null for absence")
            mapping[path] = digest
        for operation in operations:
            path = operation["path"]
            if path not in mapping:
                raise InputError("PATCH_STATE: every operation needs a before identity")
            absent = mapping[path] is None
            if absent != (operation["action"] == "add"):
                raise InputError("PATCH_STATE: add requires absence; replace/remove require existing bytes")
        if state_paths is not None and set(mapping) != state_paths:
            raise InputError("PATCH_STATE: supported states must cover the same complete path set")
        state_paths = set(mapping)
        signature = tuple(sorted(mapping.items()))
        if signature in signatures:
            raise InputError("PATCH_STATE: duplicate coherent installation state")
        signatures.add(signature)
    # Every exported runtime member must have an installation operation.
    runtime_payloads = {name for name, entry in entries.items() if entry.get("source_path") is not None}
    if runtime_payloads != used_payloads:
        raise InputError("PATCH_OPERATION: every source payload needs exactly one operation")


def preflight_target(data: dict[str, Any], entries: dict[str, dict], target: Path) -> dict:
    """Never modify the installation; return an authorized state only after full checks."""
    target = target.resolve(strict=True)
    if not target.is_dir():
        raise InputError("PATCH_TARGET: target must be an existing directory")
    observed: dict[str, str | None] = {}
    for state in data["supported_states"]:
        for item in state["files"]:
            relative = item["path"]
            path = target / relative
            if any(parent.is_symlink() for parent in [path, *path.parents] if parent != target and parent.is_relative_to(target)):
                raise InputError("PATCH_TARGET: symlinked target paths are unsupported")
            if not path.resolve().is_relative_to(target):
                raise InputError("PATCH_TARGET: target path escapes installation")
            if path.exists() and not path.is_file():
                raise InputError("PATCH_TARGET: expected a regular file or absence")
            observed[relative] = sha256_file(path) if path.is_file() else None
    final = {op["path"]: None if op["action"] == "remove" else entries[op["payload"]]["sha256"] for op in data["operations"]}
    for state in data["supported_states"]:
        before = {item["path"]: item["sha256"] for item in state["files"]}
        if all(observed[path] == digest for path, digest in before.items()):
            return {"status": "PASS", "state": state["id"], "next_action": "BACKUP_THEN_APPLY", "mutated": False}
        after = {**before, **final}
        if all(observed[path] == digest for path, digest in after.items()):
            return {"status": "PASS", "state": state["id"], "next_action": "ALREADY_CURRENT", "mutated": False}
    raise InputError("PATCH_TARGET: unknown, mixed, or newer installation; compare and reconcile without overwriting")
