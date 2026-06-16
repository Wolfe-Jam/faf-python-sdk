"""
Cross-language PARITY — the Python Dart detector must reproduce faf-cli's
(TypeScript) classification byte-for-byte on the SHARED fixtures.

tests/dart_parity_fixtures.json is a byte-identical, synced copy of faf-cli's
tests/detect/dart-parity-fixtures.json (see scripts/sync-dart-spec.sh). faf-cli
runs the same fixtures in tests/detect/dart-parity.test.ts and asserts the same
expected projection. Same input + same expected on both engines = parity proven
by test, not by eye. If the engines ever diverge, one suite goes red.
"""

import json
from pathlib import Path
from typing import Any, Dict

import pytest

from faf_sdk import detect_dart_project

_FIXTURE_FILE = Path(__file__).parent / "dart_parity_fixtures.json"
FIXTURES = json.loads(_FIXTURE_FILE.read_text(encoding="utf-8"))["fixtures"]


def _materialize(root: Path, files: Dict[str, str]) -> None:
    for rel, content in files.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")


def test_fixture_set_is_non_trivial() -> None:
    assert len(FIXTURES) >= 20


@pytest.mark.parametrize("fx", FIXTURES, ids=[f["name"] for f in FIXTURES])
def test_dart_parity(fx: Dict[str, Any], tmp_path: Path) -> None:
    _materialize(tmp_path, fx["files"])
    result = detect_dart_project(str(tmp_path))
    assert result is not None, f"{fx['name']}: detector returned None"
    assert result.to_dict() == fx["expected"], fx["name"]
