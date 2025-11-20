# FAF Technical Specification for Native Integration

**For xAI/Grok Engineering Teams**

---

## 1. Tokenization Analysis

### Token Efficiency

FAF is designed for minimal context window consumption while maximizing information density.

#### Token Counts by Section (GPT-4 tokenizer)

| Section | Typical Tokens | Priority | Parallel-Safe |
|---------|---------------|----------|---------------|
| `faf_version` | 5-10 | P0 | Yes |
| `project` (minimal) | 20-40 | P0 | Yes |
| `instant_context` | 100-200 | P0 | Yes |
| `stack` | 50-100 | P1 | Yes |
| `human_context` | 80-150 | P1 | Yes |
| `preferences` | 30-60 | P2 | Yes |
| `state` | 40-80 | P2 | Yes |
| `tags` | 20-50 | P2 | Yes |
| **Total (full)** | **400-800** | - | - |

#### Optimization: Each section is independently parseable

```python
# Parallel inference friendly - sections have no cross-dependencies
sections = yaml.safe_load(content)

# Can process in parallel:
instant_task = process_instant_context(sections.get('instant_context'))
stack_task = process_stack(sections.get('stack'))
human_task = process_human_context(sections.get('human_context'))

# No blocking, no ordering required
```

### Token Density Comparison

| Format | Typical Tokens | Structured | AI-Ready |
|--------|---------------|------------|----------|
| Raw README.md | 1500-3000 | No | No |
| package.json | 200-500 | Partial | No |
| .env + comments | 100-300 | No | No |
| **project.faf** | **400-800** | **Yes** | **Yes** |

**FAF delivers 3-5x better token efficiency than raw files.**

---

## 2. Compression Levels

For adaptive compression, FAF supports three detail levels:

### Level 1: Minimal (~150 tokens)

Maximum compression for constrained contexts:

```yaml
faf_version: 2.5.0
project:
  name: my-app
  goal: Build a CLI tool
instant_context:
  tech_stack: Python 3.11, Click, SQLite
```

**Use case:** Quick context injection, small models, rate-limited APIs

### Level 2: Standard (~400 tokens)

Balanced compression for typical use:

```yaml
faf_version: 2.5.0
ai_score: 75%
project:
  name: my-app
  goal: Build a CLI tool for data processing
instant_context:
  what_building: CLI data processing tool
  tech_stack: Python 3.11, Click, Pandas
  key_files:
    - src/cli.py
    - src/processor.py
stack:
  backend: Python
  database: SQLite
```

**Use case:** Default for most interactions, good balance

### Level 3: Full (~800 tokens)

Complete context for complex tasks:

```yaml
# All sections included
faf_version: 2.5.0
ai_score: 85%
ai_confidence: HIGH
project: {...}
instant_context: {...}
stack: {...}
human_context: {...}
preferences: {...}
state: {...}
tags: [...]
```

**Use case:** Complex multi-turn conversations, detailed planning

### Compression Algorithm

```python
def compress_faf(faf: dict, level: int = 2) -> dict:
    """
    Compress FAF to specified level

    Level 1: project + instant_context.tech_stack only
    Level 2: + stack + key_files
    Level 3: Full content
    """
    result = {
        'faf_version': faf.get('faf_version'),
        'project': {
            'name': faf['project']['name'],
            'goal': faf['project'].get('goal')
        }
    }

    if level >= 1:
        if 'instant_context' in faf:
            result['instant_context'] = {
                'tech_stack': faf['instant_context'].get('tech_stack')
            }

    if level >= 2:
        if 'instant_context' in faf:
            result['instant_context']['what_building'] = faf['instant_context'].get('what_building')
            result['instant_context']['key_files'] = faf['instant_context'].get('key_files', [])[:5]
        if 'stack' in faf:
            result['stack'] = faf['stack']

    if level >= 3:
        # Include everything
        result = faf

    return result
```

---

## 3. Bi-Sync Streaming Protocol

For real-time context synchronization between Grok and user projects.

### Protocol Overview

```
┌─────────┐                    ┌─────────┐
│  Grok   │ ◄──── bi-sync ────► │  User   │
│ Context │                    │ project │
└─────────┘                    └─────────┘
```

### Message Format

```json
{
  "version": "1.0",
  "type": "sync",
  "timestamp": "2025-11-20T17:30:00.000Z",
  "operations": [
    {
      "op": "update",
      "path": "state.phase",
      "value": "testing"
    },
    {
      "op": "append",
      "path": "state.milestones",
      "value": "MVP complete"
    }
  ]
}
```

### Operation Types

| Op | Description | Example |
|----|-------------|---------|
| `update` | Replace value | `{"op": "update", "path": "state.focus", "value": "Performance"}` |
| `append` | Add to array | `{"op": "append", "path": "tags", "value": "optimized"}` |
| `remove` | Delete field | `{"op": "remove", "path": "state.milestones", "index": 0}` |
| `merge` | Merge object | `{"op": "merge", "path": "stack", "value": {"testing": "jest"}}` |

### Sync Directions

**Grok → User (suggestions):**
```json
{
  "type": "suggestion",
  "operations": [
    {
      "op": "update",
      "path": "stack.testing",
      "value": "pytest",
      "reason": "Detected test files using pytest conventions"
    }
  ]
}
```

**User → Grok (updates):**
```json
{
  "type": "sync",
  "operations": [
    {
      "op": "update",
      "path": "state.phase",
      "value": "production"
    }
  ]
}
```

### Conflict Resolution

When both sides update the same field:

1. **Timestamp wins:** Most recent update takes precedence
2. **User priority:** User changes override Grok suggestions
3. **Merge arrays:** Append operations merge, don't replace

---

## 4. Field Priority Matrix

For parallel inference optimization:

### P0 - Critical (always load first)

| Field | Reason |
|-------|--------|
| `project.name` | Core identity |
| `project.goal` | User intent |
| `instant_context.what_building` | Primary context |
| `instant_context.tech_stack` | Technical foundation |

### P1 - Important (load in parallel)

| Field | Reason |
|-------|--------|
| `stack.*` | Technical details |
| `instant_context.key_files` | Entry points |
| `human_context.what` | Problem statement |
| `human_context.why` | Motivation |

### P2 - Context (load if tokens allow)

| Field | Reason |
|-------|--------|
| `preferences.*` | Code style |
| `state.*` | Project phase |
| `tags` | Quick matching |
| `human_context.who/where/when` | Full context |

### Parallel Loading Strategy

```python
import asyncio

async def load_faf_parallel(faf: dict) -> dict:
    """
    Load FAF sections in parallel by priority
    """
    context = {}

    # P0 - Always load (blocking)
    context['identity'] = {
        'name': faf['project']['name'],
        'goal': faf['project'].get('goal'),
        'what': faf.get('instant_context', {}).get('what_building'),
        'stack': faf.get('instant_context', {}).get('tech_stack')
    }

    # P1 - Load in parallel
    p1_tasks = [
        process_stack(faf.get('stack')),
        process_key_files(faf.get('instant_context', {}).get('key_files')),
        process_human_context(faf.get('human_context'))
    ]
    p1_results = await asyncio.gather(*p1_tasks)
    context.update(merge_results(p1_results))

    # P2 - Load if budget allows
    if token_budget_remaining() > 200:
        p2_results = await load_p2_sections(faf)
        context.update(p2_results)

    return context
```

---

## 5. Benchmarks

### Parse Performance

| Operation | FAF SDK | JSON.parse | YAML.parse |
|-----------|---------|------------|------------|
| Parse (1KB) | 2.85ms | 0.1ms | 3.2ms |
| Validate | 0.01ms | N/A | N/A |
| Stringify | 0.76ms | 0.05ms | 2.1ms |

**Note:** FAF uses YAML parsing + validation. Pure parse time is competitive with generic YAML parsers, but adds structured validation.

### Context Quality

| Metric | Raw Files | FAF |
|--------|-----------|-----|
| Structured | No | Yes |
| Typed | No | Yes |
| Validated | No | Yes |
| Scorable | No | Yes (0-100%) |
| Versionable | No | Yes |

### Token Efficiency (Real Projects)

| Project | README tokens | package.json | project.faf | Savings |
|---------|--------------|--------------|-------------|---------|
| Small CLI | 800 | 150 | 350 | 63% |
| Web App | 2400 | 400 | 600 | 79% |
| Monorepo | 5000 | 800 | 900 | 85% |

---

## 6. Security Considerations

### What FAF Contains

- Project metadata (public)
- Technology stack (public)
- File paths (semi-public)
- Development preferences (public)

### What FAF Should NOT Contain

- API keys or secrets
- Credentials
- Personal data
- Internal URLs
- Database passwords

### Validation Recommendations

```python
def security_check(faf: dict) -> list[str]:
    """
    Check for potential security issues
    """
    warnings = []

    # Check for common secret patterns
    yaml_str = yaml.dump(faf)

    patterns = [
        r'(?i)(api[_-]?key|secret|password|token)\s*[:=]\s*\S+',
        r'(?i)bearer\s+[a-zA-Z0-9-_]+',
        r'sk-[a-zA-Z0-9]{32,}',  # OpenAI keys
        r'ghp_[a-zA-Z0-9]{36}',  # GitHub tokens
    ]

    for pattern in patterns:
        if re.search(pattern, yaml_str):
            warnings.append(f"Potential secret detected: {pattern}")

    return warnings
```

---

## 7. Implementation Recommendations

### For Grok Integration

1. **Initial Load:**
   - Detect `project.faf` in user's working directory
   - Parse with Python SDK
   - Validate structure
   - Compress to appropriate level

2. **Context Injection:**
   - Inject P0 fields into system prompt
   - Load P1/P2 based on conversation needs
   - Update context as conversation evolves

3. **Bi-Sync:**
   - Track context changes during conversation
   - Suggest updates to user's project.faf
   - Sync on user approval

4. **Caching:**
   - Cache parsed FAF per session
   - Invalidate on file change
   - Use file hash for change detection

### Performance Targets

| Metric | Target | Achieved |
|--------|--------|----------|
| Parse time | <5ms | 2.85ms ✓ |
| Validate time | <1ms | 0.01ms ✓ |
| Memory per FAF | <1MB | ~50KB ✓ |
| Concurrent parses | 100+ | 100 threads ✓ |

---

## 8. API Reference

### Python SDK

```python
from faf_sdk import parse, validate, find_faf_file, stringify

# Find and load
path = find_faf_file(cwd)
faf = parse_file(path)

# Access
print(faf.project_name)
print(faf.data.instant_context.tech_stack)
print(faf.score)

# Validate
result = validate(faf)
if result.valid:
    print(f"Score: {result.score}%")

# Modify and save
faf.raw['state']['phase'] = 'production'
with open(path, 'w') as f:
    f.write(stringify(faf.raw))
```

### Type Definitions

See `faf_sdk/types.py` for complete TypedDict definitions.

---

## 9. Resources

- **IANA Registration:** `application/vnd.faf+yaml`
- **Spec:** [github.com/Wolfe-Jam/faf](https://github.com/Wolfe-Jam/faf)
- **Python SDK:** This package
- **TypeScript MCP:** [claude-faf-mcp](https://github.com/modelcontextprotocol/servers)
- **Site:** [faf.one](https://faf.one)

---

*Ready for Le Mans speeds. 🏎️*
