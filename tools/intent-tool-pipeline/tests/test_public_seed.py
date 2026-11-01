"""Public-profile boundaries, exact source mappings and fresh rebuild checks."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import zipfile
from pathlib import Path

import pytest

TOOL = Path(__file__).resolve().parents[1]
REPO = TOOL.parents[1]


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


BUILDER = load_module("public_seed_builder", TOOL / "packaging/public/build.py")
VERIFIER = load_module("public_seed_verifier", TOOL / "verify_bundle.py")


def test_public_seed_fresh_integrity_boundary_mapping_and_rebuild(tmp_path):
    first, second = tmp_path / "first.zip", tmp_path / "second.zip"
    BUILDER.build(REPO, first)
    BUILDER.build(REPO, second)
    assert first.read_bytes() == second.read_bytes()
    extracted = tmp_path / "seed"
    with zipfile.ZipFile(first) as archive:
        names = archive.namelist()
        assert not any(n.startswith(("research/", "experiments/", "discussion/", "develop/", ".git/", ".tmp/", ".venv/")) for n in names)
        assert not any(n.endswith(".zip") or "checkpoint" in n or "__pycache__" in n or "/public-backup/" in n for n in names)
        assert not any("/build_runs/" in n and not n.endswith("/README.md") for n in names)
        assert archive.read("tools/intent-tool-pipeline/VERSION") == b"0.3.0-rc.1\n"
        assert archive.read("tools/intent-tool-pipeline/SOURCE_MANIFEST.json") == (TOOL / "SOURCE_MANIFEST.json").read_bytes()
        archive.extractall(extracted)
    # Verify before any extracted Python module can create an unexpected cache.
    assert VERIFIER.verify(extracted) == []
    provenance = json.loads((extracted / "PUBLIC_PROVENANCE.json").read_text())
    assert provenance["source"]["basis"].startswith("explicit inventoried working-tree")
    assert provenance["version_mapping"]["control_revision_default"] == "1.2"
    for record in provenance["files"]:
        data = (extracted / record["path"]).read_bytes()
        assert hashlib.sha256(data).hexdigest() == record["packaged_sha256"]
        assert not Path(record["source_path"]).is_absolute()
        if record["transformation"] == "unchanged":
            assert record["source_sha256"] == record["packaged_sha256"]
            assert data == (REPO / record["path"]).read_bytes()
    # All operational role/procedure bodies retain their source bytes.
    for name in names:
        if name.startswith((".codex/agents/", ".agents/skills/", "tools/intent-tool-pipeline/pipeline_control/")):
            assert (extracted / name).read_bytes() == (REPO / name).read_bytes()
    core = BUILDER.legacy_builder(REPO)
    inventory = json.loads((extracted / "tools/intent-tool-pipeline/packaging/itp/include-list.json").read_text())
    references = core.document_references(extracted, inventory)
    assert references == json.loads((extracted / "DOCUMENT_REFERENCES.json").read_text())
    assert references["source_only_link_occurrences"] > 0
    for entry in references["unbundled_references"]:
        assert not (extracted / entry["target"]).exists()
    rebuilt = tmp_path / "rebuilt.zip"
    BUILDER.build(extracted, rebuilt)
    assert first.read_bytes() == rebuilt.read_bytes()
    # A modified seed cannot silently acquire the old snapshot's source identity.
    (extracted / "tools/intent-tool-pipeline/pipeline_ops.py").write_text("changed\n")
    with pytest.raises(ValueError, match="provenance does not match"):
        BUILDER.build(extracted, tmp_path / "changed.zip")


def test_public_installation_instructions_match_supported_entry_points():
    readme = (TOOL / "packaging/public/overlays/readme.txt").read_text(encoding="utf-8")
    for text in ("Python 3.11", "verify_bundle.py", "requirements-dev.txt", "pipeline_ops.py --help",
                 "initialize_run.py --help", "Use $intent-tool-pipeline", "--control-revision 1.0",
                 "no automatic existing-run migration", "packaging/public/build.py"):
        assert text in readme
    for relative in ("pipeline_ops.py", "verify_bundle.py", "requirements-dev.txt", "docs/contracts/agent-rollout.md"):
        assert (TOOL / relative).is_file()


def test_public_policy_has_no_root_navigation_or_omitted_source_exemptions():
    policy = json.loads((TOOL / "packaging/public/document-policy.json").read_text())
    assert policy["format"] == "itp-document-policy-1"
    assert all(e["source"] not in {"README.md", "CHANGELOG.md", "research/README.md", "experiments/README.md"}
               for e in policy["unbundled_references"])
    assert all("*" not in e["target"] for e in policy["unbundled_references"])


@pytest.mark.parametrize("name", ["../escape.txt", "tools/intent-tool-pipeline/workspace/build_runs/private.json", "C:/outside.txt", ".env"])
def test_absent_overlay_destinations_still_pass_shared_safety_checks(tmp_path, name):
    root = tmp_path / "repo"
    profile = root / "tools/intent-tool-pipeline/packaging/public"
    profile.mkdir(parents=True)
    legacy = root / "tools/intent-tool-pipeline/packaging/itp/build.py"
    legacy.parent.mkdir()
    legacy.write_bytes((TOOL / "packaging/itp/build.py").read_bytes())
    (root / "asset.txt").write_text("overlay\n")
    (profile / "include-list.json").write_text(json.dumps([name]))
    (profile / "overlays.json").write_text(json.dumps({name: "asset.txt"}))
    with pytest.raises(ValueError, match="unsafe|generated data|secrets"):
        BUILDER.build(root, tmp_path / "bad.zip")
