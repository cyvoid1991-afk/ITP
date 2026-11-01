"""Build a reproducible repository ZIP from an explicit repository include list."""
from __future__ import annotations
import argparse
import hashlib
import json
import posixpath
import re
import stat
import zipfile
from pathlib import Path, PurePosixPath
from urllib.parse import unquote, urlsplit

TOOL_PATH = Path("tools/intent-tool-pipeline")
GENERATED_FILES = {"SOURCE_MANIFEST.json", "DOCUMENT_REFERENCES.json", "DISTRIBUTION_NOTICE.md"}


def document_links(text: str):
    """Yield rendered inline Markdown targets, excluding fenced code examples."""
    fence = None
    for line in text.splitlines():
        marker = re.match(r"^\s{0,3}(`{3,}|~{3,})", line)
        if marker:
            token = marker.group(1)
            if fence is None:
                fence = token
            elif token[0] == fence[0] and len(token) >= len(fence):
                fence = None
            continue
        if fence is None:
            yield from re.findall(r"\]\(([^)\n]+)\)", line)


def document_references(root: Path, names: list[str], contents: dict[str, bytes] | None = None) -> dict:
    """Require closure or an exact, visible source-only publication decision."""
    policy_path = tool_root(root) / "packaging/itp/document-policy.json"
    if policy_path.exists():
        policy_name = policy_path.relative_to(root).as_posix()
        if policy_name not in names:
            raise ValueError("document publication policy must be inventoried")
        policy_bytes = contents[policy_name] if contents is not None else safe_file(root, policy_name).read_bytes()
        policy = json.loads(policy_bytes)
    else:
        policy = {"format": "itp-document-policy-1", "unbundled_references": []}
    if not isinstance(policy, dict) or set(policy) != {"format", "unbundled_references"} or policy.get("format") != "itp-document-policy-1" or not isinstance(policy.get("unbundled_references"), list):
        raise ValueError("invalid document publication policy")
    declared = {}
    members = set(names)
    for entry in policy["unbundled_references"]:
        if not isinstance(entry, dict) or set(entry) != {"source", "target", "reason", "kind"} or not all(isinstance(v, str) and v.strip() for v in entry.values()) or entry["kind"] not in {"source-only", "template-context"}:
            raise ValueError("invalid source-only document reference")
        source, target = entry["source"], entry["target"]
        if source not in members or not source.endswith(".md") or target.startswith("/") or "\\" in target or ":" in target or posixpath.normpath(target) != target or target in {".", ".."} or target.startswith("../") or "*" in target:
            raise ValueError(f"invalid source-only document reference: {source}: {target}")
        key = (source, target)
        if key in declared:
            raise ValueError(f"duplicate source-only document reference: {source}: {target}")
        declared[key] = entry
    bundled, source_only, used = 0, [], set()
    failures = []
    for name in sorted(members):
        if not name.endswith(".md"):
            continue
        data = contents[name] if contents is not None else safe_file(root, name).read_bytes()
        for reference in document_links(data.decode("utf-8")):
            reference = reference.strip()
            if reference.startswith("<") and ">" in reference:
                reference = reference[1:reference.index(">")]
            else:
                reference = reference.split(maxsplit=1)[0]
            parsed = urlsplit(reference)
            if parsed.scheme or parsed.netloc or not parsed.path:
                continue
            target = posixpath.normpath(posixpath.join(posixpath.dirname(name), unquote(parsed.path)))
            key = (name, target)
            present = target in members or any(n.startswith(target.rstrip("/") + "/") for n in members)
            if present:
                bundled += 1
            elif key in declared:
                used.add(key)
                source_only.append({**declared[key], "reference": reference, "source_sha256": hashlib.sha256(data).hexdigest()})
            else:
                failures.append(f"undeclared document reference: {name}: {reference} -> {target}")
    failures.extend(f"stale source-only document reference: {s}: {t}" for s, t in sorted(set(declared) - used))
    if failures:
        raise ValueError("\n".join(failures))
    return {"format": "itp-document-references-1", "bundled_link_occurrences": bundled,
            "source_only_link_occurrences": sum(e["kind"] == "source-only" for e in source_only),
            "template_context_link_occurrences": sum(e["kind"] == "template-context" for e in source_only),
            "unbundled_references": source_only}

def repository_root() -> Path:
    """Infer an embedded repository, retaining support for an original flat seed."""
    tool = Path(__file__).resolve().parents[2]
    return tool.parents[1] if tool.name == "intent-tool-pipeline" and tool.parent.name == "tools" else tool

def tool_root(root: Path) -> Path:
    embedded = root / TOOL_PATH
    return embedded if (embedded / "VERSION").is_file() else root

