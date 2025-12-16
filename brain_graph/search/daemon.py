#!/usr/bin/env python3
"""
Search daemon for brain-graph.

Keeps a persistent DuckDB connection and indexes loaded in memory
to avoid cold-start latency on every search request.
"""
from __future__ import annotations

import argparse
import json
import signal
import sys
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

import duckdb

# Add repo root to path
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from brain_graph.search.searcher import (
    bm25_search,
    deduplicate_by_document,
    embed_query,
    fuzzy_search,
    hybrid_search,
    semantic_search,
)
from brain_graph.utils.file_utils import load_config


class SearchDaemon:
    """Search daemon with persistent DB connection."""

    def __init__(self, db_path: Path, config_path: Path | None = None):
        """Initialize daemon with database and config."""
        self.db_path = db_path
        self.config = load_config(config_path)
        self.con: duckdb.DuckDBPyConnection | None = None
        self.ready = False

    def load_database(self) -> None:
        """Load database into memory with indexes."""
        print(f"Loading database from {self.db_path}...", file=sys.stderr)
        start = time.perf_counter()

        self.con = duckdb.connect(":memory:")
        self.con.execute(f"ATTACH '{self.db_path}' AS disk_db (READ_ONLY)")

        main_tables = [
            "nodes",
            "edges",
            "chunk_embeddings_256d",
            "taxonomy_embeddings_256d",
            "embedding_sources",
            "meta",
            "german_stopwords",
        ]

        for table_name in main_tables:
            exists = self.con.execute(
                f"SELECT COUNT(*) FROM duckdb_tables() WHERE database_name='disk_db' AND table_name='{table_name}'"
            ).fetchone()[0]
            if exists:
                print(f"  Loading table: {table_name}", file=sys.stderr)
                self.con.execute(
                    f"CREATE TABLE {table_name} AS SELECT * FROM disk_db.{table_name}"
                )

        self.con.execute("DETACH disk_db")

        print("Building indexes...", file=sys.stderr)

        # VSS extension + HNSW index
        vss_loaded = False
        try:
            self.con.execute("LOAD vss;")
            vss_loaded = True
        except duckdb.Error:
            try:
                self.con.execute("INSTALL vss;")
                self.con.execute("LOAD vss;")
                vss_loaded = True
            except duckdb.Error as e:
                print(
                    f"Warning: Could not load VSS extension ({e})", file=sys.stderr
                )

        if vss_loaded:
            try:
                self.con.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_chunk_embeddings_hnsw
                    ON chunk_embeddings_256d
                    USING HNSW (embedding)
                    WITH (metric = 'cosine')
                    """
                )
            except duckdb.Error as e:
                print(
                    f"Warning: Could not build HNSW index ({e})", file=sys.stderr
                )

        # FTS extension + index
        fts_loaded = False
        try:
            self.con.execute("LOAD fts;")
            fts_loaded = True
        except duckdb.Error:
            try:
                self.con.execute("INSTALL fts;")
                self.con.execute("LOAD fts;")
                fts_loaded = True
            except duckdb.Error as e:
                print(
                    f"Warning: Could not load FTS extension ({e})", file=sys.stderr
                )

        if fts_loaded:
            has_stopwords = (
                self.con.execute(
                    "SELECT COUNT(*) FROM duckdb_tables() WHERE table_name='german_stopwords'"
                ).fetchone()[0]
                > 0
            )
            stopwords_param = "german_stopwords" if has_stopwords else "none"
            try:
                self.con.execute(
                    f"""
                    PRAGMA create_fts_index(
                        'nodes', 'id', 'text', 'summary', 'title', 'description',
                        stemmer='german',
                        stopwords='{stopwords_param}',
                        ignore='(\\.|[^a-zäöüß])+',
                        strip_accents=1,
                        lower=1,
                        overwrite=1
                    )
                    """
                )
            except duckdb.Error as e:
                print(
                    f"Warning: Could not build FTS index ({e})", file=sys.stderr
                )

        elapsed = (time.perf_counter() - start) * 1000
        print(f"Database ready in {elapsed:.0f}ms", file=sys.stderr)
        self.ready = True

    def search(self, query: str, mode: str = "hybrid", limit: int = 10) -> dict[str, Any]:
        """Execute search query."""
        if not self.ready or self.con is None:
            return {
                "ok": False,
                "error": {"type": "DaemonNotReady", "message": "Daemon not ready"},
            }

        start = time.perf_counter()

        try:
            query_embedding = None
            if mode in ["semantic", "hybrid"]:
                query_embedding = embed_query(query, self.config)

            if mode == "semantic":
                results = semantic_search(self.con, query_embedding, limit)
                score_key = "similarity"
            elif mode == "bm25":
                results = bm25_search(self.con, query, limit)
                score_key = "bm25_score"
            elif mode == "fuzzy":
                results = fuzzy_search(self.con, query, limit)
                score_key = "fuzzy_score"
            else:  # hybrid
                results = hybrid_search(self.con, query, query_embedding, limit, 0.7, 0.3)
                score_key = "hybrid_score"

            results = deduplicate_by_document(results, score_key)

            duration_ms = (time.perf_counter() - start) * 1000

            return {
                "ok": True,
                "tool": "search",
                "status": "completed",
                "output": {
                    "query": query,
                    "mode": mode,
                    "limit": limit,
                    "score_key": score_key,
                },
                "results": results,
                "counts": {"results": len(results)},
                "duration_ms": duration_ms,
            }

        except Exception as e:
            duration_ms = (time.perf_counter() - start) * 1000
            return {
                "ok": False,
                "tool": "search",
                "status": "failed",
                "error": {"type": type(e).__name__, "message": str(e)},
                "duration_ms": duration_ms,
            }

    def close(self) -> None:
        """Close database connection."""
        if self.con is not None:
            self.con.close()
            self.con = None
            self.ready = False


# Global daemon instance
daemon: SearchDaemon | None = None


class SearchHTTPHandler(BaseHTTPRequestHandler):
    """HTTP request handler for search daemon."""

    def do_GET(self) -> None:
        """Handle GET requests."""
        if self.path == "/health":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            response = {
                "status": "ok" if daemon and daemon.ready else "not_ready",
                "ready": daemon.ready if daemon else False,
            }
            self.wfile.write(json.dumps(response).encode())
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self) -> None:
        """Handle POST requests."""
        if self.path == "/search":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)

            try:
                data = json.loads(body)
                query = data.get("query", "")
                mode = data.get("mode", "hybrid")
                limit = data.get("limit", 10)

                if not query:
                    self.send_response(400)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(
                        json.dumps(
                            {"ok": False, "error": "Missing 'query' parameter"}
                        ).encode()
                    )
                    return

                result = daemon.search(query, mode, limit)

                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps(result, ensure_ascii=False).encode())

            except json.JSONDecodeError:
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(
                    json.dumps({"ok": False, "error": "Invalid JSON"}).encode()
                )
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format: str, *args: Any) -> None:
        """Suppress default logging."""
        pass


def run_daemon(host: str, port: int, db_path: Path, config_path: Path | None) -> None:
    """Run the search daemon."""
    global daemon

    daemon = SearchDaemon(db_path, config_path)
    daemon.load_database()

    server = HTTPServer((host, port), SearchHTTPHandler)

    def signal_handler(sig, frame):
        print("\nShutting down daemon...", file=sys.stderr)
        daemon.close()
        server.shutdown()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    print(f"Search daemon listening on http://{host}:{port}", file=sys.stderr)
    print("Endpoints:", file=sys.stderr)
    print("  GET  /health  - Health check", file=sys.stderr)
    print("  POST /search  - Search query", file=sys.stderr)
    print("", file=sys.stderr)

    server.serve_forever()


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Brain Graph search daemon")
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Host to bind to (default: 127.0.0.1)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8765,
        help="Port to bind to (default: 8765)",
    )
    parser.add_argument(
        "--db",
        type=Path,
        default=Path(".brain_graph/brain.duckdb"),
        help="DuckDB database path (default: .brain_graph/brain.duckdb)",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=None,
        help="Config file path (default: auto-detect)",
    )

    args = parser.parse_args()

    if not args.db.exists():
        print(f"Error: Database not found: {args.db}", file=sys.stderr)
        return 1

    run_daemon(args.host, args.port, args.db, args.config)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
