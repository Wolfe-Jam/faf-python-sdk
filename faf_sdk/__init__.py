"""
FAF Python SDK - Foundational AI-context Format

IANA-registered: application/vnd.faf+yaml
https://faf.one

Usage:
    from faf_sdk import parse, validate, find_faf_file, FafFile

    # Parse a .faf file
    faf = parse(content)

    # Validate structure
    errors, warnings = validate(faf)

    # Find project.faf in directory tree
    path = find_faf_file("/path/to/project")
"""

from .parser import parse, parse_file, stringify, FafFile
from .validator import validate, ValidationResult
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

__version__ = "1.0.0"
__all__ = [
    # Parser
    "parse",
    "parse_file",
    "stringify",
    "FafFile",
    # Validator
    "validate",
    "ValidationResult",
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
