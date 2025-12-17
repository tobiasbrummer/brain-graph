import re
from pathlib import Path
from typing import Any


def parse_agent_profile(file_path: Path) -> dict[str, Any]:
    """
    Parses an agent profile markdown file.
    Extracts metadata like +tools, +model, etc.
    """
    content = file_path.read_text(encoding="utf-8")
    metadata = {}

    # Extract +key:value
    for line in content.splitlines():
        match = re.match(r"^\+([a-zA-Z0-9_]+):(.+)$", line.strip())
        if match:
            key = match.group(1)
            value = match.group(2).strip()
            if key == "tools":
                metadata[key] = [t.strip() for t in value.split(",")]
            else:
                metadata[key] = value

    metadata["name"] = file_path.stem
    return metadata


def load_all_agents(agents_dir: Path) -> list[dict[str, Any]]:
    agents = []
    if not agents_dir.exists():
        return []

    for f in agents_dir.glob("*.md"):
        agents.append(parse_agent_profile(f))
    return agents
