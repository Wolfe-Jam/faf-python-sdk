# faf-python-sdk

> **Python SDK for FAF** — parse, validate, and score `.faf` files. The foundation for [gemini-faf-mcp](https://pypi.org/project/gemini-faf-mcp/).

[![PyPI](https://img.shields.io/pypi/v/faf-python-sdk?style=for-the-badge&logo=pypi&logoColor=white)](https://pypi.org/project/faf-python-sdk/)
[![Downloads](https://img.shields.io/pypi/dm/faf-python-sdk?style=for-the-badge&color=blue)](https://pypi.org/project/faf-python-sdk/)
[![IANA](https://img.shields.io/badge/IANA-registered-informational?style=for-the-badge)](https://www.iana.org/assignments/media-types/application/vnd.faf+yaml)

**Media Type:** `application/vnd.faf+yaml`

## Installation

```bash
pip install faf-python-sdk
```

## Quick Start

```python
from faf_sdk import parse, validate, find_faf_file

# Find and parse project.faf
path = find_faf_file()
if path:
    with open(path) as f:
        faf = parse(f.read())

    print(f"Project: {faf.project_name}")
    print(f"Score: {faf.score}%")
    print(f"Stack: {faf.data.instant_context.tech_stack}")
```

## Core Functions

### Parsing

```python
from faf_sdk import parse, parse_file, stringify

# Parse from string
faf = parse(yaml_content)

# Parse from file
faf = parse_file("project.faf")

# Access typed data
print(faf.data.project.name)
print(faf.data.instant_context.what_building)
print(faf.data.stack.frontend)

# Access raw dict
print(faf.raw["project"]["goal"])

# Convert back to YAML
yaml_str = stringify(faf)
```

### Validation

```python
from faf_sdk import validate

result = validate(faf)

if result.valid:
    print(f"Valid! Score: {result.score}%")
else:
    print("Errors:", result.errors)

print("Warnings:", result.warnings)
```

### File Discovery

```python
from faf_sdk import find_faf_file, find_project_root, load_fafignore

# Find project.faf (walks up directory tree)
path = find_faf_file("/path/to/src")

# Find project root
root = find_project_root()

# Load ignore patterns
patterns = load_fafignore(root)
```

## FAF File Structure

A `.faf` file provides instant project context for AI:

```yaml
faf_version: 2.5.0
ai_score: 85%
ai_confidence: HIGH

project:
  name: my-project
  goal: Build a CLI tool for data processing

instant_context:
  what_building: CLI data processing tool
  tech_stack: Python 3.11, Click, Pandas
  key_files:
    - src/cli.py
    - src/processor.py

stack:
  frontend: None
  backend: Python
  database: SQLite
  infrastructure: Docker

human_context:
  who: Data analysts
  what: Process CSV files efficiently
  why: Current tools are slow
```

## Type Definitions

The SDK provides typed access to all FAF sections:

```python
from faf_sdk import (
    FafData,
    ProjectInfo,
    StackInfo,
    InstantContext,
    ContextQuality,
    HumanContext
)

# All fields are optional except faf_version and project.name
faf = parse(content)

# Typed access
project: ProjectInfo = faf.data.project
stack: StackInfo = faf.data.stack
context: InstantContext = faf.data.instant_context
```

## Integration Example

```python
from faf_sdk import find_faf_file, parse_file, validate

def get_project_context():
    """Load project context for AI processing"""
    path = find_faf_file()
    if not path:
        return None

    faf = parse_file(path)
    result = validate(faf)

    if not result.valid:
        raise ValueError(f"Invalid FAF: {result.errors}")

    return {
        "name": faf.data.project.name,
        "goal": faf.data.project.goal,
        "stack": faf.data.instant_context.tech_stack if faf.data.instant_context else None,
        "key_files": faf.data.instant_context.key_files if faf.data.instant_context else [],
        "score": faf.score,
    }

# Use in AI context
context = get_project_context()
if context:
    print(f"Working on: {context['name']}")
    print(f"Goal: {context['goal']}")
    print(f"Tech: {context['stack']}")
```

## FAF Ecosystem

| Package | Platform | Registry |
|---------|----------|----------|
| [gemini-faf-mcp](https://pypi.org/project/gemini-faf-mcp/) | Google Gemini | PyPI |
| [claude-faf-mcp](https://npmjs.com/package/claude-faf-mcp) | Anthropic | npm + MCP #2759 |
| [grok-faf-mcp](https://npmjs.com/package/grok-faf-mcp) | xAI | npm |
| [faf-mcp](https://npmjs.com/package/faf-mcp) | Universal | npm |
| [faf-cli](https://npmjs.com/package/faf-cli) | CLI | npm |

## Links

- **Site:** [faf.one](https://faf.one)
- **Gemini MCP:** [gemini-faf-mcp](https://pypi.org/project/gemini-faf-mcp/)
- **IANA Registration:** [application/vnd.faf+yaml](https://www.iana.org/assignments/media-types/application/vnd.faf+yaml)
- **Privacy:** [faf.one/privacy](https://faf.one/privacy)

If `faf-python-sdk` has been useful, consider starring the repo — it helps others find it.

## License

MIT
