"""Static role/transport policy guards; these do not establish live role behavior."""

from __future__ import annotations

import hashlib
import re
import tomllib
from pathlib import Path

import pytest

from pipeline_control.submissions import SUBMISSION_FILES


REPO_ROOT = Path(__file__).resolve().parents[3]
ROLES = {
    "intent_realizer": ("# Intent Realization Agent", "a57a8ba258b21a293fec27f51c4649f45ac7c77a9748417824e036e8114dc73a"),
    "product_contract_agent": ("# Product Contract Agent", "5faa4d56b27ee7a5190e1da932334b3fba6af2a6a34a361303b729bff4dd57ae"),
    "independent_verifier": ("# Independent Verifier", "4760be163e75ba52b4df3851f196fcb1ac276b6917781955cc9502e7c88d9174"),
}


def _instructions(role: str) -> str:
    config = tomllib.loads((REPO_ROOT / ".codex/agents" / f"{role}.toml").read_text(encoding="utf-8"))
    return config["developer_instructions"]


def _section(text: str, heading: str) -> str:
    marker = f"## {heading}\n"
    assert text.count(marker) == 1, f"missing or duplicate procedure section: {heading}"
    return text.split(marker, 1)[1].split("\n## ", 1)[0].strip()


def _subsection(text: str, heading: str) -> str:
    marker = f"### {heading}\n"
    assert text.count(marker) == 1, f"missing or duplicate output branch: {heading}"
    return re.split(r"\n#{1,3} ", text.split(marker, 1)[1], maxsplit=1)[0].strip()


@pytest.mark.parametrize("role", ROLES)
def test_s4_preserves_semantic_reasoning_and_keeps_it_pipeline_independent(role: str) -> None:
    title, expected_digest = ROLES[role]
    instructions = _instructions(role)
    semantic = instructions.split("## Task procedure and return", 1)[0]
    semantic = semantic[semantic.index(title):]
    # At S4 intake realizer's old runtime paragraph followed the reasoning.
    # Its relocation is permitted; the actual realization/readiness text is not.
    semantic = semantic.split("\nPermitted writes:", 1)[0].replace("\r\n", "\n").strip()
    assert hashlib.sha256(semantic.encode("utf-8")).hexdigest() == expected_digest
    assert not re.search(r"\bpipeline\b|Workflow [AB]|\.agents/|\.codex/|semantic_role_boundary|role-boundary|workspace/", semantic)


@pytest.mark.parametrize("role", ROLES)
def test_exact_result_file_exception_requires_explicit_binding_and_runtime_permission(role: str) -> None:
    instructions = _instructions(role)
    runtime = " ".join(_section(instructions, "Runtime boundary").split())
    assert "one exact new noncanonical file assigned by the parent" in runtime
    assert "procedure identity, current input identities, exact output path and completion conditions" in runtime
    assert "actual runtime permission for that path" in runtime
    assert "An output filename alone or ordinary role selection does not grant write authority" in runtime
    assert "Ordinary/unbound work remains read-only" in runtime
    assert re.search(r"If a binding is missing.*?report the affected work as blocked", runtime)
    assert "silently substitute a body return for a required file submission" in runtime
    assert "Never write canonical artifacts, orchestration state, another role's output, prior submissions, input snapshots" in runtime
    assert "symlink, junction or hard-link aliases" in runtime
    assert "parent owns registration and state changes" in runtime
    assert "permissions are inherited from the parent" in runtime
    assert "do not create a separate operating-system sandbox" in runtime
    procedure = " ".join(_section(instructions, "Task procedure and return").split())
    assert "Ordinary assignments use a task-appropriate response" in procedure
    assert "complete file and a compact reference return" in procedure
    assert "output transport does not alter the semantic judgment" in procedure


def test_result_file_exception_does_not_expand_verifier_evidence_authority() -> None:
    runtime = " ".join(_section(_instructions("independent_verifier"), "Runtime boundary").split())
    assert "Independent evidence exception" in runtime
    assert "evidence directory explicitly authorized by the parent for this task" in runtime
    assert "Without such a directory, perform read-only review unless the exact result-file exception above applies" in runtime
    assert "Do not modify the verification target, its delivered tests, acceptance baseline, existing evidence, canonical report, orchestration state, or governing instructions" in runtime
    assert "Keep generated execution output inside the authorized evidence boundary" in runtime
    assert "restrict evidence writes further, including to one exact file" in runtime


@pytest.mark.parametrize("skill,expected_digest", [
    ("author-product-contract", "6962a7516cedd19f7554e165541b08ec562bf4a4f2e70b316dfc5644c29ceee6"),
    ("independent-verification", "a611ff92c915838f31b684d3fc0261adf5712d9e46495165008740a9daf8654c"),
])
def test_s4_leaves_generic_contract_and_verification_skill_semantics_unchanged(skill: str, expected_digest: str) -> None:
    body = (REPO_ROOT / ".agents/skills" / skill / "SKILL.md").read_text(encoding="utf-8")
    semantic = body.split("## Required Inputs", 1)[1].split("## Revision History", 1)[0]
    semantic = ("## Required Inputs" + semantic).replace("\r\n", "\n").strip()
    assert hashlib.sha256(semantic.encode("utf-8")).hexdigest() == expected_digest


