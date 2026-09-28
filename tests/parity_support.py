"""
Shared fixture and oracle plumbing for the always-33 parity harness.

The oracle is faf-kernel itself: npm ``faf-scoring-kernel@3.0.0`` (the WASM
build of Wolfe-Jam/faf-rust crates/faf-kernel), driven by
scripts/kernel_oracle.js. Its answers for every fixture are recorded in
tests/fixtures/kernel_expected.json by scripts/record_kernel_expected.py, so the
harness runs without Node; when Node and the kernel are installed the harness
also re-runs the kernel live and checks the recording.
"""

import hashlib
import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parent.parent
FIXTURES = ROOT / "tests" / "fixtures"
EXPECTED = FIXTURES / "kernel_expected.json"
ORACLE = ROOT / "scripts" / "kernel_oracle.js"
KERNEL_PACKAGE = "faf-scoring-kernel@3.0.0"

_STATE_CODE = {"populated": "p", "empty": "e", "slotignored": "i"}


def _read(path: Path) -> str:
    with open(path, encoding="utf-8", newline="") as f:
        return f.read()


def collect_fixtures() -> Dict[str, str]:
    """Every parity fixture, by id → YAML text."""
    cases: Dict[str, str] = {}
    for sub in ("corpus", "edge"):
        for path in sorted((FIXTURES / sub).glob("*.faf")):
            cases[f"{sub}/{path.name}"] = _read(path)
    for name, prefix in (("edge_cases.json", "edge_cases"), ("fuzz_cases.json", "fuzz")):
        data = json.loads(_read(FIXTURES / name))
        for key in sorted(data):
            cases[f"{prefix}/{key}"] = data[key]
    return cases


def sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", errors="surrogatepass")).hexdigest()


def kernel_dir() -> Optional[str]:
    """Path of an installed faf-scoring-kernel package, or None."""
    env = os.environ.get("FAF_KERNEL_PATH")
    if env and Path(env).is_dir():
        return env
    local = ROOT / "scripts" / "node_modules" / "faf-scoring-kernel"
    return str(local) if local.is_dir() else None


def oracle_available() -> bool:
    return shutil.which("node") is not None and kernel_dir() is not None


def run_oracle(texts: List[str]) -> Dict[str, Any]:
    """Score texts with the kernel. Returns {"version": ..., "results": [...]}."""
    env = dict(os.environ)
    path = kernel_dir()
    if path:
        env["FAF_KERNEL_PATH"] = path
    proc = subprocess.run(
        ["node", str(ORACLE)],
        input=json.dumps(texts),
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=env,
        check=True,
    )
    return json.loads(proc.stdout)


def compact(entry: Dict[str, Any], slot_order: List[str]) -> Dict[str, Any]:
    """Recorded form of one oracle answer: fields + one letter per slot."""
    if not entry["ok"]:
        return {"ok": False, "error": entry["error"]}
    r = entry["result"]
    if list(r["slots"]) != slot_order:
        raise ValueError("kernel slot order changed")
    return {
        "ok": True,
        "score": r["score"],
        "tier": r["tier"],
        "populated": r["populated"],
        "empty": r["empty"],
        "ignored": r["ignored"],
        "active": r["active"],
        "total": r["total"],
        "slots": "".join(_STATE_CODE[r["slots"][s]] for s in slot_order),
    }


def compact_python(result: Dict[str, Any], slot_order: List[str]) -> Dict[str, Any]:
    """The same recorded form for a faf_sdk ``Mk4Result.to_dict()``."""
    return {
        "ok": True,
        "score": result["score"],
        "tier": result["tier"],
        "populated": result["populated"],
        "empty": result["empty"],
        "ignored": result["ignored"],
        "active": result["active"],
        "total": result["total"],
        "slots": "".join(_STATE_CODE[result["slots"][s]] for s in slot_order),
    }


def load_expected() -> Dict[str, Any]:
    return json.loads(_read(EXPECTED))
