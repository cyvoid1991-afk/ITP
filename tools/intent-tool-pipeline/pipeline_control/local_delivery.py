"""Integrity and evidence checks for local deliveries; never grant release authority."""

from __future__ import annotations

import hashlib
import json
import re
import zipfile
from pathlib import Path
from typing import Any

from .delivery_target import preflight_target, validate_patch
from .io_utils import InputError, read_structured, resolve_within, sha256_file


DISPOSITION = "PRE_EXISTING_DELTA_NOT_VERIFIED_BASELINE"
METHOD_VERSION = "local-delivery/1.0"
HISTORY_NAMES = ("REVISION_HISTORY.md", "CHANGELOG.md", "README.md")
HISTORY_MARKER = re.compile(r"Local delivery record:\s*`([^`\r\n]+)`")


def safe_path(value: Any) -> str:
    if not isinstance(value, str) or not value or '\\' in value or any(char in value for char in ':*?"<>|') or any(ord(char) < 32 for char in value) or value.startswith('/'):
        raise InputError("DELIVERY_PATH: expected a canonical relative slash-separated path")
    parts = value.split('/')
    if any(part in {'', '.', '..'} or part.endswith((' ', '.')) for part in parts):
        raise InputError("DELIVERY_PATH: empty, traversal, or ambiguous path component")
    if any(re.fullmatch(r'(?i)(con|prn|aux|nul|com[1-9]|lpt[1-9])(?:\..*)?', part) for part in parts):
        raise InputError("DELIVERY_PATH: reserved Windows name")
    return value


def file_ref(root: Path, value: Any) -> Path:
    relative = safe_path(value)
    path = root / relative
    if any(p.is_symlink() for p in [path, *path.parents] if p != root and p.is_relative_to(root)):
        raise InputError("DELIVERY_PATH: symbolic links are unsupported")
    result = resolve_within(root, relative, must_exist=True)
    if not result.is_file():
        raise InputError("DELIVERY_PATH: expected a regular file")
    return result


def _digest(value: Any) -> str:
    if not isinstance(value, str) or re.fullmatch('[0-9a-f]{64}', value) is None:
        raise InputError("DELIVERY_HASH: expected lowercase SHA-256")
    return value


