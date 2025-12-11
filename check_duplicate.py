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
from pathlib import Path

import duckdb

from file_utils import get_source_hash


def check_duplicate(input_file: Path, db_path: str = ":memory:") -> dict | None:
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

    try:
        # Connect to DB (read-only)
        conn = duckdb.connect(db_path, read_only=True)

        # Query for matching hash
        result = conn.execute("""
            SELECT ulid, source_file, source_commit, created_at
            FROM meta
            WHERE source_hash = ?
        """, [input_hash]).fetchone()

        conn.close()

        if result:
            return {
                'ulid': result[0],
                'source_file': result[1],
                'source_commit': result[2],
                'created_at': result[3],
                'hash': input_hash
            }

        return None

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return None


def main():
    parser = argparse.ArgumentParser(description="Check for duplicate documents")
    parser.add_argument("input", type=Path, help="Input file to check")
    parser.add_argument("--db", type=str, default=":memory:",
                       help="DuckDB database path (default: :memory:)")
    parser.add_argument("--quiet", action="store_true",
                       help="Suppress output, only use exit codes")
    args = parser.parse_args()

    if not args.input.exists():
        print(f"Error: File not found: {args.input}", file=sys.stderr)
        sys.exit(2)

    # Check for duplicate
    duplicate = check_duplicate(args.input, args.db)

    if duplicate:
        if not args.quiet:
            print(f"⚠️  DUPLICATE DETECTED", file=sys.stderr)
            print(f"   Input file: {args.input}", file=sys.stderr)
            print(f"   Matches existing: {duplicate['source_file']}", file=sys.stderr)
            print(f"   ULID: {duplicate['ulid']}", file=sys.stderr)
            print(f"   Hash: {duplicate['hash']}", file=sys.stderr)
            if duplicate['source_commit']:
                print(f"   Commit: {duplicate['source_commit']}", file=sys.stderr)
            print(f"   Created: {duplicate['created_at']}", file=sys.stderr)
        sys.exit(1)
    else:
        if not args.quiet:
            print(f"✓ No duplicate found", file=sys.stderr)
        sys.exit(0)


if __name__ == "__main__":
    main()
