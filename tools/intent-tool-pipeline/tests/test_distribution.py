"""Repository distribution checks; no agent calls or historical run mutation."""
from __future__ import annotations

import importlib.util
import hashlib
import json
import os
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = ROOT.parents[1] if ROOT.parent.name == "tools" else ROOT


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


BUILDER = module("repo_bundle_builder", ROOT / "packaging/itp/build.py")
VERIFY_PATH = ROOT / "verify_bundle.py"
if not VERIFY_PATH.exists():
    VERIFY_PATH = ROOT / "packaging/itp/verify_bundle.py"
VERIFIER = module("repo_bundle_verifier", VERIFY_PATH)


def fixture_root(tmp_path):
    root = tmp_path / "repo"
    (root / "packaging/itp").mkdir(parents=True)
    (root / "VERSION").write_text("0.2.0\n", encoding="utf-8")
    (root / "AGENTS.md").write_text("Example instructions\n", encoding="utf-8")
    names = ["VERSION", "AGENTS.md", "packaging/itp/include-list.json"]
    (root / names[-1]).write_text(json.dumps(names), encoding="utf-8")
    return root


def embedded_root(tmp_path):
    root = tmp_path / "repo"
    tool = root / "tools/intent-tool-pipeline"
    (tool / "packaging/itp").mkdir(parents=True)
    files = {
        "AGENTS.md": "Repository routing\n",
        ".agents/skills/example/SKILL.md": "Example skill\n",
        ".codex/config.toml": "# Local agent configuration\n",
        "pytest.ini": "[pytest]\npythonpath = tools/intent-tool-pipeline\n",
        "tools/intent-tool-pipeline/VERSION": "0.2.0\n",
        "tools/intent-tool-pipeline/README.md": "[Root](../../AGENTS.md)\n",
        "tools/intent-tool-pipeline/SOURCE_MANIFEST.json": '{"original": true}\n',
        "tools/intent-tool-pipeline/packaging/itp/build.py": (ROOT / "packaging/itp/build.py").read_text(encoding="utf-8"),
        "tools/intent-tool-pipeline/verify_bundle.py": VERIFY_PATH.read_text(encoding="utf-8"),
    }
    inventory = "tools/intent-tool-pipeline/packaging/itp/include-list.json"
    files[inventory] = json.dumps(sorted([*files, inventory]))
    for name, text in files.items():
        target = root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
    return root


