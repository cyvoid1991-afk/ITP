#!/usr/bin/env python3
"""Check local delivery records or collect them for a future pipeline intake."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from pipeline_control.io_utils import InputError, atomic_write_json, resolve_within
from pipeline_control.local_delivery import collect_deliveries, validate_delivery


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repository-root', type=Path, required=True)
    commands = parser.add_subparsers(dest='command', required=True)
    check = commands.add_parser('check', help='Check integrity/evidence; never mutate or apply a package')
    check.add_argument('--record', required=True)
    check.add_argument('--check-source', action='store_true')
    check.add_argument('--target', type=Path, help='Read-only patch preflight against an existing installation')
    intake = commands.add_parser('intake', help='Collect and validate history-linked delivery records')
    intake.add_argument('--source', required=True)
    intake.add_argument('--output', required=True, help='New repository-relative retained receipt path')
    args = parser.parse_args(argv)
    try:
        root = args.repository_root.resolve(strict=True)
        if args.command == 'check':
            data = validate_delivery(root, resolve_within(root, args.record, must_exist=True),
                                     check_source=args.check_source, target=args.target)
        else:
            output = resolve_within(root, args.output)
            if output.exists():
                raise InputError('DELIVERY_RECEIPT_EXISTS: preserve earlier intake receipts; select a new path')
            data = collect_deliveries(root, resolve_within(root, args.source, must_exist=True))
            atomic_write_json(output, data)
        result, code = {'ok': True, 'data': data, 'diagnostics': []}, 0
    except (InputError, OSError, UnicodeError, ValueError, TypeError, KeyError) as exc:
        result, code = {'ok': False, 'data': {}, 'diagnostics': [{'code': 'LOCAL_DELIVERY', 'message': str(exc)}]}, 1
    print(json.dumps(result, ensure_ascii=True, indent=2))
    return code


if __name__ == '__main__':
    raise SystemExit(main())
