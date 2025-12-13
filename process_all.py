#!/usr/bin/env python3
"""
Process all documents through the full pipeline.

Runs chunking, embedding, taxonomy matching, LLM verification, NER extraction,
and summarization on all markdown files in inbox/ and vault/.

Usage:
    python process_all.py [--inbox-only] [--vault-only] [--force]
    python process_all.py --steps chunking,embedding
    python process_all.py --steps embedding --vault-only
"""

import argparse
import subprocess
import sys
from pathlib import Path


# Available pipeline steps
AVAILABLE_STEPS = {
    'chunking': ("Chunking", ["python", "chunker.py", "-i"]),
    'embedding': ("Embedding", ["python", "embedder.py", "-i"]),
    'taxonomy': ("Taxonomy matching", ["python", "taxonomy_matcher.py", "-i"]),
    'llm_verification': ("LLM verification", ["python", "llm_verifier.py", "-i"]),
    'ner': ("NER extraction", ["python", "ner_extractor.py", "-i"]),
    'summarization': ("Summarization", ["python", "summarizer.py", "-i"]),
}


def run_pipeline_on_file(md_file: Path, steps: list[str], force: bool = False) -> bool:
    """
    Run pipeline steps on a single markdown file.

    Args:
        md_file: Path to markdown file
        steps: List of step names to run
        force: Force processing even if vault file unchanged

    Returns:
        True if successful, False otherwise
    """
    print(f"\n{'='*60}")
    print(f"Processing: {md_file}")
    print(f"Steps: {', '.join(steps)}")
    print(f"{'='*60}\n")

    # Build command list for selected steps
    pipeline_steps = []
    for step_key in steps:
        if step_key not in AVAILABLE_STEPS:
            print(f"Warning: Unknown step '{step_key}', skipping", file=sys.stderr)
            continue

        step_name, base_cmd = AVAILABLE_STEPS[step_key]
        cmd = base_cmd + [str(md_file)]

        # Add --force flag to chunking if requested
        if step_key == 'chunking' and force:
            cmd.append("--force")

        pipeline_steps.append((step_name, cmd))

    if not pipeline_steps:
        print("No valid steps to run!", file=sys.stderr)
        return False

    for step_name, cmd in pipeline_steps:
        print(f"→ {step_name}...", file=sys.stderr)
        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            print(f"✗ {step_name} failed!", file=sys.stderr)
            print(f"Error: {result.stderr}", file=sys.stderr)
            return False

        print(f"✓ {step_name} completed", file=sys.stderr)

    print(f"\n✓ Pipeline completed for {md_file.name}\n", file=sys.stderr)
    return True


def main():
    parser = argparse.ArgumentParser(
        description="Process all documents through pipeline",
        epilog=f"Available steps: {', '.join(AVAILABLE_STEPS.keys())}"
    )
    parser.add_argument("--inbox-only", action="store_true", help="Only process inbox/")
    parser.add_argument("--vault-only", action="store_true", help="Only process vault/")
    parser.add_argument("--force", action="store_true", help="Force processing (skip hash check)")
    parser.add_argument("--skip-errors", action="store_true",
                       help="Continue processing even if a file fails")
    parser.add_argument("--steps", type=str,
                       help="Comma-separated list of steps to run (default: all). "
                            f"Available: {', '.join(AVAILABLE_STEPS.keys())}")
    args = parser.parse_args()

    # Parse steps
    if args.steps:
        # Parse comma-separated steps
        selected_steps = [s.strip() for s in args.steps.split(',')]
        # Validate steps
        invalid_steps = [s for s in selected_steps if s not in AVAILABLE_STEPS]
        if invalid_steps:
            print(f"Error: Invalid steps: {', '.join(invalid_steps)}", file=sys.stderr)
            print(f"Available steps: {', '.join(AVAILABLE_STEPS.keys())}", file=sys.stderr)
            sys.exit(1)
    else:
        # Default: all steps in order
        selected_steps = list(AVAILABLE_STEPS.keys())

    print(f"Pipeline steps: {', '.join(selected_steps)}", file=sys.stderr)

    # Determine which directories to process
    dirs_to_process = []
    if args.inbox_only:
        dirs_to_process = [Path("inbox")]
    elif args.vault_only:
        dirs_to_process = [Path("vault")]
    else:
        dirs_to_process = [Path("inbox"), Path("vault")]

    # Collect all markdown files
    all_files = []
    for directory in dirs_to_process:
        if not directory.exists():
            print(f"Warning: Directory {directory} does not exist, skipping", file=sys.stderr)
            continue

        # Find all .md files recursively
        md_files = sorted(directory.rglob("*.md"))
        print(f"Found {len(md_files)} markdown files in {directory}/", file=sys.stderr)
        all_files.extend(md_files)

    if not all_files:
        print("No markdown files found!", file=sys.stderr)
        sys.exit(1)

    print(f"\n{'='*60}")
    print(f"Total: {len(all_files)} files to process")
    print(f"{'='*60}\n")

    # Process each file
    success_count = 0
    failed_files = []

    for i, md_file in enumerate(all_files, 1):
        print(f"[{i}/{len(all_files)}] {md_file}", file=sys.stderr)

        success = run_pipeline_on_file(md_file, selected_steps, force=args.force)

        if success:
            success_count += 1
        else:
            failed_files.append(md_file)
            if not args.skip_errors:
                print(f"\nAborting due to error. Use --skip-errors to continue.", file=sys.stderr)
                sys.exit(1)

    # Summary
    print(f"\n{'='*60}")
    print(f"Pipeline Summary")
    print(f"{'='*60}")
    print(f"✓ Successful: {success_count}/{len(all_files)}")

    if failed_files:
        print(f"✗ Failed: {len(failed_files)}")
        print("\nFailed files:")
        for f in failed_files:
            print(f"  - {f}")
        sys.exit(1)
    else:
        print("\n🎉 All files processed successfully!")


if __name__ == "__main__":
    main()
