"""
Archivist Agent: Distills chats into knowledge.
"""

import sys
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

from openai import OpenAI

from brain_graph.utils.file_utils import get_or_generate_ulid


class ArchivistAgent:
    """
    The Archivist agent processes 'volatile' chat logs (inbox/chats/*.md or similar),
    extracts key facts (using LLM), creates 'crystallized' notes, and archives the chat.
    """

    def __init__(self, config: dict[str, Any]):
        self.config = config
        self.client = OpenAI(
            base_url=config.get("summary_base_url", "http://localhost:8100/v1"),
            api_key=config.get("summary_api_key", "unused"),
        )
        self.model = config.get("summary_model", "mistral-7b-instruct")

    def find_volatile_chats(self, inbox_dir: Path) -> list[Path]:
        """Find markdown files with +type:chat and +status:active (or no status)."""
        chats = []
        if not inbox_dir.exists():
            return []

        for f in inbox_dir.glob("*.md"):
            try:
                content = f.read_text(encoding="utf-8")
                if "+type:chat" in content and "+status:processed" not in content:
                    chats.append(f)
            except Exception:
                pass
        return chats

    def extract_knowledge(self, content: str) -> str:
        """Uses LLM to extract key facts/notes from chat."""
        prompt = f"""
        You are an Archivist. Extract key facts, decisions, and ideas from the following chat log.
        Format the output as a valid Markdown note.
        
        Chat Log:
        {content}
        
        Output (Markdown):
        """

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"Archivist LLM Error: {e}", file=sys.stderr)
            return f"Error extracting knowledge: {e}"

    def archive_chat(self, chat_file: Path, archive_dir: Path):
        """Moves chat to archive and marks as processed."""
        archive_dir.mkdir(exist_ok=True)

        # Mark as processed in content (optional, since we move it)
        content = chat_file.read_text(encoding="utf-8")
        if "+status:processed" not in content:
            content += (
                "\n\n+status:processed\n+archived_at:" + datetime.now().isoformat()
            )
            chat_file.write_text(content, encoding="utf-8")

        # Move
        target = archive_dir / chat_file.name
        shutil.move(str(chat_file), str(target))
        print(f"Archivist: Archived {chat_file.name}", file=sys.stderr)

    def save_note(self, content: str, source_file: str, vault_dir: Path):
        """Saves the extracted note to vault."""
        vault_dir.mkdir(exist_ok=True)

        # Generate filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"note_{timestamp}.md"
        path = vault_dir / filename

        # Add metadata
        meta = f"\n\n+type:note\n+derived_from:{source_file}\n+author:&Archivist\n"
        full_content = content + meta

        path.write_text(full_content, encoding="utf-8")
        print(f"Archivist: Created note {filename}", file=sys.stderr)

    def run(self):
        print("Archivist: Scanning for volatile chats...", file=sys.stderr)
        inbox_dir = Path("inbox")
        archive_dir = Path("archive")
        vault_dir = Path("vault") / datetime.now().strftime("%Y-%m")

        chats = self.find_volatile_chats(inbox_dir)

        if not chats:
            print("Archivist: No chats found.", file=sys.stderr)
            return

        for chat in chats:
            print(f"Archivist: Processing {chat.name}...", file=sys.stderr)
            content = chat.read_text(encoding="utf-8")

            # Extract
            note_content = self.extract_knowledge(content)

            # Save Note
            self.save_note(note_content, chat.name, vault_dir)

            # Archive
            self.archive_chat(chat, archive_dir)
