"""Artifact-contract 1.0 structural validators."""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

from .evidence import passing_package_inspection, passing_test_results
from .io_utils import InputError, normalize_repository_reference, read_structured, resolve_within, sha256_file
from .result import CommandResult, Diagnostic


SCHEMA_MAJOR = "1"
LIFECYCLE_STATUSES = {"DRAFT", "ACTIVE", "SUPERSEDED"}
READINESS_STATUSES = {"PASS", "PASS_WITH_ASSUMPTIONS", "BLOCKED"}
STAGE_STATUSES = {"PENDING", "IN_PROGRESS", "PASSED", "FAILED", "BLOCKED"}
REQUIREMENT_RESULTS = {"PASS", "FAIL", "UNVERIFIED"}
OVERALL_RESULTS = {"READY", "NOT_READY", "UNVERIFIED"}
CONTROL_REVISION = "1.0"
SUPPORTED_BOUNDARY_REVISIONS = ("1.0", "1.1", "1.2")
SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
SEMANTIC_ARTIFACT_OWNERS = {
    "problem_frame": "problem_framer",
    "product_contract": "product_contract_agent",
    "verification_report": "independent_verifier",
}


def semantic_artifact_owner(state: Any, key: str) -> str | None:
    """Resolve ownership per run; absence of the opt-in marker preserves history."""
    control = state.get("control") if isinstance(state, dict) else None
    if isinstance(control, dict) and "intent_realization" in control:
        if control["intent_realization"] != CONTROL_REVISION:
            raise InputError("control.intent_realization must equal '1.0' when present")
        if not is_controlled_run_state(state):
            raise InputError("intent realization requires semantic boundary control")
        if key == "problem_frame":
            return "intent_realizer"
    return SEMANTIC_ARTIFACT_OWNERS.get(key)
DECISION_STATUSES = {"APPROVED", "AGENT_DECIDED", "REJECTED", "DEFERRED", "SUPERSEDED"}
ISSUE_STATUSES = {"OPEN", "RESOLVED", "ACCEPTED", "DEFERRED"}
APPROVAL_STATUSES = {"PENDING", "APPROVED", "REJECTED", "DEFERRED", "SUPERSEDED"}
REQUIREMENT_CATEGORIES = {"FUNCTIONAL", "NON_FUNCTIONAL", "DOCUMENTATION", "COMPATIBILITY"}
EVIDENCE_METHODS = {"TEST", "INSPECTION", "ANALYSIS", "DEMONSTRATION"}

STAGE_IDS = [
    "intake",
    "framing",
    "contract",
    "repository_analysis",
    "implementation",
    "verification",
    "repair",
    "release",
]

BOUNCE_CLASSIFICATIONS = {
    "DISCOVERABLE_CONTEXT",
    "NON_MATERIAL_CHOICE",
    "IMPLEMENTATION_DEFECT",
    "EVIDENCE_GAP",
    "CONTRACT_CONTRADICTION",
    "MATERIAL_AMBIGUITY",
    "PERMISSION_OR_EXTERNAL_AUTHORITY",
    "UNACCEPTABLE_RISK",
    "REPAIR_LIMIT_EXHAUSTED",
}
BOUNCE_RESOLUTION_TYPES = {
    "ROOT_ANSWERED",
    "USER_DECIDED",
    "CONTEXT_ADDED",
    "IMPLEMENTATION_REPAIRED",
    "EVIDENCE_ADDED",
    "CONTRACT_REVISED",
    "WAIVER_APPROVED",
    "CANCELLED",
}
RETRY_CHANGE_BASES = {
    "INPUT_CHANGED",
    "EVIDENCE_CHANGED",
    "IMPLEMENTATION_CHANGED",
    "DECISION_CHANGED",
}

PROBLEM_FRAME_HEADINGS = [
    "Contract Metadata",
    "Completion Status",
    "Input Reviewed",
    "Active Problem",
    "Objective and User Need",
    "Target UX Flow",
    "Scope",
    "Non-Scope",
    "Inputs and Outputs",
    "Failure Behavior",
    "Constraints",
    "Assumptions",
    "Decisions",
    "Open Issues and Blockers",
    "Validation Needs",
    "Handoff Readiness",
]
VERIFICATION_HEADINGS = [
    "Contract Metadata",
    "Overall Assessment",
    "Inputs and Evidence Reviewed",
    "LLM Judgment Scope",
    "Requirement Results",
    "Missing or Unusable Evidence",
    "Contract, Interface, and Documentation Drift",
    "Repair Requests",
    "Risks, Waivers, and Blockers",
    "Revalidation Needs",
    "Root Return",
]


class Validator:
    """Small imperative validator that preserves stable paths and error codes."""

    def __init__(self) -> None:
        self.diagnostics: list[Diagnostic] = []

    def error(self, code: str, path: str, message: str) -> None:
        self.diagnostics.append(Diagnostic(code=code, path=path, message=message))

    def mapping(self, value: Any, path: str) -> dict[str, Any] | None:
        if not isinstance(value, dict):
            self.error("TYPE_OBJECT", path, "must be an object/mapping")
            return None
        return value

    def sequence(self, value: Any, path: str) -> list[Any] | None:
        if not isinstance(value, list):
            self.error("TYPE_ARRAY", path, "must be an array/list")
            return None
        return value

    def required(self, mapping: dict[str, Any], fields: Iterable[str], path: str) -> None:
        for field in fields:
            if field not in mapping:
                self.error("FIELD_REQUIRED", f"{path}.{field}", "required field is missing")

    def nonempty_string(self, value: Any, path: str) -> bool:
        if not isinstance(value, str) or not value.strip():
            self.error("TYPE_NONEMPTY_STRING", path, "must be a non-empty string")
            return False
        return True

    def enum(self, value: Any, allowed: set[str], path: str) -> bool:
        if value not in allowed:
            self.error("VALUE_ENUM", path, f"must be one of {sorted(allowed)}")
            return False
        return True


def _schema_minor(value: Any) -> int | None:
    if not isinstance(value, str) or re.fullmatch(r"1\.\d+", value) is None:
        return None
    return int(value.split(".", 1)[1])


def is_controlled_run_state(data: Any) -> bool:
    """Return whether a run selects a supported semantic boundary revision."""

    if not isinstance(data, dict):
        return False
    control = data.get("control")
    return isinstance(control, dict) and control.get("semantic_role_boundary") in SUPPORTED_BOUNDARY_REVISIONS


def is_agent_artifact_run(data: Any) -> bool:
    return isinstance(data, dict) and isinstance(data.get("control"), dict) and data["control"].get("semantic_role_boundary") in ("1.1", "1.2")


def validate_control_metadata(data: Any) -> list[Diagnostic]:
    """Policy preflight shared by writers, without imposing new legacy gates."""
    validator = Validator()
    if not isinstance(data, dict):
        validator.error("STATE_TYPE", "$", "run state must be an object")
        return validator.diagnostics
    from .continuation import validate_continuation_metadata

    validator.diagnostics.extend(validate_continuation_metadata(data))
    control = data.get("control")
    controlled_schema = (_schema_minor(data.get("schema_version")) or 0) >= 1
    if control is None and "control" not in data and not controlled_schema:
        if isinstance(data.get("repair"), dict) and "rounds" in data["repair"]:
            validator.error("CONTROL_METADATA", "$.repair.rounds", "agent artifact metadata requires revision '1.1'")
        return validator.diagnostics
    if not isinstance(control, dict):
        validator.error("CONTROL_REQUIRED", "$.control", "control must be an object")
        return validator.diagnostics
    revision = control.get("semantic_role_boundary")
    if revision not in SUPPORTED_BOUNDARY_REVISIONS:
        validator.error("CONTROL_REVISION", "$.control.semantic_role_boundary", "supported revisions are '1.0', '1.1' and '1.2'")
    if not controlled_schema:
        validator.error("CONTROL_SCHEMA", "$.schema_version", "boundary control requires run-state 1.1+")
    if "intent_realization" in control and control["intent_realization"] != CONTROL_REVISION:
        validator.error("INTENT_REALIZATION_REVISION", "$.control.intent_realization", "must equal '1.0'")
    repair = data.get("repair")
    if revision not in ("1.1", "1.2"):
        if any(key in control for key in ("semantic_registrations", "latest_verification_result")) or isinstance(repair, dict) and "rounds" in repair:
            validator.error("CONTROL_METADATA", "$.control", "agent artifact metadata requires revision '1.1'")
        return validator.diagnostics
    if control.get("intent_realization") != CONTROL_REVISION:
        validator.error("INTENT_REALIZATION_REVISION", "$.control.intent_realization", "revision '1.1' requires intent realization '1.0'")
    validator.required(control, ["semantic_registrations", "latest_verification_result"], "$.control")
    receipts = validator.mapping(control.get("semantic_registrations"), "$.control.semantic_registrations")
    if receipts is not None:
        import hashlib

        for audit_id, receipt in receipts.items():
            path = f"$.control.semantic_registrations.{audit_id}"
            record = validator.mapping(receipt, path)
            if record is None:
                continue
            fields = ["artifact_key", "artifact_ref", "path", "content_sha256", "producer_role", "submission_path", "source_invocation_ref", "baseline_sha256", "boundary_evidence_ref", "registered_at", "run_state_version", "round_number"]
            validator.required(record, fields, path)
            if revision == "1.2":
                binding = record.get("procedure_binding")
                if not isinstance(binding, dict) or set(binding) != {"control_revision", "assignment_sha256", "procedure_sha256"} or binding.get("control_revision") != "1.2" or binding.get("assignment_sha256") != record.get("baseline_sha256") or not isinstance(binding.get("procedure_sha256"), str) or SHA256_PATTERN.fullmatch(binding["procedure_sha256"]) is None:
                    validator.error("REGISTRATION_PROCEDURE", path, "1.2 receipt requires its exact assignment/procedure binding")
            elif "procedure_binding" in record:
                validator.error("REGISTRATION_PROCEDURE", path, "procedure receipt requires selected revision 1.2")
            key = record.get("artifact_key")
            owner = {"problem_frame": "intent_realizer", "product_contract": "product_contract_agent", "verification_report": "independent_verifier"}.get(key) if isinstance(key, str) else None
            if owner is None or record.get("producer_role") != owner:
                validator.error("REGISTRATION_OWNER", path, "receipt must identify the selected semantic owner")
            invocation = record.get("source_invocation_ref")
            if isinstance(invocation, str) and owner:
                expected_id = hashlib.sha256(f"{owner}\0{invocation}".encode()).hexdigest()[:24]
                if audit_id != expected_id:
                    validator.error("REGISTRATION_ID", path, "receipt key differs from role/invocation audit identity")
            for field in ("path", "submission_path", "source_invocation_ref", "boundary_evidence_ref"):
                validator.nonempty_string(record.get(field), f"{path}.{field}")
            for field in ("content_sha256", "baseline_sha256"):
                value = record.get(field)
                if not isinstance(value, str) or SHA256_PATTERN.fullmatch(value) is None:
                    validator.error("CONTENT_SHA256", f"{path}.{field}", "must be a lowercase SHA-256 value")
            expected_prefix = key.replace("_", "-") if isinstance(key, str) else ""
            if not isinstance(record.get("artifact_ref"), str) or re.fullmatch(re.escape(expected_prefix) + r"@[1-9]\d*", record["artifact_ref"]) is None:
                validator.error("REGISTRATION_REF", path, "receipt must identify a positive semantic artifact version")
            version = record.get("run_state_version")
            if type(version) is not int or version < 1 or isinstance(data.get("artifact"), dict) and type(data["artifact"].get("version")) is int and version > data["artifact"]["version"]:
                validator.error("REGISTRATION_VERSION", path, "receipt state version must exist at or before current state")
            if not _is_timezone_timestamp(record.get("registered_at")):
                validator.error("TIMESTAMP_TIMEZONE", f"{path}.registered_at", "must include an explicit timezone")
            round_number = record.get("round_number")
            if round_number is not None:
                rounds = repair.get("rounds") if isinstance(repair, dict) else None
                if type(round_number) is not int or round_number < 1 or not isinstance(rounds, list) or round_number > len(rounds):
                    validator.error("REGISTRATION_ROUND", f"{path}.round_number", "must identify an existing reserved round, or be null")
        active = data.get("active_artifacts")
        if isinstance(active, dict):
            for key in SEMANTIC_ARTIFACT_OWNERS:
                entry = active.get(key)
                if not isinstance(entry, dict):
                    continue
                matches = [r for r in receipts.values() if isinstance(r, dict) and r.get("artifact_key") == key and r.get("artifact_ref") == f"{entry.get('artifact_id')}@{entry.get('version')}" and all(r.get(a) == entry.get(b) for a, b in (("path", "path"), ("content_sha256", "content_sha256"), ("producer_role", "semantic_owner"), ("source_invocation_ref", "source_invocation_ref"), ("boundary_evidence_ref", "boundary_evidence_ref")))]
                if len(matches) != 1:
                    validator.error("REGISTRATION_ACTIVE", f"$.active_artifacts.{key}", "selected active artifact requires exactly one matching receipt")
    from .rounds import validate_round_metadata

    validator.diagnostics.extend(validate_round_metadata(data))
    return validator.diagnostics

