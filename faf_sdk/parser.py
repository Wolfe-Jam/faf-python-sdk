"""
Core FAF parser - YAML parsing with validation

Mirrors the TypeScript fix-once/yaml.ts implementation for cross-language compatibility.
"""

import yaml
from typing import Any, Dict, Optional, Union
from dataclasses import dataclass

from .types import FafData


class FafParseError(Exception):
    """Raised when FAF parsing fails"""
    pass


@dataclass
class FafFile:
    """
    Parsed FAF file with both raw and typed access

    Attributes:
        data: Typed FafData object with all sections
        raw: Raw dictionary from YAML parsing
        path: Optional file path if loaded from disk
    """
    data: FafData
    raw: Dict[str, Any]
    path: Optional[str] = None

    @property
    def project_name(self) -> str:
        """Quick access to project name"""
        return self.data.project.name

    @property
    def score(self) -> Optional[int]:
        """Quick access to AI score"""
        return self.data.ai_score

    @property
    def version(self) -> str:
        """Quick access to FAF version"""
        return self.data.faf_version


def parse(content: Union[str, None], path: Optional[str] = None) -> FafFile:
    """
    Parse FAF content from string

    Args:
        content: YAML string content of .faf file
        path: Optional file path for error messages

    Returns:
        FafFile object with parsed data

    Raises:
        FafParseError: If content is invalid

    Example:
        >>> content = open("project.faf").read()
        >>> faf = parse(content)
        >>> print(faf.project_name)
        'my-project'
    """
    # Handle null/empty content
    if content is None:
        raise FafParseError("Content is null or undefined")

    if not isinstance(content, str):
        raise FafParseError(f"Content must be string, got {type(content).__name__}")

    content = content.strip()
    if not content:
        raise FafParseError("Content is empty")

    # Parse YAML
    try:
        data = yaml.safe_load(content)
    except yaml.YAMLError as e:
        location = f" in {path}" if path else ""
        raise FafParseError(f"Invalid YAML syntax{location}: {e}")

    # Validate structure
    if data is None:
        raise FafParseError("YAML parsed to null - file may be empty or all comments")

    if not isinstance(data, dict):
        raise FafParseError(
            f"FAF must be a YAML object/dictionary, got {type(data).__name__}. "
            "Arrays and primitives are not valid FAF files."
        )

    # Convert to typed structure
    try:
        faf_data = FafData.from_dict(data)
    except Exception as e:
        raise FafParseError(f"Failed to parse FAF structure: {e}")

    return FafFile(
        data=faf_data,
        raw=data,
        path=path
    )


def parse_file(filepath: str) -> FafFile:
    """
    Parse FAF from file path

    Args:
        filepath: Path to .faf file

    Returns:
        FafFile object with parsed data

    Raises:
        FafParseError: If file cannot be read or parsed
        FileNotFoundError: If file doesn't exist

    Example:
        >>> faf = parse_file("project.faf")
        >>> print(faf.data.instant_context.tech_stack)
    """
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
    except FileNotFoundError:
        raise FileNotFoundError(f"FAF file not found: {filepath}")
    except IOError as e:
        raise FafParseError(f"Failed to read {filepath}: {e}")

    return parse(content, path=filepath)


def stringify(data: Union[Dict[str, Any], FafFile, FafData],
              default_flow_style: bool = False) -> str:
    """
    Convert FAF data back to YAML string

    Args:
        data: Dictionary, FafFile, or FafData to serialize
        default_flow_style: Use flow style for collections

    Returns:
        YAML string

    Example:
        >>> yaml_str = stringify(faf.raw)
        >>> with open("output.faf", "w") as f:
        ...     f.write(yaml_str)
    """
    if isinstance(data, FafFile):
        data = data.raw
    elif isinstance(data, FafData):
        data = data.raw

    return yaml.dump(
        data,
        default_flow_style=default_flow_style,
        allow_unicode=True,
        sort_keys=False,
        indent=2
    )


def get_field(faf: FafFile, *keys: str, default: Any = None) -> Any:
    """
    Safely get nested field from FAF raw data

    Args:
        faf: Parsed FafFile
        *keys: Path to field (e.g., "project", "name")
        default: Default value if not found

    Returns:
        Field value or default

    Example:
        >>> name = get_field(faf, "project", "name")
        >>> stack = get_field(faf, "stack", "frontend", default="None")
    """
    value = faf.raw
    for key in keys:
        if isinstance(value, dict):
            value = value.get(key)
        else:
            return default
        if value is None:
            return default
    return value
