from __future__ import annotations

from brain_graph.utils.link_parser import assign_links_to_nodes, extract_links, resolve_short_ulids


def test_extract_links_finds_multiple_types() -> None:
    text = "See +link:01KCEQFS97VZFWN6Y0JH84BSM7 and +image:84BSM7 and +quelle:https://example.com"
    links = extract_links(text, context_chars=20)
    assert [l.type for l in links] == ["link", "image", "quelle"]


def test_resolve_short_ulids_replaces_when_mapping_exists() -> None:
    text = "Related: +link:84BSM7"
    links = extract_links(text)
    resolved = resolve_short_ulids(links, {"84BSM7": "01KCEQFS97VZFWN6Y0JH84BSM7"})
    assert resolved[0].target_id == "01KCEQFS97VZFWN6Y0JH84BSM7"


def test_assign_links_to_nodes_sets_source_node() -> None:
    text = "AAA +link:01KCEQFS97VZFWN6Y0JH84BSM7 BBB"
    links = extract_links(text, context_chars=5)

    nodes = [
        {"id": "chunk_1", "char_start": 0, "char_end": len(text)},
    ]

    out = assign_links_to_nodes(links, nodes, text)
    assert out[0]["source_node"] == "chunk_1"
