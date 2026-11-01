"""Discover append-only delivery links and check their consumption at new intake."""

from __future__ import annotations

from pathlib import Path

from .io_utils import InputError, read_structured, resolve_within, sha256_file
from .local_delivery import HISTORY_MARKER, HISTORY_NAMES, METHOD_VERSION, file_ref, safe_path, validate_delivery


def collect_deliveries(repository_root: Path, source_root: Path) -> dict:
    root = repository_root.resolve(strict=True)
    source_root = resolve_within(root, source_root, must_exist=True)
    if not source_root.is_dir():
        raise InputError('DELIVERY_INTAKE: source must be a directory')
    history = []
    links: set[str] = set()
    for name in HISTORY_NAMES:
        path = source_root / name
        if not path.is_file():
            continue
        path = file_ref(root, path.relative_to(root).as_posix())
        text = path.read_text(encoding='utf-8')
        found = HISTORY_MARKER.findall(text)
        # A malformed new marker must not silently turn into legacy/no-history.
        if text.count('Local delivery record:') != len(found):
            raise InputError('DELIVERY_HISTORY: malformed Local delivery record link')
        if found:
            history.append({'path': path.relative_to(root).as_posix(), 'sha256': sha256_file(path)})
            links.update(found)
    records = []
    for relative in sorted(links):
        record = validate_delivery(root, file_ref(root, relative))
        if record['source_root'] != source_root.relative_to(root).as_posix():
            raise InputError('DELIVERY_INTAKE: history links a record for a different authoritative source')
        records.append(record)
    identifiers = [record['delivery_id'] for record in records]
    if len(set(identifiers)) != len(identifiers):
        raise InputError('DELIVERY_INTAKE: distinct records must not reuse a delivery ID')
    return {'schema_version': '1.0', 'artifact_type': 'minor-delivery-intake',
            'method_version': METHOD_VERSION, 'status': 'PASS',
            'source_roots': [source_root.relative_to(root).as_posix()], 'history': history, 'records': records}


def _repository_root(project_root: Path) -> Path:
    if project_root.name == 'intent-tool-pipeline' and project_root.parent.name == 'tools':
        return project_root.parents[1]
    return project_root


def validate_intake_deliveries(project_root: Path, request: dict) -> dict | None:
    """Require hash-bound snapshots for discovered records, without changing request bytes."""
    project_root = project_root.resolve()
    root = _repository_root(project_root)
    target = request.get('target', {}).get('repository_path')
    source_roots: set[Path] = set()
    if isinstance(target, str):
        candidate = resolve_within(project_root, target)
        if candidate.is_dir():
            source_roots.add(candidate)
    contexts: dict[str, Path] = {}
    declared_records: set[str] = set()
    for context in request.get('source_context', []):
        if not isinstance(context, dict) or not isinstance(context.get('content_sha256'), str):
            continue
        raw_path = context.get('path')
        if not isinstance(raw_path, str):
            continue
        try:
            path = resolve_within(project_root, raw_path, must_exist=True)
        except InputError:
            # This extension must not impose new availability rules on unrelated
            # legacy context. Required delivery snapshots are checked below.
            continue
        if not path.is_file():
            continue
        actual_hash = sha256_file(path)
        if actual_hash == context['content_sha256']:
            contexts[actual_hash] = path
        if path.suffix.lower() not in {'.json', '.yaml', '.yml'}:
            continue
        try:
            data = read_structured(path)
        except InputError:
            continue
        if isinstance(data, dict) and data.get('artifact_type') == 'local-tool-delivery':
            if actual_hash != context['content_sha256']:
                raise InputError('DELIVERY_INTAKE: hash-bound delivery snapshot differs from its bytes')
            declared_records.add(context['content_sha256'])
            declared = data.get('source', {}).get('root') if isinstance(data.get('source'), dict) else None
            source_roots.add(resolve_within(root, safe_path(declared), must_exist=True))
    receipts = [collect_deliveries(root, source) for source in sorted(source_roots)]
    records = [record for receipt in receipts for record in receipt['records']]
    if not declared_records <= {record['record_sha256'] for record in records}:
        raise InputError('DELIVERY_INTAKE: supplied delivery snapshot is not linked by authoritative history')
    if not records:
        return None
    for record in records:
        if record['record_sha256'] not in contexts:
            raise InputError('DELIVERY_INTAKE: every discovered local record needs an exact hash-bound source_context snapshot: ' + record['record_path'])
    return {'schema_version': '1.0', 'artifact_type': 'minor-delivery-intake',
            'method_version': METHOD_VERSION, 'status': 'PASS',
            'source_roots': sorted({source for receipt in receipts for source in receipt['source_roots']}),
            'history': [history for receipt in receipts for history in receipt['history']],
            'records': records}
