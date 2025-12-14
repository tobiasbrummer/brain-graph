#!/usr/bin/env python3
"""
Check for duplicate documents by source hash.

Usage:
    python check_duplicate.py input.md --db brain.duckdb

Exit codes:
    0 - No duplicate found
    1 - Duplicate found
    2 - Error (DB not found, etc.)
"""

import argparse
import sys
import time
from pathlib import Path
from typing import Any

import duckdb

from file_utils import get_source_hash
from cli_utils import emit_json, error_result, ms_since, ok_result


def check_duplicate(input_file: Path, db_path: str) -> dict[str, Any] | None:
    """
    Check if document with same hash exists in database.

    Args:
        input_file: Path to input file
        db_path: Path to DuckDB database

    Returns:
        Dict with duplicate info or None if no duplicate
    """
    # Calculate hash
    input_hash = get_source_hash(input_file)

    # Connect to DB (read-only)
    conn = duckdb.connect(db_path, read_only=True)
    try:
        # Query for matching hash
        result = conn.execute(
            """
            SELECT ulid, source_file, source_commit, created_at
            FROM meta
            WHERE source_hash = ?
        """,
            [input_hash],
        ).fetchone()
    finally:
        conn.close()

    if result:
        return {
            "ulid": result[0],
            "source_file": result[1],
            "source_commit": result[2],
            "created_at": result[3],
            "hash": input_hash,
        }

    return None


def main():
    start = time.perf_counter()
    parser = argparse.ArgumentParser(description="Check for duplicate documents")
    parser.add_argument("input", type=Path, help="Input file to check")
    parser.add_argument("--db", type=str, default=":memory:",
                       help="DuckDB database path (default: :memory:)")
    parser.add_argument("--quiet", action="store_true",
                       help="Suppress output, only use exit codes")
    parser.add_argument(
        "--format",
        choices=["json", "text"],
        default="json",
        help="Output format (default: json)",
    )
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output")
    parser.add_argument("--debug", action="store_true", help="Include traceback in JSON error output")
    args = parser.parse_args()

    try:
        if not args.input.exists():
            raise FileNotFoundError(f"File not found: {args.input}")

        duplicate = check_duplicate(args.input, args.db)

        if duplicate:
            if args.format == "json":
                emit_json(
                    ok_result(
                        "check_duplicate",
                        status="duplicate",
                        input=str(args.input),
                        db=args.db,
                        duplicate=duplicate,
                        duration_ms=ms_since(start),
                    ),
                    pretty=args.pretty,
                )
            else:
                if not args.quiet:
                    print("DUPLICATE DETECTED", file=sys.stderr)
                    print(f"  Input file: {args.input}", file=sys.stderr)
                    print(f"  Matches existing: {duplicate['source_file']}", file=sys.stderr)
                    print(f"  ULID: {duplicate['ulid']}", file=sys.stderr)
                    print(f"  Hash: {duplicate['hash']}", file=sys.stderr)
                    if duplicate.get("source_commit"):
                        print(f"  Commit: {duplicate['source_commit']}", file=sys.stderr)
                    print(f"  Created: {duplicate['created_at']}", file=sys.stderr)
            return 1

        if args.format == "json":
            emit_json(
                ok_result(
                    "check_duplicate",
                    input=str(args.input),
                    db=args.db,
                    duplicate=None,
                    duration_ms=ms_since(start),
                ),
                pretty=args.pretty,
            )
        else:
            if not args.quiet:
                print("No duplicate found", file=sys.stderr)
        return 0
    except Exception as e:
        if args.format == "json":
            emit_json(
                error_result("check_duplicate", e, include_traceback=args.debug, duration_ms=ms_since(start)),
                pretty=args.pretty,
            )
            return 2
        raise


if __name__ == "__main__":
    raise SystemExit(main())
