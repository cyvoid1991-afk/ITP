"""Stable result and diagnostic types shared by all control-plane commands."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, order=True)
class Diagnostic:
    """One machine-readable validation or execution finding."""

    code: str
    path: str
    message: str

    def as_dict(self) -> dict[str, str]:
        return {"code": self.code, "path": self.path, "message": self.message}


@dataclass
class CommandResult:
    """Normalized command result used by both JSON and human renderers."""

    command: str
    ok: bool = True
    diagnostics: list[Diagnostic] = field(default_factory=list)
    data: dict[str, Any] = field(default_factory=dict)

    def add(self, code: str, path: str, message: str) -> None:
        self.ok = False
        self.diagnostics.append(Diagnostic(code=code, path=path, message=message))

    def extend(self, diagnostics: list[Diagnostic]) -> None:
        if diagnostics:
            self.ok = False
            self.diagnostics.extend(diagnostics)

    def as_dict(self) -> dict[str, Any]:
        return {
            "command": self.command,
            "ok": self.ok,
            "diagnostics": [item.as_dict() for item in sorted(self.diagnostics)],
            "data": self.data,
        }