def _is_timezone_timestamp(value: Any) -> bool:
    if not isinstance(value, str) or not value.strip():
        return False
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return parsed.tzinfo is not None and parsed.utcoffset() is not None


def _validate_schema_version(validator: Validator, value: Any, path: str = "schema_version") -> None:
    if not isinstance(value, str) or not value:
        validator.error("SCHEMA_VERSION", path, "must be a non-empty version string")
        return
    if value.split(".", 1)[0] != SCHEMA_MAJOR:
        validator.error("SCHEMA_UNSUPPORTED", path, f"unsupported major version {value!r}; expected 1.x")


def _validate_common_artifact(
    validator: Validator,
    data: dict[str, Any],
    expected_id: str,
    *,
    path: str = "$",
) -> None:
    validator.required(data, ["schema_version", "artifact"], path)
    _validate_schema_version(validator, data.get("schema_version"), f"{path}.schema_version")
    artifact = validator.mapping(data.get("artifact"), f"{path}.artifact")
    if artifact is None:
        return
    validator.required(
        artifact,
        ["artifact_id", "version", "lifecycle_status", "owner_role", "created_at", "updated_at"],
        f"{path}.artifact",
    )
    if artifact.get("artifact_id") != expected_id:
        validator.error(
            "ARTIFACT_ID",
            f"{path}.artifact.artifact_id",
            f"must equal {expected_id!r}",
        )
    version = artifact.get("version")
    if not isinstance(version, int) or isinstance(version, bool) or version < 1:
        validator.error("ARTIFACT_VERSION", f"{path}.artifact.version", "must be a positive integer")
    lifecycle = artifact.get("lifecycle_status")
    validator.enum(lifecycle, LIFECYCLE_STATUSES, f"{path}.artifact.lifecycle_status")
    validator.nonempty_string(artifact.get("owner_role"), f"{path}.artifact.owner_role")
    for field in ("created_at", "updated_at"):
        value = artifact.get(field)
        if value is None and lifecycle == "DRAFT":
            continue
        if not _is_timezone_timestamp(value):
            validator.error(
                "TIMESTAMP_TIMEZONE",
                f"{path}.artifact.{field}",
                "must be an ISO 8601 timestamp with an explicit timezone; null is allowed only for DRAFT",
            )


def _validate_id_records(
    validator: Validator,
    records: Any,
    path: str,
    pattern: str,
    *,
    status_allowed: set[str] | None = None,
) -> list[dict[str, Any]]:
    sequence = validator.sequence(records, path)
    if sequence is None:
        return []
    valid: list[dict[str, Any]] = []
    seen: set[str] = set()
    for index, value in enumerate(sequence):
        item_path = f"{path}[{index}]"
        item = validator.mapping(value, item_path)
        if item is None:
            continue
        identifier = item.get("id")
        if not isinstance(identifier, str) or re.fullmatch(pattern, identifier) is None:
            validator.error("ID_FORMAT", f"{item_path}.id", f"must match {pattern}")
        elif identifier in seen:
            validator.error("ID_DUPLICATE", f"{item_path}.id", f"duplicate ID {identifier}")
        else:
            seen.add(identifier)
        if status_allowed is not None:
            validator.enum(item.get("status"), status_allowed, f"{item_path}.status")
        valid.append(item)
    return valid


def validate_build_request_data(data: Any) -> list[Diagnostic]:
    validator = Validator()
    root = validator.mapping(data, "$")
    if root is None:
        return validator.diagnostics
    _validate_common_artifact(validator, root, "build-request")
    validator.required(
        root,
        [
            "project",
            "requested_outcome",
            "source_context",
            "build_profile",
            "target",
            "constraints",
            "user_decisions",
            "assumptions",
            "blockers",
            "handoff",
        ],
        "$",
    )

    project = validator.mapping(root.get("project"), "$.project")
    request_kind: Any = None
    if project is not None:
        validator.required(project, ["project_id", "name", "request_kind", "summary"], "$.project")
        request_kind = project.get("request_kind")
    target = validator.mapping(root.get("target"), "$.target")
    if target is not None:
        validator.required(target, ["repository_path", "output_path"], "$.target")
    _validate_id_records(validator, root.get("user_decisions"), "$.user_decisions", r"DEC-\d{3,}", status_allowed=DECISION_STATUSES)
    _validate_id_records(validator, root.get("assumptions"), "$.assumptions", r"ASM-\d{3,}")
    _validate_id_records(validator, root.get("blockers"), "$.blockers", r"BLK-\d{3,}", status_allowed=ISSUE_STATUSES)

    revision_of = root.get("revision_of")
    delta_request = root.get("delta_request")
    if request_kind == "REVISION":
        if not isinstance(revision_of, dict) or not isinstance(delta_request, dict):
            validator.error(
                "FRESH_REQUIRED",
                "$.revision_of",
                "REVISION requires revision_of and delta_request together; use a fresh non-revision request otherwise",
            )
        if isinstance(revision_of, dict):
            baseline_fields = [
                "run_id",
                "archive_sha256",
                "product_contract_ref",
                "product_contract_sha256",
                "verification_report_ref",
                "verification_report_sha256",
            ]
            validator.required(revision_of, baseline_fields, "$.revision_of")
            validator.nonempty_string(revision_of.get("run_id"), "$.revision_of.run_id")
            for field in ("archive_sha256", "product_contract_sha256", "verification_report_sha256"):
                value = revision_of.get(field)
                if not isinstance(value, str) or SHA256_PATTERN.fullmatch(value) is None:
                    validator.error("CONTENT_SHA256", f"$.revision_of.{field}", "must be a lowercase SHA-256 value")
            for field, pattern in (
                ("product_contract_ref", r"product-contract@\d+"),
                ("verification_report_ref", r"verification-report@\d+"),
            ):
                value = revision_of.get(field)
                if not isinstance(value, str) or re.fullmatch(pattern, value) is None:
                    validator.error("ARTIFACT_REF", f"$.revision_of.{field}", f"must match {pattern}")
        if isinstance(delta_request, dict):
            validator.required(
                delta_request,
                ["scope_classification", "requested_changes", "explicit_non_changes", "feedback_evidence"],
                "$.delta_request",
            )
            if delta_request.get("scope_classification") != "BOUNDED":
                validator.error(
                    "FRESH_REQUIRED",
                    "$.delta_request.scope_classification",
                    "delta mode accepts only an explicitly BOUNDED revision",
                )
            delta_items = _validate_id_records(
                validator,
                delta_request.get("requested_changes"),
                "$.delta_request.requested_changes",
                r"DELTA-\d{3,}",
            )
            nonchange_items = _validate_id_records(
                validator,
                delta_request.get("explicit_non_changes"),
                "$.delta_request.explicit_non_changes",
                r"NONCHANGE-\d{3,}",
            )
            feedback_items = _validate_id_records(
                validator,
                delta_request.get("feedback_evidence"),
                "$.delta_request.feedback_evidence",
                r"FEEDBACK-\d{3,}",
            )
            if not delta_items:
                validator.error("FRESH_REQUIRED", "$.delta_request.requested_changes", "bounded delta mode requires at least one requested change")
            all_ids = [item.get("id") for item in delta_items + nonchange_items + feedback_items if isinstance(item.get("id"), str)]
            if len(all_ids) != len(set(all_ids)):
                validator.error("ID_DUPLICATE", "$.delta_request", "delta request IDs must be globally unique")
            for collection, items in (
                ("requested_changes", delta_items),
                ("explicit_non_changes", nonchange_items),
            ):
                for index, item in enumerate(items):
                    validator.required(item, ["id", "statement"], f"$.delta_request.{collection}[{index}]")
                    validator.nonempty_string(item.get("statement"), f"$.delta_request.{collection}[{index}].statement")
            for index, item in enumerate(feedback_items):
                path = f"$.delta_request.feedback_evidence[{index}]"
                validator.required(item, ["id", "source_ref", "summary"], path)
                validator.nonempty_string(item.get("source_ref"), f"{path}.source_ref")
                validator.nonempty_string(item.get("summary"), f"{path}.summary")
    elif revision_of is not None or delta_request is not None:
        validator.error(
            "REVISION_FIELDS_FORBIDDEN",
            "$.revision_of",
            "revision_of and delta_request are allowed only when project.request_kind is REVISION",
        )
    return validator.diagnostics


