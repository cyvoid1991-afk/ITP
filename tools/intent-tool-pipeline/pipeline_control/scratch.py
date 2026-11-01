"""Bounded short-lived workspace allocation for clean-package verification."""

from __future__ import annotations

import json
import secrets
import shutil
import stat
import tempfile
from dataclasses import dataclass
from pathlib import Path


SCRATCH_NAMESPACE = "codex-vfy"
SCRATCH_PREFIX = "v-"
OWNERSHIP_MARKER = ".codex-scratch.json"


class ScratchError(RuntimeError):
    """Raised when a verification scratch workspace cannot be handled safely."""


def _is_reparse(path: Path) -> bool:
    metadata = path.lstat()
    attributes = getattr(metadata, "st_file_attributes", 0)
    reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
    return path.is_symlink() or bool(reparse_flag and attributes & reparse_flag)


def _resolved_direct_child(root: Path, workspace: Path) -> tuple[Path, Path]:
    resolved_root = root.resolve(strict=True)
    if _is_reparse(root):
        raise ScratchError(f"scratch root must not be a reparse point: {root}")
    if workspace.parent.resolve(strict=True) != resolved_root:
        raise ScratchError(f"scratch workspace must be a direct child of {resolved_root}: {workspace}")
    if workspace.name in {"", ".", ".."} or not workspace.name.startswith(SCRATCH_PREFIX):
        raise ScratchError(f"scratch workspace has an invalid bounded name: {workspace.name}")
    if _is_reparse(workspace):
        raise ScratchError(f"scratch workspace must not be a reparse point: {workspace}")
    return resolved_root, workspace.resolve(strict=True)


@dataclass(frozen=True)
class VerificationScratch:
    """One owned direct child beneath the framework scratch namespace."""

    root: Path
    path: Path
    token: str

    def cleanup(self) -> None:
        """Remove only this marker-bound workspace, never its namespace root."""

        try:
            _, resolved_workspace = _resolved_direct_child(self.root, self.path)
        except OSError as exc:
            raise ScratchError(f"verification scratch workspace is not inspectable: {self.path}") from exc
        marker = resolved_workspace / OWNERSHIP_MARKER
        try:
            payload = json.loads(marker.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise ScratchError(f"scratch ownership marker is unreadable: {marker}") from exc
        expected = {
            "schema_version": "1.0",
            "artifact_type": "verification-scratch-ownership",
            "token": self.token,
        }
        if payload != expected:
            raise ScratchError(f"scratch ownership marker does not match allocation: {marker}")
        try:
            shutil.rmtree(resolved_workspace)
        except OSError as exc:
            raise ScratchError(f"cannot clean verification scratch workspace {resolved_workspace}: {exc}") from exc

    def __enter__(self) -> VerificationScratch:
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        self.cleanup()


def allocate_verification_scratch(*, scratch_root: Path | None = None) -> VerificationScratch:
    """Allocate a short, uniquely owned verification workspace.

    The default namespace is beneath the operating system's short temporary
    directory. Tests and callers may inject an equally bounded root.
    """

    root = Path(scratch_root) if scratch_root is not None else Path(tempfile.gettempdir()) / SCRATCH_NAMESPACE
    workspace: Path | None = None
    try:
        root.mkdir(parents=True, exist_ok=True)
        if _is_reparse(root):
            raise ScratchError(f"scratch root must not be a reparse point: {root}")
        workspace = Path(tempfile.mkdtemp(prefix=SCRATCH_PREFIX, dir=root))
        token = secrets.token_hex(16)
        marker = workspace / OWNERSHIP_MARKER
        marker.write_text(
            json.dumps(
                {
                    "schema_version": "1.0",
                    "artifact_type": "verification-scratch-ownership",
                    "token": token,
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        _resolved_direct_child(root, workspace)
    except ScratchError:
        raise
    except (OSError, UnicodeError) as exc:
        if workspace is not None:
            try:
                if workspace.parent.resolve(strict=True) == root.resolve(strict=True):
                    shutil.rmtree(workspace)
            except OSError:
                pass
        raise ScratchError(f"cannot allocate verification scratch workspace beneath {root}: {exc}") from exc
    if workspace is None:
        raise ScratchError(f"verification scratch allocation returned no workspace beneath {root}")
    return VerificationScratch(root=root, path=workspace, token=token)
