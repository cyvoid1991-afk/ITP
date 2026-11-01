"""Command-line interface for the deterministic delivery control plane."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from .artifacts import SEMANTIC_ARTIFACTS, finalize_semantic_return, persist_semantic_artifact
from .boundary import ROLE_POLICIES, finish_role_boundary, start_role_boundary
from .io_utils import InputError, read_structured, resolve_within
from .packaging import create_package, inspect_package
from .result import CommandResult
from .state import update_bounce_back, update_state
from .test_runner import run_test_plan
from .verifier_harness import prepare_verification
from .validation import STAGE_IDS, STAGE_STATUSES, validate_contract_file, validate_run_directory


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pipeline_ops.py",
        description="Deterministic role boundaries, artifact activation, structural gates, tests, and release packaging.",
    )
    parser.add_argument(
        "--project-root",
        default=str(Path(__file__).resolve().parents[1]),
        help="Project root used to resolve all relative paths (default: intent-tool-pipeline tool directory).",
    )
    parser.add_argument(
        "--format",
        choices=("human", "json"),
        default="human",
        help="Render a concise human report or a machine-readable JSON result.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate_run = subparsers.add_parser("validate-run", help="Validate the fixed run layout and active artifacts.")
    validate_run.add_argument("--run-dir", required=True, help="Run directory under workspace/build_runs/.")

    validate_contract = subparsers.add_parser("validate-contract", help="Validate a product-contract YAML or JSON file.")
    validate_contract.add_argument("--contract", required=True, help="Product contract YAML or JSON path.")

    loader = subparsers.add_parser("load-role-assignment", help="Read a current registry-bound 1.2 assignment and original procedures without writing.")
    loader.add_argument("--run-dir", required=True)
    loader.add_argument("--baseline-sha256", required=True)
    loader.add_argument("--role", required=True, choices=sorted(ROLE_POLICIES))
    loader.add_argument("--invocation-ref", required=True)

    state = subparsers.add_parser("update-state", help="Validate and atomically apply one allowed state transition.")
    state.add_argument("--run-dir", required=True, help="Run directory containing 30_execution/run_state.json.")
    state.add_argument("--to-stage", required=True, choices=STAGE_IDS, help="Target pipeline stage.")
    state.add_argument("--stage-status", required=True, choices=sorted(STAGE_STATUSES), help="Target stage status.")
    state.add_argument("--gate-status", required=True, choices=sorted(STAGE_STATUSES), help="Target gate status.")
    state.add_argument("--evidence-ref", action="append", default=[], help="Gate evidence reference; repeat as needed.")
    state.add_argument("--rationale", required=True, help="Recorded gate rationale.")
    state.add_argument("--next-action", required=True, help="Next allowed action recorded in run state.")
    state.add_argument("--timestamp", help="Explicit timezone-aware timestamp for reproducible fixtures; defaults to UTC now.")
    state.add_argument("--failure-ref", help="Required failed verification reference when entering repair.")

    bounce_back = subparsers.add_parser(
        "update-bounce-back",
        help="Validate and atomically create or resolve one bounce-back event.",
    )
    bounce_back.add_argument("--run-dir", required=True, help="Run directory containing 30_execution/run_state.json.")
    bounce_back.add_argument("--action", required=True, choices=("create", "resolve"), help="Bounce-back mutation to apply.")
    bounce_back.add_argument("--payload", required=True, help="JSON/YAML payload for the selected action.")
    bounce_back.add_argument("--timestamp", help="Explicit timezone-aware timestamp for reproducible fixtures; defaults to UTC now.")

    boundary = subparsers.add_parser(
        "role-boundary",
        help="Start or finish a deterministic semantic-agent filesystem mutation audit.",
    )
    boundary_actions = boundary.add_subparsers(dest="boundary_action", required=True)
    boundary_start = boundary_actions.add_parser("start", help="Capture the pre-invocation run snapshot.")
    boundary_finish = boundary_actions.add_parser("finish", help="Compare the post-invocation run snapshot and record evidence.")
    for boundary_parser in (boundary_start, boundary_finish):
        boundary_parser.add_argument("--run-dir", required=True, help="Run directory protected by the audit.")
        boundary_parser.add_argument("--role", required=True, choices=sorted(ROLE_POLICIES), help="Invoked semantic role.")
        boundary_parser.add_argument("--invocation-ref", required=True, help="Unique invocation reference.")
        boundary_parser.add_argument("--timestamp", help="Explicit evidence timestamp; defaults to UTC now.")
    boundary_finish.add_argument(
        "--baseline-sha256",
        required=True,
        help="Baseline identity returned by role-boundary start.",
    )
    assignment = boundary_start.add_mutually_exclusive_group()
    assignment.add_argument("--artifact", choices=sorted(SEMANTIC_ARTIFACTS), help="Required selected-policy artifact assignment.")
    assignment.add_argument("--review-event", help="Selected-policy threshold event for an independent process review.")
    boundary_start.add_argument("--input-ref", action="append", default=[], help="Additional local consumed input; repeat as needed.")

    persist = subparsers.add_parser(
        "persist-artifact",
        help="Root-persist and activate one audited semantic artifact body.",
    )
    persist.add_argument("--run-dir", required=True, help="Boundary-control run directory.")
    persist.add_argument("--artifact", required=True, choices=sorted(SEMANTIC_ARTIFACTS), help="Semantic artifact key.")
    persist.add_argument("--source", required=True, help="Separate Root-held returned-body draft.")
    persist.add_argument("--source-invocation-ref", required=True, help="Semantic invocation that returned the body.")
    persist.add_argument("--boundary-evidence-ref", required=True, help="Matching role-boundary PASS evidence path.")
    persist.add_argument("--timestamp", help="Explicit Root persistence timestamp; defaults to UTC now.")

    finalize = subparsers.add_parser(
        "finalize-semantic-return",
        help="Finish a semantic-role audit and transactionally validate, archive, persist, and activate its return.",
    )
    finalize.add_argument("--run-dir", required=True, help="Boundary-control run directory.")
    finalize.add_argument("--artifact", required=True, choices=sorted(SEMANTIC_ARTIFACTS), help="Semantic artifact key.")
    finalize.add_argument("--role", required=True, choices=sorted(ROLE_POLICIES), help="Semantic role that owns the artifact.")
    finalize.add_argument("--invocation-ref", required=True, help="Semantic invocation that returned the body.")
    finalize.add_argument("--baseline-sha256", required=True, help="Boundary baseline identity returned by role-boundary start.")
    finalize.add_argument("--source", required=True, help="Separate repository-held returned-body draft.")
    finalize.add_argument("--expected-source-sha256", help="Expected captured submission SHA-256; required under control revision 1.1.")
    finalize.add_argument("--timestamp", help="Explicit finalize timestamp; defaults to UTC now.")

    tests = subparsers.add_parser("run-tests", help="Execute a shell-free JSON/YAML test plan and retain outputs.")
    tests.add_argument("--run-dir", required=True, help="Run directory receiving test_results.json.")
    tests.add_argument("--plan", required=True, help="JSON/YAML test plan with argv arrays.")
    tests.add_argument("--output", help="Optional result JSON path; defaults to 30_execution/test_results.json.")
    tests.add_argument("--timestamp", help="Explicit evidence timestamp; defaults to UTC now.")
    tests.add_argument("--attempt-id", help="Optional safe unique immutable attempt identifier.")

    package = subparsers.add_parser("package", help="Create a deterministic ZIP and SHA-256 release manifest.")
    package.add_argument("--run-dir", required=True, help="Run directory with passing test results.")
    package.add_argument("--spec", required=True, help="JSON/YAML package specification.")

    inspect = subparsers.add_parser("inspect-package", help="Compare an archive with its manifest and release policy.")
    inspect.add_argument("--run-dir", required=True, help="Run directory receiving package_inspection.json.")
    inspect.add_argument("--manifest", required=True, help="Release manifest JSON path.")
    inspect.add_argument("--archive", help="Optional archive override; defaults to manifest.archive_path.")
    inspect.add_argument("--output", help="Optional inspection JSON path; defaults to 50_release/package_inspection.json.")

    verification = subparsers.add_parser(
        "prepare-verification",
        help="Reconcile and execute one contract-bound clean-package verification plan.",
    )
    verification.add_argument("--run-dir", required=True, help="Run directory receiving immutable harness evidence.")
    verification.add_argument("--plan", required=True, help="Contract-bound verifier plan JSON/YAML path.")
    verification.add_argument("--contract", help="Optional explicit active-contract path; must equal the plan binding.")
    verification.add_argument("--manifest", help="Optional explicit release-manifest path; must equal the plan binding.")
    verification.add_argument("--inspection", help="Optional explicit package-inspection path; must equal the plan binding.")
    verification.add_argument("--archive", help="Optional explicit archive path; must equal the plan binding.")
    verification.add_argument("--scratch-root", help="Optional bounded short scratch namespace for tests or local policy.")
    verification.add_argument("--attempt-id", help="Optional safe unique immutable attempt identifier.")
    verification.add_argument("--timestamp", help="Explicit evidence timestamp; defaults to UTC now.")
    return parser


def _path(project_root: Path, value: str, *, must_exist: bool = False) -> Path:
    return resolve_within(project_root, value, must_exist=must_exist)


def _run(args: argparse.Namespace) -> CommandResult:
    try:
        project_root = Path(args.project_root).resolve(strict=True)
    except OSError as exc:
        result = CommandResult(command=args.command)
        result.add("PROJECT_ROOT", str(args.project_root), str(exc))
        return result
    if not project_root.is_dir():
        result = CommandResult(command=args.command)
        result.add("PROJECT_ROOT", str(project_root), "must be a directory")
        return result
    try:
        if args.command == "validate-run":
            return validate_run_directory(project_root, _path(project_root, args.run_dir))
        if args.command == "validate-contract":
            return validate_contract_file(_path(project_root, args.contract))
        if args.command == "load-role-assignment":
            from .procedures import load_role_assignment

            return load_role_assignment(project_root, _path(project_root, args.run_dir), role=args.role,
                                        invocation_ref=args.invocation_ref, baseline_sha256=args.baseline_sha256)
        if args.command == "update-state":
            return update_state(
                _path(project_root, args.run_dir),
                project_root=project_root,
                to_stage=args.to_stage,
                stage_status=args.stage_status,
                gate_status=args.gate_status,
                evidence_refs=args.evidence_ref,
                rationale=args.rationale,
                next_action=args.next_action,
                timestamp=args.timestamp,
                failure_ref=args.failure_ref,
            )
        if args.command == "update-bounce-back":
            return update_bounce_back(
                _path(project_root, args.run_dir),
                project_root=project_root,
                action=args.action,
                payload=read_structured(_path(project_root, args.payload, must_exist=True)),
                timestamp=args.timestamp,
            )
        if args.command == "role-boundary":
            if args.boundary_action == "start":
                return start_role_boundary(
                    project_root,
                    _path(project_root, args.run_dir),
                    role=args.role,
                    invocation_ref=args.invocation_ref,
                    artifact_key=args.artifact,
                    review_event_id=args.review_event,
                    input_refs=args.input_ref,
                    timestamp=args.timestamp,
                )
            return finish_role_boundary(
                project_root,
                _path(project_root, args.run_dir),
                role=args.role,
                invocation_ref=args.invocation_ref,
                baseline_sha256=args.baseline_sha256,
                timestamp=args.timestamp,
            )
        if args.command == "persist-artifact":
            return persist_semantic_artifact(
                project_root,
                _path(project_root, args.run_dir),
                artifact_key=args.artifact,
                source_path=_path(project_root, args.source, must_exist=True),
                source_invocation_ref=args.source_invocation_ref,
                boundary_evidence_ref=args.boundary_evidence_ref,
                timestamp=args.timestamp,
            )
        if args.command == "finalize-semantic-return":
            return finalize_semantic_return(
                project_root,
                _path(project_root, args.run_dir),
                artifact_key=args.artifact,
                role=args.role,
                invocation_ref=args.invocation_ref,
                baseline_sha256=args.baseline_sha256,
                source_path=Path(args.source),
                expected_source_sha256=args.expected_source_sha256,
                timestamp=args.timestamp,
            )
        if args.command == "run-tests":
            return run_test_plan(
                project_root,
                _path(project_root, args.run_dir),
                _path(project_root, args.plan, must_exist=True),
                output_path=_path(project_root, args.output) if args.output else None,
                timestamp=args.timestamp,
                attempt_id=args.attempt_id,
            )
        if args.command == "package":
            return create_package(
                project_root,
                _path(project_root, args.run_dir),
                _path(project_root, args.spec, must_exist=True),
            )
        if args.command == "inspect-package":
            return inspect_package(
                project_root,
                _path(project_root, args.run_dir),
                _path(project_root, args.manifest, must_exist=True),
                archive_path=_path(project_root, args.archive, must_exist=True) if args.archive else None,
                output_path=_path(project_root, args.output) if args.output else None,
            )
        if args.command == "prepare-verification":
            return prepare_verification(
                project_root,
                _path(project_root, args.run_dir),
                _path(project_root, args.plan, must_exist=True),
                contract_path=_path(project_root, args.contract, must_exist=True) if args.contract else None,
                manifest_path=_path(project_root, args.manifest, must_exist=True) if args.manifest else None,
                inspection_path=_path(project_root, args.inspection, must_exist=True) if args.inspection else None,
                archive_path=_path(project_root, args.archive, must_exist=True) if args.archive else None,
                scratch_root=_path(project_root, args.scratch_root) if args.scratch_root else None,
                attempt_id=args.attempt_id,
                timestamp=args.timestamp,
            )
    except InputError as exc:
        result = CommandResult(command=args.command)
        result.add("PATH_ERROR", args.command, str(exc))
        return result
    result = CommandResult(command=args.command)
    result.add("COMMAND_UNKNOWN", args.command, "unsupported command")
    return result


def render(result: CommandResult, output_format: str) -> str:
    if output_format == "json":
        return json.dumps(result.as_dict(), ensure_ascii=False, sort_keys=True)
    lines = [f"{'PASS' if result.ok else 'FAIL'}: {result.command}"]
    for diagnostic in sorted(result.diagnostics):
        lines.append(f"- [{diagnostic.code}] {diagnostic.path}: {diagnostic.message}")
    if result.data:
        for key, value in result.data.items():
            lines.append(f"- {key}: {value}")
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    result = _run(args)
    print(render(result, args.format))
    return 0 if result.ok else 1