def _validate_revision_control(validator: Validator, value: Any) -> None:
    revision = validator.mapping(value, "$.revision_control")
    if revision is None:
        return
    validator.required(revision, ["mode", "baseline", "unchanged_requirements", "impact_map"], "$.revision_control")
    if revision.get("mode") != "DELTA":
        validator.error("REVISION_MODE", "$.revision_control.mode", "must equal DELTA")
    baseline = validator.mapping(revision.get("baseline"), "$.revision_control.baseline")
    if baseline is not None:
        validator.required(
            baseline,
            [
                "run_id",
                "archive_sha256",
                "product_contract_ref",
                "product_contract_sha256",
                "verification_report_ref",
                "verification_report_sha256",
            ],
            "$.revision_control.baseline",
        )
        validator.nonempty_string(baseline.get("run_id"), "$.revision_control.baseline.run_id")
        for field in ("archive_sha256", "product_contract_sha256", "verification_report_sha256"):
            digest = baseline.get(field)
            if not isinstance(digest, str) or SHA256_PATTERN.fullmatch(digest) is None:
                validator.error("CONTENT_SHA256", f"$.revision_control.baseline.{field}", "must be a lowercase SHA-256 value")
        for field in ("product_contract_ref", "verification_report_ref"):
            validator.nonempty_string(baseline.get(field), f"$.revision_control.baseline.{field}")

    unchanged = validator.sequence(revision.get("unchanged_requirements"), "$.revision_control.unchanged_requirements")
    unchanged_ids: list[str] = []
    if unchanged is not None:
        for index, raw in enumerate(unchanged):
            path = f"$.revision_control.unchanged_requirements[{index}]"
            item = validator.mapping(raw, path)
            if item is None:
                continue
            validator.required(item, ["requirement_ref", "baseline_bundle_sha256"], path)
            ref = item.get("requirement_ref")
            if not isinstance(ref, str) or re.fullmatch(r"REQ-\d{3,}", ref) is None:
                validator.error("ARTIFACT_REF", f"{path}.requirement_ref", "must be a REQ-### reference")
            else:
                unchanged_ids.append(ref)
            digest = item.get("baseline_bundle_sha256")
            if not isinstance(digest, str) or SHA256_PATTERN.fullmatch(digest) is None:
                validator.error("CONTENT_SHA256", f"{path}.baseline_bundle_sha256", "must be a lowercase SHA-256 value")
        if len(unchanged_ids) != len(set(unchanged_ids)):
            validator.error("ID_DUPLICATE", "$.revision_control.unchanged_requirements", "each unchanged requirement may appear only once")

    impact = validator.sequence(revision.get("impact_map"), "$.revision_control.impact_map")
    item_refs: list[str] = []
    if impact is not None:
        for index, raw in enumerate(impact):
            path = f"$.revision_control.impact_map[{index}]"
            item = validator.mapping(raw, path)
            if item is None:
                continue
            validator.required(
                item,
                [
                    "delta_item_ref",
                    "disposition",
                    "baseline_requirement_refs",
                    "current_requirement_refs",
                    "source_refs",
                    "test_refs",
                    "documentation_refs",
                    "packaging_refs",
                    "migration_impact",
                    "reverification_scope",
                ],
                path,
            )
            ref = item.get("delta_item_ref")
            if not isinstance(ref, str) or re.fullmatch(r"(?:DELTA|NONCHANGE)-\d{3,}", ref) is None:
                validator.error("ARTIFACT_REF", f"{path}.delta_item_ref", "must be a DELTA-### or NONCHANGE-### reference")
            else:
                item_refs.append(ref)
            disposition = item.get("disposition")
            validator.enum(disposition, {"IMPACTED", "UNCHANGED"}, f"{path}.disposition")
            if isinstance(ref, str) and ref.startswith("DELTA-") and disposition != "IMPACTED":
                validator.error("REVISION_DISPOSITION", f"{path}.disposition", "requested changes must be IMPACTED")
            if isinstance(ref, str) and ref.startswith("NONCHANGE-") and disposition != "UNCHANGED":
                validator.error("REVISION_DISPOSITION", f"{path}.disposition", "explicit non-changes must be UNCHANGED")
            for field in (
                "baseline_requirement_refs",
                "current_requirement_refs",
                "source_refs",
                "test_refs",
                "documentation_refs",
                "packaging_refs",
            ):
                refs = validator.sequence(item.get(field), f"{path}.{field}")
                if refs is not None and any(not isinstance(candidate, str) or not candidate.strip() for candidate in refs):
                    validator.error("ARTIFACT_REF", f"{path}.{field}", "must contain only non-empty references")
                if refs is not None and len(refs) != len(set(refs)):
                    validator.error("ID_DUPLICATE", f"{path}.{field}", "must not contain duplicate references")
            validator.nonempty_string(item.get("migration_impact"), f"{path}.migration_impact")
            if item.get("reverification_scope") != "ALL_APPLICABLE_REQUIREMENTS":
                validator.error("VERIFICATION_SCOPE", f"{path}.reverification_scope", "must equal ALL_APPLICABLE_REQUIREMENTS")
        if len(item_refs) != len(set(item_refs)):
            validator.error("ID_DUPLICATE", "$.revision_control.impact_map", "each delta item may appear only once")


def validate_product_contract_data(data: Any) -> list[Diagnostic]:
    validator = Validator()
    root = validator.mapping(data, "$")
    if root is None:
        return validator.diagnostics
    _validate_common_artifact(validator, root, "product-contract")
    validator.required(
        root,
        [
            "source_artifacts",
            "readiness",
            "product",
            "scope",
            "decisions",
            "assumptions",
            "blockers",
            "verification_policy",
            "requirements",
            "acceptance_methods",
            "implementation_constraints",
            "documentation_obligations",
            "handoff",
        ],
        "$",
    )

    readiness = validator.mapping(root.get("readiness"), "$.readiness")
    if readiness is not None:
        validator.required(readiness, ["status", "rationale"], "$.readiness")
        validator.enum(readiness.get("status"), READINESS_STATUSES, "$.readiness.status")
        validator.nonempty_string(readiness.get("rationale"), "$.readiness.rationale")

    product = validator.mapping(root.get("product"), "$.product")
    if product is not None:
        validator.required(product, ["name", "objective", "primary_user", "interface_summary"], "$.product")
    scope = validator.mapping(root.get("scope"), "$.scope")
    if scope is not None:
        validator.required(scope, ["included", "excluded"], "$.scope")
        validator.sequence(scope.get("included"), "$.scope.included")
        validator.sequence(scope.get("excluded"), "$.scope.excluded")
    if "revision_control" in root:
        _validate_revision_control(validator, root.get("revision_control"))

    _validate_id_records(validator, root.get("decisions"), "$.decisions", r"DEC-\d{3,}", status_allowed=DECISION_STATUSES)
    assumptions = _validate_id_records(validator, root.get("assumptions"), "$.assumptions", r"ASM-\d{3,}")
    blockers = _validate_id_records(validator, root.get("blockers"), "$.blockers", r"BLK-\d{3,}", status_allowed=ISSUE_STATUSES)
    for index, item in enumerate(blockers):
        if not isinstance(item.get("blocking"), bool):
            validator.error("BLOCKING_FLAG", f"$.blockers[{index}].blocking", "must be true or false")

    requirements = _validate_id_records(validator, root.get("requirements"), "$.requirements", r"REQ-\d{3,}")
    acceptance = _validate_id_records(validator, root.get("acceptance_methods"), "$.acceptance_methods", r"ACC-\d{3,}")
    requirement_ids = {item.get("id") for item in requirements if isinstance(item.get("id"), str)}
    acceptance_ids = {item.get("id") for item in acceptance if isinstance(item.get("id"), str)}

    if not requirements:
        validator.error("REQUIREMENTS_EMPTY", "$.requirements", "must contain at least one applicable requirement")
    if not acceptance:
        validator.error("ACCEPTANCE_EMPTY", "$.acceptance_methods", "must contain at least one acceptance method")

    for index, requirement in enumerate(requirements):
        path = f"$.requirements[{index}]"
        validator.required(requirement, ["id", "category", "title", "statement", "source_refs", "acceptance_refs"], path)
        validator.enum(requirement.get("category"), REQUIREMENT_CATEGORIES, f"{path}.category")
        validator.nonempty_string(requirement.get("title"), f"{path}.title")
        validator.nonempty_string(requirement.get("statement"), f"{path}.statement")
        refs = validator.sequence(requirement.get("acceptance_refs"), f"{path}.acceptance_refs")
        if refs is not None:
            if not refs:
                validator.error("MAPPING_EMPTY", f"{path}.acceptance_refs", "must reference at least one acceptance method")
            for ref in refs:
                if not isinstance(ref, str) or ref not in acceptance_ids:
                    validator.error("MAPPING_UNRESOLVED", f"{path}.acceptance_refs", f"unknown acceptance ID {ref!r}")

    for index, method in enumerate(acceptance):
        path = f"$.acceptance_methods[{index}]"
        validator.required(
            method,
            ["id", "requirement_refs", "evidence_method", "procedure", "expected_result", "evidence_required"],
            path,
        )
        validator.enum(method.get("evidence_method"), EVIDENCE_METHODS, f"{path}.evidence_method")
        refs = validator.sequence(method.get("requirement_refs"), f"{path}.requirement_refs")
        if refs is not None:
            if not refs:
                validator.error("MAPPING_EMPTY", f"{path}.requirement_refs", "must reference at least one requirement")
            for ref in refs:
                if not isinstance(ref, str) or ref not in requirement_ids:
                    validator.error("MAPPING_UNRESOLVED", f"{path}.requirement_refs", f"unknown requirement ID {ref!r}")

    # Enforce references in both directions, not merely existence in each namespace.
    requirement_by_id = {item["id"]: item for item in requirements if isinstance(item.get("id"), str)}
    acceptance_by_id = {item["id"]: item for item in acceptance if isinstance(item.get("id"), str)}
    for req_id, requirement in requirement_by_id.items():
        for acc_id in requirement.get("acceptance_refs", []) if isinstance(requirement.get("acceptance_refs"), list) else []:
            if not isinstance(acc_id, str):
                continue
            method = acceptance_by_id.get(acc_id)
            if method is not None and req_id not in method.get("requirement_refs", []):
                validator.error("MAPPING_ONE_SIDED", f"$.requirements[{req_id}].acceptance_refs", f"{acc_id} does not reference {req_id} back")
    for acc_id, method in acceptance_by_id.items():
        for req_id in method.get("requirement_refs", []) if isinstance(method.get("requirement_refs"), list) else []:
            if not isinstance(req_id, str):
                continue
            requirement = requirement_by_id.get(req_id)
            if requirement is not None and acc_id not in requirement.get("acceptance_refs", []):
                validator.error("MAPPING_ONE_SIDED", f"$.acceptance_methods[{acc_id}].requirement_refs", f"{req_id} does not reference {acc_id} back")

    policy = validator.mapping(root.get("verification_policy"), "$.verification_policy")
    llm_ids: list[Any] = []
    if policy is not None:
        validator.required(policy, ["scope", "default_nature", "llm_judgment_requirements"], "$.verification_policy")
        if policy.get("scope") != "ALL_APPLICABLE_REQUIREMENTS":
            validator.error("VERIFICATION_SCOPE", "$.verification_policy.scope", "must equal ALL_APPLICABLE_REQUIREMENTS")
        if policy.get("default_nature") != "DETERMINISTIC":
            validator.error("VERIFICATION_NATURE", "$.verification_policy.default_nature", "must equal DETERMINISTIC")
        raw_llm = validator.sequence(policy.get("llm_judgment_requirements"), "$.verification_policy.llm_judgment_requirements")
        if raw_llm is not None:
            llm_ids = raw_llm
            if any(not isinstance(item, str) for item in raw_llm):
                validator.error("ID_FORMAT", "$.verification_policy.llm_judgment_requirements", "must contain only REQ-### strings")
            elif len(set(raw_llm)) != len(raw_llm):
                validator.error("ID_DUPLICATE", "$.verification_policy.llm_judgment_requirements", "contains duplicate requirement IDs")
            for req_id in raw_llm:
                if not isinstance(req_id, str) or req_id not in requirement_ids:
                    validator.error("MAPPING_UNRESOLVED", "$.verification_policy.llm_judgment_requirements", f"unknown requirement ID {req_id!r}")
        if "applicable_requirement_ids" in policy:
            listed = policy.get("applicable_requirement_ids")
            if (
                not isinstance(listed, list)
                or any(not isinstance(item, str) for item in listed)
                or set(listed) != requirement_ids
                or len(listed) != len(requirement_ids)
            ):
                validator.error("APPLICABLE_SET", "$.verification_policy.applicable_requirement_ids", "must list every active requirement exactly once")
        if "applicable_requirement_count" in policy and policy.get("applicable_requirement_count") != len(requirement_ids):
            validator.error("APPLICABLE_COUNT", "$.verification_policy.applicable_requirement_count", "does not match the active requirement count")

    for req_id in llm_ids:
        if not isinstance(req_id, str):
            continue
        requirement = requirement_by_id.get(req_id)
        if requirement is None:
            continue
        linked = [acceptance_by_id.get(ref) for ref in requirement.get("acceptance_refs", [])]
        if not any(isinstance(item, dict) and isinstance(item.get("judgment_criteria"), str) and item["judgment_criteria"].strip() for item in linked):
            validator.error("JUDGMENT_CRITERIA", f"$.verification_policy.llm_judgment_requirements[{req_id}]", "requires judgment_criteria on at least one linked acceptance method")

    open_blocking = any(item.get("blocking") is True and item.get("status") == "OPEN" for item in blockers)
    if readiness is not None and readiness.get("status") in {"PASS", "PASS_WITH_ASSUMPTIONS"} and open_blocking:
        validator.error("FALSE_READINESS", "$.readiness.status", "cannot pass while an open blocking issue exists")
    if readiness is not None and readiness.get("status") == "PASS" and assumptions:
        confirmation_needed = any(item.get("requires_user_confirmation") is True and item.get("status") == "OPEN" for item in assumptions)
        if confirmation_needed:
            validator.error("FALSE_READINESS", "$.readiness.status", "cannot PASS with an open confirmation-required assumption")
    return validator.diagnostics


