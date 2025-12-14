"""Search subcommands for brain CLI."""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent.parent


def cmd_search(args: argparse.Namespace) -> int:
    """Execute search command."""
    script = REPO_ROOT / "brain_graph" / "search" / "searcher.py"

    python_exe = (os.environ.get("BG_PYTHON") or "").strip() or sys.executable
    cmd = [python_exe, str(script), args.query]

    # Add mode-specific flags
    if args.mode == "fuzzy":
        cmd.append("--fuzzy-only")
    elif args.mode == "semantic":
        cmd.append("--semantic-only")
    # Default: no mode flag = hybrid mode

    if args.limit:
        cmd.extend(["--limit", str(args.limit)])

    # Always use JSON format for consistency
    cmd.append("--format=json")
    if not args.raw:
        cmd.append("--pretty")

    result = subprocess.run(cmd)
    return result.returncode


def setup_search_parser(subparsers) -> None:
    """Setup search subcommand parser."""
    search_parser = subparsers.add_parser(
        "search",
        help="Search the knowledge base",
        description="Semantic search with optional fuzzy/BM25 fallback and reranking",
    )
    
    search_parser.add_argument(
        "query",
        help="Search query",
    )
    
    search_parser.add_argument(
        "mode",
        nargs="?",
        choices=["fuzzy", "semantic"],
        help="Search mode (default: full pipeline with semantic + reranking)",
    )
    
    search_parser.add_argument(
        "-l", "--limit",
        type=int,
        help="Maximum number of results",
    )
    
    search_parser.add_argument(
        "--raw",
        action="store_true",
        help="Output raw JSON without pretty-printing",
    )

    search_parser.set_defaults(func=cmd_search)
