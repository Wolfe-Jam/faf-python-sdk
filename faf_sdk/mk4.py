"""
Mk4 Championship Engine — 33-Slot Scoring

Ported from faf-wasm-sdk/src/mk4.rs (100% parity).
Philosophy: Populated, Empty, or Slotignored.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Tuple, Dict, Any

import yaml


class SlotState(Enum):
    EMPTY = "empty"
    POPULATED = "populated"
    SLOTIGNORED = "slotignored"


class LicenseTier(Enum):
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


# 8 placeholder strings — case-insensitive rejection (mk4.rs lines 224-233)
_PLACEHOLDERS = frozenset([
    "describe your project goal",
    "development teams",
    "cloud platform",
    "null",
    "none",
    "unknown",
    "n/a",
    "not applicable",
])


def score_faf(yaml_content: str, tier: LicenseTier = LicenseTier.BASE) -> Mk4Result:
    """Calculate the official FAF Mk4 score from YAML content."""
    try:
        doc = yaml.safe_load(yaml_content)
    except yaml.YAMLError:
        doc = {}
    if not isinstance(doc, dict):
        doc = {}

    slot_paths = _get_slot_paths(tier)
    populated = 0
    ignored = 0
    slots: List[Tuple[str, SlotState]] = []

    for path in slot_paths:
        state = _get_slot_state(doc, path)
        if state == SlotState.POPULATED:
            populated += 1
        elif state == SlotState.SLOTIGNORED:
            ignored += 1
        slots.append((path, state))

    total = 33 if tier == LicenseTier.ENTERPRISE else 21
    active = total - ignored

    if active == 0:
        score_val = 0
    else:
        score_val = round((populated / active) * 100)

    return Mk4Result(
        score=score_val,
        tier=_score_to_tier(score_val),
        populated=populated,
        ignored=ignored,
        active=active,
        total=total,
        slots=slots,
    )


def _get_slot_paths(tier: LicenseTier) -> List[str]:
    """The Universal DNA Map — exact order from mk4.rs lines 126-176."""
    slots = [
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
        "stack.frontend",
        "stack.css_framework",
        "stack.ui_library",
        "stack.state_management",
        # Backend Stack (5)
        "stack.backend",
        "stack.api_type",
        "stack.runtime",
        "stack.database",
        "stack.connection",
        # Universal Stack (3)
        "stack.hosting",
        "stack.build",
        "stack.cicd",
    ]

    if tier == LicenseTier.ENTERPRISE:
        slots.extend([
            # Enterprise Infra (5)
            "stack.monorepo_tool",
            "stack.package_manager",
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
        ])

    return slots


def _get_slot_state(doc: dict, path: str) -> SlotState:
    """Determine the state of a specific slot (mk4.rs lines 179-219)."""
    parts = path.split(".")
    current = doc

    for part in parts:
        if isinstance(current, dict) and part in current:
            current = current[part]
        else:
            return SlotState.EMPTY

    # None = YAML null/~ (mk4.rs line 217: _ => Empty)
    if current is None:
        return SlotState.EMPTY

    # String values (mk4.rs lines 192-200)
    if isinstance(current, str):
        s = current.strip()
        if s == "slotignored":
            return SlotState.SLOTIGNORED
        if _is_valid_populated(s):
            return SlotState.POPULATED
        return SlotState.EMPTY

    # Numbers and bools — always Populated (mk4.rs line 202)
    if isinstance(current, (int, float, bool)):
        return SlotState.POPULATED

    # Sequences — Populated if non-empty (mk4.rs lines 203-209)
    if isinstance(current, list):
        return SlotState.POPULATED if current else SlotState.EMPTY

    # Mappings — Populated if non-empty (mk4.rs lines 210-216)
    if isinstance(current, dict):
        return SlotState.POPULATED if current else SlotState.EMPTY

    return SlotState.EMPTY


def _is_valid_populated(s: str) -> bool:
    """Placeholder rejection — 8 magic strings (mk4.rs lines 223-236)."""
    return len(s) > 0 and s.lower() not in _PLACEHOLDERS


def _score_to_tier(score: int) -> str:
    """Mk4 official tier calculation — aligned with faf-cli v6 tiers.ts."""
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
