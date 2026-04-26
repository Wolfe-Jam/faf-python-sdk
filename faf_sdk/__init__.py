"""
faf-python-sdk — Persistent project context for Python.

Parse, validate, and score `.faf` files. The foundation other Python
FAF tools (gemini-faf-mcp, custom MCP servers, CI validators) build on.

IANA-registered media type: application/vnd.faf+yaml
Site: https://faf.one

Usage:
    from faf_sdk import parse_file, score_faf

    faf = parse_file("project.faf")
    print(faf.data.project.name)

    with open("project.faf") as f:
        result = score_faf(f.read())
    print(f"Score: {result.score}% {result.tier}")

FAF defines. MD instructs. AI codes.
"""

from .parser import parse, parse_file, stringify, FafFile
from .validator import validate, ValidationResult
from .mk4 import score_faf, Mk4Result, SlotState, LicenseTier
from .discovery import find_faf_file, find_project_root, load_fafignore
from .types import (
    FafData,
    ProjectInfo,
    StackInfo,
    InstantContext,
    ContextQuality,
    HumanContext,
    AIScoring
)

__version__ = "1.1.2"
__all__ = [
    # Parser
    "parse",
    "parse_file",
    "stringify",
    "FafFile",
    # Validator
    "validate",
    "ValidationResult",
    # Mk4 Scoring Engine
    "score_faf",
    "Mk4Result",
    "SlotState",
    "LicenseTier",
    # Discovery
    "find_faf_file",
    "find_project_root",
    "load_fafignore",
    # Types
    "FafData",
    "ProjectInfo",
    "StackInfo",
    "InstantContext",
    "ContextQuality",
    "HumanContext",
    "AIScoring",
]
