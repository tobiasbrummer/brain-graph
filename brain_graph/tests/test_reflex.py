import unittest
from pathlib import Path
import tempfile
import shutil
from brain_graph.agents.reflex import ReflexEngine
from brain_graph.agents.tools import TOOL_REGISTRY, Tool


class MockTool:
    name = "mock_tool"
    trigger_status = "mock_trigger"

    def execute(self, file_path: str, content: str) -> str:
        return "\n> Mock executed."


class TestReflex(unittest.TestCase):
    def setUp(self):
        self.test_dir = Path(tempfile.mkdtemp())
        self.config_dir = self.test_dir / "config" / "agents"
        self.config_dir.mkdir(parents=True)
        self.inbox_dir = self.test_dir / "inbox"
        self.inbox_dir.mkdir()

        # Create agent profile
        (self.config_dir / "mock_agent.md").write_text(
            """
+tools:mock_tool
""",
            encoding="utf-8",
        )

        # Register mock tool
        TOOL_REGISTRY["mock_tool"] = MockTool()

    def tearDown(self):
        shutil.rmtree(self.test_dir)
        if "mock_tool" in TOOL_REGISTRY:
            del TOOL_REGISTRY["mock_tool"]

    def test_reflex_trigger(self):
        # Create trigger file
        trigger_file = self.inbox_dir / "trigger.md"
        trigger_file.write_text(
            """# Trigger
+status:mock_trigger
""",
            encoding="utf-8",
        )

        engine = ReflexEngine(self.test_dir)
        engine.run()

        content = trigger_file.read_text(encoding="utf-8")
        self.assertIn("+status:done_mock_tool", content)
        self.assertIn("> Mock executed.", content)


if __name__ == "__main__":
    unittest.main()