def validate_run_state_data(data: Any, *, direct_entry: bool = False) -> list[Diagnostic]:
    validator = Validator()
    root = validator.mapping(data, "$")
    if root is None:
        return validator.diagnostics
    validator.diagnostics.extend(validate_control_metadata(root))
    _validate_common_artifact(validator, root, "run-state")
    validator.required(
        root,
        ["run", "stages", "gates", "active_artifacts", "repair", "bounce_back_events", "blockers", "required_approvals"],
        "$",
    )

    controlled_schema = (_schema_minor(root.get("schema_version")) or 0) >= 1
    control = root.get("control")
    if isinstance(control, dict) and "intent_realization" in control:
        if control["intent_realization"] != CONTROL_REVISION or not controlled_schema or not is_controlled_run_state(root):
            validator.error("INTENT_REALIZATION_REVISION", "$.control.intent_realization", "must equal '1.0' on a boundary-controlled 1.1+ run")
    if controlled_schema:
        if not isinstance(control, dict):
            validator.error("CONTROL_REQUIRED", "$.control", "run-state 1.1+ requires boundary-control metadata")
        else:
            validator.required(
                control,
                ["semantic_role_boundary", "verification_validation_identity"],
                "$.control",
            )
            if control.get("semantic_role_boundary") not in SUPPORTED_BOUNDARY_REVISIONS:
                validator.error(
                    "CONTROL_REVISION",
                    "$.control.semantic_role_boundary",
                    f"must be one of {SUPPORTED_BOUNDARY_REVISIONS!r}",
                )
            validation_identity = control.get("verification_validation_identity")
            if validation_identity is not None:
                identity = validator.mapping(validation_identity, "$.control.verification_validation_identity")
                if identity is not None:
                    validator.required(
                        identity,
                        ["artifact_id", "version", "path", "content_sha256", "validated_at"],
                        "$.control.verification_validation_identity",
                    )
                    if identity.get("artifact_id") != "verification-report":
                        validator.error(
                            "VERIFICATION_IDENTITY",
                            "$.control.verification_validation_identity.artifact_id",
                            "must equal 'verification-report'",
                        )
                    version = identity.get("version")
                    if not isinstance(version, int) or isinstance(version, bool) or version < 1:
                        validator.error(
                            "ARTIFACT_VERSION",
                            "$.control.verification_validation_identity.version",
                            "must be a positive integer",
                        )
                    validator.nonempty_string(identity.get("path"), "$.control.verification_validation_identity.path")
                    if not isinstance(identity.get("content_sha256"), str) or SHA256_PATTERN.fullmatch(identity["content_sha256"]) is None:
                        validator.error(
                            "CONTENT_SHA256",
                            "$.control.verification_validation_identity.content_sha256",
                            "must be a lowercase SHA-256 value",
                        )
                    if not _is_timezone_timestamp(identity.get("validated_at")):
                        validator.error(
                            "TIMESTAMP_TIMEZONE",
                            "$.control.verification_validation_identity.validated_at",
                            "must be an ISO 8601 timestamp with an explicit timezone",
                        )
                    candidate_binding = identity.get("candidate_binding")
                    if candidate_binding is not None:
                        binding = validator.mapping(
                            candidate_binding,
                            "$.control.verification_validation_identity.candidate_binding",
                        )
                        if binding is not None:
                            validator.required(
                                binding,
                                [
                                    "product_contract_ref",
                                    "product_contract_path",
                                    "product_contract_sha256",
                                    "manifest_path",
                                    "manifest_sha256",
                                    "inspection_path",
                                    "inspection_sha256",
                                    "archive_path",
                                    "archive_sha256",
                                ],
                                "$.control.verification_validation_identity.candidate_binding",
                            )
                            for field in (
                                "product_contract_ref",
                                "product_contract_path",
                                "manifest_path",
                                "inspection_path",
                                "archive_path",
                            ):
                                validator.nonempty_string(
                                    binding.get(field),
                                    f"$.control.verification_validation_identity.candidate_binding.{field}",
                                )
                            for field in (
                                "product_contract_sha256",
                                "manifest_sha256",
                                "inspection_sha256",
                                "archive_sha256",
                            ):
                                digest = binding.get(field)
                                if not isinstance(digest, str) or SHA256_PATTERN.fullmatch(digest) is None:
                                    validator.error(
                                        "CONTENT_SHA256",
                                        f"$.control.verification_validation_identity.candidate_binding.{field}",
                                        "must be a lowercase SHA-256 value",
                                    )

            revision_baseline = control.get("revision_baseline")
            if revision_baseline is not None:
                baseline = validator.mapping(revision_baseline, "$.control.revision_baseline")
                if baseline is not None:
                    baseline_fields = [
                        "mode",
                        "run_id",
                        "run_dir",
                        "target_repository_path",
                        "archive_path",
                        "archive_sha256",
                        "product_contract_ref",
                        "product_contract_path",
                        "product_contract_sha256",
                        "verification_report_ref",
                        "verification_report_path",
                        "verification_report_sha256",
                        "manifest_path",
                        "manifest_sha256",
                        "inspection_path",
                        "inspection_sha256",
                        "resolved_at",
                    ]
                    validator.required(baseline, baseline_fields, "$.control.revision_baseline")
                    extra_fields = sorted(set(baseline) - set(baseline_fields))
                    if extra_fields:
                        validator.error(
                            "REVISION_LINEAGE",
                            "$.control.revision_baseline",
                            f"must contain only the immediate exact baseline identity; unexpected fields={extra_fields}",
                        )
                    if baseline.get("mode") != "VERIFIED_DELTA_SOURCE":
                        validator.error("REVISION_MODE", "$.control.revision_baseline.mode", "must equal VERIFIED_DELTA_SOURCE")
                    for field in (
                        "run_id",
                        "run_dir",
                        "target_repository_path",
                        "archive_path",
                        "product_contract_ref",
                        "product_contract_path",
                        "verification_report_ref",
                        "verification_report_path",
                        "manifest_path",
                        "inspection_path",
                    ):
                        validator.nonempty_string(baseline.get(field), f"$.control.revision_baseline.{field}")
                    for field in (
                        "archive_sha256",
                        "product_contract_sha256",
                        "verification_report_sha256",
                        "manifest_sha256",
                        "inspection_sha256",
                    ):
                        digest = baseline.get(field)
                        if not isinstance(digest, str) or SHA256_PATTERN.fullmatch(digest) is None:
                            validator.error("CONTENT_SHA256", f"$.control.revision_baseline.{field}", "must be a lowercase SHA-256 value")
                    if not _is_timezone_timestamp(baseline.get("resolved_at")):
                        validator.error("TIMESTAMP_TIMEZONE", "$.control.revision_baseline.resolved_at", "must be an ISO 8601 timestamp with an explicit timezone")

    active_artifacts = validator.mapping(root.get("active_artifacts"), "$.active_artifacts")
    if active_artifacts is not None:
        artifact_ids = {
            "build_request": "build-request",
            "problem_frame": "problem-frame",
            "product_contract": "product-contract",
            "run_state": "run-state",
            "verification_report": "verification-report",
        }
        validator.required(active_artifacts, artifact_ids, "$.active_artifacts")
        for key, expected_id in artifact_ids.items():
            entry = active_artifacts.get(key)
            if entry is None:
                if key in {"build_request", "run_state"}:
                    validator.error("ACTIVE_ARTIFACT", f"$.active_artifacts.{key}", "must not be null")
                continue
            mapping = validator.mapping(entry, f"$.active_artifacts.{key}")
            if mapping is None:
                continue
            validator.required(mapping, ["artifact_id", "version", "path"], f"$.active_artifacts.{key}")
            if mapping.get("artifact_id") != expected_id:
                validator.error("ACTIVE_ARTIFACT_ID", f"$.active_artifacts.{key}.artifact_id", f"must equal {expected_id!r}")
            version = mapping.get("version")
            if not isinstance(version, int) or isinstance(version, bool) or version < 1:
                validator.error("ARTIFACT_VERSION", f"$.active_artifacts.{key}.version", "must be a positive integer")
            validator.nonempty_string(mapping.get("path"), f"$.active_artifacts.{key}.path")
            if controlled_schema and key in SEMANTIC_ARTIFACT_OWNERS:
                validator.required(
                    mapping,
                    [
                        "content_sha256",
                        "semantic_owner",
                        "persistence_owner",
                        "source_invocation_ref",
                        "boundary_evidence_ref",
                    ],
                    f"$.active_artifacts.{key}",
                )
                digest = mapping.get("content_sha256")
                if not isinstance(digest, str) or SHA256_PATTERN.fullmatch(digest) is None:
                    validator.error(
                        "CONTENT_SHA256",
                        f"$.active_artifacts.{key}.content_sha256",
                        "must be a lowercase SHA-256 value",
                    )
                try:
                    expected_owner = semantic_artifact_owner(root, key)
                except InputError:
                    expected_owner = None  # The invalid marker is diagnosed above.
                if mapping.get("semantic_owner") != expected_owner:
                    validator.error(
                        "SEMANTIC_OWNER",
                        f"$.active_artifacts.{key}.semantic_owner",
                        f"must equal {expected_owner!r}",
                    )
                if mapping.get("persistence_owner") != "root_codex":
                    validator.error(
                        "PERSISTENCE_OWNER",
                        f"$.active_artifacts.{key}.persistence_owner",
                        "must equal 'root_codex'",
                    )
                validator.nonempty_string(
                    mapping.get("source_invocation_ref"),
                    f"$.active_artifacts.{key}.source_invocation_ref",
                )
                validator.nonempty_string(
                    mapping.get("boundary_evidence_ref"),
                    f"$.active_artifacts.{key}.boundary_evidence_ref",
                )
        run_state_entry = active_artifacts.get("run_state")
        artifact_metadata = root.get("artifact")
        if isinstance(run_state_entry, dict) and isinstance(artifact_metadata, dict):
            if run_state_entry.get("version") != artifact_metadata.get("version"):
                validator.error(
                    "ACTIVE_ARTIFACT_VERSION",
                    "$.active_artifacts.run_state.version",
                    "must match run-state artifact.version",
                )

    run = validator.mapping(root.get("run"), "$.run")
    if run is not None:
        validator.required(run, ["run_id", "project_id", "current_stage", "next_allowed_action"], "$.run")
        if run.get("current_stage") not in STAGE_IDS:
            validator.error("STAGE_ID", "$.run.current_stage", f"must be one of {STAGE_IDS}")

    stages = validator.sequence(root.get("stages"), "$.stages") or []
    stage_by_id: dict[str, dict[str, Any]] = {}
    for index, value in enumerate(stages):
        path = f"$.stages[{index}]"
        stage = validator.mapping(value, path)
        if stage is None:
            continue
        validator.required(stage, ["id", "status", "gate_id"], path)
        stage_id = stage.get("id")
        if isinstance(stage_id, str) and stage_id in stage_by_id:
            validator.error("ID_DUPLICATE", f"{path}.id", f"duplicate stage {stage_id!r}")
        elif isinstance(stage_id, str):
            stage_by_id[stage_id] = stage
        validator.enum(stage.get("status"), STAGE_STATUSES, f"{path}.status")
    if [item.get("id") for item in stages if isinstance(item, dict)] != STAGE_IDS:
        validator.error("STAGE_SET", "$.stages", f"must contain the fixed stage IDs in order: {STAGE_IDS}")

    gates = validator.sequence(root.get("gates"), "$.gates") or []
    gate_by_id: dict[str, dict[str, Any]] = {}
    for index, value in enumerate(gates):
        path = f"$.gates[{index}]"
        gate = validator.mapping(value, path)
        if gate is None:
            continue
        validator.required(gate, ["id", "status", "evidence_refs", "rationale"], path)
        gate_id = gate.get("id")
        if isinstance(gate_id, str) and gate_id in gate_by_id:
            validator.error("ID_DUPLICATE", f"{path}.id", f"duplicate gate {gate_id!r}")
        elif isinstance(gate_id, str):
            gate_by_id[gate_id] = gate
        validator.enum(gate.get("status"), STAGE_STATUSES, f"{path}.status")
        validator.sequence(gate.get("evidence_refs"), f"{path}.evidence_refs")
        validator.nonempty_string(gate.get("rationale"), f"{path}.rationale")
    for stage_id, stage in stage_by_id.items():
        stage_gate_id = stage.get("gate_id")
        gate = gate_by_id.get(stage_gate_id) if isinstance(stage_gate_id, str) else None
        if stage.get("status") != "PENDING" and gate is None:
            validator.error("GATE_MISSING", f"$.stages[{stage_id}].gate_id", "non-pending stage must have a gate record")
        if stage.get("status") == "PASSED" and gate is not None:
            if gate.get("status") != "PASSED":
                validator.error("GATE_MISMATCH", f"$.stages[{stage_id}].status", "PASSED stage requires a PASSED gate")
            if not gate.get("evidence_refs"):
                validator.error("GATE_EVIDENCE", f"$.gates[{stage.get('gate_id')}].evidence_refs", "PASSED gate requires evidence")

    repair = validator.mapping(root.get("repair"), "$.repair")
    if repair is not None:
        validator.required(repair, ["active_attempt", "maximum_attempts", "last_failure_ref"], "$.repair")
        active = repair.get("active_attempt")
        maximum = repair.get("maximum_attempts")
        if not isinstance(active, int) or isinstance(active, bool) or active < 0:
            validator.error("REPAIR_ATTEMPT", "$.repair.active_attempt", "must be a non-negative integer")
        if not isinstance(maximum, int) or isinstance(maximum, bool) or maximum < 1:
            validator.error("REPAIR_MAXIMUM", "$.repair.maximum_attempts", "must be a positive integer")
        if isinstance(active, int) and isinstance(maximum, int) and active > maximum:
            validator.error("REPAIR_LIMIT", "$.repair.active_attempt", "cannot exceed maximum_attempts")

    events = _validate_id_records(validator, root.get("bounce_back_events"), "$.bounce_back_events", r"BB-\d{3,}")
    for index, event in enumerate(events):
        path = f"$.bounce_back_events[{index}]"
        validator.required(
            event,
            ["created_at", "origin", "assigned_to", "classification", "status", "summary", "affected_stages", "affected_refs", "required_resolution", "resolution", "retry"],
            path,
        )
        validator.enum(event.get("classification"), BOUNCE_CLASSIFICATIONS, f"{path}.classification")
        validator.enum(event.get("status"), {"OPEN", "RESOLVED", "SUPERSEDED"}, f"{path}.status")
        if not _is_timezone_timestamp(event.get("created_at")):
            validator.error("TIMESTAMP_TIMEZONE", f"{path}.created_at", "must be an ISO 8601 timestamp with an explicit timezone")
        validator.nonempty_string(event.get("assigned_to"), f"{path}.assigned_to")
        validator.nonempty_string(event.get("summary"), f"{path}.summary")
        validator.nonempty_string(event.get("required_resolution"), f"{path}.required_resolution")
        origin = validator.mapping(event.get("origin"), f"{path}.origin")
        if origin is not None:
            validator.required(origin, ["role", "invocation_ref", "result_artifact_ref", "result"], f"{path}.origin")
            validator.nonempty_string(origin.get("role"), f"{path}.origin.role")
            validator.nonempty_string(origin.get("invocation_ref"), f"{path}.origin.invocation_ref")
            validator.nonempty_string(origin.get("result"), f"{path}.origin.result")
        affected = validator.sequence(event.get("affected_stages"), f"{path}.affected_stages")
        if affected is not None:
            if not affected:
                validator.error("BOUNCE_AFFECTED_STAGE", f"{path}.affected_stages", "must not be empty")
            for stage_id in affected:
                if stage_id not in STAGE_IDS:
                    validator.error("STAGE_ID", f"{path}.affected_stages", f"unknown stage {stage_id!r}")
        validator.sequence(event.get("affected_refs"), f"{path}.affected_refs")
        retry = validator.mapping(event.get("retry"), f"{path}.retry")
        if retry is not None:
            validator.required(retry, ["agent_role", "allowed", "change_basis", "prior_invocation_ref"], f"{path}.retry")
            validator.nonempty_string(retry.get("agent_role"), f"{path}.retry.agent_role")
            validator.nonempty_string(retry.get("prior_invocation_ref"), f"{path}.retry.prior_invocation_ref")
            allowed = retry.get("allowed")
            if not isinstance(allowed, bool):
                validator.error("RETRY_ALLOWED", f"{path}.retry.allowed", "must be true or false")
            change_basis = retry.get("change_basis")
            if not isinstance(change_basis, list):
                validator.error("RETRY_CHANGE_BASIS", f"{path}.retry.change_basis", "must be an array")
            else:
                invalid = [item for item in change_basis if item not in RETRY_CHANGE_BASES]
                if invalid:
                    validator.error("RETRY_CHANGE_BASIS", f"{path}.retry.change_basis", f"contains unsupported values {invalid}")
                if event.get("status") == "RESOLVED" and allowed is True and not change_basis:
                    validator.error("UNCHANGED_RETRY", f"{path}.retry.change_basis", "resolved retry requires a changed input, evidence, implementation, or decision")
            if event.get("status") == "OPEN" and allowed is not False:
                validator.error("OPEN_RETRY", f"{path}.retry.allowed", "open bounce-back must keep retry disabled")
        resolution = event.get("resolution")
        if event.get("status") == "RESOLVED":
            resolution_map = validator.mapping(resolution, f"{path}.resolution")
            if resolution_map is not None:
                validator.required(
                    resolution_map,
                    ["resolved_at", "resolved_by", "resolution_type", "summary", "changed_artifact_refs", "decision_refs", "evidence_refs"],
                    f"{path}.resolution",
                )
                validator.enum(resolution_map.get("resolution_type"), BOUNCE_RESOLUTION_TYPES, f"{path}.resolution.resolution_type")
                for field in ("changed_artifact_refs", "decision_refs", "evidence_refs"):
                    validator.sequence(resolution_map.get(field), f"{path}.resolution.{field}")

    blockers = _validate_id_records(validator, root.get("blockers"), "$.blockers", r"BLK-\d{3,}", status_allowed=ISSUE_STATUSES)
    for index, blocker in enumerate(blockers):
        if not isinstance(blocker.get("blocking"), bool):
            validator.error("BLOCKING_FLAG", f"$.blockers[{index}].blocking", "must be true or false")
    approvals = validator.sequence(root.get("required_approvals"), "$.required_approvals") or []
    approval_ids: set[str] = set()
    for index, value in enumerate(approvals):
        path = f"$.required_approvals[{index}]"
        approval = validator.mapping(value, path)
        if approval is None:
            continue
        validator.required(approval, ["id", "owner", "status", "summary"], path)
        identifier = approval.get("id")
        if not isinstance(identifier, str) or re.fullmatch(r"APPROVAL-\d{3,}", identifier) is None:
            validator.error("ID_FORMAT", f"{path}.id", "must match APPROVAL-###")
        elif identifier in approval_ids:
            validator.error("ID_DUPLICATE", f"{path}.id", f"duplicate ID {identifier}")
        else:
            approval_ids.add(identifier)
        validator.enum(approval.get("status"), APPROVAL_STATUSES, f"{path}.status")

    current_stage = run.get("current_stage") if run else None
    current = stage_by_id.get(current_stage) if isinstance(current_stage, str) else None
    if current_stage in STAGE_IDS and current is None:
        validator.error("CURRENT_STAGE", "$.run.current_stage", "does not resolve to a stage entry")
    release = stage_by_id.get("release", {})
    if controlled_schema and stage_by_id.get("verification", {}).get("status") == "PASSED":
        if not isinstance(control, dict) or control.get("verification_validation_identity") is None:
            validator.error(
                "VERIFICATION_IDENTITY_REQUIRED",
                "$.control.verification_validation_identity",
                "a passed verification stage requires a captured validation identity",
            )
    if release.get("status") == "PASSED":
        required_passed = ["intake", "framing", "contract", "repository_analysis", "implementation", "verification"]
        if direct_entry:
            required_passed.remove("framing")
        incomplete = [stage_id for stage_id in required_passed if stage_by_id.get(stage_id, {}).get("status") != "PASSED"]
        if incomplete:
            validator.error("FALSE_RELEASE", "$.stages.release", f"prior stages are not PASSED: {incomplete}")
        if any(item.get("blocking") is True and item.get("status") == "OPEN" for item in blockers):
            validator.error("FALSE_RELEASE", "$.stages.release", "cannot pass with an open blocking issue")
        if any(isinstance(item, dict) and item.get("status") == "PENDING" for item in approvals):
            validator.error("FALSE_RELEASE", "$.stages.release", "cannot pass with a pending approval")
    return validator.diagnostics


