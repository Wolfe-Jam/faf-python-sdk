#!/usr/bin/env python3
"""Record faf-kernel's answers for every parity fixture.

Runs the kernel oracle (scripts/kernel_oracle.js → faf-scoring-kernel@3.0.0)
over tests/fixtures/{corpus,edge}/*.faf, edge_cases.json and fuzz_cases.json,
and writes tests/fixtures/kernel_expected.json. The kernel decides every value;
nothing here is computed in Python.

Setup:  npm install --prefix scripts        (installs the pinned kernel)
Usage:  python scripts/record_kernel_expected.py
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tests"))

import parity_support as ps  # noqa: E402


def main() -> None:
    if not ps.oracle_available():
        sys.exit("kernel oracle not available: install Node and run "
                 "`npm install --prefix scripts`")
    fixtures = ps.collect_fixtures()
    ids = list(fixtures)
    live = ps.run_oracle([fixtures[i] for i in ids])
    first_ok = next(r for r in live["results"] if r["ok"])
    slot_order = list(first_ok["result"]["slots"])
    cases = {}
    for case_id, entry in zip(ids, live["results"]):
        cases[case_id] = {"sha256": ps.sha256(fixtures[case_id]),
                          **ps.compact(entry, slot_order)}
    out = {
        "kernel": {"package": ps.KERNEL_PACKAGE, "sdk_version": live["version"]},
        "slot_order": slot_order,
        "cases": cases,
    }
    # One case per line keeps diffs readable when a fixture changes.
    lines = [f" {json.dumps(k)}: {json.dumps(v, ensure_ascii=True)}" for k, v in cases.items()]
    head = json.dumps({k: out[k] for k in ("kernel", "slot_order")}, ensure_ascii=True)
    ps.EXPECTED.write_text(head[:-1] + ',\n"cases": {\n' + ",\n".join(lines) + "\n}}\n",
                           encoding="utf-8")
    errors = sum(1 for c in cases.values() if not c["ok"])
    print(f"recorded {len(cases)} cases ({errors} unreadable) to "
          f"{ps.EXPECTED.relative_to(ps.ROOT)}")


if __name__ == "__main__":
    main()
