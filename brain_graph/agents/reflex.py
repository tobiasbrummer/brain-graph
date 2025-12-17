import sys
from pathlib import Path
from brain_graph.utils.agent_parser import load_all_agents
from brain_graph.agents.tools import get_tool


class ReflexEngine:
    def __init__(self, root_dir: Path):
        self.root_dir = root_dir
        self.agents_dir = root_dir / "config" / "agents"
        self.agents = load_all_agents(self.agents_dir)
        self.tools_map = self._build_tool_map()

    def _build_tool_map(self):
        mapping = {}
        for agent in self.agents:
            tools = agent.get("tools", [])
            for tool_name in tools:
                tool = get_tool(tool_name)
                if tool:
                    # We map the trigger status to the tool
                    # Note: If multiple tools use the same trigger, this simple map
                    # will overwrite. For now, we assume 1:1 mapping.
                    mapping[tool.trigger_status] = tool
        return mapping

    def run(self):
        """
        Scans for documents with statuses that trigger tools.
        """
        if not self.tools_map:
            return

        # Scan for triggers
        # We look for +status:<trigger>
        for trigger, tool in self.tools_map.items():
            self._process_trigger(trigger, tool)

    def _process_trigger(self, trigger: str, tool):
        # Find files with +status:trigger
        # We check inbox and review folders.
        search_dirs = [self.root_dir / "inbox", self.root_dir / "review"]

        for d in search_dirs:
            if not d.exists():
                continue
            for f in d.glob("*.md"):
                try:
                    content = f.read_text(encoding="utf-8")
                    # Simple string check first
                    if f"+status:{trigger}" in content:
                        print(
                            f"Reflex: Triggering {tool.name} on {f.name}",
                            file=sys.stderr,
                        )
                        result = tool.execute(str(f), content)

                        # Update file
                        # Replace the status to avoid re-triggering
                        # We use a simple replace for now.
                        new_content = content.replace(
                            f"+status:{trigger}", f"+status:done_{tool.name}"
                        )
                        new_content += result
                        f.write_text(new_content, encoding="utf-8")
                except Exception as e:
                    print(f"Error processing {f}: {e}", file=sys.stderr)


if __name__ == "__main__":
    # Simple CLI for testing
    if len(sys.argv) > 1:
        root = Path(sys.argv[1])
    else:
        root = Path(".")

    engine = ReflexEngine(root)
    engine.run()