def validate_markdown_headings(text: str, required: list[str], artifact_path: str) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    positions: list[int] = []
    for heading in required:
        match = re.search(rf"^##\s+{re.escape(heading)}\s*$", text, flags=re.MULTILINE)
        if match is None:
            diagnostics.append(Diagnostic("MARKDOWN_HEADING", artifact_path, f"missing required heading: {heading}"))
        else:
            positions.append(match.start())
    if len(positions) == len(required) and positions != sorted(positions):
        diagnostics.append(Diagnostic("MARKDOWN_ORDER", artifact_path, "required headings are not in contract order"))
    return diagnostics


def markdown_metadata(text: str) -> dict[str, Any]:
    def field(label: str) -> str | None:
        match = re.search(rf"^-\s+{re.escape(label)}:\s*`?([^`\r\n]+)`?", text, flags=re.MULTILINE | re.IGNORECASE)
        return match.group(1).strip() if match else None

    version = field("Artifact version") or field("Version")
    return {
        "artifact_id": field("Artifact ID"),
        "version": int(version) if isinstance(version, str) and version.isdigit() else version,
        "lifecycle_status": field("Lifecycle status"),
        "semantic_owner": field("Semantic owner") or field("Owner role"),
    }


def parse_verification_results(text: str) -> tuple[str | None, dict[str, str], list[Diagnostic]]:
    diagnostics: list[Diagnostic] = []
    overall_match = re.search(
        r"^##\s+Overall Assessment\s*$([\s\S]*?)(?=^##\s+|\Z)",
        text,
        flags=re.MULTILINE,
    )
    overall = None
    if overall_match:
        token = re.search(r"\b(READY|NOT_READY|UNVERIFIED)\b", overall_match.group(1))
        if token:
            overall = token.group(1)
    if overall not in OVERALL_RESULTS:
        diagnostics.append(Diagnostic("VERIFICATION_OVERALL", "verification_report.md", "missing READY, NOT_READY, or UNVERIFIED overall assessment"))

    section_match = re.search(
        r"^##\s+Requirement Results\s*$([\s\S]*?)(?=^##\s+|\Z)",
        text,
        flags=re.MULTILINE,
    )
    results: dict[str, str] = {}
    if section_match is None:
        return overall, results, diagnostics
    for line in section_match.group(1).splitlines():
        if not line.lstrip().startswith("|"):
            continue
        cells = [cell.strip().replace("`", "") for cell in line.strip().strip("|").split("|")]
        if not cells or re.fullmatch(r"REQ-\d{3,}", cells[0]) is None:
            continue
        result = next((cell for cell in cells[1:] if cell in REQUIREMENT_RESULTS), None)
        if result is None:
            diagnostics.append(Diagnostic("VERIFICATION_RESULT", f"verification_report.md:{cells[0]}", "row lacks PASS, FAIL, or UNVERIFIED"))
            continue
        if cells[0] in results:
            diagnostics.append(Diagnostic("VERIFICATION_DUPLICATE", f"verification_report.md:{cells[0]}", "requirement appears more than once"))
        results[cells[0]] = result
    return overall, results, diagnostics


