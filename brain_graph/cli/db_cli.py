"""Database subcommands for brain CLI."""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent.parent


def cmd_db_build(args: argparse.Namespace) -> int:
    """Build DuckDB database from processed markdown files."""
    script = REPO_ROOT / "brain_graph" / "db" / "db_builder.py"
    
    cmd = [sys.executable, str(script)]
    
    if args.args:
        cmd.extend(args.args)
    
    result = subprocess.run(cmd)
    return result.returncode


def cmd_db_test(args: argparse.Namespace) -> int:
    """Test database integrity and queries."""
    script = REPO_ROOT / "brain_graph" / "db" / "test_db.py"
    
    cmd = [sys.executable, str(script)]
    
    if args.args:
        cmd.extend(args.args)
    
    result = subprocess.run(cmd)
    return result.returncode


def setup_db_parser(subparsers) -> None:
    """Setup database subcommand parser."""
    db_parser = subparsers.add_parser(
        "db",
        help="Database management commands",
        description="Build and manage the DuckDB knowledge base",
    )
    
    db_subparsers = db_parser.add_subparsers(dest="db_command", help="Database commands")
    db_subparsers.required = True
    
    # build subcommand
    build_parser = db_subparsers.add_parser(
        "build",
        help="Build database from processed markdown files",
    )
    build_parser.add_argument(
        "args",
        nargs=argparse.REMAINDER,
        help="Additional arguments",
    )
    build_parser.set_defaults(func=cmd_db_build)
    
    # test subcommand
    test_parser = db_subparsers.add_parser(
        "test",
        help="Test database integrity",
    )
    test_parser.add_argument(
        "args",
        nargs=argparse.REMAINDER,
        help="Additional arguments",
    )
    test_parser.set_defaults(func=cmd_db_test)
