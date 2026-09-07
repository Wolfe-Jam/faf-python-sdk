"""
AI-context file authoring — AGENTS.md and GEMINI.md from .faf data.

Python port of faf-cli's `src/interop/agents.ts` + `gemini.ts`, kept in
parity with the canonical TypeScript. Deterministic projection from curated
truth — facts, not freewritten prose. Human Context (who/why marketing) is
intentionally omitted from AGENTS.md; it belongs in the README / .faf DNA,
not agent ops.

Both take the raw parsed .faf dict (`FafFile.data.raw`) — the .faf format
carries top-level `commands` / `key_files` / `security` that the typed model
doesn't surface.
"""

from __future__ import annotations

from typing import Any

__all__ = ["generate_agents_md", "generate_gemini_md", "faf_meta_tag", "title_label", "slot_label"]

# --- shared helpers ----------------------------------------------------------

_ACRONYMS = {
    "API", "CI", "CD", "MCP", "CLI", "SDK", "UI", "UX", "AI", "ML", "DB", "ORM",
    "OS", "HTTP", "HTTPS", "REST", "RPC", "JSON", "YAML", "XML", "SQL", "CSS",
    "HTML", "AWS", "GCP", "CDN", "DNS", "JWT", "ID", "IP", "URL", "URI", "TS", "JS",
}

# Canonical .faf slot labels (from faf-cli src/core/slots.ts).
_SLOT_LABELS = {
    "stack.frontend": "Framework", "stack.css_framework": "CSS",
    "stack.ui_library": "UI Library", "stack.state_management": "State",
    "stack.backend": "Backend", "stack.api_type": "API", "stack.runtime": "Runtime",
    "stack.database": "Database", "stack.connection": "Connection",
    "stack.hosting": "Hosting", "stack.build": "Build", "stack.cicd": "CI/CD",
    "stack.monorepo_tool": "Monorepo", "stack.package_manager": "Package Manager",
    "stack.workspaces": "Workspaces", "stack.admin": "Admin", "stack.cache": "Cache",
    "stack.search": "Search", "stack.storage": "Storage",
}

# Preference keys that describe human<->assistant interaction, not repo conventions.
_HUMAN_PREF = {
    "commit_style", "communication", "response_style", "explanation_level",
    "explanations", "documentation", "code_first",
}

# Stack keys that are context/marketing, not actual stack.
_NON_STACK = {"target_user", "core_problem", "mission_purpose"}


def _present(v: Any) -> bool:
    """Non-empty, not 'slotignored', non-empty list."""
    if v is None or v == "" or v == "slotignored":
        return False
    if isinstance(v, (list, tuple)) and len(v) == 0:
        return False
    return True


def _filled(v: Any) -> bool:
    """A string slot value carrying real content."""
    return isinstance(v, str) and v.strip() not in ("", "slotignored")


def _fmt_val(v: Any) -> str:
    if isinstance(v, (list, tuple)):
        return ", ".join(str(x) for x in v)
    return str(v)


def title_label(key: str) -> str:
    """snake_case -> Title Case, acronym-aware. `api_type` -> 'API Type'."""
    out: list[str] = []
    for w in key.split("_"):
        if not w:
            out.append(w)
        elif w.upper() in _ACRONYMS:
            out.append(w.upper())
        else:
            out.append(w[0].upper() + w[1:])
    return " ".join(out)


def slot_label(path: str) -> str:
    """Canonical display label for a .faf slot path; falls back to title_label."""
    if path in _SLOT_LABELS:
        return _SLOT_LABELS[path]
    key = path.rsplit(".", 1)[-1] if "." in path else path
    return title_label(key)


def faf_meta_tag(faf: dict) -> str:
    """The two-line `<!-- faf: ... -->` metastamp every faf-authored file opens with."""
    proj = faf.get("project") or {}
    name = str(proj.get("name") or "").strip()
    lang = str(proj.get("main_language") or "").strip()
    typ = str(proj.get("type") or "").strip()
    desc = str(proj.get("goal") or "").strip()
    line1 = f"<!-- faf: {' | '.join([name, lang, typ, desc])} -->"
    kv = ["claim=project.faf", "family=FAF"]
    line2 = f"<!-- faf: {' | '.join(kv)} -->"
    return f"{line1}\n{line2}"


# --- command classification (shared by both) --------------------------------

