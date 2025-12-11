"""
File handling utilities for brain-graph-2.

Handles:
- Filename slugification
- ULID generation and extraction
- Output path generation for new structure
- Markdown ULID injection
"""

import hashlib
import re
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


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
        hash_bytes = hashlib.sha1(content.encode('utf-8')).digest()[:10]
    else:
        # Random: use urandom
        import os
        hash_bytes = os.urandom(10)

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
    slug = slugify(md_path.stem)
    ulid_suffix = ulid[-6:]  # Last 6 chars of ULID
    filename_base = f"{slug}-{ulid_suffix}"

    # Month folder
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
