import unittest
import json
import shutil
import tempfile
from pathlib import Path
from brain_graph.conversion.chat_converter import convert_chat_json


class TestChatConverter(unittest.TestCase):
    def setUp(self):
        self.test_dir = Path(tempfile.mkdtemp())
        self.inbox_dir = self.test_dir / "inbox"
        self.inbox_dir.mkdir()

        self.json_file = self.test_dir / "test_chat.json"
        self.json_file.write_text(
            json.dumps(
                {
                    "title": "Test Chat",
                    "date": "2025-12-17",
                    "model": "gpt-4",
                    "messages": [
                        {"role": "user", "text": "Hello"},
                        {"role": "assistant", "text": "Hi there"},
                    ],
                }
            ),
            encoding="utf-8",
        )

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_conversion(self):
        convert_chat_json(self.json_file, self.inbox_dir)

        expected_file = self.inbox_dir / "chat_Test_Chat.md"
        self.assertTrue(expected_file.exists())

        content = expected_file.read_text(encoding="utf-8")
        self.assertIn("# Test Chat", content)
        self.assertIn("+type:chat", content)
        self.assertIn("+status:active", content)
        self.assertIn("**User**:", content)
        self.assertIn("Hello", content)
        self.assertIn("**Assistant**:", content)
        self.assertIn("Hi there", content)

    def test_userscript_wrapping(self):
        userscript_content = """Here is the script:
// ==UserScript==
// @name Test Script
// ==/UserScript==
console.log('test');"""

        self.json_file.write_text(
            json.dumps(
                {
                    "title": "Script Chat",
                    "messages": [{"role": "user", "text": userscript_content}],
                }
            ),
            encoding="utf-8",
        )

        convert_chat_json(self.json_file, self.inbox_dir)

        expected_file = self.inbox_dir / "chat_Script_Chat.md"
        content = expected_file.read_text(encoding="utf-8")

        self.assertIn("```javascript", content)
        self.assertIn("// ==UserScript==", content)
        self.assertIn("console.log('test');", content)
        self.assertIn("```", content)

    def test_generic_code_wrapping(self):
        # Test Python snippet
        python_msg = """Here is some python:
import os
def foo():
    print("bar")
    
That was code."""

        self.json_file.write_text(
            json.dumps(
                {
                    "title": "Python Chat",
                    "messages": [{"role": "user", "text": python_msg}],
                }
            ),
            encoding="utf-8",
        )

        convert_chat_json(self.json_file, self.inbox_dir)

        expected_file = self.inbox_dir / "chat_Python_Chat.md"
        content = expected_file.read_text(encoding="utf-8")

        # Should wrap the code part
        self.assertIn("```", content)
        self.assertIn("import os", content)
        self.assertIn("def foo():", content)
        # "That was code." should be outside or at least the block should end
        # My heuristic might wrap "That was code." if it doesn't look "texty" enough,
        # but "That was code." matches the text_pattern (Capital, ends with .)

        # Check structure: Text -> Code -> Text
        # We expect:
        # Here is some python:
        # ```
        # import os
        # ...
        # ```
        # That was code.

        # Simple check: ``` appears before "import" and after "print"
        import_idx = content.find("import os")
        first_tick = content.find("```")
        self.assertLess(first_tick, import_idx)

    def test_bash_wrapping(self):
        bash_msg = """Run this:
sudo apt update
sudo apt install python3
Done."""
        self.json_file.write_text(
            json.dumps(
                {"title": "Bash Chat", "messages": [{"role": "user", "text": bash_msg}]}
            ),
            encoding="utf-8",
        )

        convert_chat_json(self.json_file, self.inbox_dir)
        content = (self.inbox_dir / "chat_Bash_Chat.md").read_text(encoding="utf-8")

        self.assertIn("```bash", content)
        self.assertIn("sudo apt update", content)

    def test_css_wrapping(self):
        css_msg = """Style it:
body {
    color: red;
}
.class {
    margin: 0;
}"""
        self.json_file.write_text(
            json.dumps(
                {"title": "CSS Chat", "messages": [{"role": "user", "text": css_msg}]}
            ),
            encoding="utf-8",
        )

        convert_chat_json(self.json_file, self.inbox_dir)
        content = (self.inbox_dir / "chat_CSS_Chat.md").read_text(encoding="utf-8")

        self.assertIn("```css", content)
        self.assertIn("body {", content)


if __name__ == "__main__":
    unittest.main()