def safe_file(root: Path, name: str) -> Path:
    parts = PurePosixPath(name).parts
    if not parts or PurePosixPath(name).as_posix() != name or "\\" in name or ":" in name or name.startswith("/") or any(p.casefold() in {".", "..", ".git", ".venv", "__pycache__", ".pytest_cache", ".tmp"} for p in parts):
        raise ValueError(f"unsafe package path: {name}")
    if any(len(p) > 32 for p in parts[:-1]) or len(parts[-1]) > 64:
        raise ValueError(f"package member exceeds name budget: {name}")
    relative = name.casefold().removeprefix(TOOL_PATH.as_posix() + "/")
    private_roots = ("codex_workspace/", "intent_deliver/", "demo_workspace/", "deliverables/", "workspace/", "test_workspace/t/")
    scaffolds = {prefix + leaf for prefix in private_roots for leaf in ("README.md", "AGENTS.md", ".gitkeep")}
    scaffolds.update({"workspace/build_runs/README.md", "workspace/framework_development/README.md"})
    scaffolds = {name.casefold() for name in scaffolds}
    if relative.startswith(private_roots) and relative not in scaffolds:
        raise ValueError(f"product or generated data cannot enter the framework bundle: {name}")
    if name.lower().endswith(".zip"):
        raise ValueError(f"release archives cannot enter the framework bundle: {name}")
    if any(p.casefold() == ".env" or p.casefold().startswith(".env.") and p.casefold() != ".env.example" for p in parts):
        raise ValueError(f"environment secrets cannot enter the framework bundle: {name}")
    path = root.joinpath(*parts)
    if any(p.is_symlink() or bool(getattr(p.lstat(), "st_file_attributes", 0) & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)) for p in (path, *path.parents) if p.exists() or p.is_symlink()):
        raise ValueError(f"symlink or reparse point not allowed: {name}")
    if not path.resolve().is_relative_to(root.resolve()) or not path.is_file():
        raise ValueError(f"missing or escaped package file: {name}")
    return path

def build(root: Path, output: Path) -> dict:
    root = root.resolve()
    tool = tool_root(root)
    version = (tool / "VERSION").read_text(encoding="utf-8").strip()
    if not re.fullmatch(r"\d+\.\d+\.\d+(?:-[a-z0-9.-]+)?", version):
        raise ValueError("invalid VERSION")
    names = json.loads((tool / "packaging/itp/include-list.json").read_text(encoding="utf-8"))
    if not isinstance(names, list) or not all(isinstance(n, str) for n in names):
        raise ValueError("include list must contain path strings")
    if len({n.casefold() for n in names}) != len(names) or {n.casefold() for n in names} & {n.casefold() for n in GENERATED_FILES}:
        raise ValueError("duplicate/case-colliding paths or self-referential manifest")
    contents = {name: safe_file(root, name).read_bytes() for name in sorted(names)}
    references = document_references(root, names, contents)
    contents["DOCUMENT_REFERENCES.json"] = (json.dumps(references, indent=2) + "\n").encode()
    notice = "# Framework distribution boundary\n\nThis is a selected framework seed, not a complete repository archive.\n"
    notice += f"\n**{references['source_only_link_occurrences']} local Markdown link occurrences intentionally point to source-only material absent from this bundle.**\n"
    notice += "See DOCUMENT_REFERENCES.json for every exact source, target, reason and packaged source digest. Source-only links refer to the original repository; historical targets may already be unavailable there. They are not bundled evidence.\n"
    notice += f"\n**{references['template_context_link_occurrences']} additional local Markdown link occurrences are setup-template references.** Their text resolves only after installation at the documented destination, not from the packaged template location.\n"
    doc = (tool.relative_to(root) / "docs/distribution.md").as_posix()
    if doc in contents:
        notice += f"\nRead the [publication policy]({doc}) before relying on historical evidence.\n"
    contents["DISTRIBUTION_NOTICE.md"] = notice.encode()
    manifest = {"name": "intent-tool-pipeline", "version": version, "format": "repo-seed-1", "files": [
        {"path": name, "size": len(data), "sha256": hashlib.sha256(data).hexdigest()}
        for name, data in contents.items()
    ]}
    contents["SOURCE_MANIFEST.json"] = (json.dumps(manifest, indent=2) + "\n").encode()
    output = output.resolve()
    if len(str(output.parent)) >= 180 or len(output.name) > 64:
        raise ValueError("output exceeds Windows path budget")
    if str(output).casefold() in {str(root / n).casefold() for n in contents}:
        raise ValueError("output would overwrite a packaged source")
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "w") as archive:
        for name, data in contents.items():
            info = zipfile.ZipInfo(name, date_time=(2026, 10, 1, 0, 0, 0))
            info.create_system = 3
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, data)
    with zipfile.ZipFile(output) as archive:
        if archive.testzip() is not None or any(archive.read(n) != b for n, b in contents.items()):
            raise ValueError("archive verification failed")
    return {"path": str(output), "files": len(contents), "sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
            "bundled_link_occurrences": references["bundled_link_occurrences"],
            "source_only_link_occurrences": references["source_only_link_occurrences"],
            "template_context_link_occurrences": references["template_context_link_occurrences"]}

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, default=repository_root(), help="repository root (or original flat seed root)")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    tool = tool_root(args.project_root)
    version = (tool / "VERSION").read_text(encoding="utf-8").strip()
    output = args.output or tool / "dist" / f"intent-tool-pipeline-{version}.zip"
    print(json.dumps(build(args.project_root, output), indent=2))

if __name__ == "__main__":
    main()
