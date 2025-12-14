"""Daemon subcommands for brain CLI."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

import requests


REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_PORT = 8765


def cmd_daemon_start(args: argparse.Namespace) -> int:
    """Start the search daemon."""
    script = REPO_ROOT / "brain_graph" / "search" / "daemon.py"

    cmd = [sys.executable, str(script)]

    if args.host:
        cmd.extend(["--host", args.host])
    if args.port:
        cmd.extend(["--port", str(args.port)])
    if args.db:
        cmd.extend(["--db", args.db])
    if args.config:
        cmd.extend(["--config", args.config])

    if args.background:
        # Run in background
        print(f"Starting daemon in background on port {args.port or DEFAULT_PORT}...")
        subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        # Wait a bit and check if it's alive
        time.sleep(2)
        try:
            response = requests.get(
                f"http://{args.host or '127.0.0.1'}:{args.port or DEFAULT_PORT}/health",
                timeout=2,
            )
            if response.ok:
                print("Daemon started successfully")
                return 0
            else:
                print("Daemon may have failed to start", file=sys.stderr)
                return 1
        except requests.RequestException:
            print("Daemon may have failed to start", file=sys.stderr)
            return 1
    else:
        # Run in foreground
        result = subprocess.run(cmd)
        return result.returncode


def cmd_daemon_stop(args: argparse.Namespace) -> int:
    """Stop the search daemon."""
    # Find and kill daemon process
    try:
        result = subprocess.run(
            ["pkill", "-f", "brain_graph/search/daemon.py"],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            print("Daemon stopped")
            return 0
        else:
            print("No daemon process found", file=sys.stderr)
            return 1
    except FileNotFoundError:
        print("Error: pkill command not found", file=sys.stderr)
        return 1


def cmd_daemon_status(args: argparse.Namespace) -> int:
    """Check daemon status."""
    try:
        response = requests.get(
            f"http://{args.host or '127.0.0.1'}:{args.port or DEFAULT_PORT}/health",
            timeout=2,
        )
        if response.ok:
            data = response.json()
            print(f"Daemon status: {data.get('status')}")
            print(f"Ready: {data.get('ready')}")
            return 0
        else:
            print("Daemon not responding", file=sys.stderr)
            return 1
    except requests.RequestException as e:
        print(f"Daemon not reachable: {e}", file=sys.stderr)
        return 1


def setup_daemon_parser(subparsers) -> None:
    """Setup daemon subcommand parser."""
    daemon_parser = subparsers.add_parser(
        "daemon",
        help="Search daemon management",
        description="Manage the persistent search daemon for better performance",
    )

    daemon_subparsers = daemon_parser.add_subparsers(
        dest="daemon_command", help="Daemon commands"
    )
    daemon_subparsers.required = True

    # start subcommand
    start_parser = daemon_subparsers.add_parser(
        "start", help="Start the search daemon"
    )
    start_parser.add_argument(
        "--host", default="127.0.0.1", help="Host to bind to (default: 127.0.0.1)"
    )
    start_parser.add_argument(
        "--port", type=int, default=DEFAULT_PORT, help=f"Port to bind to (default: {DEFAULT_PORT})"
    )
    start_parser.add_argument(
        "--db", help="DuckDB database path (default: .brain_graph/brain.duckdb)"
    )
    start_parser.add_argument("--config", help="Config file path")
    start_parser.add_argument(
        "-b",
        "--background",
        action="store_true",
        help="Run in background",
    )
    start_parser.set_defaults(func=cmd_daemon_start)

    # stop subcommand
    stop_parser = daemon_subparsers.add_parser("stop", help="Stop the search daemon")
    stop_parser.set_defaults(func=cmd_daemon_stop)

    # status subcommand
    status_parser = daemon_subparsers.add_parser(
        "status", help="Check daemon status"
    )
    status_parser.add_argument(
        "--host", default="127.0.0.1", help="Daemon host (default: 127.0.0.1)"
    )
    status_parser.add_argument(
        "--port", type=int, default=DEFAULT_PORT, help=f"Daemon port (default: {DEFAULT_PORT})"
    )
    status_parser.set_defaults(func=cmd_daemon_status)
