"""Preflight run writers before executing commands or creating evidence."""

from pathlib import Path

from .io_utils import InputError, read_structured
from .result import Diagnostic
from .validation import validate_control_metadata


def run_mutation_diagnostics(run_dir: Path, *, allow_missing_state: bool = False) -> list[Diagnostic]:
    # Import lazily: finalization recovery owns journal interpretation and may
    # validate state while a transaction is still PREPARED.
    from .finalize_journal import pending_transaction_diagnostics

    diagnostics = pending_transaction_diagnostics(run_dir)
    state_path = run_dir / "30_execution/run_state.json"
    if not state_path.exists() and allow_missing_state:
        return diagnostics
    try:
        state = read_structured(state_path)
    except InputError as exc:
        return diagnostics + [Diagnostic("STATE_READ", str(state_path), str(exc))]
    return diagnostics + validate_control_metadata(state)


def run_forward_diagnostics(project_root: Path, run_dir: Path, *, allow_missing_state: bool = False) -> list[Diagnostic]:
    """Forward consumers additionally require current active procedures.

Boundary capture/finalization and coordination of earlier-stage repair use the
pure preflight, retaining their existing provenance and transition checks.
"""
    diagnostics = run_mutation_diagnostics(run_dir, allow_missing_state=allow_missing_state)
    state_path = run_dir / "30_execution/run_state.json"
    if diagnostics or not state_path.is_file():
        return diagnostics
    from .procedures import active_procedure_diagnostics

    return diagnostics + active_procedure_diagnostics(project_root, run_dir, read_structured(state_path), current=True)
