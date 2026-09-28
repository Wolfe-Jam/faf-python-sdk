"""
Mk4 Championship Engine — always-33 scoring

Ported from faf-kernel (Wolfe-Jam/faf-rust, crates/faf-kernel/src/score.rs).
npm ``faf-scoring-kernel@3.0.0`` is the WASM build of the same kernel, and the
parity harness (tests/test_always33_parity.py) checks this module against it.

Philosophy: Populated, Empty, or Slotignored.
Score = populated ÷ active, where active = 33 − slotignored.
"""

import math
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Tuple, Union

from . import _kernel_yaml as ky


class SlotState(Enum):
    EMPTY = "empty"
    POPULATED = "populated"
    SLOTIGNORED = "slotignored"


class LicenseTier(Enum):
    """Kept for API compatibility. Scoring is always 33 slots for every tier."""

    BASE = "base"
    ENTERPRISE = "enterprise"


@dataclass
class Mk4Result:
    score: int
    tier: str
    populated: int
    ignored: int
    active: int
    total: int
    slots: List[Tuple[str, SlotState]]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "score": self.score,
            "tier": self.tier,
            "populated": self.populated,
            "empty": self.total - self.populated - self.ignored,
            "ignored": self.ignored,
            "active": self.active,
            "total": self.total,
            "slots": {name: state.value for name, state in self.slots},
        }


#: The total number of FAF slots. Always 33; a "21-base" file carries the 12
#: enterprise slots as ``slotignored``.
TOTAL_SLOTS = 33

#: The Universal DNA Map — the 33 canonical Mk4 slot paths, in kernel order.
SLOTS: Tuple[str, ...] = (
    # Project Meta (3)
    "project.name",
    "project.goal",
    "project.main_language",
    # Human Context (6)
    "human_context.who",
    "human_context.what",
    "human_context.why",
    "human_context.where",
    "human_context.when",
    "human_context.how",
    # Frontend Stack (4)
    "stack.framework",
    "stack.css",
    "stack.ui_library",
    "stack.state",
    # Backend Stack (5)
    "stack.backend",
    "stack.api",
    "stack.runtime",
    "stack.db",
    "stack.connection",
    # Universal Stack (3)
    "stack.hosting",
    "stack.build",
    "stack.cicd",
    # Enterprise Infra (5)
    "stack.monorepo_tool",
    "stack.pkg_manager",
    "stack.workspaces",
    "monorepo.packages_count",
    "monorepo.build_orchestrator",
    # Enterprise App (4)
    "stack.admin",
    "stack.cache",
    "stack.search",
    "stack.storage",
    # Enterprise Ops (3)
    "monorepo.versioning_strategy",
    "monorepo.shared_configs",
    "monorepo.remote_cache",
)

#: Legacy key read when the canonical short key is empty (kernel legacy_alias_for).
LEGACY_ALIASES: Dict[str, str] = {
    "stack.framework": "stack.frontend",
    "stack.css": "stack.css_framework",
    "stack.state": "stack.state_management",
    "stack.api": "stack.api_type",
    "stack.db": "stack.database",
    "stack.pkg_manager": "stack.package_manager",
}

# Placeholder strings — case-insensitive rejection (kernel is_valid_populated_string).
_PLACEHOLDERS = frozenset([
    "describe your project goal",
    "development teams",
    "cloud platform",
    "null",
    "none",
    "unknown",
    "tbd",
    "todo",
    "n/a",
    "not applicable",
])

# Rust char::is_whitespace (Unicode White_Space) — what str::trim strips.
# Python's str.strip() also strips U+001C..U+001F, which Rust keeps.
_RUST_WHITESPACE = (
    "\u0009\u000a\u000b\u000c\u000d \u0085  "
    "           "
    "    　"
)


