import unittest
import shutil
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch
from brain_graph.agents.archivist import ArchivistAgent


class TestArchivist(unittest.TestCase):
    def setUp(self):
        self.test_dir = Path(tempfile.mkdtemp())
        self.inbox_dir = self.test_dir / "inbox"
        self.archive_dir = self.test_dir / "archive"
        self.vault_dir = self.test_dir / "vault" / "2025-12"

        self.inbox_dir.mkdir()
        self.archive_dir.mkdir()
        self.vault_dir.mkdir(parents=True)

        # Create test chat
        self.chat_file = self.inbox_dir / "chat.md"
        self.chat_file.write_text(
            """# Chat
+type:chat
+status:active

Content...
""",
            encoding="utf-8",
        )

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    @patch("brain_graph.agents.archivist.OpenAI")
    def test_archivist_flow(self, mock_openai):
        # Mock LLM response
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value.choices[0].message.content = (
            "# Extracted Note\nFact 1"
        )
        mock_openai.return_value = mock_client

        agent = ArchivistAgent({})

        # Override paths for testing (since run() uses hardcoded paths relative to cwd)
        # We'll test the methods individually instead of run() to avoid chdir mess

        # 1. Find
        chats = agent.find_volatile_chats(self.inbox_dir)
        self.assertEqual(len(chats), 1)
        self.assertEqual(chats[0].name, "chat.md")

        # 2. Extract
        content = chats[0].read_text(encoding="utf-8")
        note_content = agent.extract_knowledge(content)
        self.assertIn("Fact 1", note_content)

        # 3. Save
        agent.save_note(note_content, "chat.md", self.vault_dir)
        notes = list(self.vault_dir.glob("*.md"))
        self.assertEqual(len(notes), 1)
        self.assertIn("+derived_from:chat.md", notes[0].read_text(encoding="utf-8"))

        # 4. Archive
        agent.archive_chat(chats[0], self.archive_dir)
        self.assertFalse(self.chat_file.exists())
        archived_chat = self.archive_dir / "chat.md"
        self.assertTrue(archived_chat.exists())
        self.assertIn("+status:processed", archived_chat.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
