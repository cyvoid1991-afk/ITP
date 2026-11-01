"""Build the curated ITP public repository seed without changing source files."""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import subprocess
import zipfile
from pathlib import Path

TOOL = "tools/intent-tool-pipeline"
PROFILE = TOOL + "/packaging/public"
VERSION = "0.3.0-rc.1"
PROVENANCE = "PUBLIC_PROVENANCE.json"


def json_bytes(value):
    return (json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def digest(data):
    return hashlib.sha256(data).hexdigest()


def repository_root():
    return Path(__file__).resolve().parents[4]


def legacy_builder(root):
    spec = importlib.util.spec_from_file_location("itp_seed_core", root / TOOL / "packaging/itp/build.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def source_identity(root):
    """Record Git context without exposing local paths or omitted file names."""
    def git(*args):
        result = subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True)
        return result.stdout.strip() if result.returncode == 0 else None
    try:
        head = git("rev-parse", "HEAD")
        dirty = git("status", "--porcelain", "--untracked-files=normal")
    except OSError:
        head, dirty = None, None
    return {"repository": "Nexus_AI", "basis": "explicit inventoried working-tree bytes, including local changes",
            "git_head": head, "working_tree_dirty": None if dirty is None else bool(dirty),
            "clean_commit_claim": False}


def build(root: Path, output: Path):
    root = root.resolve()
    core = legacy_builder(root)
    profile = root / PROFILE
    names = json.loads((profile / "include-list.json").read_text(encoding="utf-8"))
    if not isinstance(names, list) or not all(isinstance(n, str) for n in names):
        raise ValueError("public inventory must contain path strings")
    generated = core.GENERATED_FILES | {PROVENANCE}
    if len({n.casefold() for n in names}) != len(names) or {n.casefold() for n in names} & {n.casefold() for n in generated}:
        raise ValueError("duplicate/case-colliding paths or generated public member")
    overlays = json.loads((profile / "overlays.json").read_text(encoding="utf-8"))
    if not isinstance(overlays, dict) or set(overlays) - set(names):
        raise ValueError("overlay targets must be inventoried")
    # safe_file validates every physical input, including overlays, before use.
    contents, records = {}, []
    for name in sorted(names):
        source = overlays.get(name, name)
        data = core.safe_file(root, source).read_bytes()
        try:
            original = core.safe_file(root, name).read_bytes()
        except ValueError as exc:
            # The shared validator checks lexical safety, private boundaries,
            # budgets and reparse aliases before checking physical existence.
            # An overlay may add a destination, never bypass those checks.
            target = root / name
            if (name not in overlays or str(exc) != f"missing or escaped package file: {name}"
                    or target.exists() or not target.resolve().is_relative_to(root)):
                raise
            original = None
        contents[name] = data
        records.append({"path": name, "source_path": source,
                        "source_sha256": digest(data), "original_path": name if original is not None else None,
                        "original_sha256": digest(original) if original is not None else None,
                        "packaged_sha256": digest(data), "transformation": "overlay" if source != name else "unchanged"})
    # Adapt only the two Nexus-layout assertions, retaining all runtime tests.
    test_name = TOOL + "/tests/test_distribution.py"
    before = b'        assert "research/README.md" in archive.namelist()\n        assert "experiments/README.md" in archive.namelist()'
    after = b'        assert not any(n.startswith(("research/", "experiments/", "discussion/", "develop/")) for n in archive.namelist())\n        assert "tools/intent-tool-pipeline/packaging/public/build.py" in archive.namelist()'
    if contents[test_name].count(before) == 1:
        contents[test_name] = contents[test_name].replace(before, after)
    elif contents[test_name].count(after) != 1:
        raise ValueError("public distribution test adaptation no longer matches source")
    for record in records:
        if record["path"] == test_name:
            record.update(packaged_sha256=digest(contents[test_name]), transformation="public-layout-assertions")
    # Inventories and exact exception policy are explicit profile assets.
    for name, data, rule in [
        (TOOL + "/packaging/itp/include-list.json", json_bytes(names), "public-inventory"),
        (TOOL + "/packaging/itp/document-policy.json", contents[PROFILE + "/document-policy.json"], "public-document-policy"),
    ]:
        contents[name] = data
        next(r for r in records if r["path"] == name).update(packaged_sha256=digest(data), transformation=rule)
    references = core.document_references(root, names, contents)
    previous = root / PROVENANCE
    if previous.exists():
        provenance_data = core.safe_file(root, PROVENANCE).read_bytes()
        provenance = json.loads(provenance_data)
        expected = {r["path"]: r["packaged_sha256"] for r in provenance["files"]}
        if provenance.get("format") != "itp-public-provenance-1" or provenance.get("version") != VERSION or expected != {n: digest(b) for n, b in contents.items()}:
            raise ValueError("public provenance does not match current seed; build a new reviewed source snapshot")
    else:
        provenance = {"format": "itp-public-provenance-1", "version": VERSION,
                      "public_repository": "https://github.com/cyvoid1991-afk/ITP",
                      "source": source_identity(root),
                      "version_mapping": {"source_component_version": (root / TOOL / "VERSION").read_text(encoding="utf-8").strip(),
                                          "public_bundle_version": VERSION, "control_revision_default": "1.2",
                                          "meaning": "Public candidate identity; not a clean upstream release or control protocol version."},
                      "files": records}
        provenance_data = json_bytes(provenance)
    contents[PROVENANCE] = provenance_data
    contents["DOCUMENT_REFERENCES.json"] = json_bytes(references)
    contents["DISTRIBUTION_NOTICE.md"] = (
        "# ITP public seed boundary\n\n"
        "This is the curated 0.3.0-rc.1 public candidate, assembled from inventoried working-tree bytes.\n\n"
        f"**{references['source_only_link_occurrences']} local Markdown link occurrences intentionally point to source-only material absent from this bundle.**\n\n"
        f"**{references['template_context_link_occurrences']} additional local Markdown link occurrences are setup-template references.**\n\n"
        "Exact targets, reasons and referring-file hashes are in DOCUMENT_REFERENCES.json. Source-only records are historical identities, not shipped or freshly verified evidence.\n\n"
        "Read [installation](README.md), [source identity](SOURCE_IDENTITY.md), and the [publication policy](tools/intent-tool-pipeline/docs/distribution.md).\n"
    ).encode("utf-8")
    contents = dict(sorted(contents.items()))
    contents["SOURCE_MANIFEST.json"] = json_bytes({"name": "intent-tool-pipeline", "version": VERSION, "format": "repo-seed-1",
        "files": [{"path": n, "size": len(b), "sha256": digest(b)} for n, b in contents.items()]})
    output = output.resolve()
    if len(str(output.parent)) >= 180 or len(output.name) > 64:
        raise ValueError("output exceeds Windows path budget")
    protected = set(names) | set(overlays.values()) | generated
    if str(output).casefold() in {str(root / n).casefold() for n in protected}:
        raise ValueError("output would overwrite a packaged source")
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "w") as archive:
        for name, data in contents.items():
            info = zipfile.ZipInfo(name, date_time=(2026, 11, 1, 0, 0, 0))
            info.create_system, info.compress_type, info.external_attr = 3, zipfile.ZIP_DEFLATED, 0o100644 << 16
            archive.writestr(info, data)
    with zipfile.ZipFile(output) as archive:
        if archive.testzip() is not None or any(archive.read(n) != b for n, b in contents.items()):
            raise ValueError("archive verification failed")
    return {"path": str(output), "version": VERSION, "files": len(contents), "sha256": digest(output.read_bytes()),
            "source_only_link_occurrences": references["source_only_link_occurrences"],
            "template_context_link_occurrences": references["template_context_link_occurrences"]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, default=repository_root())
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(build(args.project_root, args.output), indent=2))


if __name__ == "__main__":
    main()
