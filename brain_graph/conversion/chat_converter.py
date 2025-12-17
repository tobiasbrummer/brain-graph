"""
Chat Converter: Converts JSON chat exports to Markdown for the Inbox.
Supports formats from: ChatGPT, Claude, Gemini (via common export tools).
"""

import json
import re
import sys
from pathlib import Path
from typing import Any


def format_message_content(text: str) -> str:
    """
    Formats message content, e.g., wrapping code blocks that are not wrapped.
    Uses heuristics to detect code blocks in user messages.
    """
    if not text:
        return ""

    # If the text already contains code blocks, assume it's formatted or mixed enough.
    if "```" in text:
        return text

    lines = text.split("\n")
    output = []
    in_code = False
    code_buffer = []

    # Regex for lines that definitely start code
    # Includes Python, JS/TS, HTML, JSON markers, UserScript header, Bash, Lua, CSS
    code_start_pattern = re.compile(
        r"^\s*(import|from|class|def|if|for|while|try|except|with|async|await|"  # Python
        r"function|const|let|var|switch|case|interface|type|export|return|public|private|protected|"  # JS/TS
        r"@|//|/\*|<[a-zA-Z]|"  # Decorators, Comments, HTML, CSS (@media etc)
        r"console\.log|print\(|"  # Common prints
        r"// ==UserScript==|"  # Specific UserScript header
        r"echo|sudo|apt|pip|npm|cd|ls|cat|grep|#\!/|"  # Bash
        r"local|require|"  # Lua
        r"body|html|div|span|h[1-6]|a\s*\{|\.[a-zA-Z0-9_-]+\s*\{|#[a-zA-Z0-9_-]+\s*\{"  # CSS selectors (basic)
        r")"
    )

    # Regex for lines that look like structural code endings or continuations
    code_continuation_pattern = re.compile(r"^\s*([}\] );]+|{)$")

    # Regex for lines that definitely look like natural language text
    # Starts with capital letter, ends with punctuation, has spaces, no obvious code symbols
    text_pattern = re.compile(r"^[A-Z][^;{}()=]+[.?!:]$")

    for line in lines:
        stripped = line.strip()
        is_code_start = bool(code_start_pattern.match(line))
        is_code_continuation = bool(code_continuation_pattern.match(line))

        if not in_code:
            if is_code_start or (is_code_continuation and stripped):
                # Start of a code block
                # If we have previous text, ensure a blank line before
                if output and output[-1].strip():
                    output.append("")
                in_code = True
                code_buffer = [line]
            else:
                output.append(line)
        else:
            # We are inside a code block
            # Heuristic to exit:
            # 1. Line looks strongly like text
            # 2. AND line is not a comment
            # 3. AND line is not indented (assuming code is often indented or structured)

            is_text = text_pattern.match(line)
            is_comment = (
                stripped.startswith("//")
                or stripped.startswith("#")
                or stripped.startswith("/*")
            )

            if (
                is_text
                and not is_comment
                and not line.startswith("    ")
                and not line.startswith("\t")
            ):
                # End of code block
                lang = ""
                if code_buffer:
                    first = code_buffer[0].strip()
                    if "// ==UserScript==" in first:
                        lang = "javascript"
                    elif (
                        first.startswith("def ")
                        or first.startswith("import ")
                        or first.startswith("from ")
                    ):
                        lang = "python"
                    elif (
                        first.startswith("function ")
                        or first.startswith("const ")
                        or first.startswith("let ")
                        or first.startswith("var ")
                    ):
                        lang = "javascript"
                    elif first.startswith("<"):
                        lang = "html"
                    elif (
                        first.startswith("#!")
                        or first.startswith("echo ")
                        or first.startswith("sudo ")
                        or first.startswith("pip ")
                        or first.startswith("npm ")
                        or first.startswith("cd ")
                        or first.startswith("ls ")
                    ):
                        lang = "bash"
                    elif first.startswith("local ") or first.startswith("require("):
                        lang = "lua"
                    elif "{" in first and (
                        first.startswith(".")
                        or first.startswith("#")
                        or first.startswith("@")
                        or first[0].islower()
                    ):
                        lang = "css"

                output.append(f"```{lang}")
                output.extend(code_buffer)
                output.append("```")
                output.append("")  # Spacing

                code_buffer = []
                in_code = False
                output.append(line)
            else:
                code_buffer.append(line)

    # Flush remaining code buffer
    if in_code:
        lang = ""
        if code_buffer:
            first = code_buffer[0].strip()
            if "// ==UserScript==" in first:
                lang = "javascript"
            elif (
                first.startswith("def ")
                or first.startswith("import ")
                or first.startswith("from ")
            ):
                lang = "python"
            elif (
                first.startswith("function ")
                or first.startswith("const ")
                or first.startswith("let ")
                or first.startswith("var ")
            ):
                lang = "javascript"
            elif first.startswith("<"):
                lang = "html"
            elif (
                first.startswith("#!")
                or first.startswith("echo ")
                or first.startswith("sudo ")
                or first.startswith("pip ")
                or first.startswith("npm ")
                or first.startswith("cd ")
                or first.startswith("ls ")
            ):
                lang = "bash"
            elif first.startswith("local ") or first.startswith("require("):
                lang = "lua"
            elif "{" in first and (
                first.startswith(".")
                or first.startswith("#")
                or first.startswith("@")
                or first[0].islower()
            ):
                lang = "css"

        output.append(f"```{lang}")
        output.extend(code_buffer)
        output.append("```")

    return "\n".join(output)


