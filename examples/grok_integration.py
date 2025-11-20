#!/usr/bin/env python3
"""
Grok/xAI Integration Example

Shows how to use FAF SDK for native AI context integration.
This is what xAI engineers would use for bi-sync embedding.
"""

import json
from typing import Any, Dict, Optional
from faf_sdk import (
    parse,
    parse_file,
    validate,
    find_faf_file,
    find_project_root,
    load_fafignore,
    list_project_files
)


def load_project_context(project_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Load complete project context for AI processing

    This function demonstrates the full flow:
    1. Find project.faf
    2. Parse and validate
    3. Extract key context for AI consumption
    4. Return structured data ready for embedding

    Args:
        project_path: Optional starting directory

    Returns:
        Structured context dict for AI
    """
    # Find project.faf
    faf_path = find_faf_file(project_path)
    if not faf_path:
        return {
            "error": "No project.faf found",
            "suggestion": "Run 'faf init' to create one"
        }

    # Parse
    faf = parse_file(faf_path)

    # Validate
    result = validate(faf)
    if not result.valid:
        return {
            "error": "Invalid FAF file",
            "details": result.errors
        }

    # Build context structure optimized for AI
    context = {
        "meta": {
            "faf_version": faf.version,
            "score": faf.score,
            "confidence": faf.data.ai_confidence,
            "source": faf_path
        },
        "project": {
            "name": faf.data.project.name,
            "goal": faf.data.project.goal,
            "language": faf.data.project.main_language
        }
    }

    # Add instant context (most important for AI)
    if faf.data.instant_context:
        ic = faf.data.instant_context
        context["instant"] = {
            "what": ic.what_building,
            "stack": ic.tech_stack,
            "deployment": ic.deployment,
            "key_files": ic.key_files,
            "commands": ic.commands
        }

    # Add stack details
    if faf.data.stack:
        s = faf.data.stack
        context["stack"] = {
            "frontend": s.frontend,
            "backend": s.backend,
            "database": s.database,
            "infrastructure": s.infrastructure,
            "testing": s.testing,
            "cicd": s.cicd
        }

    # Add human context (the 6 W's)
    if faf.data.human_context:
        hc = faf.data.human_context
        context["human"] = {
            "who": hc.who,
            "what": hc.what,
            "why": hc.why,
            "how": hc.how,
            "where": hc.where,
            "when": hc.when
        }

    # Add tags for quick matching
    context["tags"] = faf.data.tags

    return context


def get_project_files_context(project_path: Optional[str] = None,
                                extensions: Optional[list] = None) -> Dict[str, Any]:
    """
    Get project file structure respecting .fafignore

    Useful for AI to understand project structure without
    including node_modules, .env, etc.

    Args:
        project_path: Optional project root
        extensions: Filter by extensions (e.g., [".py", ".ts"])

    Returns:
        File structure context
    """
    root = find_project_root(project_path)
    if not root:
        return {"error": "No project root found"}

    patterns = load_fafignore(root)
    files = list_project_files(root, patterns, extensions)

    return {
        "root": root,
        "total_files": len(files),
        "files": files[:100],  # Limit for context window
        "truncated": len(files) > 100
    }


def create_grok_context(project_path: Optional[str] = None) -> str:
    """
    Create formatted context string for Grok consumption

    This is the bi-sync native embedding format.
    Returns a structured string optimized for LLM consumption.

    Args:
        project_path: Optional project path

    Returns:
        Formatted context string
    """
    context = load_project_context(project_path)

    if "error" in context:
        return f"[FAF Error] {context['error']}"

    # Build formatted string
    lines = [
        f"[FAF Context - {context['meta']['score']}% AI-ready]",
        "",
        f"Project: {context['project']['name']}",
        f"Goal: {context['project']['goal']}",
        ""
    ]

    if "instant" in context:
        ic = context["instant"]
        lines.extend([
            f"Building: {ic['what']}",
            f"Stack: {ic['stack']}",
            ""
        ])

        if ic["key_files"]:
            lines.append("Key files:")
            for f in ic["key_files"]:
                lines.append(f"  - {f}")
            lines.append("")

    if "stack" in context:
        s = context["stack"]
        stack_items = [f"{k}: {v}" for k, v in s.items() if v and v != "None"]
        if stack_items:
            lines.append("Stack details:")
            for item in stack_items:
                lines.append(f"  {item}")
            lines.append("")

    if "human" in context:
        h = context["human"]
        lines.extend([
            "Context:",
            f"  Who: {h['who']}",
            f"  What: {h['what']}",
            f"  Why: {h['why']}",
            ""
        ])

    if context.get("tags"):
        lines.append(f"Tags: {', '.join(context['tags'])}")

    return "\n".join(lines)


# Example usage for xAI integration
if __name__ == "__main__":
    print("=" * 50)
    print("FAF SDK - Grok Integration Demo")
    print("=" * 50)

    # Try to find a real project.faf
    path = find_faf_file()

    if path:
        print(f"\nFound: {path}\n")

        # Load structured context
        context = load_project_context()
        print("Structured context:")
        print(json.dumps(context, indent=2, default=str))

        print("\n" + "=" * 50)
        print("\nFormatted for Grok:")
        print(create_grok_context())

    else:
        print("\nNo project.faf found in current directory tree.")
        print("Run 'faf init' in a project to create one.")
        print("\nDemo with example data:")

        # Demo with example
        from basic_usage import EXAMPLE_FAF

        faf = parse(EXAMPLE_FAF)
        print(f"\nProject: {faf.project_name}")
        print(f"Score: {faf.score}%")
        print(f"Stack: {faf.data.instant_context.tech_stack}")
