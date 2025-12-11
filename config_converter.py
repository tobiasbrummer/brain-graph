#!/usr/bin/env python3
"""
Config Converter: config.md → config.json

Parst Markdown-Config mit +key: value Feldern, generiert strukturiertes JSON.

Usage:
    python config_converter.py --input config.md --output config.json
"""

import argparse
import json
import re
from pathlib import Path
from typing import Any


SECTION_RE = re.compile(r"^##\s+(.+)$")
FIELD_RE = re.compile(r"^\+([^:]+):(.*)$")


def parse_config(text: str) -> dict[str, dict[str, Any]]:
    """
    Parst config.md in strukturiertes Dict.

    Returns: {section_name: {key: value, ...}, ...}
    """
    config: dict[str, dict[str, Any]] = {}
    current_section: str | None = None

    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#") and not line.startswith("##"):
            continue

        # Section header
        m = SECTION_RE.match(line)
        if m:
            section_name = m.group(1).strip().lower().replace(" ", "_")
            current_section = section_name
            config[section_name] = {}
            continue

        # Field
        m = FIELD_RE.match(line)
        if m and current_section:
            key = m.group(1).strip()
            value_str = m.group(2).strip()

            # Type conversion
            value: Any = value_str
            if value_str.isdigit():
                value = int(value_str)
            elif value_str.replace(".", "", 1).isdigit():
                value = float(value_str)
            elif value_str.lower() in ("true", "false"):
                value = value_str.lower() == "true"
            elif "<" in value_str or ">" in value_str:
                value = value_str.strip("<>")

            config[current_section][key] = value

    return config


def flatten_config(nested: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """
    Flacht Config für tool.pkms Format ab.

    embedding.base_url → embedding_base_url
    """
    flat: dict[str, Any] = {}

    for section, fields in nested.items():
        for key, value in fields.items():
            flat_key = f"{section}_{key}"
            flat[flat_key] = value

    return flat


def main():
    parser = argparse.ArgumentParser(description="Convert config.md to config.json")
    parser.add_argument("--input", type=Path, default=Path("config/config.md"),
                        help="Input config.md")
    parser.add_argument("--output", type=Path, default=Path(".brain_graph/config/config.json"),
                        help="Output config.json")
    args = parser.parse_args()

    if not args.input.exists():
        print(f"Error: Input file not found: {args.input}")
        return 1

    # Parse
    text = args.input.read_text(encoding="utf-8")
    nested_config = parse_config(text)

    # Flatten für tool.pkms kompatibilität
    flat_config = flatten_config(nested_config)

    # Write
    args.output.write_text(
        json.dumps(flat_config, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    print(f"Written {args.output} ({len(flat_config)} settings)")
    return 0


if __name__ == "__main__":
    exit(main())
