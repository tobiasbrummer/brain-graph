from __future__ import annotations

import pytest

from brain_graph.models import Link, LinkType


def test_link_allows_url_for_quelle() -> None:
    link = Link(type=LinkType.QUELLE, target_id="https://example.com")
    assert link.target_id == "https://example.com"


def test_link_requires_ulid_for_internal_links() -> None:
    with pytest.raises(ValueError):
        Link(type=LinkType.LINK, target_id="https://example.com")