def _classify_commands(faf: dict) -> dict:
    commands = faf.get("commands") or {}
    entries = [(k, v) for k, v in commands.items() if _present(v)]
    test_cmds = [(k, v) for k, v in entries if "test" in k.lower()]
    lint_cmds = [
        (k, v) for k, v in entries
        if ("lint" in k.lower() or "check" in k.lower()) and "test" not in k.lower()
    ]
    setup_raw = [
        (k, v) for k, v in entries
        if not any(t in k.lower() for t in ("test", "lint", "check"))
    ]

    def setup_rank(k: str) -> int:
        n = k.lower()
        if "install" in n or "deps" in n:
            return 0
        if "build" in n and "rebuild" not in n:
            return 1
        if n == "dev" or "develop" in n:
            return 2
        if n == "start" or "run" in n:
            return 3
        return 4

    setup_cmds = sorted(setup_raw, key=lambda kv: (setup_rank(kv[0]), kv[0]))
    verify_cmds = test_cmds + lint_cmds
    return {
        "test": test_cmds, "lint": lint_cmds, "setup": setup_cmds, "verify": verify_cmds,
    }


def _key_files(faf: dict) -> list:
    kf = faf.get("key_files")
    if not kf:
        ic = faf.get("instant_context") or {}
        kf = ic.get("key_files")
    return kf or []


# --- AGENTS.md -------------------------------------------------------------

def generate_agents_md(faf: dict) -> str:
    """Author a BETTER-shaped AGENTS.md from raw .faf data. Deterministic."""
    lines: list[str] = []

    def push(s: str = "") -> None:
        lines.append(s)

    proj = faf.get("project") or {}
    ai = faf.get("ai_instructions") or {}
    prefs = faf.get("preferences") or {}
    security = faf.get("security") or {}
    branch = str(proj["default_branch"]) if _present(proj.get("default_branch")) else "main"

    cmds = _classify_commands(faf)
    setup_cmds, test_cmds, lint_cmds, verify_cmds = (
        cmds["setup"], cmds["test"], cmds["lint"], cmds["verify"],
    )
    test_cmd = test_cmds[0][1] if test_cmds else None
    build_cmd = next((v for k, v in setup_cmds if "build" in k.lower()), None)
    key_files = _key_files(faf)

    push(faf_meta_tag(faf))
    push()
    push(f"# AGENTS.md — {proj.get('name') or 'Project'}")
    push()

    # 1 - orientation
    bits: list[str] = []
    if proj.get("main_language"):
        bits.append(str(proj["main_language"]))
    if _present(proj.get("type")):
        bits.append(f"type: {proj['type']}")
    if _present(proj.get("version")):
        bits.append(f"v{proj['version']}")
    orientation = str(proj["goal"]).strip() if proj.get("goal") else ""
    if bits:
        orientation += (" — " if orientation else "") + " · ".join(bits)
    if orientation:
        push(orientation)
        push()
    push(
        "> Authored by faf — refresh with `faf export --agents` or the "
        "`faf_agents` MCP tool. The managed block is regenerated each time; "
        "hand-written content outside it is preserved."
    )
    push()

    # 2 - setup & build
    if setup_cmds:
        push("## Setup & build")
        push()
        push("```bash")
        for k, v in setup_cmds:
            push(f"{v}    # {k}")
        push("```")
        push()

    # 3 - run the tests
    if verify_cmds:
        push("## Run the tests")
        push()
        push("```bash")
        for _, v in verify_cmds:
            push(v)
        push("```")
        push()

    # 4 - where things live
    if key_files:
        push("## Where things live")
        push()
        rows = []
        for f in key_files:
            s = str(f)
            at = s.find(" — ")
            rows.append((s[:at], s[at + 3:]) if at > 0 else (s, ""))
        if any(role for _, role in rows):
            push("| Path | Role |")
            push("|------|------|")
            for path, role in rows:
                push(f"| `{path}` | {role} |")
        else:
            for path, _ in rows:
                push(f"- `{path}`")
        push()

    # 5 - conventions
    conventions: dict[str, str] = {}

    def collect(obj: Any) -> None:
        if not isinstance(obj, dict):
            return
        for k, v in obj.items():
            if k in _HUMAN_PREF or not _present(v):
                continue
            label = title_label(k)
            conventions.setdefault(label, _fmt_val(v))

    collect(ai.get("working_style"))
    collect(prefs)
    detected_conv = faf.get("conventions") or []
    if conventions or detected_conv:
        push("## Conventions")
        push()
        for label, val in conventions.items():
            push(f"- **{label}:** {val}")
        for c in detected_conv:
            if _present(c):
                push(f"- {c}")
        push()

    # 6 - guardrails
    warnings = [w for w in (ai.get("warnings") or []) if _present(w)]
    always = ["read the tree"]
    if test_cmd:
        always.append(f"run the tests (`{test_cmd}`)")
    if build_cmd:
        always.append("build the project")
    for _, v in lint_cmds[:1]:
        always.append(f"`{v}`")
    push("## Guardrails")
    push()
    for w in warnings:
        push(f"- {w}")
    push(f"- **Always OK:** {' · '.join(dict.fromkeys(always))}.")
    push("- **Ask first:** dependency installs, deletions, migrations, schema changes, publish/release.")
    push(
        f"- **Never:** force-push · push straight to `{branch}` (branch and open a PR) · commit secrets."
    )
    push()

    # 7 - definition of done
    dod: list[str] = []
    for _, v in lint_cmds:
        dod.append(f"`{v}` exits 0")
    for _, v in test_cmds:
        dod.append(f"`{v}` passes")
    dod.append("changes committed with a conventional message")
    push("## Definition of Done")
    push()
    push(f"Done when: {' · '.join(dict.fromkeys(dod))}.")
    push()

    # 8 - when stuck
    push("## When stuck")
    push()
    push(
        "Ask a clarifying question, propose a short plan, or open a draft PR with "
        f"notes — do not push large speculative changes to `{branch}`."
    )
    push()

    # 9 - security & secrets
    if security and (_present(security.get("secrets")) or (security.get("never") or [])):
        push("## Security & secrets")
        push()
        if _present(security.get("secrets")):
            ex = f" (see `{security['example']}`)" if _present(security.get("example")) else ""
            push(f"- Secrets live in `{security['secrets']}`{ex}. Never read or commit them.")
        for n in security.get("never") or []:
            if _present(n):
                push(f"- Never read or commit `{n}`.")
        push()

    # 10 - commit & PR
    push("## Commit & PR")
    push()
    if _present(prefs.get("commit_style")):
        push(f"- Commit style: {_fmt_val(prefs['commit_style'])}")
    else:
        push("- Conventional Commits preferred (`feat:`, `fix:`, `chore:`, …).")
    push(f"- Branch off `{branch}` and open a PR — never commit to `{branch}` directly.")
    push("- If build/test scripts or layout change, refresh this file in the **same PR**.")
    push()

    # stack (reference)
    stack = faf.get("stack") or {}
    if isinstance(stack, dict):
        rendered = [
            f"- **{slot_label(f'stack.{k}')}:** {v.strip()}"
            for k, v in stack.items()
            if k not in _NON_STACK and _filled(v)
        ]
        if rendered:
            push("## Stack")
            push()
            lines.extend(rendered)
            push()

    gen = faf.get("generated")
    if _present(gen):
        push(f"*Context authored: {gen}*")

    return "\n".join(lines)