def score_faf(
    yaml_content: Union[str, bytes],
    tier: LicenseTier = LicenseTier.BASE,
) -> Mk4Result:
    """Calculate the official FAF Mk4 score — always 33 slots, same as faf-kernel.

    Every file is scored against all 33 slots. The 12 enterprise slots count
    unless the file marks them ``slotignored``; ``slotignored`` slots drop out
    of the denominator (``active = 33 - ignored``). A file with the 21 base
    slots filled and no markers scores 64% (21/33); the same file with the 12
    enterprise slots marked ``slotignored`` scores 100% (21/21).

    ``tier`` is still accepted so existing callers keep working, but it no
    longer changes the slot count: ``LicenseTier.BASE`` and
    ``LicenseTier.ENTERPRISE`` give the same result.

    YAML the kernel cannot read (syntax errors, duplicate keys, more than one
    document, ...) scores 0 with every slot empty. It does not raise.
    """
    del tier  # accepted for compatibility; always-33 ignores it
    try:
        if isinstance(yaml_content, bytes):
            yaml_content = yaml_content.decode("utf-8")
        doc = ky.load(yaml_content)
    except (ky.KernelYamlError, UnicodeDecodeError, RecursionError):
        doc = None

    populated = 0
    ignored = 0
    slots: List[Tuple[str, SlotState]] = []
    for path in SLOTS:
        state = _slot_state(doc, path)
        if state == SlotState.POPULATED:
            populated += 1
        elif state == SlotState.SLOTIGNORED:
            ignored += 1
        slots.append((path, state))

    active = TOTAL_SLOTS - ignored
    score_val = 0 if active == 0 else _round_half_away((populated / active) * 100.0)

    return Mk4Result(
        score=score_val,
        tier=_score_to_tier(score_val),
        populated=populated,
        ignored=ignored,
        active=active,
        total=TOTAL_SLOTS,
        slots=slots,
    )


def _round_half_away(x: float) -> int:
    """Rust ``f64::round`` (half away from zero) for x >= 0. Python's round()
    is half-to-even, which differs at e.g. 1/8 = 12.5%."""
    fl = math.floor(x)
    return int(fl) + 1 if x - fl >= 0.5 else int(fl)


def _slot_state(doc: Any, path: str) -> SlotState:
    """Canonical path first, legacy alias fallback (kernel slot_state)."""
    state = _walk_path_state(doc, path)
    if state == SlotState.EMPTY:
        legacy = LEGACY_ALIASES.get(path)
        if legacy is not None:
            return _walk_path_state(doc, legacy)
    return state


def _walk_path_state(doc: Any, path: str) -> SlotState:
    """Walk a dotted path and classify the value (kernel walk_path_state)."""
    current = doc
    for part in path.split("."):
        mapping = ky.untag(current)
        if not isinstance(mapping, ky.Mapping):
            return SlotState.EMPTY
        key = ky.str_key(part)
        if key not in mapping:
            return SlotState.EMPTY
        current = mapping[key]

    if isinstance(current, str):
        s = current.strip(_RUST_WHITESPACE)
        if s == "slotignored":
            return SlotState.SLOTIGNORED
        if _is_valid_populated(s):
            return SlotState.POPULATED
        return SlotState.EMPTY
    if isinstance(current, (bool, int, float)):
        return SlotState.POPULATED
    if isinstance(current, (list, dict)):
        return SlotState.POPULATED if current else SlotState.EMPTY
    # Null and tagged values (e.g. `!custom x`) are Empty.
    return SlotState.EMPTY


def _is_valid_populated(s: str) -> bool:
    """Placeholder rejection (kernel is_valid_populated_string)."""
    return len(s) > 0 and s.lower() not in _PLACEHOLDERS


def _score_to_tier(score: int) -> str:
    """Canonical tier name (kernel tier_name, source of truth: faf-cli tiers.ts)."""
    if score >= 100:
        return "TROPHY"
    if score >= 99:
        return "GOLD"
    if score >= 95:
        return "SILVER"
    if score >= 85:
        return "BRONZE"
    if score >= 70:
        return "GREEN"
    if score >= 55:
        return "YELLOW"
    if score >= 1:
        return "RED"
    return "WHITE"
