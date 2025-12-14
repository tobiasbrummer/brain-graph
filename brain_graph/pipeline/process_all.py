#!/usr/bin/env python3
"""
Process all documents through the full pipeline.

Runs chunking, embedding, taxonomy matching, LLM verification, NER extraction,
and summarization on all markdown files in inbox/ and vault/.

Usage:
    python process_all.py [--inbox-only] [--vault-only] [--force]
    python process_all.py --steps chunking,embedding
    python process_all.py --steps embedding --vault-only

Output:
    By default, prints a single JSON object on stdout for agent workflows.
    Use `--format text` for human-oriented output.
"""

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from brain_graph.utils.cli_utils import emit_json, error_result, ms_since, ok_result

# Available pipeline steps
AVAILABLE_STEPS = {
    "chunking": ("Chunking", "chunker.py", ["-i"]),
    "embedding": ("Embedding", "embedder.py", ["-i"]),
    "taxonomy": ("Taxonomy matching", "taxonomy_matcher.py", ["-i"]),
    "llm_verification": ("LLM verification", "llm_verifier.py", ["-i"]),
    "ner": ("NER extraction", "ner_extractor.py", ["-i"]),
    "summarization": ("Summarization", "summarizer.py", ["-i"]),
}


REPO_ROOT = Path(__file__).resolve().parent


def _tool_python() -> str:
    override = (os.environ.get("BG_PYTHON") or "").strip()
    if override:
        return override
    venv_python = REPO_ROOT / ".venv" / "bin" / "python"
    if venv_python.exists():
        return venv_python.as_posix()
    return sys.executable


def _parse_json_maybe(text: str) -> tuple[dict[str, Any] | None, str]:
    stdout = text.strip()
    if not stdout:
        return None, ""
    lines = [ln for ln in stdout.splitlines() if ln.strip()]
    candidate = lines[-1] if lines else stdout
    try:
        import json

        obj = json.loads(candidate)
        if isinstance(obj, dict):
            return obj, candidate
    except Exception:
        return None, stdout
    return None, stdout


def _run_step(
    *,
    md_file: Path,
    step_key: str,
    python_exe: str,
    child_format: str,
    force: bool,
    debug: bool,
) -> dict[str, Any]:
    step_name, script, required_prefix = AVAILABLE_STEPS[step_key]
    script_path = (REPO_ROOT / script).as_posix()

    cmd = [python_exe, script_path, *required_prefix, str(md_file), "--format", child_format]
    if debug and child_format == "json":
        cmd.append("--debug")
    if step_key == "chunking" and force:
        cmd.append("--force")

    proc = subprocess.run(
        cmd,
        stdout=subprocess.PIPE if child_format == "json" else None,
        text=True,
    )

    parsed, raw = (None, "")
    if child_format == "json":
        parsed, raw = _parse_json_maybe(proc.stdout or "")

    return {
        "step": step_key,
        "name": step_name,
        "command": cmd,
        "returncode": proc.returncode,
        "result": parsed,
        "raw_stdout": raw if (parsed is None and child_format == "json") else None,
    }


def run_pipeline_on_file(
    md_file: Path,
    steps: list[str],
    *,
    force: bool = False,
    python_exe: str,
    child_format: str,
    debug: bool,
) -> dict[str, Any]:
    """
    Run pipeline steps on a single markdown file.

    Args:
        md_file: Path to markdown file
        steps: List of step names to run
        force: Force processing even if vault file unchanged

    Returns:
        Dict with step results and status.
    """
    print(f"Processing: {md_file}", file=sys.stderr)
    print(f"Steps: {', '.join(steps)}", file=sys.stderr)

    # Build command list for selected steps
    pipeline_steps: list[str] = []
    for step_key in steps:
        if step_key not in AVAILABLE_STEPS:
            print(f"Warning: Unknown step '{step_key}', skipping", file=sys.stderr)
            continue

        pipeline_steps.append(step_key)

    if not pipeline_steps:
        print("No valid steps to run!", file=sys.stderr)
        return {"file": str(md_file), "ok": False, "status": "no_steps", "steps": []}

    step_results: list[dict[str, Any]] = []
    for step_key in pipeline_steps:
        step_name = AVAILABLE_STEPS[step_key][0]
        print(f"→ {step_name}...", file=sys.stderr)
        step_result = _run_step(
            md_file=md_file,
            step_key=step_key,
            python_exe=python_exe,
            child_format=child_format,
            force=force,
            debug=debug,
        )
        step_results.append(step_result)

        if step_result["returncode"] != 0:
            print(f"✗ {step_name} failed (rc={step_result['returncode']})", file=sys.stderr)
            return {
                "file": str(md_file),
                "ok": False,
                "status": "failed",
                "failed_step": step_key,
                "steps": step_results,
            }

        print(f"✓ {step_name} completed", file=sys.stderr)

    return {"file": str(md_file), "ok": True, "status": "ok", "steps": step_results}


