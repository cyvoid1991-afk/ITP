#!/usr/bin/env python3
"""Initialize one fixed-layout artifact-contract 1.0 build run safely."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence


FRAMEWORK_ROOT = Path(__file__).resolve().parents[4] / "tools" / "intent-tool-pipeline"
if str(FRAMEWORK_ROOT) not in sys.path:
    sys.path.insert(0, str(FRAMEWORK_ROOT))

from pipeline_control.io_utils import (  # noqa: E402
    InputError,
    atomic_write_json,
    read_structured,
    repository_relative,
    resolve_within,
    sha256_file,
)
from pipeline_control.revision import resolve_revision_baseline  # noqa: E402
from pipeline_control.local_delivery import validate_intake_deliveries  # noqa: E402
from pipeline_control.validation import (  # noqa: E402
    STAGE_IDS,
    SUPPORTED_BOUNDARY_REVISIONS,
    validate_build_request_data,
    validate_run_directory,
)


PROJECT_ID_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
GATE_IDS = {
    "intake": "GATE-INTAKE",
    "framing": "GATE-FRAMING",
    "contract": "GATE-CONTRACT",
    "repository_analysis": "GATE-REPOSITORY",
    "implementation": "GATE-IMPLEMENTATION",
    "verification": "GATE-VERIFICATION",
    "repair": "GATE-REPAIR",
    "release": "GATE-RELEASE",
}


def _timestamp(value: str | None) -> str:
    if value is None:
        return datetime.now(timezone.utc).isoformat(timespec="seconds")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise InputError("--timestamp must be an ISO 8601 value with an explicit timezone") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise InputError("--timestamp must include an explicit timezone")
    return value


def _diagnostics(items: list[Any]) -> list[dict[str, str]]:
    return [item.as_dict() for item in sorted(items)]


def _state(
    project_id: str,
    run_id: str,
    timestamp: str,
    revision_baseline: dict[str, Any] | None = None,
    control_revision: str = "1.2",
) -> dict[str, Any]:
    state = {
        "schema_version": "1.1",
        "artifact": {
            "artifact_id": "run-state",
            "version": 1,
            "lifecycle_status": "ACTIVE",
            "owner_role": "root_codex",
            "created_at": timestamp,
            "updated_at": timestamp,
        },
        "run": {
            "run_id": run_id,
            "project_id": project_id,
            "current_stage": "intake",
            "next_allowed_action": "Validate and pass the active intake, or record its blocker.",
        },
        "stages": [
            {
                "id": stage_id,
                "status": "IN_PROGRESS" if stage_id == "intake" else "PENDING",
                "gate_id": GATE_IDS[stage_id],
            }
            for stage_id in STAGE_IDS
        ],
        "gates": [
            {
                "id": GATE_IDS[stage_id],
                "status": "IN_PROGRESS" if stage_id == "intake" else "PENDING",
                "evidence_refs": [],
                "rationale": "Intake validation is in progress." if stage_id == "intake" else "Not yet evaluated.",
            }
            for stage_id in STAGE_IDS
        ],
        "active_artifacts": {
            "build_request": {
                "artifact_id": "build-request",
                "version": 1,
                "path": "00_intake/build_request.yaml",
            },
            "problem_frame": None,
            "product_contract": None,
            "run_state": {
                "artifact_id": "run-state",
                "version": 1,
                "path": "30_execution/run_state.json",
            },
            "verification_report": None,
        },
        "control": {
            "semantic_role_boundary": control_revision,
            "intent_realization": "1.0",
            "verification_validation_identity": None,
        },
        "repair": {
            "active_attempt": 0,
            "maximum_attempts": 2,
            "last_failure_ref": None,
        },
        "bounce_back_events": [],
        "blockers": [],
        "required_approvals": [],
    }
    if control_revision in {"1.1", "1.2"}:
        state["control"].update(semantic_registrations={}, latest_verification_result=None)
        state["repair"].update(maximum_attempts=4, rounds=[])
    if revision_baseline is not None:
        state["control"]["revision_baseline"] = {
            **revision_baseline,
            "resolved_at": timestamp,
        }
    return state


def initialize(project_root: Path, request_path: Path, run_id: str | None, timestamp: str, *, control_revision: str = "1.2") -> dict[str, Any]:
    if control_revision not in SUPPORTED_BOUNDARY_REVISIONS:
        return {"ok": False, "diagnostics": [{"code": "CONTROL_REVISION", "path": "control_revision", "message": "supported revisions are '1.0', '1.1' and '1.2'"}], "data": {}}
    request = read_structured(request_path)
    request_diagnostics = validate_build_request_data(request)
    if request_diagnostics:
        return {
            "ok": False,
            "diagnostics": _diagnostics(request_diagnostics),
            "data": {},
        }
    if not isinstance(request, dict):
        return {
            "ok": False,
            "diagnostics": [{"code": "REQUEST_TYPE", "path": str(request_path), "message": "request must be a mapping"}],
            "data": {},
        }

    artifact = request.get("artifact", {})
    if not isinstance(artifact, dict) or artifact.get("lifecycle_status") != "ACTIVE":
        return {
            "ok": False,
            "diagnostics": [{"code": "REQUEST_NOT_ACTIVE", "path": str(request_path), "message": "build request lifecycle_status must be ACTIVE"}],
            "data": {},
        }

    project = request.get("project", {})
    project_id = project.get("project_id") if isinstance(project, dict) else None
    if not isinstance(project_id, str) or PROJECT_ID_PATTERN.fullmatch(project_id) is None:
        return {
            "ok": False,
            "diagnostics": [{"code": "PROJECT_ID", "path": "$.project.project_id", "message": "must use lowercase letters, digits, and single hyphens"}],
            "data": {},
        }
    effective_run_id = run_id or project_id
    if PROJECT_ID_PATTERN.fullmatch(effective_run_id) is None:
        return {
            "ok": False,
            "diagnostics": [{"code": "RUN_ID", "path": "--run-id", "message": "must use lowercase letters, digits, and single hyphens"}],
            "data": {},
        }

    revision_baseline: dict[str, Any] | None = None
    handoff = request.get("handoff")
    if not isinstance(handoff, dict) or handoff.get("next_stage", "framing") not in {"framing", "contract"}:
        return {"ok": False, "diagnostics": [{"code": "INTAKE_ROUTE", "path": "$.handoff.next_stage", "message": "new runs must select framing (A) or contract (direct B)"}], "data": {}}
    if project.get("request_kind") == "REVISION":
        baseline_result = resolve_revision_baseline(project_root, request)
        if not baseline_result.ok:
            return {
                "ok": False,
                "diagnostics": _diagnostics(baseline_result.diagnostics),
                "data": {},
            }
        revision_baseline = baseline_result.data

    try:
        local_delivery_intake = validate_intake_deliveries(project_root, request)
    except (InputError, OSError, UnicodeError) as exc:
        return {"ok": False, "diagnostics": [{"code": "LOCAL_DELIVERY_INTAKE", "path": "$.source_context", "message": str(exc)}], "data": {}}

    runs_root = resolve_within(project_root, "workspace/build_runs")
    runs_root.mkdir(parents=True, exist_ok=True)
    run_dir = resolve_within(project_root, runs_root / project_id)
    if run_dir.exists():
        return {
            "ok": False,
            "diagnostics": [{"code": "RUN_EXISTS", "path": repository_relative(project_root, run_dir), "message": "refusing to overwrite or reuse an existing run"}],
            "data": {},
        }

    staging = runs_root / f".init-{uuid.uuid4().hex[:8]}"
    stage_directories = [
        "00_intake",
        "10_framing",
        "20_contract",
        "30_execution",
        "40_verification",
        "50_release",
    ]
    try:
        for relative in stage_directories:
            (staging / relative).mkdir(parents=True, exist_ok=False)
        request_destination = staging / "00_intake" / "build_request.yaml"
        request_destination.write_bytes(request_path.read_bytes())
        if local_delivery_intake is not None:
            atomic_write_json(staging / "00_intake" / "minor_delivery_intake.json", local_delivery_intake)
        state = _state(project_id, effective_run_id, timestamp, revision_baseline, control_revision)
        state["active_artifacts"]["build_request"]["content_sha256"] = sha256_file(request_destination)
        atomic_write_json(staging / "30_execution" / "run_state.json", state)
        validation = validate_run_directory(project_root, staging)
        if not validation.ok:
            return {
                "ok": False,
                "diagnostics": _diagnostics(validation.diagnostics),
                "data": {},
            }
        os.replace(staging, run_dir)
    except OSError as exc:
        return {
            "ok": False,
            "diagnostics": [{"code": "RUN_INITIALIZATION", "path": str(staging), "message": str(exc)}],
            "data": {},
        }
    finally:
        if staging.exists() and staging.is_dir() and staging.parent == runs_root:
            shutil.rmtree(staging)

    return {
        "ok": True,
        "diagnostics": [],
        "data": {
            "project_id": project_id,
            "run_id": effective_run_id,
            "run_dir": repository_relative(project_root, run_dir),
            "request_path": repository_relative(project_root, run_dir / "00_intake" / "build_request.yaml"),
            "state_path": repository_relative(project_root, run_dir / "30_execution" / "run_state.json"),
            "repair_maximum_attempts": state["repair"]["maximum_attempts"],
            "control_revision": control_revision,
            "operational_status": "PROCEDURE_BOUND" if control_revision == "1.2" else "ARTIFACT_SUBMISSION" if control_revision == "1.1" else "LEGACY",
        },
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Create one non-overwriting fixed-layout build-tool pipeline run.",
    )
    parser.add_argument(
        "--project-root",
        default=str(FRAMEWORK_ROOT),
        help="Repository root that will receive workspace/build_runs/ (default: inferred framework root).",
    )
    parser.add_argument("--request", required=True, help="Active artifact-contract 1.0 build request under the project root.")
    parser.add_argument("--run-id", help="Optional run ID; defaults to project.project_id.")
    parser.add_argument("--control-revision", choices=SUPPORTED_BOUNDARY_REVISIONS, default="1.2", help="Boundary control revision: default 1.2 procedure-bound submissions; explicitly select 1.0 for legacy control, or 1.1 for earlier submission control. New runs only; existing runs are never migrated.")
    parser.add_argument("--timestamp", help="Timezone-aware ISO 8601 initialization timestamp; defaults to current UTC.")
    parser.add_argument("--format", choices=("human", "json"), default="human", help="Output format.")
    return parser


def render(result: dict[str, Any], output_format: str) -> str:
    if output_format == "json":
        return json.dumps(result, ensure_ascii=False, sort_keys=True)
    lines = ["PASS: initialize-run" if result["ok"] else "FAIL: initialize-run"]
    for item in result["diagnostics"]:
        lines.append(f"- [{item['code']}] {item['path']}: {item['message']}")
    for key, value in result["data"].items():
        lines.append(f"- {key}: {value}")
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        project_root = Path(args.project_root).resolve(strict=True)
        if not project_root.is_dir():
            raise InputError("--project-root must identify an existing directory")
        request_path = resolve_within(project_root, args.request, must_exist=True)
        result = initialize(project_root, request_path, args.run_id, _timestamp(args.timestamp), control_revision=args.control_revision)
    except (InputError, OSError) as exc:
        result = {
            "ok": False,
            "diagnostics": [{"code": "INPUT", "path": "initialize-run", "message": str(exc)}],
            "data": {},
        }
    print(render(result, args.format))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