def parse_problem_frame_readiness(text: str) -> str | None:
    section = re.search(
        r"^##\s+Completion Status\s*$([\s\S]*?)(?=^##\s+|\Z)",
        text,
        flags=re.MULTILINE,
    )
    if section is None:
        return None
    match = re.search(r"\b(PASS_WITH_ASSUMPTIONS|PASS|BLOCKED)\b", section.group(1))
    return match.group(1) if match else None


def _validate_active_identity(
    project_root: Path,
    run_dir: Path,
    mapping: dict[str, Any],
    key: str,
    candidate: Path,
    validator: Validator,
) -> None:
    recorded_hash = mapping.get("content_sha256")
    if isinstance(recorded_hash, str) and SHA256_PATTERN.fullmatch(recorded_hash) is not None and candidate.is_file():
        try:
            current_hash = sha256_file(candidate)
        except OSError as exc:
            validator.error("ARTIFACT_READ", str(candidate), str(exc))
        else:
            if current_hash != recorded_hash:
                validator.error(
                    "ACTIVE_ARTIFACT_HASH",
                    f"$.active_artifacts.{key}.content_sha256",
                    f"recorded {recorded_hash} does not match current {current_hash}",
                )

    evidence_ref = mapping.get("boundary_evidence_ref")
    if not isinstance(evidence_ref, str) or not evidence_ref:
        return
    try:
        normalized_evidence_ref = normalize_repository_reference(evidence_ref)
    except InputError:
        validator.error(
            "BOUNDARY_EVIDENCE",
            f"$.active_artifacts.{key}.boundary_evidence_ref",
            "must be repository- or run-relative",
        )
        return
    evidence_path = (project_root / normalized_evidence_ref).resolve(strict=False)
    if not evidence_path.exists():
        evidence_path = (run_dir / normalized_evidence_ref).resolve(strict=False)
    try:
        evidence_path.relative_to(run_dir.resolve())
    except ValueError:
        validator.error(
            "BOUNDARY_EVIDENCE",
            f"$.active_artifacts.{key}.boundary_evidence_ref",
            "must remain inside the run directory",
        )
        return
    try:
        evidence = read_structured(evidence_path)
    except InputError as exc:
        validator.error("BOUNDARY_EVIDENCE", str(evidence_path), str(exc))
        return
    # The state validator independently checks this owner against the run marker.
    expected_role = mapping.get("semantic_owner", SEMANTIC_ARTIFACT_OWNERS.get(key))
    if (
        not isinstance(evidence, dict)
        or evidence.get("artifact_type") != "role-boundary-result"
        or evidence.get("status") != "PASS"
        or evidence.get("role") != expected_role
        or evidence.get("invocation_ref") != mapping.get("source_invocation_ref")
    ):
        validator.error(
            "BOUNDARY_EVIDENCE",
            str(evidence_path),
            "must be a matching role-boundary PASS for the active source invocation",
        )


def _active_artifact_path(
    project_root: Path,
    run_dir: Path,
    entry: Any,
    key: str,
    validator: Validator,
) -> Path | None:
    if entry is None:
        return None
    mapping = validator.mapping(entry, f"$.active_artifacts.{key}")
    if mapping is None:
        return None
    validator.required(mapping, ["artifact_id", "version", "path"], f"$.active_artifacts.{key}")
    raw_path = mapping.get("path")
    if not isinstance(raw_path, str) or not raw_path:
        validator.error("ARTIFACT_PATH", f"$.active_artifacts.{key}.path", "must be a non-empty relative path")
        return None
    try:
        normalized_raw_path = normalize_repository_reference(raw_path)
    except InputError:
        validator.error("ARTIFACT_PATH", f"$.active_artifacts.{key}.path", "must be repository- or run-relative")
        return None
    candidate = (project_root / normalized_raw_path).resolve(strict=False)
    if not candidate.exists():
        candidate = (run_dir / normalized_raw_path).resolve(strict=False)
    try:
        candidate.relative_to(run_dir.resolve())
    except ValueError:
        validator.error("ARTIFACT_SCOPE", f"$.active_artifacts.{key}.path", "active artifact must remain inside the run directory")
        return None
    if not candidate.is_file():
        validator.error("ARTIFACT_MISSING", f"$.active_artifacts.{key}.path", f"file does not exist: {raw_path}")
    else:
        _validate_active_identity(project_root, run_dir, mapping, key, candidate, validator)
    return candidate


def _bound_candidate_path(
    project_root: Path,
    run_dir: Path,
    raw: Any,
    *,
    run_bound: bool,
) -> Path:
    if not isinstance(raw, str) or not raw.strip():
        raise InputError("captured path must be a non-empty string")
    normalized = normalize_repository_reference(raw)
    if not run_bound:
        candidate = resolve_within(project_root, normalized, must_exist=True)
        if not candidate.is_file():
            raise InputError(f"captured path is not a file: {raw}")
        return candidate
    candidates = {
        candidate.resolve()
        for candidate in (project_root / normalized, run_dir / normalized)
        if candidate.is_file()
    }
    contained = [candidate for candidate in candidates if candidate.is_relative_to(run_dir.resolve())]
    if len(contained) != 1:
        raise InputError("captured run path must resolve unambiguously inside the run")
    return contained[0]


