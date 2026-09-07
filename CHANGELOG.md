# Changelog

All notable changes to faf-python-sdk are documented here.
Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)

## [1.3.0] - 2026-09-06 — The Interop Edition

The SDK can now author AI-context files, not just parse and score them.

### Added
- `faf_sdk.interop` — `generate_agents_md(faf)` and `generate_gemini_md(faf)`,
  Python ports of faf-cli's `src/interop/agents.ts` + `gemini.ts`, kept in
  parity with the canonical TypeScript. Deterministic BETTER-shaped projection:
  `## Setup & build` (install→build→dev ordered) · `## Run the tests` ·
  `## Where things live` · `## Conventions` · three-tier `## Guardrails` ·
  `## Definition of Done` · `## When stuck` · `## Security & secrets` ·
  `## Commit & PR` · `## Stack`. Human Context (who/why marketing) is
  intentionally omitted from AGENTS.md — it belongs in the README / .faf DNA.
- `faf_meta_tag(faf)`, `title_label(key)`, `slot_label(path)` — the shared
  label + metastamp helpers, also from `src/interop`.
- Both take the **raw parsed dict** (`FafFile.data.raw`) — the .faf
  format carries top-level `commands` / `key_files` / `security` that the typed
  model doesn't surface.
- 17 tests, including deterministic-output and human-context-omission guards.

### Fixed
- `[tool.mypy] python_version` was `"3.9"` — rejected by modern mypy
  (`must be 3.10 or higher`). Set to `"3.10"`.

## [1.2.0] - 2026-06-16 — The Dart Edition

Adds `detect_dart_project()`: content-aware Dart/Flutter detection from a `pubspec.yaml` (Flutter app vs package · Dart MCP / backend / CLI / library), reproducing faf-cli's engine byte-for-byte — 20 shared fixtures, parity-tested.

### Added
- `detect_dart_project(dir)` → `DartProject` — the SDK's first detection capability. Reads `pubspec.yaml` and classifies: Flutter app vs reusable package, Dart MCP server, Dart backend (Serverpod / Dart Frog / Shelf / …), Dart CLI, or library. Exported from `faf_sdk`.
- `faf_sdk/dart_detection.json` — the detection KNOWLEDGE spec, vendored byte-identical from faf-cli (the single source); ships in the wheel, loaded at runtime.
- `tests/test_dart_parity.py` — 20 shared fixtures run identically by faf-cli and this SDK; parity proven by test, not by eye.
- `scripts/sync-dart-spec.sh` — vendor + `--check` (byte-identity) the spec & fixtures from faf-cli.

### Notes
- Mirrors faf-cli `src/detect/dart.ts` exactly (A+B hybrid). To bolster Dart support, edit the spec in faf-cli (the Truth) and re-sync. No new runtime dependencies.

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
