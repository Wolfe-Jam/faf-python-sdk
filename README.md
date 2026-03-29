# faf-python-sdk

> **Python SDK for FAF** — parse, validate, and score `.faf` files with the Mk4 Championship Scoring Engine. The foundation for [gemini-faf-mcp](https://pypi.org/project/gemini-faf-mcp/).

[![PyPI](https://img.shields.io/pypi/v/faf-python-sdk?style=for-the-badge&logo=pypi&logoColor=white)](https://pypi.org/project/faf-python-sdk/)
[![Downloads](https://img.shields.io/pypi/dm/faf-python-sdk?style=for-the-badge&color=blue)](https://pypi.org/project/faf-python-sdk/)
[![Tests](https://img.shields.io/badge/tests-175%20passing-brightgreen?style=for-the-badge)](https://github.com/Wolfe-Jam/faf-python-sdk)
[![IANA](https://img.shields.io/badge/IANA-registered-informational?style=for-the-badge)](https://www.iana.org/assignments/media-types/application/vnd.faf+yaml)

**Media Type:** `application/vnd.faf+yaml` (IANA registered)

## What's New in v1.1.0

**Mk4 Championship Scoring Engine** — the same 33-slot scoring algorithm used by the Rust compiler and TypeScript CLI, now in Python. Same slots, same formula, same scores. Every FAF tool in every language now agrees on what 100% means.

- `score_faf()` — Mk4 scoring with 21-slot Base or 33-slot Enterprise tiers
- 100% parity with `faf-wasm-sdk` (Rust) and `faf-cli` (TypeScript)
- 3 crash bugs fixed (malformed YAML, null project fields)
- 175 tests including 88 WJTTC championship-grade tests (concurrency, adversarial input, security)

**Why this matters:** If you're building on FAF in Python — MCP servers, Gemini extensions, CI pipelines — your scores now match every other FAF tool exactly. No more "it scored 85% in the CLI but 60% in Python." One engine, one truth.

## Installation

```bash
pip install faf-python-sdk
```

## Quick Start

```python
from faf_sdk import parse_file, score_faf

# Parse a .faf file
faf = parse_file("project.faf")
print(f"Project: {faf.project_name}")

# Score it with the Mk4 engine
with open("project.faf") as f:
    result = score_faf(f.read())

print(f"Score: {result.score}% {result.tier}")
print(f"Slots: {result.populated}/{result.total} populated")
```

## Mk4 Scoring

The Mk4 engine scores `.faf` files by checking 21 universal slots (project metadata, human context, tech stack). Each slot is **Populated**, **Empty**, or **Slotignored**. The score is the percentage of active slots that are populated.

```python
from faf_sdk import score_faf, LicenseTier

# Base scoring (21 slots)
result = score_faf(yaml_content)
print(result.score)      # 0-100
print(result.tier)       # Trophy/Gold/Silver/Bronze/Green/Yellow/Red
print(result.populated)  # slots with real data
print(result.active)     # total minus slotignored
print(result.slots)      # per-slot breakdown

# Enterprise scoring (33 slots — adds monorepo/infra)
result = score_faf(yaml_content, LicenseTier.ENTERPRISE)
```

**Placeholder rejection:** Values like `"null"`, `"unknown"`, `"n/a"`, `"Describe your project goal"` are detected and scored as Empty — not Populated.

**Slotignored:** Set any slot to `slotignored` to exclude it from scoring. A backend-only project can mark `frontend: slotignored` and still reach 100%.

## Parsing

```python
from faf_sdk import parse, parse_file, stringify

# Parse from string or file
faf = parse(yaml_content)
faf = parse_file("project.faf")

# Typed access
print(faf.data.project.name)
print(faf.data.project.goal)
print(faf.data.stack.backend)
print(faf.data.human_context.who)

# Raw dict access
print(faf.raw["project"]["goal"])

# Convert back to YAML
yaml_str = stringify(faf)
```

## Validation

```python
from faf_sdk import validate

result = validate(faf)

if result.valid:
    print(f"Valid! Score: {result.score}%")
else:
    print("Errors:", result.errors)

print("Warnings:", result.warnings)
```

## File Discovery

```python
from faf_sdk import find_faf_file, find_project_root

# Find project.faf (walks up directory tree)
path = find_faf_file("/path/to/src")

# Find project root by markers (package.json, pyproject.toml, .git, etc.)
root = find_project_root()
```

## API Reference

| Function | Returns | Description |
|----------|---------|-------------|
| `score_faf(yaml, tier?)` | `Mk4Result` | Mk4 score (21 or 33 slots) |
| `parse(content)` | `FafFile` | Parse YAML string |
| `parse_file(path)` | `FafFile` | Parse from file path |
| `validate(faf)` | `ValidationResult` | Structure validation + warnings |
| `stringify(data)` | `str` | Convert back to YAML |
| `find_faf_file(dir?)` | `str \| None` | Find project.faf in tree |
| `find_project_root(dir?)` | `str \| None` | Find project root |

## FAF Ecosystem

| Package | Platform | Registry |
|---------|----------|----------|
| **faf-python-sdk** | **Python foundation** | **PyPI** |
| [gemini-faf-mcp](https://pypi.org/project/gemini-faf-mcp/) | Google Gemini | PyPI |
| [claude-faf-mcp](https://npmjs.com/package/claude-faf-mcp) | Anthropic | npm + MCP #2759 |
| [grok-faf-mcp](https://npmjs.com/package/grok-faf-mcp) | xAI | npm |
| [faf-cli](https://npmjs.com/package/faf-cli) | CLI | npm |

## Links

- **Site:** [faf.one](https://faf.one)
- **IANA Registration:** [application/vnd.faf+yaml](https://www.iana.org/assignments/media-types/application/vnd.faf+yaml)
- **Gemini MCP:** [gemini-faf-mcp](https://pypi.org/project/gemini-faf-mcp/)

## License

MIT