def validate_verification_reconciliation(
    project_root: Path,
    run_dir: Path,
    state_data: dict[str, Any],
) -> list[Diagnostic]:
    """Require release to use the verification bytes captured when verification passed."""

    if not is_controlled_run_state(state_data):
        return []
    validator = Validator()
    control = state_data.get("control")
    identity = control.get("verification_validation_identity") if isinstance(control, dict) else None
    active = state_data.get("active_artifacts")
    entry = active.get("verification_report") if isinstance(active, dict) else None
    if not isinstance(identity, dict) or not isinstance(entry, dict):
        validator.error(
            "RELEASE_RECONCILIATION",
            "$.control.verification_validation_identity",
            "release requires an active report and captured verification identity",
        )
        return validator.diagnostics
    for field in ("artifact_id", "version", "path", "content_sha256"):
        if identity.get(field) != entry.get(field):
            validator.error(
                "RELEASE_RECONCILIATION",
                f"$.control.verification_validation_identity.{field}",
                "does not match the active verification report",
            )
    path = _active_artifact_path(project_root, run_dir, entry, "verification_report", validator)
    if path is not None and path.is_file() and isinstance(identity.get("content_sha256"), str):
        try:
            current_hash = sha256_file(path)
        except OSError as exc:
            validator.error("ARTIFACT_READ", str(path), str(exc))
        else:
            if current_hash != identity["content_sha256"]:
                validator.error(
                    "RELEASE_RECONCILIATION",
                    str(path),
                    "active verification bytes changed after verification validation",
                )
    return _validate_candidate_binding(project_root, run_dir, state_data, identity, validator)


def validate_revalidation_candidate(project_root: Path, run_dir: Path, state_data: dict[str, Any]) -> list[Diagnostic]:
    """A reopened evidence review retains its candidate until formal repair."""
    identity = state_data.get("control", {}).get("verification_validation_identity")
    if not isinstance(identity, dict):
        return []
    return _validate_candidate_binding(project_root, run_dir, state_data, identity, Validator())


def _validate_candidate_binding(
    project_root: Path, run_dir: Path, state_data: dict[str, Any],
    identity: dict[str, Any], validator: Validator,
) -> list[Diagnostic]:
    active = state_data.get("active_artifacts")
    binding = identity.get("candidate_binding")
    if binding is None:
        # Schema 1.1 predates candidate binding. It remains readable, but is
        # deliberately ineligible to become a revision baseline.
        return validator.diagnostics
    if not isinstance(binding, dict):
        validator.error(
            "RELEASE_RECONCILIATION",
            "$.control.verification_validation_identity.candidate_binding",
            "captured candidate binding must be an object",
        )
        return validator.diagnostics

    bound_paths: dict[str, Path] = {}
    for name in ("product_contract", "manifest", "inspection", "archive"):
        try:
            bound_paths[name] = _bound_candidate_path(
                project_root,
                run_dir,
                binding.get(f"{name}_path"),
                run_bound=name != "archive",
            )
        except InputError as exc:
            validator.error(
                "RELEASE_RECONCILIATION",
                f"$.control.verification_validation_identity.candidate_binding.{name}_path",
                str(exc),
            )
    if len(bound_paths) != 4:
        return validator.diagnostics

    for name, candidate in bound_paths.items():
        expected_hash = binding.get(f"{name}_sha256")
        try:
            actual_hash = sha256_file(candidate)
        except OSError as exc:
            validator.error("ARTIFACT_READ", str(candidate), str(exc))
            continue
        if actual_hash != expected_hash:
            validator.error(
                "RELEASE_RECONCILIATION",
                f"$.control.verification_validation_identity.candidate_binding.{name}_sha256",
                f"captured {name} bytes changed after verification validation",
            )

    contract_entry = active.get("product_contract") if isinstance(active, dict) else None
    contract_path = _active_artifact_path(
        project_root, run_dir, contract_entry, "product_contract", validator
    )
    if not isinstance(contract_entry, dict) or contract_path is None:
        validator.error("RELEASE_RECONCILIATION", "$.active_artifacts.product_contract", "captured candidate requires an active contract")
    else:
        contract_ref = f"{contract_entry.get('artifact_id')}@{contract_entry.get('version')}"
        if binding.get("product_contract_ref") != contract_ref:
            validator.error("RELEASE_RECONCILIATION", "$.control.verification_validation_identity.candidate_binding.product_contract_ref", "does not match the active contract")
        if contract_path.resolve() != bound_paths["product_contract"]:
            validator.error("RELEASE_RECONCILIATION", "$.control.verification_validation_identity.candidate_binding.product_contract_path", "does not identify the active contract")

    inspection_ok, inspection_message, inspection = passing_package_inspection(
        project_root, bound_paths["inspection"]
    )
    if not inspection_ok or not isinstance(inspection, dict):
        validator.error("RELEASE_RECONCILIATION", str(bound_paths["inspection"]), inspection_message)
        return validator.diagnostics
    try:
        inspection_manifest = _bound_candidate_path(
            project_root, run_dir, inspection.get("manifest_path"), run_bound=True
        )
        inspection_archive = _bound_candidate_path(
            project_root, run_dir, inspection.get("archive_path"), run_bound=False
        )
        manifest = read_structured(bound_paths["manifest"])
        from .evidence import reconcile_source

        source_result = CommandResult(command="source-reconciliation")
        released = any(
            isinstance(stage, dict) and stage.get("id") == "release" and stage.get("status") == "PASSED"
            for stage in state_data.get("stages", [])
        )
        # A retained completed baseline describes its archive, not the live
        # tree that a later authorized revision is expected to change.
        if isinstance(manifest, dict) and not released:
            reconcile_source(project_root, manifest, manifest.get("entries"), source_result)
        for diagnostic in source_result.diagnostics:
            validator.error("RELEASE_RECONCILIATION", diagnostic.path, diagnostic.message)
        manifest_archive = _bound_candidate_path(
            project_root,
            run_dir,
            manifest.get("archive_path") if isinstance(manifest, dict) else None,
            run_bound=False,
        )
    except InputError as exc:
        validator.error("RELEASE_RECONCILIATION", str(bound_paths["inspection"]), str(exc))
    else:
        if inspection_manifest != bound_paths["manifest"]:
            validator.error("RELEASE_RECONCILIATION", "$.control.verification_validation_identity.candidate_binding.manifest_path", "inspection no longer identifies the captured manifest")
        if inspection_archive != bound_paths["archive"] or manifest_archive != bound_paths["archive"]:
            validator.error("RELEASE_RECONCILIATION", "$.control.verification_validation_identity.candidate_binding.archive_path", "inspection or manifest no longer identifies the captured archive")
    return validator.diagnostics


def validate_stage_artifact_readiness(
    project_root: Path,
    run_dir: Path,
    state_data: dict[str, Any],
    stage_id: str,
) -> list[Diagnostic]:
    """Validate the authoritative artifact that semantically gates one stage."""

    validator = Validator()
    artifacts = state_data.get("active_artifacts")
    if not isinstance(artifacts, dict):
        validator.error("ACTIVE_ARTIFACT", "$.active_artifacts", "must be an object before evaluating a semantic gate")
        return validator.diagnostics
    artifact_key = {
        "intake": "build_request",
        "framing": "problem_frame",
        "contract": "product_contract",
        "verification": "verification_report",
    }.get(stage_id)
    if artifact_key is None:
        return []
    path = _active_artifact_path(project_root, run_dir, artifacts.get(artifact_key), artifact_key, validator)
    if path is None or not path.is_file():
        return validator.diagnostics
    try:
        if stage_id == "intake":
            data = read_structured(path)
            validator.diagnostics.extend(validate_build_request_data(data))
            readiness = data.get("handoff", {}).get("readiness") if isinstance(data, dict) and isinstance(data.get("handoff"), dict) else None
            if readiness not in {"PASS", "PASS_WITH_ASSUMPTIONS"}:
                validator.error("STAGE_READINESS", str(path), f"intake handoff readiness must permit progression; found {readiness!r}")
        elif stage_id == "framing":
            text = path.read_text(encoding="utf-8")
            readiness = parse_problem_frame_readiness(text)
            if readiness not in {"PASS", "PASS_WITH_ASSUMPTIONS"}:
                validator.error("STAGE_READINESS", str(path), f"problem frame readiness must permit progression; found {readiness!r}")
        elif stage_id == "contract":
            data = read_structured(path)
            validator.diagnostics.extend(validate_product_contract_data(data))
            readiness = data.get("readiness", {}).get("status") if isinstance(data, dict) and isinstance(data.get("readiness"), dict) else None
            if readiness not in {"PASS", "PASS_WITH_ASSUMPTIONS"}:
                validator.error("STAGE_READINESS", str(path), f"product contract readiness must permit progression; found {readiness!r}")
        elif stage_id == "verification":
            text = path.read_text(encoding="utf-8")
            overall, _, parsed = parse_verification_results(text)
            validator.diagnostics.extend(parsed)
            if overall != "READY":
                validator.error("STAGE_READINESS", str(path), f"verification must be READY before progression; found {overall!r}")
    except (InputError, OSError, UnicodeError) as exc:
        validator.error("ARTIFACT_READ", str(path), str(exc))
    return validator.diagnostics


def validate_semantic_prerequisites(
    project_root: Path,
    run_dir: Path,
    state_data: dict[str, Any],
    stage_ids: Iterable[str],
) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    for stage_id in stage_ids:
        diagnostics.extend(validate_stage_artifact_readiness(project_root, run_dir, state_data, stage_id))
    return diagnostics


def validate_contract_file(path: Path) -> CommandResult:
    result = CommandResult(command="validate-contract")
    if not path.is_file():
        result.add("INPUT_MISSING", str(path), "contract file does not exist")
        return result
    try:
        data = read_structured(path)
    except InputError as exc:
        result.add("PARSE_ERROR", str(path), str(exc))
        return result
    result.extend(validate_product_contract_data(data))
    if result.ok:
        result.data = {
            "contract_path": str(path),
            "requirement_count": len(data["requirements"]),
            "acceptance_method_count": len(data["acceptance_methods"]),
            "schema_version": data["schema_version"],
        }
    return result


