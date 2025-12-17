import unittest
import hashlib
from brain_graph.pipeline.chunker import build_graph, Block
from brain_graph.pipeline.chunker import Edge


class TestProvenance(unittest.TestCase):
    def test_author_edge_creation(self):
        # Mock blocks
        blocks = [
            Block(type="heading", content="Title", level=1),
            Block(type="text", content="Some text.\n+author:&TestAgent", level=1),
        ]

        config = {
            "chunk_target_tokens": 100,
            "chunk_min_tokens": 10,
            "chunk_overlap_tokens": 0,
            "chunk_language": "en",
        }

        doc_ulid = "01HQXN00000000000000000000"

        nodes, edges = build_graph(blocks, "test.md", config, doc_ulid=doc_ulid)

        # Check for authored_by edge
        found = False
        for edge in edges:
            if edge.type == "authored_by" and edge.from_id == doc_ulid:
                # Check target ID
                agent_name = "&TestAgent"
                agent_hash = hashlib.sha1(agent_name.lower().encode()).hexdigest()[:8]
                expected_id = f"entity_{agent_hash}"

                if edge.to_id == expected_id:
                    found = True
                    break

        self.assertTrue(found, "authored_by edge not found or incorrect")


if __name__ == "__main__":
    unittest.main()
