# faf-sdk

Python SDK for **FAF (Foundational AI-context Format)** - the IANA-registered format for AI project context.

**Media Type:** `application/vnd.faf+yaml`

## Installation

```bash
pip install faf-sdk
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

## Why FAF?

Every AI conversation starts from zero. No memory of your project. No understanding of your stack. Just vibes.

FAF solves this with a single, IANA-registered file that gives AI instant project context:

- **One file, one read, full understanding**
- **19ms average execution**
- **Zero setup friction**
- **MIT licensed, works everywhere**

## Links

- **Spec:** [github.com/Wolfe-Jam/faf](https://github.com/Wolfe-Jam/faf)
- **Site:** [faf.one](https://faf.one)
- **MCP Server:** [claude-faf-mcp](https://github.com/modelcontextprotocol/servers/tree/main/src/faf)
- **IANA Registration:** `application/vnd.faf+yaml`

## License

MIT