def validate_run_directory(
    project_root: Path,
    run_dir: Path,
    *,
    _revision_guard: frozenset[Path] | None = None,
) -> CommandResult:
    from .workflow import validate_contract_sources, validate_run_state_context

    result = CommandResult(command="validate-run")
    validator = Validator()
    if not run_dir.is_dir():
        result.add("RUN_MISSING", str(run_dir), "run directory does not exist")
        return result

    required_directories = [
        "00_intake",
        "10_framing",
        "20_contract",
        "30_execution",
        "40_verification",
        "50_release",
    ]
    for relative in required_directories:
        if not (run_dir / relative).is_dir():
            validator.error("RUN_DIRECTORY", relative, "required stage directory is missing")

    state_path = run_dir / "30_execution" / "run_state.json"
    build_path = run_dir / "00_intake" / "build_request.yaml"
    state_data: dict[str, Any] | None = None
    build_data: dict[str, Any] | None = None
    for path, label, validation in (
        (build_path, "build_request", validate_build_request_data),
        (state_path, "run_state", validate_run_state_data),
    ):
        if not path.is_file():
            validator.error("ARTIFACT_MISSING", str(path), f"required {label} artifact is missing")
            continue
        try:
            data = read_structured(path)
        except InputError as exc:
            validator.error("PARSE_ERROR", str(path), str(exc))
            continue
        validator.diagnostics.extend(
            validate_run_state_context(project_root, run_dir, data)
            if label == "run_state" else validation(data)
        )
        if label == "build_request" and isinstance(data, dict):
            build_data = data
        if label == "run_state" and isinstance(data, dict):
            state_data = data

    contract_data: dict[str, Any] | None = None
    verification_text: str | None = None
    if state_data is not None:
        artifacts = state_data.get("active_artifacts")
        if isinstance(artifacts, dict):
            paths: dict[str, Path | None] = {}
            for key in ("build_request", "problem_frame", "product_contract", "run_state", "verification_report"):
                paths[key] = _active_artifact_path(project_root, run_dir, artifacts.get(key), key, validator)

            expected = {
                "build_request": "build-request",
                "problem_frame": "problem-frame",
                "product_contract": "product-contract",
                "run_state": "run-state",
                "verification_report": "verification-report",
            }
            for key in ("build_request", "run_state"):
                entry = artifacts.get(key)
                if entry is None:
                    validator.error("ACTIVE_ARTIFACT", f"$.active_artifacts.{key}", "must always be active")

            stage_by_id = {
                item.get("id"): item
                for item in state_data.get("stages", [])
                if isinstance(item, dict) and isinstance(item.get("id"), str)
            }
            requirements_by_stage = {
                # IN_PROGRESS is the normal document-registration window: the
                # owning artifact may be absent before persist-artifact and
                # active afterward. Terminal semantic states require the
                # registered artifact that justifies their conclusion.
                "framing": ("problem_frame", {"PASSED", "FAILED", "BLOCKED"}),
                "contract": ("product_contract", {"PASSED", "FAILED", "BLOCKED"}),
                "verification": ("verification_report", {"PASSED", "FAILED", "BLOCKED"}),
                # Release consumes an already registered verification report;
                # it never owns the report-registration window.
                "release": ("verification_report", {"IN_PROGRESS", "PASSED", "FAILED", "BLOCKED"}),
            }
            for stage_id, (key, required_statuses) in requirements_by_stage.items():
                stage = stage_by_id.get(stage_id)
                if isinstance(stage, dict) and stage.get("status") in required_statuses and artifacts.get(key) is None:
                    validator.error(
                        "ACTIVE_ARTIFACT",
                        f"$.active_artifacts.{key}",
                        f"required when {stage_id} is {stage.get('status')}",
                    )

            for key, path in paths.items():
                if path is None or not path.is_file():
                    continue
                entry = artifacts.get(key)
                if path.suffix.lower() in {".yaml", ".yml", ".json"}:
                    try:
                        data = read_structured(path)
                    except InputError as exc:
                        validator.error("PARSE_ERROR", str(path), str(exc))
                        continue
                    if key == "product_contract":
                        contract_data = data if isinstance(data, dict) else None
                        validator.diagnostics.extend(validate_product_contract_data(data))
                    artifact = data.get("artifact") if isinstance(data, dict) else None
                    if isinstance(artifact, dict) and isinstance(entry, dict):
                        if artifact.get("artifact_id") != expected[key] or artifact.get("artifact_id") != entry.get("artifact_id"):
                            validator.error("ACTIVE_ARTIFACT_ID", f"$.active_artifacts.{key}", "active reference does not match artifact metadata")
                        if artifact.get("version") != entry.get("version"):
                            validator.error("ACTIVE_ARTIFACT_VERSION", f"$.active_artifacts.{key}", "active version does not match artifact metadata")
                else:
                    try:
                        text = path.read_text(encoding="utf-8")
                    except (OSError, UnicodeError) as exc:
                        validator.error("ARTIFACT_READ", str(path), str(exc))
                        continue
                    headings = PROBLEM_FRAME_HEADINGS if key == "problem_frame" else VERIFICATION_HEADINGS
                    validator.diagnostics.extend(validate_markdown_headings(text, headings, str(path)))
                    metadata = markdown_metadata(text)
                    if isinstance(entry, dict):
                        if is_controlled_run_state(state_data) and state_data["control"].get("intent_realization") == CONTROL_REVISION and metadata.get("semantic_owner") != entry.get("semantic_owner"):
                            validator.error("SEMANTIC_OWNER", f"$.active_artifacts.{key}.semantic_owner", "active owner does not match Markdown metadata")
                        if metadata.get("artifact_id") != entry.get("artifact_id"):
                            validator.error("ACTIVE_ARTIFACT_ID", f"$.active_artifacts.{key}", "active reference does not match Markdown metadata")
                        if metadata.get("version") != entry.get("version"):
                            validator.error("ACTIVE_ARTIFACT_VERSION", f"$.active_artifacts.{key}", "active version does not match Markdown metadata")
                    if key == "verification_report":
                        verification_text = text

        if build_data is not None:
            build_project = build_data.get("project", {}).get("project_id") if isinstance(build_data.get("project"), dict) else None
            state_project = state_data.get("run", {}).get("project_id") if isinstance(state_data.get("run"), dict) else None
            if build_project != state_project:
                validator.error("PROJECT_ID_MISMATCH", "$.run.project_id", "run state and build request project IDs differ")

    coverage_contract = contract_data
    # A counted contract revision retains the old report as historical evidence
    # until a new verifier submission replaces it. Check that report against its
    # own exact contract, without granting it authority over the revised one.
    if state_data is not None and is_agent_artifact_run(state_data):
        rounds = state_data.get("repair", {}).get("rounds", [])
        current_round = rounds[-1] if rounds and isinstance(rounds[-1], dict) else {}
        source = current_round.get("source_verification")
        active_report = state_data.get("active_artifacts", {}).get("verification_report")
        verification_stage = next((s for s in state_data.get("stages", []) if isinstance(s, dict) and s.get("id") == "verification"), {})
        if (current_round.get("status") == "IN_PROGRESS" and verification_stage.get("status") == "IN_PROGRESS"
                and isinstance(source, dict) and isinstance(active_report, dict)
                and source.get("report_ref") == f"{active_report.get('artifact_id')}@{active_report.get('version')}"
                and source.get("report_sha256") == active_report.get("content_sha256")):
            try:
                binding = source["candidate_binding"]
                canonical = run_dir / "20_contract/product_contract.yaml"
                version = binding["product_contract_ref"].rsplit("@", 1)[1]
                historical = canonical.parent / "history" / f"{canonical.stem}.v{version}{canonical.suffix}"
                bound = next((p for p in (canonical, historical) if p.is_file() and sha256_file(p) == binding["product_contract_sha256"]), None)
                if bound is None:
                    raise InputError("retained source report requires its exact original contract")
                coverage_contract = read_structured(bound)
                if not isinstance(coverage_contract, dict):
                    raise InputError("retained report contract must contain an object")
            except (InputError, OSError, KeyError, TypeError, ValueError) as exc:
                validator.error("ROUND_CONTRACT_IDENTITY", "verification_report.md", str(exc))

    if coverage_contract is not None and verification_text is not None:
        overall, verification_results, parse_diagnostics = parse_verification_results(verification_text)
        validator.diagnostics.extend(parse_diagnostics)
        requirement_ids = [item.get("id") for item in coverage_contract.get("requirements", []) if isinstance(item, dict)]
        if set(verification_results) != set(requirement_ids) or len(verification_results) != len(requirement_ids):
            missing = sorted(set(requirement_ids) - set(verification_results))
            extra = sorted(set(verification_results) - set(requirement_ids))
            validator.error("VERIFICATION_COVERAGE", "verification_report.md", f"must cover every active requirement exactly once; missing={missing}, extra={extra}")
        if overall == "READY" and any(value != "PASS" for value in verification_results.values()):
            validator.error("FALSE_VERIFICATION_READY", "verification_report.md", "READY requires every active requirement result to PASS")

        if state_data is not None:
            stage_map = {item.get("id"): item for item in state_data.get("stages", []) if isinstance(item, dict)}
            if stage_map.get("release", {}).get("status") == "PASSED":
                if overall != "READY" or any(value != "PASS" for value in verification_results.values()):
                    validator.error("FALSE_RELEASE", "$.stages.release", "release cannot pass without a READY all-PASS verification report")
                open_blockers = [
                    item for item in state_data.get("blockers", [])
                    if isinstance(item, dict) and item.get("blocking") is True and item.get("status") == "OPEN"
                ]
                pending_approvals = [
                    item for item in state_data.get("required_approvals", [])
                    if isinstance(item, dict) and item.get("status") == "PENDING"
                ]
                if open_blockers or pending_approvals:
                    validator.error("FALSE_RELEASE", "$.stages.release", "release cannot pass with open blockers or pending approvals")

    if state_data is not None:
        stage_map = {item.get("id"): item for item in state_data.get("stages", []) if isinstance(item, dict)}
        for semantic_stage in ("intake", "framing", "contract", "verification"):
            if stage_map.get(semantic_stage, {}).get("status") == "PASSED":
                validator.diagnostics.extend(
                    validate_stage_artifact_readiness(project_root, run_dir, state_data, semantic_stage)
                )
        if stage_map.get("verification", {}).get("status") == "PASSED":
            validator.diagnostics.extend(validate_contract_sources(project_root, run_dir, state_data, contract_data))
            validator.diagnostics.extend(validate_verification_reconciliation(project_root, run_dir, state_data))
        if is_controlled_run_state(state_data) and stage_map.get("release", {}).get("status") == "PASSED":
            tests_ok, tests_message, _ = passing_test_results(
                run_dir / "30_execution" / "test_results.json", project_root
            )
            if not tests_ok:
                validator.error("TESTS_NOT_PASSING", "30_execution/test_results.json", tests_message)
            inspection_ok, inspection_message, _ = passing_package_inspection(
                project_root, run_dir / "50_release" / "package_inspection.json"
            )
            if not inspection_ok:
                validator.error("PACKAGE_NOT_INSPECTED", "50_release/package_inspection.json", inspection_message)

    if build_data is not None and state_data is not None:
        from .revision import validate_revision_contract

        validator.diagnostics.extend(
            validate_revision_contract(
                project_root,
                build_data,
                state_data,
                contract_data,
                _lineage_guard=(_revision_guard or frozenset()) | {run_dir.resolve()},
            )
        )

    result.extend(validator.diagnostics)
    if result.ok:
        result.data = {
            "run_dir": str(run_dir),
            "schema_version": state_data.get("schema_version") if state_data else None,
            "current_stage": state_data.get("run", {}).get("current_stage") if state_data else None,
            "validated_stage_directories": required_directories,
        }
    return result
