"""
FAF validation - check structure and completeness

Mirrors claude-faf-mcp/src/faf-core/commands/validate.ts
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Tuple, Union

from .parser import FafFile, parse


@dataclass
class ValidationResult:
    """
    Result of FAF validation

    Attributes:
        valid: True if no errors (warnings OK)
        errors: List of critical errors
        warnings: List of non-critical warnings
        score: Calculated completeness score (0-100)
    """
    valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    score: int = 0

    def __bool__(self) -> bool:
        return self.valid


def validate(faf: Union[FafFile, Dict[str, Any], str]) -> ValidationResult:
    """
    Validate FAF file structure and completeness

    Args:
        faf: FafFile, raw dict, or YAML string to validate

    Returns:
        ValidationResult with errors, warnings, and score

    Example:
        >>> result = validate(faf)
        >>> if not result.valid:
        ...     print("Errors:", result.errors)
        >>> print(f"Score: {result.score}%")
    """
    errors: List[str] = []
    warnings: List[str] = []

    # Parse if string
    if isinstance(faf, str):
        try:
            faf = parse(faf)
        except Exception as e:
            return ValidationResult(
                valid=False,
                errors=[f"Parse error: {e}"],
                score=0
            )

    # Get raw data
    if isinstance(faf, FafFile):
        data = faf.raw
    else:
        data = faf

    # Required fields
    if "faf_version" not in data:
        errors.append("Missing required field: faf_version")

    if "project" not in data:
        errors.append("Missing required field: project")
    else:
        project = data["project"]
        if isinstance(project, dict):
            if "name" not in project:
                errors.append("Missing required field: project.name")
        elif not isinstance(project, str):
            errors.append("project must be object or string")

    # Recommended sections
    if "instant_context" not in data:
        warnings.append("Missing recommended section: instant_context")
    else:
        ic = data["instant_context"]
        if isinstance(ic, dict):
            if "what_building" not in ic:
                warnings.append("Missing instant_context.what_building")
            if "tech_stack" not in ic:
                warnings.append("Missing instant_context.tech_stack")

    if "stack" not in data:
        warnings.append("Missing recommended section: stack")

    # Optional but useful
    if "human_context" not in data:
        warnings.append("Missing section: human_context (the 6 W's)")

    if "ai_instructions" not in data:
        warnings.append("Missing section: ai_instructions")

    # Type validations
    if "tags" in data and not isinstance(data["tags"], list):
        errors.append("tags must be an array")

    if "ai_score" in data:
        score_val = data["ai_score"]
        if isinstance(score_val, str):
            if not score_val.endswith("%"):
                warnings.append("ai_score should end with % (e.g., '85%')")
        elif not isinstance(score_val, (int, float)):
            errors.append("ai_score must be number or percentage string")

    # Calculate completeness score
    score = _calculate_score(data)

    return ValidationResult(
        valid=len(errors) == 0,
        errors=errors,
        warnings=warnings,
        score=score
    )


def _calculate_score(data: Dict[str, Any]) -> int:
    """
    Calculate completeness score based on filled sections

    Scoring breakdown:
    - Required fields (30 points)
    - Core sections (40 points)
    - Extended sections (30 points)
    """
    score = 0
    max_score = 100

    # Required fields (30 points)
    if "faf_version" in data:
        score += 10
    if "project" in data:
        score += 10
        project = data["project"]
        if isinstance(project, dict):
            if project.get("name"):
                score += 5
            if project.get("goal"):
                score += 5

    # Core sections (40 points)
    if "instant_context" in data:
        ic = data["instant_context"]
        score += 5
        if isinstance(ic, dict):
            if ic.get("what_building"):
                score += 5
            if ic.get("tech_stack"):
                score += 5
            if ic.get("key_files"):
                score += 5

    if "stack" in data:
        score += 10
        stack = data["stack"]
        if isinstance(stack, dict) and len(stack) > 2:
            score += 5

    if "context_quality" in data:
        score += 5

    # Extended sections (30 points)
    if "human_context" in data:
        score += 10

    if "ai_instructions" in data:
        score += 5

    if "preferences" in data:
        score += 5

    if "state" in data:
        score += 5

    if data.get("tags"):
        score += 5

    return min(score, max_score)


def validate_quick(content: str) -> Tuple[bool, str]:
    """
    Quick validation returning simple pass/fail with message

    Args:
        content: YAML string to validate

    Returns:
        Tuple of (valid, message)

    Example:
        >>> valid, msg = validate_quick(yaml_content)
        >>> if not valid:
        ...     print(f"Invalid: {msg}")
    """
    result = validate(content)

    if not result.valid:
        return False, f"Invalid: {'; '.join(result.errors)}"
    elif result.warnings:
        return True, f"Valid with warnings: {'; '.join(result.warnings[:2])}"
    else:
        return True, f"Valid (score: {result.score}%)"
