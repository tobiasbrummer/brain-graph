from __future__ import annotations

from brain_graph.pipeline import chunker


def test_chunker_node_ulids_use_document_timestamp_and_are_stable() -> None:
    doc_ulid = "01KCEQFS97VZFWN6Y0JH84BSM7"
    md = (
        f"# Title\n+id:{doc_ulid}\n\n"
        "## Section\n\n"
        "This is a longer paragraph so language detection has enough text to work.\n"
        "Another sentence to exceed the minimum length.\n"
    )

    blocks = chunker.parse_markdown(md)
    cfg = {
        "chunk_target_tokens": 64,
        "chunk_min_tokens": 10,
        "chunk_overlap_tokens": 5,
        "chunk_language": "en",
    }

    nodes1, edges1 = chunker.build_graph(blocks, "note.md", cfg, doc_ulid=doc_ulid)
    nodes2, edges2 = chunker.build_graph(blocks, "note.md", cfg, doc_ulid=doc_ulid)

    assert [n.id for n in nodes1] == [n.id for n in nodes2]
    assert [n.ulid for n in nodes1] == [n.ulid for n in nodes2]
    assert [e.to_dict() for e in edges1] == [e.to_dict() for e in edges2]

    assert nodes1
    assert all(n.ulid[:10] == doc_ulid[:10] for n in nodes1)