def convert_chat_json(json_path: Path, output_dir: Path):
    """Converts a single JSON chat file to Markdown."""
    try:
        data = json.loads(json_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        print(f"Error: Could not decode {json_path}", file=sys.stderr)
        return

    # Extract Metadata
    title = data.get("title", "Untitled Chat")
    date = data.get("date", "")
    model = data.get("model", "unknown")
    messages = data.get("messages", [])

    # Generate Filename (slugified title)
    safe_title = "".join(c if c.isalnum() else "_" for c in title).strip("_")
    filename = f"chat_{safe_title}.md"
    output_path = output_dir / filename

    # Build Markdown Content
    md_lines = [
        f"# {title}",
        "",
        "+type:chat",
        "+status:active",
    ]

    if date:
        md_lines.append(f"+date:{date}")
    if model:
        md_lines.append(f"+model:{model}")

    md_lines.append("")

    for msg in messages:
        role = msg.get("role", "unknown").capitalize()
        text = msg.get("text") or msg.get("content") or ""

        # Handle list of content parts (sometimes used in Claude/OpenAI exports)
        if isinstance(text, list):
            text = "\n".join(str(part) for part in text)

        text = format_message_content(text)

        md_lines.append(f"**{role}**:")
        md_lines.append(text)
        md_lines.append("")
        md_lines.append("---")
        md_lines.append("")

    # Write to Inbox
    output_path.write_text("\n".join(md_lines), encoding="utf-8")
    print(f"Converted: {json_path.name} -> {output_path}", file=sys.stderr)


def main():
    if len(sys.argv) < 2:
        print(
            "Usage: python -m brain_graph.conversion.chat_converter <json_file_or_dir>",
            file=sys.stderr,
        )
        sys.exit(1)

    input_path = Path(sys.argv[1])
    output_dir = Path("inbox")
    output_dir.mkdir(exist_ok=True)

    if input_path.is_file():
        convert_chat_json(input_path, output_dir)
    elif input_path.is_dir():
        for f in input_path.glob("*.json"):
            convert_chat_json(f, output_dir)
    else:
        print(f"Error: Input {input_path} not found.", file=sys.stderr)


if __name__ == "__main__":
    main()
