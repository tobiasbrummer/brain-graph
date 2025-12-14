#!/usr/bin/env python3
"""Documentation extractor for brain agent docs command.

Extracts docstrings, function signatures, and parameters from Python modules
for LLM agent consumption.
"""
from __future__ import annotations

import argparse
import ast
import importlib
import inspect
import json
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parent.parent.parent

# Map tool names to module paths
TOOL_MAP = {
    "chunker": "brain_graph.pipeline.chunker",
    "embedder": "brain_graph.pipeline.embedder",
    "taxonomy": "brain_graph.pipeline.taxonomy_matcher",
    "verify": "brain_graph.pipeline.llm_verifier",
    "ner": "brain_graph.pipeline.ner_extractor",
    "summarizer": "brain_graph.pipeline.summarizer",
    "searcher": "brain_graph.search.searcher",
    "search": "brain_graph.search.searcher",
    "reranking": "brain_graph.search.reranking",
    "db_builder": "brain_graph.db.db_builder",
    "db": "brain_graph.db.db_builder",
    "models": "brain_graph.models",
}


def extract_function_docs(func: Any) -> dict[str, Any]:
    """Extract documentation from a function."""
    doc = inspect.getdoc(func) or ""
    sig = inspect.signature(func)
    
    params = []
    for name, param in sig.parameters.items():
        param_info = {
            "name": name,
            "annotation": str(param.annotation) if param.annotation != inspect.Parameter.empty else None,
            "default": str(param.default) if param.default != inspect.Parameter.empty else None,
        }
        params.append(param_info)
    
    return {
        "name": func.__name__,
        "docstring": doc,
        "parameters": params,
        "return_annotation": str(sig.return_annotation) if sig.return_annotation != inspect.Signature.empty else None,
    }


def extract_class_docs(cls: Any) -> dict[str, Any]:
    """Extract documentation from a class."""
    doc = inspect.getdoc(cls) or ""
    
    methods = []
    for name, member in inspect.getmembers(cls, inspect.isfunction):
        if not name.startswith("_") or name == "__init__":
            methods.append(extract_function_docs(member))
    
    return {
        "name": cls.__name__,
        "docstring": doc,
        "methods": methods,
    }


def extract_module_docs(module_name: str) -> dict[str, Any]:
    """Extract all documentation from a module."""
    # Add repo to path
    if str(REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(REPO_ROOT))
    
    try:
        module = importlib.import_module(module_name)
    except ImportError as e:
        return {
            "error": f"Could not import module '{module_name}': {e}",
            "module": module_name,
        }
    
    module_doc = inspect.getdoc(module) or ""
    
    functions = []
    classes = []
    
    for name, member in inspect.getmembers(module):
        # Skip private and imported members
        if name.startswith("_"):
            continue
        
        if inspect.isfunction(member) and member.__module__ == module_name:
            functions.append(extract_function_docs(member))
        elif inspect.isclass(member) and member.__module__ == module_name:
            classes.append(extract_class_docs(member))
    
    return {
        "module": module_name,
        "docstring": module_doc,
        "functions": functions,
        "classes": classes,
    }


