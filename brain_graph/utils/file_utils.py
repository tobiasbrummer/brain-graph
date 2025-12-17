"""
File handling utilities for brain-graph-2.

Handles:
- Filename slugification
- ULID generation and extraction
- Output path generation for new structure
- Markdown ULID injection
"""

import hashlib
import json
import re
import subprocess
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional


_INJECTED_ULID_LINE_RE = re.compile(r"^\+id:[0-9A-HJKMNP-TV-Z]{26}\s*$", re.MULTILINE)


def strip_ulid_lines(text: str) -> str:
    """Remove injected '+id:<ULID>' lines from markdown snippets."""
    return _INJECTED_ULID_LINE_RE.sub("", text)


def load_config(config_path: Path | None = None) -> dict[str, Any]:
    """
    Load configuration from config.json.

    Searches for config.json in:
    1. .brain_graph/config/config.json (new structure)
    2. config.json (old structure, fallback)

    Args:
        config_path: Optional explicit path to config file

    Returns:
        Configuration dictionary
    """
    if config_path is None:
        # Search in current directory and parents
        for parent in [Path.cwd(), *Path.cwd().parents]:
            # Try new structure first
            candidate = parent / ".brain_graph" / "config" / "config.json"
            if candidate.exists():
                config_path = candidate
                break

            # Try old structure as fallback
            candidate = parent / "config.json"
            if candidate.exists():
                config_path = candidate
                break

    if config_path and config_path.exists():
        return json.loads(config_path.read_text(encoding="utf-8"))

    # Fallback: Try to parse config/config.md directly if no json found
    try:
        md_path = Path("config/config.md")
        if md_path.exists():
            # Lazy import to avoid circular deps
            import importlib.util
            spec = importlib.util.spec_from_file_location("config_converter", "brain_graph/conversion/config_converter.py")
            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                return module.flatten_config(module.parse_config(md_path.read_text(encoding="utf-8")))
    except Exception:
        pass

    if config_path is None or not config_path.exists():
        # Return empty config instead of raising, to allow bootstrapping
        return {}
            "  - .brain_graph/config/config.json\n"
            "  - config.json\n"
            "Please create a config file or use --config to specify the path."
        )

    return json.loads(config_path.read_text(encoding="utf-8"))


def slugify(text: str) -> str:
    """
    Convert text to URL-safe slug.

    Examples:
        "Jazz Einführung" -> "jazz-einfuhrung"
        "C++ Programming" -> "c-programming"
    """
    # Normalize unicode (ü -> u, ä -> a)
    text = unicodedata.normalize('NFKD', text)
    text = text.encode('ascii', 'ignore').decode('ascii')

    # Lowercase
    text = text.lower()

    # Replace non-alphanumeric with hyphens
    text = re.sub(r'[^a-z0-9]+', '-', text)

    # Remove leading/trailing hyphens
    text = text.strip('-')

    # Collapse multiple hyphens
    text = re.sub(r'-+', '-', text)

    return text


def generate_ulid(content: str = "", timestamp: Optional[datetime] = None) -> str:
    """
    Generate deterministic ULID.

    ULIDs are sortable time-based IDs:
    - First 10 chars: timestamp (milliseconds since epoch, base32)
    - Last 16 chars: randomness (we use content hash for determinism)

    Args:
        content: Content to hash for determinism (empty = random)
        timestamp: Optional timestamp (default: now)

    Returns:
        26-character ULID string
    """
    if timestamp is None:
        timestamp = datetime.now(timezone.utc)

    # Timestamp component (48 bits = 10 base32 chars)
    ts_ms = int(timestamp.timestamp() * 1000)

    # Base32 encoding (Crockford alphabet)
    base32_alphabet = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"

    # Encode timestamp
    ts_encoded = ""
    ts_value = ts_ms
    for _ in range(10):
        ts_encoded = base32_alphabet[ts_value % 32] + ts_encoded
        ts_value //= 32

    # Randomness component (80 bits = 16 base32 chars)
    if content:
        # Deterministic: use SHA1 hash of content
        hash_bytes = hashlib.sha1(content.encode('utf-8')).digest()[:16]
    else:
        # Random: use urandom
        import os
        hash_bytes = os.urandom(16)

    # Encode randomness
    random_encoded = ""
    for byte in hash_bytes:
        random_encoded += base32_alphabet[byte % 32]

    return ts_encoded + random_encoded[:16]


