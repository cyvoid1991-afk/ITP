from __future__ import annotations

import re
import tomllib
from pathlib import Path

import pytest

from pipeline_control.validation import PROBLEM_FRAME_HEADINGS, markdown_metadata, validate_markdown_headings


ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = ROOT.parents[1]
ADAPTER_ROOT = REPO_ROOT / '.agents' / 'skills' / 'build-tool-pipeline' / 'references'
CUSTOM_AGENT_FILES = (
    "intent_realizer.toml",
    "collaborative_intent_shaping_agent.toml",
    "product_contract_agent.toml",
    "independent_verifier.toml",
)


def _load_toml(path: Path) -> dict:
    with path.open("rb") as handle:
        return tomllib.load(handle)


def _normalized(text: str) -> str:
    return " ".join(text.split())


def test_root_is_enabled_and_semantic_roles_are_disabled() -> None:
    root_config = _load_toml(REPO_ROOT / ".codex" / "config.toml")
    assert root_config["agents"] == {
        "enabled": True,
        "max_concurrent_threads_per_session": 3,
        "default_subagent_model": "gpt-6.1-sol",
        "default_subagent_reasoning_effort": "high",
    }

    for filename in CUSTOM_AGENT_FILES:
        agent_config = _load_toml(REPO_ROOT / ".codex" / "agents" / filename)
        assert agent_config["agents"]["enabled"] is False
        assert "Delegation: prohibited" in agent_config["developer_instructions"]
        assert "Do not spawn" in agent_config["developer_instructions"]


def test_pipeline_semantic_agents_preserve_configured_models_and_high_reasoning() -> None:
    for filename in CUSTOM_AGENT_FILES:
        agent_config = _load_toml(REPO_ROOT / ".codex" / "agents" / filename)
        expected = (
            "gpt-6-astra"
            if filename in {"intent_realizer.toml", "collaborative_intent_shaping_agent.toml"}
            else "gpt-6.1-sol"
        )
        assert agent_config["model"] == expected
        assert agent_config["model_reasoning_effort"] == "high"


def test_root_controlled_delegation_policy_is_explicit() -> None:
    repository_rules = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
    pipeline_skill = (
        REPO_ROOT / ".agents" / "skills" / "build-tool-pipeline" / "SKILL.md"
    ).read_text(encoding="utf-8")

    assert "Root Codex owns top-level delegation" in repository_rules
    assert "custom semantic roles" in repository_rules
    assert "Built-in workers and" in repository_rules
    assert "Keep top-level delegation Root-owned" in pipeline_skill
    assert "built-in workers and explorers retain" in pipeline_skill


def test_problem_framer_output_contract_matches_validator_heading_order() -> None:
    instructions = (ADAPTER_ROOT / 'framing-adapter.md').read_text(encoding='utf-8')
    markers = [f"`## {heading}`" for heading in PROBLEM_FRAME_HEADINGS]
    positions = [instructions.find(marker) for marker in markers]

    assert all(position >= 0 for position in positions), {
        heading: marker
        for heading, marker, position in zip(PROBLEM_FRAME_HEADINGS, markers, positions)
        if position < 0
    }
    assert positions == sorted(positions)
    assert "Use every level-2 heading exactly once" in instructions
    for metadata_line in (
        "- Schema version: `1.0`",
        "- Artifact ID: `problem-frame`",
        "- Version: `<positive integer assigned by the parent>`",
        "- Lifecycle status: `ACTIVE`",
        "- Owner role: `problem_framer`",
        "- Run ID: `<run ID named by the parent>`",
        "- Canonical path: `<exact path named by the parent>`",
    ):
        assert metadata_line in instructions
    assert "Do not bold the metadata labels" in instructions


def test_realizer_skill_owns_compatible_artifact_format() -> None:
    config = _load_toml(REPO_ROOT / ".codex" / "agents" / "intent_realizer.toml")
    instructions = config["developer_instructions"]
    assert config["sandbox_mode"] == "read-only"
    skill_ref = ".agents/skills/intent-realization/SKILL.md"
    assert skill_ref not in instructions
    skill = (REPO_ROOT / skill_ref).read_text(encoding="utf-8")

    # The published format must still produce the adapter's exact heading set.
    headings = re.findall(r"^\d+\. `(#{1,2} [^`]+)`$", skill, flags=re.MULTILINE)
    assert headings == ["# Problem Frame", *(f"## {h}" for h in PROBLEM_FRAME_HEADINGS)]
    assert not validate_markdown_headings("\n".join(headings), PROBLEM_FRAME_HEADINGS, "problem_frame.md")
    metadata = markdown_metadata(skill.replace("<positive integer assigned by Root>", "3"))
    assert metadata == {
        "artifact_id": "problem-frame",
        "version": 3,
        "lifecycle_status": "ACTIVE",
        "semantic_owner": "intent_realizer",
    }

    # Repository-specific input/output contracts must not drift back into the role.
    for runtime_marker in ("build_request.yaml", "problem_frame.md", "FRESH_REQUIRED", "- Artifact ID:"):
        assert runtime_marker in skill
        assert runtime_marker not in instructions
    assert "headings/metadata in the role runtime" not in skill


def test_problem_framer_revision_contract_is_complete_and_fresh_safe() -> None:
    for raw_contract in [(ADAPTER_ROOT / 'framing-adapter.md').read_text(encoding='utf-8')]:
        contract = _normalized(raw_contract)
        assert "exact resolved verified baseline" in contract
        assert "immutable context" in contract
        assert "complete current frame" in contract
        assert "explicit non-changes" in contract
        assert "migration impact" in contract
        assert "regression" in contract
        assert "FRESH_REQUIRED" in contract
        assert "broad, incompatible, or materially ambiguous" in contract


