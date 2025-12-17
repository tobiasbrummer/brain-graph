"""
Researcher Agent: Validates hypotheses using external search.
"""

import os
import sys
import json
from datetime import date
from pathlib import Path
from typing import Any, Optional

from openai import OpenAI

try:
    from tavily import TavilyClient
except ImportError:
    TavilyClient = None

from brain_graph.utils.file_utils import get_or_generate_ulid


class ResearcherAgent:
    """
    The Researcher agent takes pending hypotheses, searches the web for evidence,
    and updates the hypothesis status.
    """

    def __init__(self, config: dict[str, Any]):
        self.config = config
        self.client = OpenAI(
            base_url=config.get("summary_base_url", "http://localhost:8100/v1"),
            api_key=config.get("summary_api_key", "unused"),
        )
        self.model = config.get("summary_model", "mistral-7b-instruct")

        api_key = os.environ.get("TAVILY_API_KEY")
        if TavilyClient and api_key:
            self.tavily = TavilyClient(api_key=api_key)
        else:
            self.tavily = None
            print(
                "Warning: Tavily client not available (missing library or TAVILY_API_KEY). Research will be mocked.",
                file=sys.stderr,
            )

    def find_pending_hypotheses(self, inbox_dir: Path) -> list[Path]:
        """Find markdown files with +type:hypothesis and +status:pending."""
        pending = []
        if not inbox_dir.exists():
            return []

        for f in inbox_dir.glob("*.md"):
            try:
                content = f.read_text(encoding="utf-8")
                if "+type:hypothesis" in content and "+status:pending" in content:
                    pending.append(f)
            except Exception:
                pass
        return pending

    def search_web(self, query: str) -> str:
        """Perform web search."""
        if self.tavily:
            try:
                response = self.tavily.search(query=query, search_depth="basic")
                context = "\n".join([r["content"] for r in response.get("results", [])])
                return context
            except Exception as e:
                print(f"Tavily search error: {e}", file=sys.stderr)
                return ""
        return "Mock search result: No evidence found (Tavily not configured)."

    def validate(self, hypothesis_text: str) -> dict[str, Any]:
        """Validate hypothesis using LLM and Web Search."""
        # 1. Generate search queries
        query_prompt = (
            f"Generate 3 search queries to validate this hypothesis: {hypothesis_text}"
        )
        # (Simplified: just use the hypothesis as query for now)
        query = hypothesis_text

        # 2. Search
        context = self.search_web(query)

        # 3. Evaluate
        eval_prompt = f"""Hypothesis: {hypothesis_text}

Evidence from Web:
{context}

Evaluate if the evidence supports the hypothesis.
Return JSON with:
- status: "validated" or "rejected" or "inconclusive"
- reason: Short explanation
- insight: A synthesized insight if validated (optional)
"""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": eval_prompt}],
                max_tokens=300,
                temperature=0.3,
                response_format={"type": "json_object"},
            )
            result = json.loads(response.choices[0].message.content)
            return result
        except Exception as e:
            print(f"Researcher LLM error: {e}", file=sys.stderr)
            return {"status": "inconclusive", "reason": f"Error: {e}"}

    def update_hypothesis_file(self, file_path: Path, result: dict[str, Any]):
        """Update the markdown file with results."""
        content = file_path.read_text(encoding="utf-8")

        # Update status
        content = content.replace(
            "+status:pending", f"+status:{result.get('status', 'inconclusive')}"
        )

        # Append result
        append_text = f"""
## Ergebnis ({result.get('status')})
{result.get('reason')}

"""
        if result.get("status") == "validated" and result.get("insight"):
            append_text += f"## Insight\n{result['insight']}\n"

        file_path.write_text(content + append_text, encoding="utf-8")
        print(
            f"Researcher: Updated {file_path} ({result.get('status')})", file=sys.stderr
        )

        # Archive to vault/hypotheses
        self.archive_hypothesis(file_path, result)

    def archive_hypothesis(self, file_path: Path, result: dict[str, Any]):
        """Move processed hypothesis to vault/hypotheses/ and update index."""
        hypotheses_dir = Path("vault/hypotheses")
        hypotheses_dir.mkdir(parents=True, exist_ok=True)

        new_path = hypotheses_dir / file_path.name
        file_path.rename(new_path)

        # Update Index
        index_file = hypotheses_dir / "INDEX.md"
        if not index_file.exists():
            index_file.write_text(
                "# Hypothesen Index\n\n| Datum | Status | Titel | Link |\n|---|---|---|---|\n",
                encoding="utf-8",
            )

        # Extract title
        content = new_path.read_text(encoding="utf-8")
        title_line = content.splitlines()[0].replace("# ", "").strip()
        date_str = date.today().isoformat()
        status = result.get("status", "unknown")

        with index_file.open("a", encoding="utf-8") as f:
            f.write(f"| {date_str} | {status} | {title_line} | [[{new_path.name}]] |\n")

        print(f"Researcher: Archived to {new_path} and updated index.", file=sys.stderr)

    def run(self):
        """Main execution method."""
        review_dir = Path("review")
        pending = self.find_pending_hypotheses(review_dir)
        if not pending:
            print("Researcher: No pending hypotheses found.", file=sys.stderr)
            return

        for p in pending:
            # Extract hypothesis text (simplified)
            content = p.read_text(encoding="utf-8")
            # Assume title or "Vermutung" section holds the text
            # Just take the first line for now
            hypothesis_text = content.splitlines()[0].replace("# ", "")

            result = self.validate(hypothesis_text)
            self.update_hypothesis_file(p, result)