def snapshot_sha256(files: list[dict]) -> str:
    inventory = sorted(files, key=lambda item: item['path'])
    return hashlib.sha256(json.dumps(inventory, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()).hexdigest()


def _identities(items: Any, label: str) -> dict[str, dict]:
    if not isinstance(items, list) or not items:
        raise InputError(f"{label}: expected nonempty file inventory")
    result: dict[str, dict] = {}
    for item in items:
        if not isinstance(item, dict):
            raise InputError(f"{label}: expected an object")
        path = safe_path(item.get('path'))
        _digest(item.get('sha256'))
        if path.casefold() in {name.casefold() for name in result}:
            raise InputError(f"{label}: duplicate path")
        result[path] = item
    names = {name.casefold() for name in result}
    if any('/'.join(name.split('/')[:i]).casefold() in names for name in result for i in range(1, len(name.split('/')))):
        raise InputError(f"{label}: file and directory paths collide")
    return result


def _evidence(root: Path, reference: Any) -> dict:
    if not isinstance(reference, dict):
        raise InputError("DELIVERY_EVIDENCE: missing reference")
    path = file_ref(root, reference.get('path'))
    if sha256_file(path) != _digest(reference.get('sha256')):
        raise InputError("DELIVERY_EVIDENCE: content identity mismatch")
    data = read_structured(path)
    if not isinstance(data, dict):
        raise InputError("DELIVERY_EVIDENCE: expected structured check/judgment evidence")
    return data


def _checks(root: Path, data: dict, source_hash: str, archive_hash: str) -> None:
    required = {'source-focused', 'source-suite', 'package-load'}
    if data['package']['kind'] == 'patch':
        required |= {'patch-preflight', 'patch-rejection', 'patch-reapply', 'patch-recovery'}
    checks = data.get('checks')
    if not isinstance(checks, list):
        raise InputError("DELIVERY_CHECK: missing check records")
    ids: set[str] = set()
    for check in checks:
        if not isinstance(check, dict):
            raise InputError("DELIVERY_CHECK: expected an object")
        identifier = check.get('criterion_id')
        if not isinstance(identifier, str) or not identifier.strip() or identifier in ids:
            raise InputError("DELIVERY_CHECK: each criterion must have one unique identity")
        ids.add(identifier)
        status = check.get('status')
        if status not in {'PASS', 'FAIL', 'BLOCKED', 'NOT_RUN'}:
            raise InputError("DELIVERY_CHECK: invalid status")
        if status != 'PASS':
            raise InputError(f"DELIVERY_CHECK_{status}: mandatory criterion {identifier} cannot advance")
        if any(not isinstance(check.get(key), str) or not check[key].strip() for key in ('method', 'method_version')):
            raise InputError("DELIVERY_CHECK: method and method_version are required")
        expected_subject = source_hash if identifier.startswith('source-') else archive_hash
        if check.get('subject_sha256') != expected_subject:
            raise InputError("DELIVERY_CHECK: stale or mismatched subject identity")
        evidence = _evidence(root, check.get('evidence'))
        if evidence.get('status') != status or evidence.get('subject_sha256') != expected_subject or not evidence.get('observed'):
            raise InputError("DELIVERY_EVIDENCE: result, subject, and observed outcome must support the check")
    if not required <= ids:
        raise InputError('DELIVERY_CHECK: missing required criteria: ' + ', '.join(sorted(required - ids)))
    judgment = data.get('judgment')
    if not isinstance(judgment, dict) or not isinstance(judgment.get('criterion'), str) or not judgment['criterion'].strip():
        raise InputError("DELIVERY_JUDGMENT: semantic compatibility review is required")
    for key in ('assumptions', 'uncertainties', 'unresolved'):
        if not isinstance(judgment.get(key), list) or any(not isinstance(item, str) for item in judgment[key]):
            raise InputError("DELIVERY_JUDGMENT: explicit assumption, uncertainty and unresolved lists required")
    if judgment.get('subject_sha256') != archive_hash:
        raise InputError("DELIVERY_JUDGMENT: review must identify the delivered archive")
    if judgment.get('assessment') != 'ACCEPT' or judgment['unresolved']:
        raise InputError("DELIVERY_JUDGMENT: unresolved mandatory semantic conditions require review")
    evidence = _evidence(root, judgment.get('evidence'))
    if any(evidence.get(key) != judgment.get(key) for key in ('criterion', 'assessment', 'subject_sha256', 'assumptions', 'uncertainties', 'unresolved')):
        raise InputError("DELIVERY_JUDGMENT: evidence does not match recorded judgment")


def validate_delivery(repository_root: Path, record_path: Path, *, check_source: bool = False, target: Path | None = None) -> dict:
    root = repository_root.resolve(strict=True)
    record_path = resolve_within(root, record_path, must_exist=True)
    record_path = file_ref(root, record_path.relative_to(root).as_posix())
    data = read_structured(record_path)
    if not isinstance(data, dict) or data.get('schema_version') != '1.0' or data.get('artifact_type') != 'local-tool-delivery':
        raise InputError("DELIVERY_CONTRACT: expected local-tool-delivery 1.0")
    if data.get('disposition') != DISPOSITION:
        raise InputError("DELIVERY_DISPOSITION: local delivery must retain its non-baseline classification")
    for key in ('delivery_id', 'producer'):
        if not isinstance(data.get(key), str) or not data[key].strip():
            raise InputError(f"DELIVERY_CONTRACT: missing {key}")
    baseline = data.get('baseline')
    if baseline != 'unknown':
        keys = {'run_id', 'archive_sha256', 'product_contract_ref', 'product_contract_sha256', 'verification_report_ref', 'verification_report_sha256'}
        if not isinstance(baseline, dict) or not keys <= baseline.keys() or any(not isinstance(baseline[k], str) or not baseline[k].strip() for k in keys):
            raise InputError("DELIVERY_BASELINE: use unknown or a complete exact-evidence reference")
        for key in keys:
            if key.endswith('sha256'):
                _digest(baseline[key])
    source, package = data.get('source'), data.get('package')
    if not isinstance(source, dict) or not isinstance(package, dict):
        raise InputError("DELIVERY_CONTRACT: source and package are required")
    source_root = resolve_within(root, safe_path(source.get('root')), must_exist=True)
    if not source_root.is_dir():
        raise InputError("DELIVERY_SOURCE: authoritative root must be a directory")
    revisions = source.get('revision_ids')
    if not isinstance(revisions, list) or not revisions or any(not isinstance(v, str) or not v.strip() for v in revisions) or len(set(revisions)) != len(revisions):
        raise InputError("DELIVERY_REVISIONS: expected unique nonempty revision IDs")
    history = file_ref(root, source.get('history_path'))
    if history.parent != source_root or history.name not in HISTORY_NAMES:
        raise InputError("DELIVERY_HISTORY: use a discoverable source-root REVISION_HISTORY.md, CHANGELOG.md, or README.md")
    history_text = history.read_text(encoding='utf-8')
    relative_record = record_path.relative_to(root).as_posix()
    if relative_record not in HISTORY_MARKER.findall(history_text) or any(revision not in history_text for revision in revisions):
        raise InputError("DELIVERY_HISTORY: history must link this record and identify every included revision")
    source_files = _identities(source.get('files'), 'DELIVERY_SOURCE')
    if source.get('snapshot_sha256') != snapshot_sha256(list(source_files.values())):
        raise InputError("DELIVERY_SOURCE: snapshot identity does not match its file inventory")
    if check_source:
        for path, identity in source_files.items():
            if sha256_file(file_ref(source_root, path)) != identity['sha256']:
                raise InputError("DELIVERY_SOURCE: current authoritative source differs from the checked snapshot")
    if package.get('kind') not in {'patch', 'full'}:
        raise InputError("DELIVERY_KIND: expected patch or full")
    archive = file_ref(root, package.get('path'))
    archive_hash = _digest(package.get('sha256'))
    if archive == record_path or sha256_file(archive) != archive_hash:
        raise InputError("DELIVERY_ARCHIVE: archive identity mismatch")
    entries = _identities(package.get('entries'), 'DELIVERY_ARCHIVE')
    exported: set[str] = set()
    for entry in entries.values():
        if 'source_path' not in entry:
            raise InputError("DELIVERY_SOURCE: each member declares source_path or null packaging metadata")
        relative = entry['source_path']
        if relative is not None:
            safe_path(relative)
            if relative not in source_files or source_files[relative]['sha256'] != entry['sha256']:
                raise InputError("DELIVERY_SOURCE: package payload is not the identified source")
            if relative in exported:
                raise InputError("DELIVERY_SOURCE: duplicate exported source file")
            exported.add(relative)
    if not exported:
        raise InputError("DELIVERY_SOURCE: a tool package must export identified source")
    try:
        with zipfile.ZipFile(archive) as bundle:
            infos = bundle.infolist()
            if len(infos) != len(entries) or {info.filename for info in infos} != set(entries):
                raise InputError("DELIVERY_ARCHIVE: exact member inventory mismatch")
            for info in infos:
                safe_path(info.filename)
                if info.is_dir() or (info.external_attr >> 16) & 0o170000 == 0o120000 or info.flag_bits & 1:
                    raise InputError("DELIVERY_ARCHIVE: directories, symlinks and encrypted members unsupported")
                if hashlib.sha256(bundle.read(info)).hexdigest() != entries[info.filename]['sha256']:
                    raise InputError("DELIVERY_ARCHIVE: payload hash mismatch")
    except (zipfile.BadZipFile, RuntimeError, NotImplementedError) as exc:
        raise InputError(f"DELIVERY_ARCHIVE: unreadable ZIP: {exc}") from exc
    if package['kind'] == 'patch':
        validate_patch(data, entries, safe_path)
    elif target is not None:
        raise InputError("DELIVERY_TARGET: --target applies only to patch preflight")
    _checks(root, data, source['snapshot_sha256'], archive_hash)
    result = {'status': 'PASS', 'method_version': METHOD_VERSION, 'delivery_id': data['delivery_id'],
              'record_path': relative_record, 'record_sha256': sha256_file(record_path),
              'source_root': source['root'], 'revision_ids': revisions, 'archive_path': package['path'],
              'archive_sha256': archive_hash, 'disposition': DISPOSITION, 'eligible_baseline': False,
              'source_checked': check_source, 'checks': [{'criterion_id': c['criterion_id'], 'status': c['status']} for c in data['checks']]}
    if target is not None:
        result['target'] = preflight_target(data, entries, target)
    return result


def collect_deliveries(repository_root: Path, source_root: Path) -> dict:
    from .delivery_intake import collect_deliveries as collect
    return collect(repository_root, source_root)


def validate_intake_deliveries(project_root: Path, request: dict) -> dict | None:
    from .delivery_intake import validate_intake_deliveries as consume
    return consume(project_root, request)