def test_product_contract_adapter_preserves_exact_revision_rules() -> None:
    for raw_contract in [(ADAPTER_ROOT / 'contract-adapter.md').read_text(encoding='utf-8')]:
        contract = _normalized(raw_contract)
        assert "complete current contract" in contract
        assert "revision_control" in contract
        assert "baseline_bundle_sha256" in contract
        assert "full requirement" in contract
        assert "full linked acceptance" in contract
        assert "shared acceptance" in contract
        assert "impact_map" in contract
        assert "ALL_APPLICABLE_REQUIREMENTS" in contract
        assert "FRESH_REQUIRED" in contract


def test_independent_verifier_scopes_legacy_body_and_selected_file_transport() -> None:
    instructions = (ADAPTER_ROOT / 'verification-adapter.md').read_text(encoding='utf-8')

    for required_input in (
        "product_contract.yaml",
        "release manifest",
        "package inspection",
        "release archive",
        "verifier-harness attempt",
        "cleanup evidence",
    ):
        assert required_input in instructions
    legacy = _normalized(instructions.split("### Legacy full-body return\n", 1)[1].split("\n## ", 1)[0])
    selected = _normalized(instructions.split("### Selected compact return\n", 1)[1].split("\n### ", 1)[0])
    assert "returns the complete report body even for NOT_READY or UNVERIFIED" in legacy
    assert "Do not write the canonical report" in legacy
    assert "complete the assigned report even for NOT_READY or UNVERIFIED" in selected
    assert "actual path, artifact ID/version, content SHA-256, invocation" in selected
    assert "Root registers those bytes without changing the verdict" in selected
    assert "Root Codex owns registration, canonical activation and state transitions" in instructions
    assert "do not create, edit, replace, or directly write" in instructions
    assert "40_verification/probes/<audit-id>/" in instructions
    assert "operational evidence, not semantic judgment" in instructions
    assert "without patching the delivery to pass" in instructions


@pytest.mark.parametrize('filename', CUSTOM_AGENT_FILES)
def test_reusable_role_has_no_fixed_pipeline_dependency(filename: str) -> None:
    """Static policy guard; behavioral evaluations are recorded separately."""
    config = _load_toml(REPO_ROOT / '.codex' / 'agents' / filename)
    instruction = config['developer_instructions']
    for pipeline_marker in (
        'Native Runtime Procedure', 'Required workflow skill', 'Workflow A',
        'Workflow B', 'build_request.yaml', 'problem_frame.md',
        'product_contract.yaml', 'verification_report.md', 'FRESH_REQUIRED',
        '40_verification/', 'workspace/build_runs/', 'baseline_bundle_sha256',
    ):
        assert pipeline_marker not in instruction
    assert 'No particular workflow is mandatory solely because this role was selected.' in instruction
    assert 'do not silently switch to ordinary mode' in instruction
    assert 'parent owns canonical persistence' in instruction
    assert config['name'] == Path(filename).stem
    assert config['sandbox_mode'] == ('workspace-write' if filename == 'independent_verifier.toml' else 'read-only')


@pytest.mark.parametrize('skill,adapter', [
    ('author-product-contract', 'contract-adapter.md'),
    ('independent-verification', 'verification-adapter.md'),
    ('problem-framing', 'framing-adapter.md'),
])
def test_generic_skill_routes_to_existing_adapter_without_owning_its_schema(skill: str, adapter: str) -> None:
    path = REPO_ROOT / '.agents' / 'skills' / skill / 'SKILL.md'
    body = path.read_text(encoding='utf-8')
    # History is append-only and can describe the old location of a rule.
    active = body.split('## Revision History')[0]
    targets = [path.parent / link for link in re.findall(r'\]\(([^)#]+)(?:#[^)]*)?\)', active)]
    assert (ADAPTER_ROOT / adapter).resolve() in [target.resolve() for target in targets]
    assert all(target.is_file() for target in targets)
    for marker in ('baseline_bundle_sha256', '40_verification/probes/', 'FRESH_REQUIRED', 'revision_control'):
        assert marker not in active


def test_governed_invocation_routes_are_loadable_and_explicit() -> None:
    invocation = ADAPTER_ROOT / 'invocation.md'
    body = invocation.read_text(encoding='utf-8')
    targets = [invocation.parent / link for link in re.findall(r'\]\(([^)#]+)(?:#[^)]*)?\)', body)]
    assert all(target.is_file() for target in targets)
    for adapter in ('contract-adapter.md', 'verification-adapter.md', 'framing-adapter.md'):
        assert adapter in body
        assert 'invocation.md' in (ADAPTER_ROOT / adapter).read_text(encoding='utf-8')
    pipeline = (ADAPTER_ROOT.parent / 'SKILL.md').read_text(encoding='utf-8')
    gate = (ADAPTER_ROOT / 'gate-map.md').read_text(encoding='utf-8')
    realizer = (ADAPTER_ROOT.parent.parent / 'intent-realization' / 'SKILL.md').read_text(encoding='utf-8')
    assert 'references/invocation.md' in pipeline
    assert 'invocation.md' in gate and 'invocation.md' in realizer
    assert 'references/contract-adapter.md' in pipeline
    assert 'references/verification-adapter.md' in pipeline
    assert 'framing-adapter.md' in gate


def test_verifier_generic_boundary_does_not_grant_ambient_write_access() -> None:
    instruction = _load_toml(REPO_ROOT / '.codex/agents/independent_verifier.toml')['developer_instructions']
    normalized = _normalized(instruction)
    for rule in (
        'Without such a directory, perform read-only review',
        'Do not modify the verification target',
        'existing evidence, canonical report, orchestration state, or governing instructions',
        'symlink, junction or hard-link aliases',
        'as a boundary failure',
    ):
        assert rule in normalized