def main():
    start = time.perf_counter()
    parser = argparse.ArgumentParser(
        description="Process all documents through pipeline",
        epilog=f"Available steps: {', '.join(AVAILABLE_STEPS.keys())}"
    )
    parser.add_argument("--inbox-only", action="store_true", help="Only process inbox/")
    parser.add_argument("--vault-only", action="store_true", help="Only process vault/")
    parser.add_argument("--force", action="store_true", help="Force processing (skip hash check)")
    parser.add_argument("--skip-errors", action="store_true",
                       help="Continue processing even if a file fails")
    parser.add_argument(
        "--format",
        choices=["json", "text"],
        default="json",
        help="Output format (default: json)",
    )
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output")
    parser.add_argument("--debug", action="store_true", help="Include traceback in JSON error output")
    parser.add_argument(
        "--include-results",
        action="store_true",
        help="Include per-file/per-step results in JSON output",
    )
    parser.add_argument("--steps", type=str,
                       help="Comma-separated list of steps to run (default: all). "
                            f"Available: {', '.join(AVAILABLE_STEPS.keys())}")
    args = parser.parse_args()

    try:
        # Parse steps
        if args.steps:
            selected_steps = [s.strip() for s in args.steps.split(",") if s.strip()]
            invalid_steps = [s for s in selected_steps if s not in AVAILABLE_STEPS]
            if invalid_steps:
                raise ValueError(f"Invalid steps: {', '.join(invalid_steps)}")
        else:
            selected_steps = list(AVAILABLE_STEPS.keys())

        print(f"Pipeline steps: {', '.join(selected_steps)}", file=sys.stderr)

        # Determine which directories to process
        if args.inbox_only and args.vault_only:
            raise ValueError("Use only one of --inbox-only or --vault-only")
        if args.inbox_only:
            dirs_to_process = [Path("inbox")]
        elif args.vault_only:
            dirs_to_process = [Path("vault")]
        else:
            dirs_to_process = [Path("inbox"), Path("vault")]

        # Collect all markdown files
        all_files: list[Path] = []
        for directory in dirs_to_process:
            if not directory.exists():
                print(f"Warning: Directory {directory} does not exist, skipping", file=sys.stderr)
                continue
            md_files = sorted(directory.rglob("*.md"))
            print(f"Found {len(md_files)} markdown files in {directory}/", file=sys.stderr)
            all_files.extend(md_files)

        if not all_files:
            raise FileNotFoundError("No markdown files found")

        print(f"Total: {len(all_files)} files to process", file=sys.stderr)

        python_exe = _tool_python()
        child_format = "json" if args.format == "json" else "text"

        # Process each file
        success_count = 0
        failed_files: list[str] = []
        all_results: list[dict[str, Any]] = []

        for i, md_file in enumerate(all_files, 1):
            print(f"[{i}/{len(all_files)}] {md_file}", file=sys.stderr)
            file_result = run_pipeline_on_file(
                md_file,
                selected_steps,
                force=args.force,
                python_exe=python_exe,
                child_format=child_format,
                debug=args.debug,
            )
            if args.include_results:
                all_results.append(file_result)
            if file_result.get("ok"):
                success_count += 1
            else:
                failed_files.append(str(md_file))
                if not args.skip_errors:
                    break

        exit_code = 0 if not failed_files else 2

        result = ok_result(
            "process_all",
            status="ok" if exit_code == 0 else ("partial" if args.skip_errors else "aborted"),
            directories=[str(p) for p in dirs_to_process],
            steps=selected_steps,
            counts={
                "files_total": len(all_files),
                "files_succeeded": success_count,
                "files_failed": len(failed_files),
            },
            failed_files=failed_files,
            results=all_results if args.include_results else None,
            duration_ms=ms_since(start),
        )
        if args.format == "json":
            emit_json(result, pretty=args.pretty)
        else:
            print(f"Successful: {success_count}/{len(all_files)}", file=sys.stderr)
            if failed_files:
                print(f"Failed: {len(failed_files)}", file=sys.stderr)
                for f in failed_files:
                    print(f"  - {f}", file=sys.stderr)
        return exit_code
    except Exception as e:
        if args.format == "json":
            emit_json(error_result("process_all", e, include_traceback=args.debug, duration_ms=ms_since(start)), pretty=args.pretty)
            return 1
        raise


if __name__ == "__main__":
    raise SystemExit(main())
