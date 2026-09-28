"""
Always-33 parity harness — faf_sdk.score_faf vs faf-kernel.

For every fixture, ``score_faf(yaml)`` must equal faf-kernel on score, tier,
populated, empty, ignored, active, total and the state of each of the 33 slots.
The expected values are the kernel's own answers (npm faf-scoring-kernel@3.0.0,
the WASM build of Wolfe-Jam/faf-rust crates/faf-kernel), recorded in
tests/fixtures/kernel_expected.json by scripts/record_kernel_expected.py.

Fixtures:
- corpus/      the project.faf of every public Wolfe-Jam repo that has one
- edge/        one file per scoring rule (21 + 12 markers, tbd/todo, short keys,
               flow YAML, BOM, empty values, unreadable YAML, ...)
- edge_cases/  YAML-layer cases (tags, tabs, directives, limits, ...)
- fuzz/        seeded fuzz documents (scripts/gen_fuzz_cases.py)

Where the kernel returns a parse error, score_faf must return score 0 with every
slot empty and must not raise; the kernel YAML loader must report the same
document as unreadable.

With Node and the kernel installed (``npm install --prefix scripts``), the
recording is also checked against the live kernel. Set FAF_REQUIRE_KERNEL=1 to
fail instead of skip when the kernel is not installed.
"""

import os

import pytest

from faf_sdk import _kernel_yaml as ky
from faf_sdk.mk4 import SLOTS, SlotState, score_faf

from . import parity_support as ps

FIXTURES = ps.collect_fixtures()
EXPECTED = ps.load_expected()
SLOT_ORDER = EXPECTED["slot_order"]


def test_recording_covers_every_fixture():
    assert set(EXPECTED["cases"]) == set(FIXTURES), (
        "fixtures changed: run `python scripts/record_kernel_expected.py`"
    )


def test_slot_order_matches_kernel():
    assert list(SLOTS) == SLOT_ORDER
    assert len(SLOT_ORDER) == 33


def test_corpus_is_present():
    corpus = [k for k in FIXTURES if k.startswith("corpus/")]
    assert len(corpus) >= 58


@pytest.mark.parametrize("case_id", sorted(FIXTURES))
def test_parity(case_id):
    text = FIXTURES[case_id]
    expected = EXPECTED["cases"][case_id]
    assert expected["sha256"] == ps.sha256(text), "fixture changed since it was recorded"

    result = score_faf(text)  # must never raise

    if expected["ok"]:
        assert ps.compact_python(result.to_dict(), SLOT_ORDER) == {
            k: v for k, v in expected.items() if k != "sha256"
        }
    else:
        with pytest.raises(ky.KernelYamlError):
            ky.load(text)
        assert result.score == 0
        assert result.tier == "WHITE"
        assert result.populated == 0
        assert result.ignored == 0
        assert result.active == 33
        assert result.total == 33
        assert all(state == SlotState.EMPTY for _, state in result.slots)


@pytest.mark.parametrize("unit", ["[", "{a: "])
def test_deep_flow_stops_at_kernel_depth_limit(unit):
    """Flow nesting past 128 is unreadable to the kernel; the scanner stops at
    flow level 129 instead of reading on (the simple-key scan is O(depth) per
    token, so reading on is quadratic). Checked by position, not by time."""
    from yaml.scanner import ScannerError

    from faf_sdk._libyaml_scanner import LibyamlScanner

    scanner = LibyamlScanner(unit * 20000)
    with pytest.raises(ScannerError):
        while scanner.get_token() is not None:
            pass
    assert scanner.flow_level == 129
    assert scanner.pos <= 129 * len(unit)


def test_recording_matches_live_kernel():
    if not ps.oracle_available():
        if os.environ.get("FAF_REQUIRE_KERNEL") == "1":
            pytest.fail("kernel oracle required but not installed")
        pytest.skip("kernel oracle not installed (npm install --prefix scripts)")
    ids = sorted(FIXTURES)
    live = ps.run_oracle([FIXTURES[i] for i in ids])
    assert live["version"] == EXPECTED["kernel"]["sdk_version"]
    mismatched = []
    for case_id, entry in zip(ids, live["results"]):
        recorded = {k: v for k, v in EXPECTED["cases"][case_id].items() if k != "sha256"}
        if ps.compact(entry, SLOT_ORDER) != recorded:
            mismatched.append(case_id)
    assert not mismatched, f"recording differs from the live kernel: {mismatched[:10]}"