def test_embedded_bundle_defaults_reproducibility_and_provenance(tmp_path):
    root = embedded_root(tmp_path)
    tool = root / "tools/intent-tool-pipeline"
    original_manifest = (tool / "SOURCE_MANIFEST.json").read_bytes()
    # Files outside the explicit inventory must never appear in the archive.
    for name in ("original.zip", ".venv/pyvenv.cfg", "tools/intent-tool-pipeline/codex_workspace/product/secret.py", "tools/intent-tool-pipeline/workspace/build_runs/private/state.json"):
        excluded = root / name
        excluded.parent.mkdir(parents=True, exist_ok=True)
        excluded.write_text("private")
    result = subprocess.run([sys.executable, str(tool / "packaging/itp/build.py")], cwd=tmp_path, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    first = Path(json.loads(result.stdout)["path"])
    assert first.parent == tool / "dist"
    second = tmp_path / "second.zip"
    BUILDER.build(root, second)
    assert first.read_bytes() == second.read_bytes()
    extracted = tmp_path / "out"
    with zipfile.ZipFile(first) as archive:
        assert "AGENTS.md" in archive.namelist()
        assert ".agents/skills/example/SKILL.md" in archive.namelist()
        assert ".codex/config.toml" in archive.namelist()
        assert "pytest.ini" in archive.namelist()
        assert "tools/intent-tool-pipeline/README.md" in archive.namelist()
        assert "original.zip" not in archive.namelist()
        assert not any(".venv/" in n or "/private/" in n or "/product/" in n for n in archive.namelist())
        assert archive.read("tools/intent-tool-pipeline/SOURCE_MANIFEST.json") == original_manifest
        assert json.loads(archive.read("SOURCE_MANIFEST.json"))["format"] == "repo-seed-1"
        archive.extractall(extracted)
    assert (tool / "SOURCE_MANIFEST.json").read_bytes() == original_manifest
    with pytest.raises(ValueError, match="overwrite"):
        BUILDER.build(root, tool / "SOURCE_MANIFEST.json")
    assert VERIFIER.verify(extracted) == []
    result = subprocess.run([sys.executable, str(extracted / "tools/intent-tool-pipeline/verify_bundle.py")], cwd=tmp_path, capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
    (extracted / "tools/intent-tool-pipeline/README.md").write_text("changed")
    assert "changed: tools/intent-tool-pipeline/README.md" in VERIFIER.verify(extracted)


def test_flat_reproducible_archive_and_integrity_failures(tmp_path):
    root = fixture_root(tmp_path)
    first, second = tmp_path / "one.zip", tmp_path / "two.zip"
    BUILDER.build(root, first)
    BUILDER.build(root, second)
    assert first.read_bytes() == second.read_bytes()
    extracted = tmp_path / "out"
    with zipfile.ZipFile(first) as archive:
        assert "AGENTS.md" in archive.namelist()
        assert len(archive.namelist()) == 6
        assert json.loads(archive.read("DOCUMENT_REFERENCES.json"))["source_only_link_occurrences"] == 0
        assert "0 local Markdown link occurrences" in archive.read("DISTRIBUTION_NOTICE.md").decode()
        archive.extractall(extracted)
    assert VERIFIER.verify(extracted) == []
    result = subprocess.run([sys.executable, str(VERIFY_PATH), "--root", str(extracted)], cwd=tmp_path, capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
    (extracted / ".git").mkdir()
    (extracted / ".git/config").write_text("local Git metadata")
    assert VERIFIER.verify(extracted) == []
    (extracted / "AGENTS.md").write_text("changed")
    assert "changed: AGENTS.md" in VERIFIER.verify(extracted)
    (extracted / "VERSION").unlink()
    assert "missing or invalid: VERSION" in VERIFIER.verify(extracted)
    (extracted / "secret.txt").write_text("unexpected")
    assert "unexpected: secret.txt" in VERIFIER.verify(extracted)


@pytest.mark.parametrize("name", ["", ".", "../outside.txt", "/absolute.txt", "C:/outside.txt", ".git/config", ".venv/pyvenv.cfg", ".VENV/pyvenv.cfg", "./AGENTS.md", "codex_workspace/tool/code.py", "codex_workspace/tool/README.md", "workspace/build_runs/run/state.json", "workspace/framework_development/private.json", ".env", ".ENV", "original.zip", "tools/intent-tool-pipeline/codex_workspace/tool/code.py", "tools/intent-tool-pipeline/Codex_workspace/tool/code.py", "tools/intent-tool-pipeline/workspace/build_runs/run/state.json", ".pytest_cache/data.json"])
def test_builder_rejects_unsafe_members(tmp_path, name):
    root = fixture_root(tmp_path)
    (root / "packaging/itp/include-list.json").write_text(json.dumps([name]))
    with pytest.raises(ValueError):
        BUILDER.build(root, tmp_path / "bad.zip")


def test_duplicate_case_paths_rejected(tmp_path):
    root = fixture_root(tmp_path)
    (root / "packaging/itp/include-list.json").write_text(json.dumps(["AGENTS.md", "agents.md"]))
    with pytest.raises(ValueError, match="duplicate"):
        BUILDER.build(root, tmp_path / "bad.zip")


def test_builder_rejects_manifest_self_reference_and_output_collision(tmp_path):
    root = fixture_root(tmp_path)
    with pytest.raises(ValueError, match="overwrite"):
        BUILDER.build(root, root / "AGENTS.md")
    (root / "packaging/itp/include-list.json").write_text(json.dumps(["source_manifest.json"]))
    with pytest.raises(ValueError, match="self-referential"):
        BUILDER.build(root, tmp_path / "bad.zip")


@pytest.mark.parametrize("name", ["", ".", "../outside.txt", "C:/outside.txt", "./AGENTS.md", "AGENTS.md/../other.txt", "SOURCE_MANIFEST.json", ".GIT/config"])
def test_verifier_rejects_unsafe_manifest_members(tmp_path, name):
    root = fixture_root(tmp_path)
    manifest = {"format": "repo-seed-1", "files": [{"path": name, "size": 0, "sha256": "0" * 64}]}
    (root / "SOURCE_MANIFEST.json").write_text(json.dumps(manifest))
    assert VERIFIER.verify(root) == [f"unsafe manifest path: {name}"]


def test_builder_and_verifier_reject_symlink_escape(tmp_path):
    root = fixture_root(tmp_path)
    outside = tmp_path / "outside.txt"
    outside.write_text("outside")
    linked = root / "linked.txt"
    try:
        linked.symlink_to(outside)
    except OSError:
        pytest.skip("symlink creation unavailable")
    (root / "packaging/itp/include-list.json").write_text(json.dumps(["linked.txt"]))
    with pytest.raises(ValueError, match="symlink"):
        BUILDER.build(root, tmp_path / "bad.zip")
    manifest = {"format": "repo-seed-1", "files": [{"path": "linked.txt", "size": 7, "sha256": "0" * 64}]}
    (root / "SOURCE_MANIFEST.json").write_text(json.dumps(manifest))
    assert "missing or invalid: linked.txt" in VERIFIER.verify(root)


def write_document_policy(root, entries):
    names_path = root / "packaging/itp/include-list.json"
    names = json.loads(names_path.read_text(encoding="utf-8"))
    policy_name = "packaging/itp/document-policy.json"
    if policy_name not in names:
        names.append(policy_name)
        names_path.write_text(json.dumps(names), encoding="utf-8")
    (root / policy_name).write_text(json.dumps({"format": "itp-document-policy-1", "unbundled_references": entries}), encoding="utf-8")
    return names


def test_source_only_links_are_exact_disclosed_and_do_not_publish_evidence(tmp_path):
    root = fixture_root(tmp_path)
    data = b"[Source evidence](workspace/private/log.json#attempt)\n[Again](workspace/private/log.json)\n"
    (root / "AGENTS.md").write_bytes(data)
    # Intentionally absent targets also permit rebuilding an extracted seed.
    entry = {"source": "AGENTS.md", "target": "workspace/private/log.json", "reason": "Private diagnostic evidence remains in the source repository.", "kind": "source-only"}
    names = write_document_policy(root, [entry])
    output = tmp_path / "seed.zip"
    result = BUILDER.build(root, output)
    assert result["source_only_link_occurrences"] == 2
    with zipfile.ZipFile(output) as archive:
        assert entry["target"] not in archive.namelist()
        assert archive.read("AGENTS.md") == data
        report = json.loads(archive.read("DOCUMENT_REFERENCES.json"))
        assert report["bundled_link_occurrences"] == 0
        assert report["source_only_link_occurrences"] == 2
        assert {e["reference"] for e in report["unbundled_references"]} == {"workspace/private/log.json#attempt", "workspace/private/log.json"}
        for e in report["unbundled_references"]:
            assert {k: e[k] for k in entry} == entry
            assert e["source_sha256"] == hashlib.sha256(data).hexdigest()
        assert "2 local Markdown link occurrences" in archive.read("DISTRIBUTION_NOTICE.md").decode()
        extracted = tmp_path / "out"
        archive.extractall(extracted)
    assert VERIFIER.verify(extracted) == []
    assert BUILDER.document_references(extracted, names) == report
    rebuilt = tmp_path / "rebuilt.zip"
    BUILDER.build(extracted, rebuilt)
    assert output.read_bytes() == rebuilt.read_bytes()


def test_undeclared_link_fails_even_if_private_target_exists(tmp_path):
    root = fixture_root(tmp_path)
    private = root / "workspace/private/log.json"
    private.parent.mkdir(parents=True)
    private.write_text("{}")
    (root / "AGENTS.md").write_text("[Private](workspace/private/log.json)")
    with pytest.raises(ValueError, match="undeclared document reference"):
        BUILDER.build(root, tmp_path / "seed.zip")


@pytest.mark.parametrize("change", ["removed", "bundled", "unknown-source", "unknown-target", "duplicate", "wildcard", "unlisted-policy"])
def test_stale_or_invalid_document_policy_rejected(tmp_path, change):
    root = fixture_root(tmp_path)
    (root / "AGENTS.md").write_text("[Elsewhere](elsewhere.md)")
    entry = {"source": "AGENTS.md", "target": "elsewhere.md", "reason": "Outside this seed.", "kind": "source-only"}
    entries = [entry]
    if change == "unknown-source":
        entry["source"] = "unknown.md"
    elif change == "unknown-target":
        entry["target"] = "different.md"
    elif change == "duplicate":
        entries.append(dict(entry))
    elif change == "wildcard":
        entry["target"] = "*.md"
    names = write_document_policy(root, entries)
    if change == "removed":
        (root / "AGENTS.md").write_text("Link removed")
    elif change == "bundled":
        (root / "elsewhere.md").write_text("Now included")
        names.append("elsewhere.md")
    elif change == "unlisted-policy":
        names.remove("packaging/itp/document-policy.json")
    (root / "packaging/itp/include-list.json").write_text(json.dumps(names))
    with pytest.raises(ValueError, match="document reference|publication policy"):
        BUILDER.build(root, tmp_path / "bad.zip")


def test_markdown_targets_use_inventory_and_ignore_fenced_examples(tmp_path):
    root = fixture_root(tmp_path)
    (root / "AGENTS.md").write_text('[Inventory](packaging/)\n[Fragment](#heading)\n[URL](https://example.test/)\n[Encoded](%56ERSION#v)\n[Title](<VERSION> "version")\n```markdown\n[Template](missing.md)\n```\n~~~\n[Example](another-missing.md)\n~~~\n')
    report = BUILDER.document_references(root, json.loads((root / "packaging/itp/include-list.json").read_text()))
    assert report["bundled_link_occurrences"] == 3
    assert report["source_only_link_occurrences"] == 0


def test_template_context_is_separate_and_captured_source_bytes_bind_report(tmp_path, monkeypatch):
    root = fixture_root(tmp_path)
    data = b"[Setup destination](target/entry.md)\n"
    (root / "AGENTS.md").write_bytes(data)
    names = write_document_policy(root, [{"source": "AGENTS.md", "target": "target/entry.md", "reason": "Template installed at repository root.", "kind": "template-context"}])
    original = BUILDER.document_references

    def after_capture(root, names, contents):
        (root / "AGENTS.md").write_text("Changed after capture")
        return original(root, names, contents)

    monkeypatch.setattr(BUILDER, "document_references", after_capture)
    output = tmp_path / "template.zip"
    result = BUILDER.build(root, output)
    assert result["source_only_link_occurrences"] == 0
    assert result["template_context_link_occurrences"] == 1
    with zipfile.ZipFile(output) as archive:
        assert archive.read("AGENTS.md") == data
        report = json.loads(archive.read("DOCUMENT_REFERENCES.json"))
        assert report["unbundled_references"][0]["source_sha256"] == hashlib.sha256(data).hexdigest()
        assert "1 additional local Markdown link occurrences are setup-template references" in archive.read("DISTRIBUTION_NOTICE.md").decode()


@pytest.mark.skipif(os.name != "nt", reason="Windows junction semantics")
@pytest.mark.parametrize("outside", [False, True])
def test_builder_rejects_windows_junction_alias(tmp_path, outside):
    root = fixture_root(tmp_path)
    target = (tmp_path if outside else root) / "target"
    target.mkdir()
    (target / "data.txt").write_text("outside")
    alias = root / "alias"
    quote = lambda p: "'" + str(p).replace("'", "''") + "'"
    creation = subprocess.run(["powershell.exe", "-NoProfile", "-Command", f"New-Item -ItemType Junction -Path {quote(alias)} -Target {quote(target)} | Out-Null"], capture_output=True, text=True)
    assert creation.returncode == 0, creation.stdout + creation.stderr
    try:
        (root / "packaging/itp/include-list.json").write_text(json.dumps(["alias/data.txt"]))
        with pytest.raises(ValueError, match="reparse point"):
            BUILDER.build(root, tmp_path / "bad.zip")
        if outside:
            manifest = {"format": "repo-seed-1", "files": [{"path": "alias/data.txt", "size": 7, "sha256": "0" * 64}]}
            (root / "SOURCE_MANIFEST.json").write_text(json.dumps(manifest))
            assert "missing or invalid: alias/data.txt" in VERIFIER.verify(root)
    finally:
        alias.rmdir()


def test_distribution_document_links():
    """Only assembled repositories have this inventory; source tests stay usable."""
    inventory = ROOT / "packaging/itp/include-list.json"
    if not inventory.exists():
        pytest.skip("assembled repository check")
    report = BUILDER.document_references(REPO_ROOT, json.loads(inventory.read_text(encoding="utf-8")))
    assert report["bundled_link_occurrences"] > 0
    assert report["source_only_link_occurrences"] > 0


def test_repository_inventory_build_and_extract(tmp_path):
    """The actual allowlist must produce a self-consistent distributable seed."""
    original_manifest = (ROOT / "SOURCE_MANIFEST.json").read_bytes()
    output = tmp_path / "seed.zip"
    BUILDER.build(REPO_ROOT, output)
    extracted = tmp_path / "seed"
    with zipfile.ZipFile(output) as archive:
        archive.extractall(extracted)
        assert not any(n.startswith(("research/", "experiments/", "discussion/", "develop/")) for n in archive.namelist())
        assert "tools/intent-tool-pipeline/packaging/public/build.py" in archive.namelist()
    assert VERIFIER.verify(extracted) == []
    names = json.loads((ROOT / "packaging/itp/include-list.json").read_text(encoding="utf-8"))
    report = BUILDER.document_references(extracted, names)
    assert json.loads((extracted / "DOCUMENT_REFERENCES.json").read_text()) == report
    assert report["source_only_link_occurrences"] > 0
    for entry in report["unbundled_references"]:
        assert not (extracted / entry["target"]).exists()
    assert "source-only material absent from this bundle" in (extracted / "DISTRIBUTION_NOTICE.md").read_text()
    assert (extracted / "tools/intent-tool-pipeline/SOURCE_MANIFEST.json").read_bytes() == original_manifest
    assert (ROOT / "SOURCE_MANIFEST.json").read_bytes() == original_manifest