def format_text(docs: dict[str, Any]) -> str:
    """Format documentation as human-readable text."""
    if "error" in docs:
        return f"Error: {docs['error']}"
    
    lines = []
    lines.append(f"Module: {docs['module']}")
    lines.append("=" * (len(docs['module']) + 8))
    lines.append("")
    
    if docs.get("docstring"):
        lines.append(docs["docstring"])
        lines.append("")
    
    if docs.get("functions"):
        lines.append("Functions:")
        lines.append("-" * 10)
        for func in docs["functions"]:
            lines.append(f"\n{func['name']}(")
            for param in func["parameters"]:
                annotation = f": {param['annotation']}" if param['annotation'] else ""
                default = f" = {param['default']}" if param['default'] else ""
                lines.append(f"  {param['name']}{annotation}{default},")
            ret = f" -> {func['return_annotation']}" if func['return_annotation'] else ""
            lines.append(f"){ret}")
            
            if func.get("docstring"):
                lines.append("")
                for line in func["docstring"].split("\n"):
                    lines.append(f"  {line}")
            lines.append("")
    
    if docs.get("classes"):
        lines.append("Classes:")
        lines.append("-" * 8)
        for cls in docs["classes"]:
            lines.append(f"\nclass {cls['name']}:")
            if cls.get("docstring"):
                for line in cls["docstring"].split("\n"):
                    lines.append(f"  {line}")
            
            if cls.get("methods"):
                lines.append("\n  Methods:")
                for method in cls["methods"]:
                    lines.append(f"\n  {method['name']}(")
                    for param in method["parameters"]:
                        annotation = f": {param['annotation']}" if param['annotation'] else ""
                        default = f" = {param['default']}" if param['default'] else ""
                        lines.append(f"    {param['name']}{annotation}{default},")
                    ret = f" -> {method['return_annotation']}" if method['return_annotation'] else ""
                    lines.append(f"  ){ret}")
                    
                    if method.get("docstring"):
                        lines.append("")
                        for line in method["docstring"].split("\n"):
                            lines.append(f"    {line}")
            lines.append("")
    
    return "\n".join(lines)


def format_markdown(docs: dict[str, Any]) -> str:
    """Format documentation as markdown."""
    if "error" in docs:
        return f"# Error\n\n{docs['error']}"
    
    lines = []
    lines.append(f"# {docs['module']}")
    lines.append("")
    
    if docs.get("docstring"):
        lines.append(docs["docstring"])
        lines.append("")
    
    if docs.get("functions"):
        lines.append("## Functions")
        lines.append("")
        for func in docs["functions"]:
            params = ", ".join(
                f"{p['name']}" + (f": {p['annotation']}" if p['annotation'] else "") + (f" = {p['default']}" if p['default'] else "")
                for p in func["parameters"]
            )
            ret = f" -> {func['return_annotation']}" if func['return_annotation'] else ""
            lines.append(f"### `{func['name']}({params}){ret}`")
            lines.append("")
            if func.get("docstring"):
                lines.append(func["docstring"])
                lines.append("")
    
    if docs.get("classes"):
        lines.append("## Classes")
        lines.append("")
        for cls in docs["classes"]:
            lines.append(f"### `{cls['name']}`")
            lines.append("")
            if cls.get("docstring"):
                lines.append(cls["docstring"])
                lines.append("")
            
            if cls.get("methods"):
                lines.append("**Methods:**")
                lines.append("")
                for method in cls["methods"]:
                    params = ", ".join(
                        f"{p['name']}" + (f": {p['annotation']}" if p['annotation'] else "") + (f" = {p['default']}" if p['default'] else "")
                        for p in method["parameters"]
                    )
                    ret = f" -> {method['return_annotation']}" if method['return_annotation'] else ""
                    lines.append(f"- `{method['name']}({params}){ret}`")
                    if method.get("docstring"):
                        # Indent docstring
                        for line in method["docstring"].split("\n"):
                            lines.append(f"  {line}")
                lines.append("")
    
    return "\n".join(lines)


def main() -> int:
    """Main entry point for doc extractor."""
    parser = argparse.ArgumentParser(
        description="Extract documentation from brain_graph modules"
    )
    parser.add_argument(
        "tool",
        help="Tool name or module path (e.g., 'embedder' or 'brain_graph.pipeline.embedder')",
    )
    parser.add_argument(
        "--format",
        choices=["text", "json", "markdown"],
        default="text",
        help="Output format",
    )
    
    args = parser.parse_args()
    
    # Resolve tool name to module
    module_name = TOOL_MAP.get(args.tool, args.tool)
    
    # Extract documentation
    docs = extract_module_docs(module_name)
    
    # Format output
    if args.format == "json":
        print(json.dumps(docs, indent=2, ensure_ascii=False))
    elif args.format == "markdown":
        print(format_markdown(docs))
    else:  # text
        print(format_text(docs))
    
    return 0 if "error" not in docs else 1


if __name__ == "__main__":
    raise SystemExit(main())