def extract_ulid_from_md(md_path: Path) -> Optional[str]:
    """
    Extract ULID from Markdown file.

    Looks for: +id:01KC21EJ23HHJQNF5FBB3941PS

    Args:
        md_path: Path to markdown file

    Returns:
        ULID string or None if not found
    """
    try:
        content = md_path.read_text(encoding='utf-8')
        match = re.search(r'\+id:([A-Z0-9]{26})', content)
        if match:
            return match.group(1)
    except Exception:
        pass
    return None


def inject_ulid_into_md(md_path: Path, ulid: str) -> bool:
    """
    Inject ULID into Markdown file after first heading.

    Format:
        # Title
        +id:01KC21EJ23HHJQNF5FBB3941PS

    Args:
        md_path: Path to markdown file
        ulid: ULID string to inject

    Returns:
        True if injected, False if already exists or error
    """
    try:
        content = md_path.read_text(encoding='utf-8')

        # Check if ULID already exists
        if re.search(r'\+id:[A-Z0-9]{26}', content):
            return False

        # Find first heading
        lines = content.split('\n')
        for i, line in enumerate(lines):
            if line.startswith('#'):
                # Insert ULID after heading
                lines.insert(i + 1, f'+id:{ulid}')
                break
        else:
            # No heading found, insert at top
            lines.insert(0, f'+id:{ulid}')

        # Write back
        md_path.write_text('\n'.join(lines), encoding='utf-8')
        return True

    except Exception:
        return False


def get_month_folder(timestamp: Optional[datetime] = None) -> str:
    """
    Get YYYY-MM folder name for current or given timestamp.

    Args:
        timestamp: Optional timestamp (default: now)

    Returns:
        YYYY-MM string (e.g., "2025-12")
    """
    if timestamp is None:
        timestamp = datetime.now(timezone.utc)
    return timestamp.strftime("%Y-%m")


def get_output_paths(
    md_path: Path,
    ulid: str,
    base_dir: Path = Path(".brain_graph/data")
) -> dict[str, Path]:
    """
    Generate output paths for all files related to a markdown file.

    Args:
        md_path: Path to source markdown file
        ulid: ULID of the document
        base_dir: Base directory for output (default: .brain_graph/data)

    Returns:
        Dict with keys: embeddings, nodes, edges, ner_nodes, ner_edges, meta
    """
    # Generate filename base
    # Remove ULID suffix if already present (e.g., from vault filename)
    stem = md_path.stem
    stem = re.sub(r'-[A-Z0-9]{6}$', '', stem, flags=re.IGNORECASE)
    slug = slugify(stem)
    ulid_suffix = ulid[-6:]  # Last 6 chars of ULID
    filename_base = f"{slug}-{ulid_suffix}"

    # Month folder - extract from path if vault/YYYY-MM/ structure
    # Otherwise use current month (fallback for non-vault files)
    parent_name = md_path.parent.name
    if re.match(r'^\d{4}-\d{2}$', parent_name):
        month = parent_name
    else:
        month = get_month_folder()

    # Paths
    paths = {
        'embeddings': base_dir / 'embeddings' / month / f"{filename_base}.parquet",
        'nodes': base_dir / 'nodes' / month / f"{filename_base}.nodes.json",
        'edges': base_dir / 'edges' / month / f"{filename_base}.edges.json",
        'ner_nodes': base_dir / 'ner' / 'nodes' / month / f"{filename_base}.ner.nodes.json",
        'ner_edges': base_dir / 'ner' / 'edges' / month / f"{filename_base}.ner.edges.json",
        'meta': base_dir / 'meta' / month / f"{filename_base}.meta.json",
    }

    return paths


