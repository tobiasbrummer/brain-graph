#!/usr/bin/env python3
"""Main CLI entry point with subcommands."""
from __future__ import annotations

import argparse
import sys
from typing import NoReturn


def main() -> int:
    """Main entry point for brain CLI."""
    parser = argparse.ArgumentParser(
        prog="brain",
        description="Brain Graph - Semantic knowledge base CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    subparsers.required = True
    
    # Search commands
    from brain_graph.cli.search_cli import setup_search_parser
    setup_search_parser(subparsers)
    
    # Pipeline commands
    from brain_graph.cli.pipeline_cli import setup_pipeline_parser
    setup_pipeline_parser(subparsers)
    
    # Database commands
    from brain_graph.cli.db_cli import setup_db_parser
    setup_db_parser(subparsers)
    
    # Agent commands
    from brain_graph.cli.agent_cli import setup_agent_parser
    setup_agent_parser(subparsers)

    # Daemon commands
    from brain_graph.cli.daemon_cli import setup_daemon_parser
    setup_daemon_parser(subparsers)

    args = parser.parse_args()
    
    # Dispatch to subcommand handler
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
