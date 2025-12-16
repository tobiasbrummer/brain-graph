"""Pipeline subcommands for brain CLI."""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent.parent

PIPELINE_TOOLS = {
    "chunk": ("brain_graph/pipeline/chunker.py", "Chunk markdown file into semantic sections"),
    "embed": ("brain_graph/pipeline/embedder.py", "Generate embeddings for text chunks"),
    "code-embed": ("brain_graph/pipeline/code_embedder.py", "Generate embeddings for code units (functions/classes/methods)"),
    "taxonomy-embed": ("brain_graph/pipeline/taxonomy_embedder.py", "Generate embeddings for taxonomy categories"),
    "taxonomy": ("brain_graph/pipeline/taxonomy_matcher.py", "Match content to taxonomy categories"),
    "verify": ("brain_graph/pipeline/llm_verifier.py", "Verify content with LLM"),
    "ner": ("brain_graph/pipeline/ner_extractor.py", "Extract named entities"),
    "summarize": ("brain_graph/pipeline/summarizer.py", "Generate summaries"),
    "process-all": ("brain_graph/pipeline/process_all.py", "Process all files through pipeline"),
}


def cmd_pipeline(args: argparse.Namespace) -> int:
    """Execute pipeline command."""
    tool = args.tool
    script_path, _ = PIPELINE_TOOLS[tool]
    script = REPO_ROOT / script_path

    python_exe = (os.environ.get("BG_PYTHON") or "").strip() or sys.executable
    cmd = [python_exe, str(script)]
    
    # Most tools take -i <file>
    if args.file and tool != "process-all":
        cmd.extend(["-i", args.file])
    
    # Add passthrough args
    if args.args:
        cmd.extend(args.args)
    
    # Always request JSON output
    if "--format" not in cmd:
        cmd.extend(["--format", "json"])
    
    result = subprocess.run(cmd)
    return result.returncode


def setup_pipeline_parser(subparsers) -> None:
    """Setup pipeline subcommand parser."""
    pipeline_parser = subparsers.add_parser(
        "pipeline",
        help="Run pipeline processing tools",
        description="Process markdown files through the ingestion pipeline",
    )
    
    pipeline_parser.add_argument(
        "tool",
        choices=list(PIPELINE_TOOLS.keys()),
        help="Pipeline tool to run",
    )
    
    pipeline_parser.add_argument(
        "file",
        nargs="?",
        help="Markdown file to process (not needed for process-all)",
    )
    
    pipeline_parser.add_argument(
        "args",
        nargs=argparse.REMAINDER,
        help="Additional arguments to pass to the tool",
    )
    
    pipeline_parser.set_defaults(func=cmd_pipeline)
