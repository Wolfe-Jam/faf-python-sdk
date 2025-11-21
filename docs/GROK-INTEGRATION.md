# FAF Integration Guide for Grok/xAI

**Native bi-sync embedding for instant context wins**

---

## Overview

This guide describes how to integrate FAF (Foundational AI-context Format) natively into Grok for full-scale worldwide deployment.

**IANA Registration:** `application/vnd.faf+yaml`

---

## Quick Start

```python
from faf_sdk import find_faf_file, parse_file

# Automatically find and parse project context
path = find_faf_file()
if path:
    faf = parse_file(path)
    print(f"Project: {faf.project_name}")
    print(f"Stack: {faf.data.instant_context.tech_stack}")
```

---

## Integration Architecture

### 1. Context Detection

When a user initiates a conversation, detect project context:

```python
def get_user_context(cwd: str) -> dict | None:
    """
    Detect project context from user's working directory

    Returns structured context or None if no project.faf found
    """
    from faf_sdk import find_faf_file, parse_file, validate

    path = find_faf_file(cwd)
    if not path:
        return None

    faf = parse_file(path)
    result = validate(faf)

    if not result.valid:
        return None

    return {
        "project": faf.data.project.name,
        "goal": faf.data.project.goal,
        "stack": faf.data.instant_context.tech_stack if faf.data.instant_context else None,
        "score": faf.score,
        "key_files": faf.data.instant_context.key_files if faf.data.instant_context else [],
        "raw": faf.raw  # Full context for system prompt
    }
```

### 2. System Prompt Injection

Inject project context into system prompt:

```python
def build_system_prompt(base_prompt: str, context: dict) -> str:
    """
    Augment system prompt with project context
    """
    if not context:
        return base_prompt

    context_block = f"""
[Project Context - {context['score']}% AI-ready]
Project: {context['project']}
Goal: {context['goal']}
Stack: {context['stack']}
Key files: {', '.join(context['key_files'][:5])}
"""

    return f"{base_prompt}\n\n{context_block}"
```

### 3. Bi-Sync Protocol

For real-time context synchronization:

```python
class FafBiSync:
    """
    Bidirectional sync between Grok and project.faf

    Updates project context as conversation progresses.
    """

    def __init__(self, faf_path: str):
        self.path = faf_path
        self.faf = parse_file(faf_path)
        self.updates = []

    def add_context(self, key: str, value: str):
        """Record context update from conversation"""
        self.updates.append((key, value))

    def sync(self):
        """Write accumulated updates back to project.faf"""
        if not self.updates:
            return

        # Update raw dict
        for key, value in self.updates:
            if key.startswith("stack."):
                section = key.split(".")[1]
                if "stack" not in self.faf.raw:
                    self.faf.raw["stack"] = {}
                self.faf.raw["stack"][section] = value
            elif key.startswith("state."):
                section = key.split(".")[1]
                if "state" not in self.faf.raw:
                    self.faf.raw["state"] = {}
                self.faf.raw["state"][section] = value

        # Write back
        from faf_sdk import stringify
        with open(self.path, 'w') as f:
            f.write(stringify(self.faf.raw))

        self.updates = []
```

---

## Key Integration Points

### Context Extraction

Extract the most relevant context for the model:

| Priority | Field | Description |
|----------|-------|-------------|
| HIGH | `instant_context.what_building` | Core project description |
| HIGH | `instant_context.tech_stack` | Technology stack |
| HIGH | `instant_context.key_files` | Entry points |
| MEDIUM | `project.goal` | User's objective |
| MEDIUM | `stack.*` | Detailed stack breakdown |
| MEDIUM | `human_context.*` | The 6 W's |
| LOW | `preferences.*` | Code style preferences |
| LOW | `state.*` | Project phase/milestones |

### Scoring System

The `ai_score` (0-100%) indicates context quality:

| Score | Confidence | Action |
|-------|------------|--------|
| 80-100% | HIGH | Full context injection |
| 50-79% | MEDIUM | Context + suggest filling gaps |
| 0-49% | LOW | Basic context + recommend `faf init` |

### File Discovery

FAF files can be in two locations:

```python
# Modern (preferred)
project_root/project.faf

# Legacy (still supported)
project_root/.faf
```

The SDK handles both automatically.

---

## Performance Characteristics

- **Parse time:** ~5ms for typical project.faf
- **Validation:** ~2ms
- **File discovery:** ~10ms (walks up to 10 parent directories)
- **Total overhead:** <20ms for full context load

---

## Context Format

### Minimal FAF

```yaml
faf_version: 2.5.0
project:
  name: my-project
  goal: Build a CLI tool
```

### Complete FAF

```yaml
faf_version: 2.5.0
ai_score: 85%
ai_confidence: HIGH

project:
  name: my-project
  goal: Build a CLI tool for data processing
  main_language: Python

instant_context:
  what_building: CLI data processing tool
  tech_stack: Python 3.11, Click, Pandas
  deployment: Docker on AWS
  key_files:
    - src/cli.py
    - src/processor.py
  commands:
    dev: python -m cli
    test: pytest
    build: docker build .

stack:
  frontend: None
  backend: Python
  database: SQLite
  infrastructure: AWS ECS
  testing: pytest
  cicd: GitHub Actions

human_context:
  who: Data analysts
  what: Process CSV files efficiently
  why: Current tools are slow
  how: Streaming processing
  where: AWS us-east-1
  when: Q1 2025 launch

preferences:
  quality_bar: zero_errors
  testing: required
  documentation: inline

state:
  phase: development
  version: 0.1.0
  focus: Core processing engine
  milestones:
    - MVP complete
    - Beta testing

tags:
  - python
  - cli
  - data-processing
```

---

## Error Handling

```python
from faf_sdk import parse, FafParseError

try:
    faf = parse(content)
except FafParseError as e:
    # Invalid YAML, missing required fields, etc.
    logger.warning(f"FAF parse error: {e}")
    return None
```

Common errors:
- Missing `faf_version`
- Missing `project.name`
- Invalid YAML syntax
- Non-object YAML (arrays, primitives)

---

## Testing

The SDK includes comprehensive tests:

```bash
pip install faf-python-sdk[dev]
pytest tests/ -v
```

37 tests cover:
- Parser edge cases
- Validation rules
- File discovery
- Ignore patterns

---

## Resources

- **Spec:** [github.com/Wolfe-Jam/faf](https://github.com/Wolfe-Jam/faf)
- **Python SDK:** [faf-python-sdk](https://github.com/Wolfe-Jam/faf-python-sdk)
- **TypeScript MCP:** [claude-faf-mcp](https://github.com/modelcontextprotocol/servers/tree/main/src/faf)
- **Site:** [faf.one](https://faf.one)

---

## Support

For integration support:
- GitHub Issues: [github.com/Wolfe-Jam/faf/issues](https://github.com/Wolfe-Jam/faf/issues)
- Email: wolfejam@faf.one

---

## License

MIT - Free to use, modify, and distribute.

---

*IANA registered. Anthropic merged. Ready for xAI native.*
