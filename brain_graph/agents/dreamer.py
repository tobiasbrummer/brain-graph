"""
Dreamer Agent: Finds latent bridges in the knowledge graph.
"""

import sys
from datetime import date
from pathlib import Path
from typing import Any

import duckdb
import ulid
from openai import OpenAI

from brain_graph.db.db_builder import BrainGraphDB


class DreamerAgent:
    """
    The Dreamer agent analyzes the graph topology and vector embeddings
    to find "Latent Bridges" - concepts that are semantically similar
    but not connected in the graph.
    """

    def __init__(self, db_path: Path, config: dict[str, Any]):
        self.db_path = db_path
        self.config = config
        self.client = OpenAI(
            base_url=config.get("summary_base_url", "http://localhost:8100/v1"),
            api_key=config.get("summary_api_key", "unused"),
        )
        self.model = config.get("summary_model", "mistral-7b-instruct")

    def connect(self) -> duckdb.DuckDBPyConnection:
        """Connect to the database."""
        # We use read_only=True to avoid locking if the daemon is also reading?
        # DuckDB allows multiple readers.
        return duckdb.connect(str(self.db_path), read_only=True)

    def find_latent_bridges(self, limit: int = 5) -> list[dict[str, Any]]:
        """
        Find pairs of chunks with high similarity but no direct connection.
        """
        con = self.connect()
        try:
            # This query finds pairs of chunks with similarity > 0.85
            # that are NOT connected by any edge.
            # We limit to a random sample to avoid O(N^2) on the full graph every time.
            # Or we use the HNSW index via a join?
            # DuckDB's HNSW index is used for `array_cosine_distance(col, const)`.
            # It doesn't optimize `array_cosine_distance(col1, col2)` join yet.
            # So we sample one side.

            print("Dreamer: Scanning for latent bridges...", file=sys.stderr)

            # Sample 20 random chunks
            sample_chunks = con.execute(
                """
                SELECT chunk_id, embedding, text, source_file 
                FROM chunk_embeddings_256d 
                JOIN nodes ON chunk_embeddings_256d.chunk_id = nodes.id
                ORDER BY random() 
                LIMIT 20
            """
            ).fetchall()

            candidates = []

            for chunk_id, embedding, text, source_file in sample_chunks:
                # Find top similar for this chunk
                # Note: We need to cast the python list to FLOAT[256] in SQL
                # But we can't pass list directly as param for array literal easily in python client sometimes?
                # Actually we can.

                similar = con.execute(
                    """
                    SELECT 
                        e.chunk_id, 
                        n.text, 
                        n.source_file,
                        1.0 - array_cosine_distance(e.embedding, ?::FLOAT[256]) as sim
                    FROM chunk_embeddings_256d e
                    JOIN nodes n ON e.chunk_id = n.id
                    WHERE e.chunk_id != ?
                    ORDER BY array_cosine_distance(e.embedding, ?::FLOAT[256]) ASC
                    LIMIT 10
                """,
                    [embedding, chunk_id, embedding],
                ).fetchall()

                for other_id, other_text, other_source, sim in similar:
                    if sim < 0.82:  # Threshold from requirements
                        continue

                    # Check if connected
                    connected = con.execute(
                        """
                        SELECT 1 FROM edges 
                        WHERE (from_id = ? AND to_id = ?) 
                           OR (from_id = ? AND to_id = ?)
                    """,
                        [chunk_id, other_id, other_id, chunk_id],
                    ).fetchone()

                    if connected:
                        continue

                    # Check for rejected hypothesis
                    # We look for a hypothesis document that links to both source files
                    rejected = con.execute(
                        """
                        SELECT 1
                        FROM meta m
                        JOIN doc_links l1 ON m.ulid = l1.source_doc_id
                        JOIN doc_links l2 ON m.ulid = l2.source_doc_id
                        JOIN meta m1 ON l1.target_doc_id = m1.ulid
                        JOIN meta m2 ON l2.target_doc_id = m2.ulid
                        WHERE m.doc_type = 'hypothesis'
                          AND m.research_status = 'rejected'
                          AND m1.source_file = ?
                          AND m2.source_file = ?
                        """,
                        [source_file, other_source],
                    ).fetchone()

                    if rejected:
                        # print(f"Dreamer: Skipping rejected hypothesis between {source_file} and {other_source}", file=sys.stderr)
                        continue

                    # Found a latent bridge!
                    candidates.append(
                        {
                            "source": {
                                "id": chunk_id,
                                "text": text,
                                "file": source_file,
                            },
                            "target": {
                                "id": other_id,
                                "text": other_text,
                                "file": other_source,
                            },
                            "similarity": sim,
                        }
                    )
                    if len(candidates) >= limit:
                        return candidates

            return candidates
        finally:
            con.close()

    def formulate_hypothesis(self, bridge: dict[str, Any]) -> str:
        """Generate a hypothesis explaining the connection."""
        prompt = f"""You are a research assistant. I found a high semantic similarity ({bridge['similarity']:.2f}) between two text chunks that are not explicitly connected.

Chunk A ({bridge['source']['file']}):
"{bridge['source']['text']}"

Chunk B ({bridge['target']['file']}):
"{bridge['target']['text']}"

Formulate a scientific hypothesis why these two concepts might be related. 
Start with "Hypothese:". Keep it concise (max 3 sentences).
"""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=150,
                temperature=0.7,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"Dreamer LLM error: {e}", file=sys.stderr)
            return f"Hypothese: Automatisch generierte Verbindung basierend auf Vektor-Ähnlichkeit ({bridge['similarity']:.2f})."

    def create_hypothesis_file(
        self, bridge: dict[str, Any], hypothesis_text: str, output_dir: Path
    ):
        """Create a markdown file for the hypothesis."""
        doc_ulid = str(ulid.new())
        filename = f"hyp--{doc_ulid}.md"
        path = output_dir / filename

        content = f"""# {hypothesis_text.splitlines()[0]}

+type:hypothesis
+status:pending
+date:{date.today().isoformat()}
+similarity:{bridge['similarity']:.2f}
+source_a:[[{bridge['source']['file']}]]
+source_b:[[{bridge['target']['file']}]]

## Vermutung
{hypothesis_text}

## Kontext
* **Source A:** {bridge['source']['text'][:200]}...
* **Source B:** {bridge['target']['text'][:200]}...

"""
        path.write_text(content, encoding="utf-8")
        print(f"Dreamer: Created hypothesis {path}", file=sys.stderr)

    def run(self):
        """Main execution method."""
        bridges = self.find_latent_bridges()
        if not bridges:
            print("Dreamer: No latent bridges found.", file=sys.stderr)
            return

        # Ensure output dir exists
        output_dir = Path("review")
        output_dir.mkdir(exist_ok=True)

        for bridge in bridges:
            hypothesis = self.formulate_hypothesis(bridge)
            self.create_hypothesis_file(bridge, hypothesis, output_dir)
