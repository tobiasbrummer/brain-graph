"""Agent subcommands for brain CLI."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent.parent


def cmd_agent_docs(args: argparse.Namespace) -> int:
    """Get documentation for a specific tool."""
    script = REPO_ROOT / "brain_graph" / "cli" / "doc_extractor.py"

    python_exe = (os.environ.get("BG_PYTHON") or "").strip() or sys.executable
    cmd = [python_exe, str(script), args.tool]

    if args.format:
        cmd.extend(["--format", args.format])

    result = subprocess.run(cmd)
    return result.returncode


def cmd_agent_reflex(args: argparse.Namespace) -> int:
    """Run the reflex engine manually."""
    from brain_graph.agents.reflex import ReflexEngine

    try:
        engine = ReflexEngine(REPO_ROOT)
        engine.run()
        return 0
    except Exception as e:
        print(f"Reflex error: {e}", file=sys.stderr)
        return 1


def setup_agent_parser(subparsers) -> None:
    """Setup agent subcommand parser."""
    agent_parser = subparsers.add_parser(
        "agent",
        help="Agent-facing commands",
        description="Commands designed for LLM agent consumption",
    )

    agent_subparsers = agent_parser.add_subparsers(
        dest="agent_command", help="Agent commands"
    )
    agent_subparsers.required = True

    # docs subcommand
    docs_parser = agent_subparsers.add_parser(
        "docs",
        help="Extract documentation for a tool",
    )
    docs_parser.add_argument(
        "tool",
        help="Tool name (e.g., 'embedding', 'chunker', 'searcher')",
    )
    docs_parser.add_argument(
        "--format",
        choices=["text", "json", "markdown"],
        default="text",
        help="Output format",
    )
    docs_parser.set_defaults(func=cmd_agent_docs)

    # reflex subcommand
    reflex_parser = agent_subparsers.add_parser(
        "reflex",
        help="Run the reflex engine (tool execution)",
    )
    reflex_parser.set_defaults(func=cmd_agent_reflex)
