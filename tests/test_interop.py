"""Tests for faf_sdk.interop — AGENTS.md / GEMINI.md generators."""

from faf_sdk import faf_meta_tag, generate_agents_md, generate_gemini_md
from faf_sdk.interop import slot_label, title_label

# A representative .faf as the raw parsed dict.
SAMPLE = {
    "faf_version": "3.0",
    "project": {
        "name": "widget-api",
        "goal": "REST API for widget inventory",
        "main_language": "TypeScript",
        "type": "api",
        "version": "2.1.0",
    },
    "commands": {
        "install": "npm ci",
        "build": "npm run build",
        "dev": "npm run dev",
        "test": "npm test",
        "lint": "npm run lint",
    },
    "key_files": ["src/server.ts — the entry point", "src/routes/ — the handlers"],
    "ai_instructions": {
        "warnings": ["Never touch the billing module without a review"],
        "working_style": {"testing": "required", "quality_bar": "zero_errors"},
    },
    "preferences": {"commit_style": "conventional", "communication": "direct"},
    "security": {"secrets": ".env", "example": ".env.example"},
    "stack": {
        "backend": "fastify",
        "database": "postgres",
        "api_type": "rest",
        "target_user": "developers",
    },
    "generated": "2026-09-06T00:00:00Z",
}


# --- helpers ---------------------------------------------------------------

def test_title_label_acronyms():
    assert title_label("api_type") == "API Type"
    assert title_label("mcp_sdk") == "MCP SDK"
    assert title_label("runtime") == "Runtime"
    assert title_label("state_management") == "State Management"


def test_slot_label_canonical_then_fallback():
    assert slot_label("stack.cicd") == "CI/CD"
    assert slot_label("stack.api_type") == "API"
    assert slot_label("stack.made_up_key") == "Made Up Key"


def test_faf_meta_tag_two_lines():
    tag = faf_meta_tag(SAMPLE)
    line1, line2 = tag.split("\n")
    assert line1 == (
        "<!-- faf: widget-api | TypeScript | api | REST API for widget inventory -->"
    )
    assert line2 == "<!-- faf: claim=project.faf | family=FAF -->"


# --- AGENTS.md -----------------------------------------------------------

def test_agents_md_sections_present():
    md = generate_agents_md(SAMPLE)
    for section in (
        "# AGENTS.md — widget-api",
        "## Setup & build",
        "## Run the tests",
        "## Where things live",
        "## Conventions",
        "## Guardrails",
        "## Definition of Done",
        "## When stuck",
        "## Security & secrets",
        "## Commit & PR",
        "## Stack",
    ):
        assert section in md, f"missing {section!r}"


def test_agents_md_omits_human_context():
    md = generate_agents_md({**SAMPLE, "human_context": {"who": "devs", "why": "money"}})
    assert "## Human Context" not in md
    assert "## Context" not in md
    assert "money" not in md


def test_agents_md_setup_ordered_install_build_dev():
    md = generate_agents_md(SAMPLE)
    block = md.split("## Setup & build")[1].split("```")[1]
    # first line is the ```bash language tag
    lines = [ln for ln in block.strip().splitlines()][1:]
    assert lines[0].startswith("npm ci")
    assert lines[1].startswith("npm run build")
    assert lines[2].startswith("npm run dev")


def test_agents_md_guardrails_always_render_even_with_no_data():
    md = generate_agents_md({"faf_version": "3.0", "project": {"name": "bare"}})
    assert "## Guardrails" in md
    assert "## Definition of Done" in md
    assert "## Commit & PR" in md
    assert "**Never:** force-push" in md


def test_agents_md_key_files_table_when_roles_present():
    md = generate_agents_md(SAMPLE)
    assert "| Path | Role |" in md
    assert "| `src/server.ts` | the entry point |" in md


def test_agents_md_security_never_leaks_values():
    md = generate_agents_md(SAMPLE)
    assert "Secrets live in `.env`" in md
    assert "see `.env.example`" in md


def test_agents_md_stack_drops_non_stack_marketing_keys():
    md = generate_agents_md(SAMPLE)
    assert "developers" not in md.split("## Stack")[1]  # target_user filtered


def test_agents_md_deterministic():
    assert generate_agents_md(SAMPLE) == generate_agents_md(dict(SAMPLE))


def test_agents_md_human_prefs_excluded_from_conventions():
    md = generate_agents_md(SAMPLE)
    conv = md.split("## Conventions")[1].split("##")[0]
    assert "communication" not in conv.lower()
    assert "Testing" in conv


# --- GEMINI.md ----------------------------------------------------------

def test_gemini_md_structure():
    md = generate_gemini_md(SAMPLE)
    assert md.startswith("<!-- faf:")
    assert "# GEMINI.md — widget-api" in md
    assert "Project: widget-api" in md
    assert "## Setup & build" in md
    assert "## Test & verify" in md
    assert "## Before changing things" in md


def test_gemini_md_no_guardrail_ladder():
    # GEMINI.md is lighter — no Definition of Done / When stuck
    md = generate_gemini_md(SAMPLE)
    assert "## Definition of Done" not in md
    assert "## Guardrails" not in md


# --- edge cases -------------------------------------------------------

def test_minimal_faf_does_not_crash():
    minimal = {"faf_version": "3.0", "project": {"name": "x"}}
    assert "# AGENTS.md — x" in generate_agents_md(minimal)
    assert "# GEMINI.md — x" in generate_gemini_md(minimal)


def test_key_files_from_instant_context_fallback():
    faf = {
        "faf_version": "3.0",
        "project": {"name": "y"},
        "instant_context": {"key_files": ["a.py", "b.py"]},
    }
    md = generate_agents_md(faf)
    assert "- `a.py`" in md


def test_commands_from_instant_context_are_not_used_at_toplevel():
    # top-level `commands` is the source; instant_context.commands is separate
    faf = {"faf_version": "3.0", "project": {"name": "z"}, "commands": {"test": "go test ./..."}}
    md = generate_agents_md(faf)
    assert "go test ./..." in md
