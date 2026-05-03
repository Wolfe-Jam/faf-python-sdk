# Contributing

Contributions are welcome. Bug fixes, doc improvements, new validators,
new scoring tactics in `mk4`, new discovery sources — all useful.

This file describes **how to land a change cleanly**.

---

## Setup

```bash
git clone https://github.com/Wolfe-Jam/faf-python-sdk
cd faf-python-sdk
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

That's it. You're ready to run tests and ship a fix.

---

## Before opening a PR

Run the full check pass:

```bash
pytest tests/ -v          # all tests must pass
mypy faf_sdk/             # strict typing — no untyped defs
```

If both come back clean, you're good to push. PRs that don't pass tests
will not be reviewed.

---

## PR conventions

| Type of change | Required |
|---|---|
| Bug fix | A regression test that fails on the bug, passes after the fix. The test comes **with** the fix, not after. |
| New feature | Tests for the new surface. If it touches the `.faf` format itself, see "Architecture decisions" below — the SDK doesn't extend the format unilaterally. |
| Doc-only | No tests required. README + CHANGELOG entries still expected. |
| Refactor | Existing tests must pass unchanged. Coverage must stay ≥ existing baseline. |

`mypy faf_sdk/` must be clean. Strict mode is on (`disallow_untyped_defs = true`).
The `[tool.mypy]` section in `pyproject.toml` is authoritative.

---

## Branch model

- `main` is always shippable. Tagged releases come from `main`.
- Work on feature branches. PR → squash-merge into `main`.
- Don't open PRs against tagged commits. Tags are immutable; any
  fix lands on `main` and gets a new tag if it's release-worthy.

---

## Commit messages

- Imperative mood: "fix: handle empty .faf gracefully" not "fixed" / "fixes".
- Conventional-commits prefix is appreciated but not enforced
  (`fix:` / `feat:` / `refactor:` / `chore:` / `docs:` / `test:`).
- Body explains the **why** when it's non-obvious. The diff explains
  the what.
- No marketing language in commit subjects. Commit messages are
  technical, not promotional.

---

## Code style

- **Names over comments.** A well-named function or variable doesn't
  need a comment explaining what it does.
- **WHY-comments are welcome** where the *why* isn't obvious — a
  hidden constraint, a workaround for a specific bug, a non-obvious
  invariant.
- **No marketing prose in code comments.** Internal docs are
  documentation, not pitch material.
- Type hints on all public signatures. `disallow_untyped_defs` is on.
- `from __future__ import annotations` at the top of any new module
  using `|` union types — keeps Python 3.8/3.9 compatibility.

---

## Adding a new validator / scorer / parser

The SDK's modules are deliberately narrow:

| Module | Job |
|---|---|
| `parser` | Read `.faf` (YAML) into typed dicts |
| `validator` | Check `.faf` against the schema |
| `mk4` | Score `.faf` (the FAF "ECU" — championship tiers) |
| `discovery` | Find `.faf` files in a project |
| `types` | Shared dataclasses + protocols |

When adding to one of these, **stay in lane**. A scoring change goes in
`mk4`, not `validator`. A new file-finder goes in `discovery`. Cross-cutting
features need a small RFC in the PR description before code lands.

---

## Architecture decisions

The SDK has firm design rules that aren't up for debate in PRs:

1. **The `.faf` format spec lives in the FAF organization, not the SDK.**
   PRs that change parser/validator behavior to "support a new format
   feature" before the format spec adds it will be closed. The SDK
   *implements* the spec; it doesn't *extend* it.
2. **MIT-licensed and dependency-light.** The SDK has one runtime
   dependency (`pyyaml`) and that's the floor we want to defend. PRs
   that add runtime deps need strong justification.
3. **The SDK is the foundation other Python FAF tools build on**
   (gemini-faf-mcp, custom MCP servers, CI validators). Breaking
   changes to public surfaces go behind a major version bump.

---

## CI doctrine

Two rules from the project's CI philosophy:

1. **Red means real.** A red `test` job is a real, actionable failure.
   We don't tolerate flaky tests — if a test fails intermittently,
   that's a bug in the test, fix it before merging anything else.
2. **Type-check is observability, not a gate.** mypy failures show up
   but tests are the only hard gate. Type cleanup PRs are welcome but
   never urgent.

If CI goes red after a merge, the breaking change owns the
fix — revert is on the table, no shame.

---

## Where to file issues

[github.com/Wolfe-Jam/faf-python-sdk/issues](https://github.com/Wolfe-Jam/faf-python-sdk/issues)

For security issues: don't open a public issue. Email
**team@faf.one** with details.

---

## License

MIT. Fork it, ship it, embed it, enjoy it.

**Don't copy FAF brand. Do your own.**
