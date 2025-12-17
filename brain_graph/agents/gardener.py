"""
Gardener Agent: Maintains the taxonomy and structure.
"""

import sys
from pathlib import Path
from typing import Any

import duckdb

from brain_graph.db.db_builder import BrainGraphDB


class GardenerAgent:
    """
    The Gardener agent identifies frequent tags that should be promoted
    to taxonomy categories.
    """

    def __init__(self, db_path: Path, config: dict[str, Any]):
        self.db_path = db_path
        self.config = config

    def connect(self) -> duckdb.DuckDBPyConnection:
        return duckdb.connect(str(self.db_path), read_only=True)

    def find_candidates(self, min_occurrences: int = 5) -> list[tuple[str, int]]:
        """Find tags that appear frequently but are not categories."""
        con = self.connect()
        try:
            # Extract hashtags
            # Note: This regex is simple.
            candidates = con.execute(
                f"""
                WITH tags AS (
                    SELECT unnest(regexp_extract_all(text, '#[a-zA-Z0-9_]+')) as tag
                    FROM nodes
                )
                SELECT tag, count(*) as c
                FROM tags
                GROUP BY tag
                HAVING c >= ?
                ORDER BY c DESC
            """,
                [min_occurrences],
            ).fetchall()

            # Filter out existing categories
            # We need to know existing categories.
            # Assuming taxonomy_embeddings_256d has category_id (slugs).
            # Hashtags usually don't match slugs exactly (#Project_X vs project-x).
            # For now, just return the raw tags.

            return candidates
        finally:
            con.close()

    def create_suggestion(self, tag: str, count: int, output_dir: Path):
        """Create a suggestion file."""
        clean_tag = tag.lstrip("#")
        filename = f"suggestion--category_{clean_tag}.md"
        path = output_dir / filename

        if path.exists():
            return

        content = f"""# Vorschlag: Kategorie {tag}

+type:suggestion
+status:pending
+occurrences:{count}

Der Tag `{tag}` wurde {count} mal gefunden. Soll er in die Taxonomie aufgenommen werden?

## Aktionen
* [ ] In `config/taxonomy.md` eintragen
* [ ] `brain pipeline process --all` ausführen (um Tags zu konvertieren)
"""
        path.write_text(content, encoding="utf-8")
        print(f"Gardener: Created suggestion {path}", file=sys.stderr)

    def run(self):
        """Main execution method."""
        candidates = self.find_candidates()

        output_dir = Path("review")
        output_dir.mkdir(exist_ok=True)

        if candidates:
            for tag, count in candidates:
                self.create_suggestion(tag, count, output_dir)
        else:
            print("Gardener: No candidates found.", file=sys.stderr)

        # Resurfacing (Flashback)
        self.resurface_old_notes(output_dir)

    def resurface_old_notes(self, output_dir: Path):
        """Find important but neglected notes."""
        con = self.connect()
        try:
            # Logic: High importance, Low weight (decayed), Not viewed recently
            # We use the relevance_scores view
            # importance > 7, days_since_modified > 180

            flashbacks = con.execute(
                """
                SELECT ulid, importance, days_since_modified 
                FROM relevance_scores
                WHERE importance >= 7 AND days_since_modified > 180
                ORDER BY random()
                LIMIT 1
            """
            ).fetchall()

            for ulid, imp, days in flashbacks:
                # Get node details
                node = con.execute(
                    "SELECT title, source_file FROM nodes WHERE ulid = ?", [ulid]
                ).fetchone()
                if node:
                    title, source = node
                    self.create_flashback(title, source, days, output_dir)

        except Exception as e:
            print(f"Gardener Resurfacing error: {e}", file=sys.stderr)
        finally:
            con.close()

    def create_flashback(self, title: str, source: str, days: float, output_dir: Path):
        filename = f"flashback--{title.replace(' ', '_')}.md"
        path = output_dir / filename
        if path.exists():
            return

        content = f"""# Flashback: {title}

+type:flashback
+status:pending
+days_dormant:{int(days)}
+source:[[{source}]]

Diese Notiz war wichtig (Importance > 7), wurde aber seit {int(days)} Tagen nicht bearbeitet.
Ist sie noch aktuell?

## Aktionen
* [ ] Aktualisieren (Edit)
* [ ] Archivieren (Decay akzeptieren)
* [ ] Bestätigen (Touch)
"""
        path.write_text(content, encoding="utf-8")
        print(f"Gardener: Created flashback {path}", file=sys.stderr)
