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
import time
from pathlib import Path
from typing import Any

from brain_graph.utils.cli_utils import emit_json, error_result, ms_since, ok_result


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
    start = time.perf_counter()
    parser = argparse.ArgumentParser(description="Convert config.md to config.json")
    parser.add_argument("--input", type=Path, default=Path("config/config.md"),
                        help="Input config.md")
    parser.add_argument("--output", type=Path, default=Path(".brain_graph/config/config.json"),
                        help="Output config.json")
    parser.add_argument(
        "--format",
        choices=["json", "text"],
        default="json",
        help="Output format (default: json)",
    )
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output")
    parser.add_argument("--debug", action="store_true", help="Include traceback in JSON error output")
    args = parser.parse_args()

    try:
        if not args.input.exists():
            raise FileNotFoundError(f"Input file not found: {args.input}")

        # Parse
        text = args.input.read_text(encoding="utf-8")
        nested_config = parse_config(text)

        # Flatten für tool.pkms kompatibilität
        flat_config = flatten_config(nested_config)

        # Write
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(flat_config, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )

        result = ok_result(
            "config_converter",
            input=str(args.input),
            output={"config": str(args.output)},
            counts={"settings": len(flat_config), "sections": len(nested_config)},
            duration_ms=ms_since(start),
        )
        if args.format == "json":
            emit_json(result, pretty=args.pretty)
        else:
            print(f"Written {args.output} ({len(flat_config)} settings)")
        return 0
    except Exception as e:
        if args.format == "json":
            emit_json(
                error_result("config_converter", e, include_traceback=args.debug, duration_ms=ms_since(start)),
                pretty=args.pretty,
            )
            return 1
        raise


if __name__ == "__main__":
    raise SystemExit(main())
