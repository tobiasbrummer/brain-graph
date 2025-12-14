#!/usr/bin/env python3
"""
Parse links from SYNTAX.md (+link:, +image:, +projekt:, +quelle:).

Extracts links with:
- Type (link/image/projekt/quelle)
- Target ULID (full or short, auto-completed)
- Source node (chunk/section where link appears)
- Context (surrounding text)
- Character offset
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal


ULID_PATTERN = r"[0-9A-HJKMNP-TV-Z]{26}"
SHORT_ULID_PATTERN = r"[0-9A-HJKMNP-TV-Z]{4,26}"

# From SYNTAX.md
LINK_PATTERN = re.compile(
    r"\+(?P<type>link|image|projekt|quelle):(?P<target>[^\s]+)",
    re.IGNORECASE
)

LinkType = Literal["link", "image", "projekt", "quelle"]


@dataclass
class ParsedLink:
    """A link extracted from markdown."""
    type: LinkType
    target_id: str  # ULID (full or short)
    char_offset: int
    context: str | None = None


def extract_links(text: str, context_chars: int = 100) -> list[ParsedLink]:
    """
    Extract all +link:, +image:, +projekt:, +quelle: from text.

    Args:
        text: Markdown text to parse
        context_chars: Number of chars to extract around link for context

    Returns:
        List of ParsedLink objects
    """
    links: list[ParsedLink] = []

    for match in LINK_PATTERN.finditer(text):
        link_type = match.group("type").lower()
        target = match.group("target")

        # Extract ULID from target (may be short or full). For `+quelle:...`,
        # allow arbitrary URL/reference strings.
        ulid_match = re.search(SHORT_ULID_PATTERN, target)
        if ulid_match:
            target_id = ulid_match.group()
        else:
            if link_type != "quelle":
                continue
            target_id = target

        # Extract context
        start = max(0, match.start() - context_chars)
        end = min(len(text), match.end() + context_chars)
        context = text[start:end].strip()

        links.append(ParsedLink(
            type=link_type,  # type: ignore
            target_id=target_id,
            char_offset=match.start(),
            context=context
        ))

    return links


def resolve_short_ulids(
    links: list[ParsedLink],
    ulid_map: dict[str, str]
) -> list[ParsedLink]:
    """
    Resolve short ULIDs to full ULIDs using a mapping.

    Args:
        links: List of ParsedLink objects (may have short ULIDs)
        ulid_map: Dict mapping short ULID suffixes to full ULIDs

    Returns:
        List of ParsedLink objects with full ULIDs
    """
    resolved: list[ParsedLink] = []

    for link in links:
        target_id = link.target_id

        # If already full ULID, keep as-is
        if len(target_id) == 26 and re.match(ULID_PATTERN, target_id):
            resolved.append(link)
            continue

        # Try to resolve short ULID
        full_ulid = ulid_map.get(target_id)
        if full_ulid:
            link.target_id = full_ulid
            resolved.append(link)
        else:
            # Keep short ULID if not resolvable (validation will catch this)
            resolved.append(link)

    return resolved


def assign_links_to_nodes(
    links: list[ParsedLink],
    nodes: list[dict],
    text: str
) -> list[dict]:
    """
    Assign links to source nodes based on char_offset.

    Args:
        links: List of ParsedLink objects
        nodes: List of node dicts with char_start/char_end (chunks/sections)
        text: Full document text

    Returns:
        List of link dicts with source_node field
    """
    result: list[dict] = []

    for link in links:
        source_node = None

        # Find which node contains this link
        for node in nodes:
            char_start = node.get("char_start")
            char_end = node.get("char_end")

            if (isinstance(char_start, int) and
                isinstance(char_end, int) and
                char_start <= link.char_offset < char_end):
                source_node = node.get("id")
                break

        result.append({
            "type": link.type,
            "target_id": link.target_id,
            "source_node": source_node,
            "context": link.context,
            "char_offset": link.char_offset
        })

    return result


if __name__ == "__main__":
    # Simple test
    test_text = """
    # Test Document

    Check out this project: +projekt:01HAR6DP2M7G1KQ3Y3VQ8C0Q for more details.

    Here's an image: +image:8C0Q showing the architecture.

    Related: +link:01G3X1MK2N and +quelle:https://example.com
    """

    links = extract_links(test_text)
    for link in links:
        print(f"{link.type}: {link.target_id} at offset {link.char_offset}")
        print(f"  Context: {link.context[:50]}...")
        print()