def ensure_output_dirs(paths: dict[str, Path]):
    """
    Ensure all output directories exist.

    Args:
        paths: Dict of output paths (from get_output_paths)
    """
    for path in paths.values():
        path.parent.mkdir(parents=True, exist_ok=True)


def get_or_generate_ulid(md_path: Path, content: str = "") -> str:
    """
    Get ULID from markdown file or generate new one.

    Args:
        md_path: Path to markdown file
        content: Content for deterministic generation (optional)

    Returns:
        ULID string
    """
    # Try to extract existing ULID
    ulid = extract_ulid_from_md(md_path)
    if ulid:
        return ulid

    # Generate new ULID
    ulid = generate_ulid(content or md_path.read_text(encoding='utf-8'))

    # Inject into markdown
    inject_ulid_into_md(md_path, ulid)

    return ulid


def get_source_hash(file_path: Path) -> str:
    """
    Calculate SHA256 hash of source file.

    Args:
        file_path: Path to file

    Returns:
        Hash string in format "sha256:abc123..." (first 16 chars)
    """
    content = file_path.read_bytes()
    hash_digest = hashlib.sha256(content).hexdigest()[:16]
    return f"sha256:{hash_digest}"


def get_source_version(file_path: Path) -> dict[str, Any]:
    """
    Get git commit info for source file.

    Args:
        file_path: Path to source file

    Returns:
        Dict with keys:
        - source_commit: short hash of last commit that changed file (or None)
        - source_commit_date: ISO timestamp of commit (or None)
        - source_dirty: True if file has uncommitted changes
    """
    import subprocess

    result = {
        "source_commit": None,
        "source_commit_date": None,
        "source_dirty": False
    }

    try:
        # Letzter commit der die Datei änderte
        commit = subprocess.run(
            ["git", "log", "-1", "--format=%H", "--", str(file_path)],
            capture_output=True, text=True, check=True, cwd=file_path.parent
        ).stdout.strip()

        if commit:
            commit_date = subprocess.run(
                ["git", "log", "-1", "--format=%aI", "--", str(file_path)],
                capture_output=True, text=True, check=True, cwd=file_path.parent
            ).stdout.strip()

            # Check uncommitted changes
            status = subprocess.run(
                ["git", "status", "--porcelain", str(file_path)],
                capture_output=True, text=True, check=True, cwd=file_path.parent
            ).stdout.strip()

            result["source_commit"] = commit[:8]  # short hash
            result["source_commit_date"] = commit_date
            result["source_dirty"] = bool(status)

    except (subprocess.CalledProcessError, FileNotFoundError):
        # Kein git repo oder Datei nicht in git - ist ok
        pass

    return result


def update_meta(meta_path: Path, step_data: dict[str, Any]) -> None:
    """
    Update meta.json with processing step.

    Args:
        meta_path: Path to meta.json
        step_data: Dict with step information (must contain 'step' key)
                  Common fields: step, completed, timestamp, ...

    Example:
        update_meta(output_paths['meta'], {
            'step': 'chunking',
            'chunk_count': 42,
            'section_count': 5
        })
    """
    # Load existing meta or create new
    if meta_path.exists():
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
    else:
        meta = {"processing_steps": []}

    # Update modified timestamp
    now = datetime.now(timezone.utc)
    meta["modified_at"] = now.isoformat()

    # Add timestamp to step_data if not present
    if "timestamp" not in step_data:
        step_data["timestamp"] = now.isoformat()

    # Ensure completed flag exists
    if "completed" not in step_data:
        step_data["completed"] = True

    # Append step
    meta["processing_steps"].append(step_data)

    # Create directory if needed
    meta_path.parent.mkdir(parents=True, exist_ok=True)

    # Write back
    meta_path.write_text(
        json.dumps(meta, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
