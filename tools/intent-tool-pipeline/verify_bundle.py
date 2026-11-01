"""Check a freshly extracted repository before installation or local edits."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath

def repository_root() -> Path:
    tool = Path(__file__).resolve().parent
    return tool.parents[1] if tool.name == "intent-tool-pipeline" and tool.parent.name == "tools" else tool

def verify(root: Path) -> list[str]:
    root = root.resolve()
    failures = []
    try:
        manifest_path = root / "SOURCE_MANIFEST.json"
        if manifest_path.is_symlink():
            return ["invalid manifest: symlink not allowed"]
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if not isinstance(manifest, dict) or manifest.get("format") != "repo-seed-1":
            return ["unsupported manifest format"]
        expected = {}
        for entry in manifest["files"]:
            name = entry["path"]
            if not isinstance(name, str):
                return [f"unsafe manifest path: {name}"]
            parts = PurePosixPath(name).parts
            if not parts or PurePosixPath(name).as_posix() != name or "\\" in name or ":" in name or name.startswith("/") or any(p.casefold() in {"..", ".git"} for p in parts) or name.casefold() == "source_manifest.json":
                return [f"unsafe manifest path: {name}"]
            if name.casefold() in {n.casefold() for n in expected}:
                return [f"duplicate manifest path: {name}"]
            expected[name] = entry
        for name, entry in expected.items():
            path = root / name
            linked = any(p.is_symlink() for p in (path, *path.parents))
            if not path.resolve().is_relative_to(root) or linked or not path.is_file():
                failures.append(f"missing or invalid: {name}")
                continue
            data = path.read_bytes()
            if len(data) != entry["size"] or hashlib.sha256(data).hexdigest() != entry["sha256"]:
                failures.append(f"changed: {name}")
        actual = {p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file() and ".git" not in p.relative_to(root).parts}
        failures.extend(f"unexpected: {n}" for n in sorted(actual - set(expected) - {"SOURCE_MANIFEST.json"}))
    except (OSError, ValueError, KeyError, TypeError) as exc:
        failures.append(f"invalid manifest: {exc}")
    return failures

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=repository_root(), help="freshly extracted repository root; use an explicit path for an original flat seed")
    args = parser.parse_args()
    failures = verify(args.root)
    print("\n".join(failures) if failures else "PASS: all bundle files match; no unexpected files")
    return 1 if failures else 0

if __name__ == "__main__":
    raise SystemExit(main())
