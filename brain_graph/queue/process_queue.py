#!/usr/bin/env python3
"""
Queue Processor: Processes files from the embedding queue.
"""
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

QUEUE_FILE = Path(".brain_graph/queue.json")
LOG_FILE = Path(".brain_graph/logs/processor.log")


def load_queue() -> dict[str, list[dict[str, Any]]]:
    if not QUEUE_FILE.exists():
        return {"pending": [], "processing": [], "failed": []}
    try:
        return json.loads(QUEUE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {"pending": [], "processing": [], "failed": []}


def save_queue(queue: dict[str, list[dict[str, Any]]]):
    QUEUE_FILE.write_text(json.dumps(queue, indent=2), encoding="utf-8")


def process_file(file_path: str) -> bool:
    """Run the pipeline for a single file."""
    print(f"Processing {file_path}...", file=sys.stderr)

    # Run process_all.py for this file
    # We assume process_all.py is in the path or we call it via python module
    cmd = [
        sys.executable,
        "-m",
        "brain_graph.pipeline.process_all",
        "--force",  # Force re-processing
        str(file_path),
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"Error processing {file_path}: {result.stderr}", file=sys.stderr)
            return False
        return True
    except Exception as e:
        print(f"Exception processing {file_path}: {e}", file=sys.stderr)
        return False


def main():
    print("Starting Queue Processor...", file=sys.stderr)

    # Ensure log dir exists
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

    while True:
        queue = load_queue()

        if not queue["pending"]:
            time.sleep(5)
            continue

        # Get next job
        job = queue["pending"].pop(0)
        job["started_at"] = datetime.now(timezone.utc).isoformat()
        queue["processing"].append(job)
        save_queue(queue)

        success = process_file(job["file"])

        # Reload queue to avoid overwriting new jobs added while processing
        queue = load_queue()
        # Remove from processing (find by file/commit)
        queue["processing"] = [
            j for j in queue["processing"] if j["file"] != job["file"]
        ]

        if success:
            # Done
            pass
        else:
            job["failed_at"] = datetime.now(timezone.utc).isoformat()
            job["retry_count"] = job.get("retry_count", 0) + 1
            if job["retry_count"] < 3:
                queue["pending"].append(job)  # Retry
            else:
                queue["failed"].append(job)

        save_queue(queue)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Processor stopped.", file=sys.stderr)
