#!/usr/bin/env python3
"""Generate the seeded fuzz fixtures for the always-33 parity harness.

Writes tests/fixtures/fuzz_cases.json: YAML documents built three ways —
slot-shaped documents with random values, byte-level mutations of the real
corpus, and YAML token soup (tabs, flow indicators, tags, anchors, BOMs,
directives, document markers). The seed is fixed, so the file is reproducible.
Expected results come only from the kernel: run scripts/record_kernel_expected.py
after regenerating.

Usage: python scripts/gen_fuzz_cases.py [--count 200] [--mutations 60] [--seed 68]
"""

import argparse
import json
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FIXTURES = ROOT / "tests" / "fixtures"

ATOMS = [
    "~", "null", "Null", "NULL", "tbd", "TODO", "none", "N/A", "slotignored",
    " slotignored ", '"slotignored"', "''", '""', "[]", "{}", "[a]", "{a: 1}",
    "yes", "no", "on", "true", "1", "0x1", "012", "1.5", ".inf", ".nan", "1e3",
    "2025-01-01", "!!str 1", "!x y", "! z", "!!int 3", '"\\u00a0"', '"\\x1c"', "=",
    "<<", "- a", "&q v", "*q", "|\n    x", ">-\n    ", '"a: b"', "'#'", "x # c",
    "unknown", "Not Applicable", "cloud platform", '"  "', "0", "-0", "+1", "1:30",
    "﻿x", '"\\t"', "a\tb", "[why?]",
]
KEYS = [
    "project", "human_context", "stack", "monorepo", "name", "goal", "main_language",
    "who", "what", "why", "where", "when", "how", "framework", "frontend", "css",
    "css_framework", "state", "state_management", "api", "api_type", "db", "database",
    "pkg_manager", "package_manager", "backend", "runtime", "connection", "hosting",
    "build", "cicd", "monorepo_tool", "workspaces", "admin", "cache", "search",
    "storage", "packages_count", "build_orchestrator", "versioning_strategy",
    "shared_configs", "remote_cache", "<<", "1", "true", "~",
]
SOUP = [
    "project", ":", " ", "  ", "\n", "\n  ", "\n    ", "\t", "-", " - ", "[", "]", "{",
    "}", ",", "?", "? ", '"', "'", "name", "goal", "x", "tbd", "~", "&a ", "*a", "!t ",
    "!!str ", "!<tag:x> ", "|", ">", "|-", ">+2", "#c", "\n---\n", "\n...\n",
    "%YAML 1.2\n---\n", "\\n", "\\", "﻿", "\r\n", " ", "\x85", "slotignored",
    "stack", "framework", ": ", ":x", "::", "--", "- -", "{a: b}", "[a, b]", '"a\\tb"',
    "'a''b'", "\n# c\n", "  #c", "0x1", "1.5", "true", "null", "é", "<<: *a\n", "=",
    "@", "`", "%",
]
MUTATIONS = [
    " ", "\n", ":", "-", "#", '"', "'", "[", "]", "{", "}", "&a", "*a", "!", "\t", "~",
    "|", ">", "%", "?", ",", "  ",
]


def gen_doc(rng: random.Random) -> str:
    lines = []
    for top in rng.sample(["project", "human_context", "stack", "monorepo", "x"],
                          rng.randint(1, 4)):
        subs = rng.sample(KEYS, rng.randint(0, 8))
        if rng.random() < 0.2:
            body = ", ".join(f"{k}: {rng.choice(ATOMS[:30])}" for k in subs)
            lines.append(f"{top}: {{{body}}}")
        else:
            anchor = f" &{top[:2]}" if rng.random() < 0.2 else ""
            lines.append(f"{top}:{anchor}")
            lines.extend(f"  {k}: {rng.choice(ATOMS)}" for k in subs)
        if rng.random() < 0.1:
            lines.append(f"z{rng.randint(0, 3)}: *{top[:2]}")
    return "\n".join(lines) + "\n"


def mutate(rng: random.Random, text: str) -> str:
    chars = list(text)
    for _ in range(rng.randint(1, 4)):
        op = rng.random()
        i = rng.randrange(len(chars) + 1)
        if op < 0.3 and chars:
            del chars[min(i, len(chars) - 1)]
        elif op < 0.6:
            chars.insert(i, rng.choice(MUTATIONS))
        else:
            lines = "".join(chars).split("\n")
            j = rng.randrange(len(lines))
            if ":" in lines[j]:
                lines[j] = lines[j].split(":")[0] + ": " + rng.choice(ATOMS)
            chars = list("\n".join(lines))
    return "".join(chars)


def soup(rng: random.Random) -> str:
    text = "".join(rng.choice(SOUP) for _ in range(rng.randint(1, 30)))
    return "project:\n  name: " + text if rng.random() < 0.5 else text


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--count", type=int, default=200, help="slot-shaped and soup cases each")
    ap.add_argument("--mutations", type=int, default=60, help="corpus mutations (larger)")
    ap.add_argument("--seed", type=int, default=68)
    args = ap.parse_args()
    rng = random.Random(args.seed)
    corpus = [p.read_text(encoding="utf-8")
              for p in sorted((FIXTURES / "corpus").glob("*.faf"))]
    cases = {}
    for i in range(args.count):
        cases[f"gen-{i:04d}"] = gen_doc(rng)
        cases[f"soup-{i:04d}"] = soup(rng)
    for i in range(args.mutations):
        cases[f"mut-{i:04d}"] = mutate(rng, rng.choice(corpus))
    out = FIXTURES / "fuzz_cases.json"
    out.write_text(json.dumps(cases, ensure_ascii=True, indent=1, sort_keys=True) + "\n",
                   encoding="utf-8")
    print(f"wrote {len(cases)} cases to {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
