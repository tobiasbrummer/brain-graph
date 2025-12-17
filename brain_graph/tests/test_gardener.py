import unittest
import duckdb
import tempfile
import shutil
from pathlib import Path
from brain_graph.agents.gardener import GardenerAgent


class TestGardener(unittest.TestCase):
    def setUp(self):
        self.test_dir = Path(tempfile.mkdtemp())
        self.db_path = self.test_dir / "test.duckdb"

        # Setup DB
        con = duckdb.connect(str(self.db_path))
        con.execute("CREATE TABLE nodes (text VARCHAR)")

        # Insert data with tags
        con.execute("INSERT INTO nodes VALUES ('This is #tag1')")
        con.execute("INSERT INTO nodes VALUES ('Another #tag1')")
        con.execute("INSERT INTO nodes VALUES ('#tag1 again')")
        con.execute("INSERT INTO nodes VALUES ('Only once #tag2')")
        con.close()

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_find_candidates(self):
        agent = GardenerAgent(self.db_path, {})
        candidates = agent.find_candidates(min_occurrences=2)

        # Should find #tag1 (3 times) but not #tag2 (1 time)
        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0][0], "#tag1")
        self.assertEqual(candidates[0][1], 3)

    def test_create_suggestion(self):
        agent = GardenerAgent(self.db_path, {})
        output_dir = self.test_dir / "review"
        output_dir.mkdir()

        agent.create_suggestion("#tag1", 3, output_dir)

        suggestion_file = output_dir / "suggestion--category_tag1.md"
        self.assertTrue(suggestion_file.exists())
        content = suggestion_file.read_text(encoding="utf-8")
        self.assertIn("+type:suggestion", content)
        self.assertIn("+occurrences:3", content)


if __name__ == "__main__":
    unittest.main()
