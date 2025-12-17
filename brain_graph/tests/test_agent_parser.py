import unittest
from pathlib import Path
import tempfile
import shutil
from brain_graph.utils.agent_parser import parse_agent_profile, load_all_agents


class TestAgentParser(unittest.TestCase):
    def setUp(self):
        self.test_dir = Path(tempfile.mkdtemp())
        self.agent_file = self.test_dir / "test_agent.md"
        self.agent_file.write_text(
            """# Test Agent

+type:agent_profile
+model:gpt-4
+tools:tool1, tool2
+status:active

Description here.
""",
            encoding="utf-8",
        )

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_parse_agent_profile(self):
        profile = parse_agent_profile(self.agent_file)
        self.assertEqual(profile["name"], "test_agent")
        self.assertEqual(profile["type"], "agent_profile")
        self.assertEqual(profile["model"], "gpt-4")
        self.assertEqual(profile["tools"], ["tool1", "tool2"])
        self.assertEqual(profile["status"], "active")

    def test_load_all_agents(self):
        agents = load_all_agents(self.test_dir)
        self.assertEqual(len(agents), 1)
        self.assertEqual(agents[0]["name"], "test_agent")


if __name__ == "__main__":
    unittest.main()