def test_invocation_selects_transport_explicitly_and_consumers_read_registered_bodies() -> None:
    body = (REPO_ROOT / ".agents/skills/build-tool-pipeline/references/invocation.md").read_text(encoding="utf-8")
    selection = " ".join(_section(body, "Select the governed transport").split())
    assert 'Normal initialization selects "1.2"' in selection
    assert 'Control.semantic_role_boundary: "1.1" or "1.2" selects' in selection
    assert 'Explicit `--control-revision 1.0` selects a new legacy run' in selection
    assert "Never infer selection from a role name" in selection
    assert "Do not upgrade an existing run or strip its marker for rollback" in selection
    rows = [line for line in _section(body, "Select the governed transport").splitlines() if line.startswith("| ")]
    ordinary = next(row for row in rows if "Ordinary reusable role" in row)
    legacy = next(row for row in rows if "Governed legacy control" in row)
    selected = next(row for row in rows if "Selected artifact invocation" in row)
    assert "Calling task's useful return format" in ordinary
    assert "Complete semantic body returned to Root" in legacy
    assert "exact start-result submission_path" in selected and "expected digest" in selected
    binding = " ".join(_section(body, "Bind the current task").split())
    for field in ("submission_path", "round_number", "baseline_sha256", "--expected-source-sha256"):
        assert field in binding
    assert "each role reads the authorized original sources and registered upstream bodies" in binding
    assert "downstream consumers read the registered body and its original sources rather than only the compact message" in binding
    assert "Do not routinely re-author or duplicate the specialist judgment" in binding
    ordinary_scope = " ".join(_section(body, "Ordinary work and other procedures").split())
    assert "No build request, run state, REQ/ACC vocabulary, release package or repository adapter is required solely" in ordinary_scope


@pytest.mark.parametrize("adapter", ["contract-adapter.md", "verification-adapter.md"])
def test_output_adapters_preserve_legacy_complete_body_and_selected_compact_identity(adapter: str) -> None:
    text = (REPO_ROOT / ".agents/skills/build-tool-pipeline/references" / adapter).read_text(encoding="utf-8")
    selected = " ".join(_subsection(text, "Selected compact return").split())
    legacy = " ".join(_subsection(text, "Legacy full-body return").split())
    assert 'selected "1.1"' in selected.lower()
    assert all(field in selected for field in ("actual", "path", "artifact ID/version", "SHA-256", "invocation", "inputs read", "evidence references"))
    assert "complete" in legacy and "body" in legacy
    if adapter == "contract-adapter.md":
        assert "complete YAML body" in legacy
        assert "reads the registered contract before implementing it" in selected
    else:
        assert "UNVERIFIED" in legacy
    assert "canonical" in legacy and ("do not claim" in legacy.lower() or "do not write" in legacy.lower())
    assert "invocation.md" in text


def test_selected_gate_recipe_matches_runtime_assignment_and_expected_digest_interface() -> None:
    text = (REPO_ROOT / ".agents/skills/build-tool-pipeline/references/gate-map.md").read_text(encoding="utf-8")
    selected = _section(text, "Selected artifact submission and registration")
    rows = {}
    for line in selected.splitlines():
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if len(cells) == 2 and cells[0] in SUBMISSION_FILES:
            rows[cells[0]] = cells[1]
    assert rows == {key: f"30_execution/sub/<audit-id>/{filename}" for key, filename in SUBMISSION_FILES.items()}
    start = next(line for line in selected.splitlines() if "pipeline_ops.py" in line and "role-boundary start" in line)
    finalize = next(line for line in selected.splitlines() if "pipeline_ops.py" in line and "finalize-semantic-return" in line)
    assert all(flag in start for flag in ("--artifact", "--input-ref", "--invocation-ref"))
    assert all(flag in finalize for flag in ("--baseline-sha256", "--source <exact-start-result-submission-path>", "--expected-source-sha256"))
    normalized = " ".join(selected.split())
    assert "A TOML edit or earlier agent does not prove reload" in normalized
    assert "actual registered brief, contract or report and original sources" in normalized
    assert "Historical replay may return is_current false; never reactivate old bytes" in normalized


def test_selected_realizer_submission_preserves_original_source_reading_and_legacy_body() -> None:
    text = (REPO_ROOT / ".agents/skills/intent-realization/SKILL.md").read_text(encoding="utf-8")
    invocation = " ".join(_subsection(text, "Invocation inputs and return ownership").split())
    assert 'control.semantic_role_boundary: "1.1"' in invocation
    assert "Legacy governed use returns the full body to Root" in invocation
    assert "only that exact file, with no siblings, probes, canonical writes or run-state changes" in invocation
    assert "read the original sources and actual registered inputs" in invocation
    assert all(field in invocation for field in ("artifact ID/version", "SHA-256", "invocation", "readiness", "unresolved decisions", "--expected-source-sha256"))
    assert "Do not return the body for transcription or claim activation" in invocation
    assert "including BLOCKED output" in invocation


def test_threshold_review_is_exact_process_evidence_and_cannot_authorize_itself() -> None:
    text = (REPO_ROOT / ".agents/skills/build-tool-pipeline/references/verification-adapter.md").read_text(encoding="utf-8")
    review = " ".join(_section(text, "Selected threshold process review").split())
    assert "--review-event <BB-ID>, mutually exclusive with --artifact" in review
    assert "40_verification/probes/<audit-id>/round-review.json" in review
    assert "parent is not an ephemeral/probe write grant" in review
    assert "no product-report submission, artifact version reservation or registration receipt" in review
    assert all(recommendation in review for recommendation in ("STOP", "REQUEST_USER_DECISION", "BOUNDED_CONTINUATION"))
    assert "positive finite integer additional_rounds" in review
    assert "Root finishes the boundary and retains PASS before presenting" in review
    assert "reviewer cannot implement corrections or approve its own recommendation" in review
    assert "silence, a Root paraphrase or the recommendation alone grants no rounds" in review