# --- GEMINI.md ------------------------------------------------------------

def generate_gemini_md(faf: dict) -> str:
    """GEMINI.md — Gemini CLI's own convention (hierarchical, @file-importable)."""
    lines: list[str] = []
    proj = faf.get("project") or {}
    cmds = _classify_commands(faf)
    setup_cmds, verify_cmds = cmds["setup"], cmds["verify"]
    key_files = _key_files(faf)

    lines.append(faf_meta_tag(faf))
    lines.append("")
    lines.append(f"# GEMINI.md — {proj.get('name') or 'Project'}")
    lines.append("")
    lines.append("> Authored from project.faf — refresh with the `faf_gemini` MCP tool or `faf export --gemini`.")
    lines.append("")

    if proj.get("name"):
        lines.append(f"Project: {proj['name']}")
    if proj.get("goal"):
        lines.append(f"Goal: {proj['goal']}")
    if proj.get("main_language"):
        lines.append(f"Language: {proj['main_language']}")

    if setup_cmds:
        lines += ["", "## Setup & build", "", "```bash"]
        for k, v in setup_cmds:
            lines.append(f"{v}    # {k}")
        lines.append("```")

    if verify_cmds:
        lines += ["", "## Test & verify", "", "```bash"]
        for _, v in verify_cmds:
            lines.append(v)
        lines.append("```")

    if key_files:
        lines += ["", "## Where things live", ""]
        for f in key_files:
            lines.append(f"- `{f}`")

    stack = faf.get("stack") or {}
    if isinstance(stack, dict):
        rendered = [
            f"- {slot_label(f'stack.{k}')}: {v.strip()}"
            for k, v in stack.items()
            if k not in _NON_STACK and _filled(v)
        ]
        if rendered:
            lines += ["", "## Stack"]
            lines.extend(rendered)

    lines += [
        "", "## Before changing things", "",
        "- Ask first: dependency installs, deletions, migrations, schema changes, publish/release.",
        "- Never: force-push · push straight to `main` · commit secrets.",
        "",
    ]
    return "\n".join(lines)
