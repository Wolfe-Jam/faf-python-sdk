# Changelog

All notable changes to faf-python-sdk are documented here.
Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)

## [1.1.2] - 2026-04-26

### Changed
- Package description aligned with the canonical "Persistent project context for Python" framing on PyPI catalog and GitHub repo metadata.
- README lede sharpened — leads with the value proposition and the audience (MCP server / CI validator / tool authors), no longer feature-list framing.

### Added
- `CHANGELOG.md` (this file) — versioned release history, separate from the README's "What's New" section.
- Brand mantra `FAF defines. MD instructs. AI codes.` anchored in the README and `__init__.py` module docstring.

### Notes
No runtime code changes. Patch release to surface description alignment in the PyPI catalog and tighten positioning copy. The catalog only updates on a new publish.

## [1.1.1] - 2026-04-18

### Fixed
- Tier alignment to match faf-cli v6 — clean geometric symbols, no emoji. v1.1.0 mistakenly returned emoji tiers; this patch normalizes them to plain uppercase strings (`TROPHY`, `GOLD`, `SILVER`, `BRONZE`, `GREEN`, `YELLOW`, `RED`).

## [1.1.0] - 2026-03-29

### Added
- **Mk4 Championship Scoring Engine** — the same 33-slot scoring algorithm used by the Rust compiler and TypeScript CLI, now in Python. Same slots, same formula, same scores.
- `score_faf()` — Mk4 scoring with 21-slot Base or 33-slot Enterprise tiers.
- 100% parity with `faf-wasm-sdk` (Rust) and `faf-cli` (TypeScript).
- 88 new WJTTC championship-grade tests (concurrency, adversarial input, security).
- Total test count: 175 (was 87).

### Fixed
- 3 crash bugs in malformed YAML and null project field handling.

## [1.0.2] - earlier

### Added
- Initial public release with `parse`, `parse_file`, `stringify`, `validate`, `find_faf_file`, `find_project_root`, and the typed `FafData` model.
