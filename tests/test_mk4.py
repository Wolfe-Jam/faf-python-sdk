"""
Mk4 Parity Tests — ported verbatim from faf-wasm-sdk/src/mk4.rs

Every test uses identical YAML inputs and expected outputs to the Rust source.
"""

import pytest
from faf_sdk.mk4 import (
    score_faf,
    SlotState,
    LicenseTier,
    _is_valid_populated,
    _score_to_tier,
)


# =========================================================================
# SLOT STATE TESTS
# =========================================================================


class TestSlotState:
    def test_empty_yaml_scores_zero(self):
        result = score_faf("empty: true")
        assert result.score == 0
        assert result.populated == 0
        assert result.total == 21

    def test_invalid_yaml_returns_zero(self):
        # Python yaml.safe_load returns None for invalid-ish YAML;
        # Rust returns error. We treat non-dict as empty → score 0.
        result = score_faf("just a string")
        assert result.score == 0
        assert result.total == 21

    def test_project_meta_3_slots(self):
        yaml_content = """
project:
  name: faf-cli
  goal: Universal AI context
  main_language: TypeScript
"""
        result = score_faf(yaml_content)
        assert result.populated == 3
        assert result.score == 14  # 3/21 = 14.28 -> 14

    def test_human_context_6_slots(self):
        yaml_content = """
human_context:
  who: wolfejam
  what: AI context format
  why: Eliminate drift tax
  where: Global
  when: "2025"
  how: FAF specification
"""
        result = score_faf(yaml_content)
        assert result.populated == 6
        assert result.score == 29  # 6/21 = 28.57 -> 29

    def test_full_base_21_slots(self):
        yaml_content = """
project:
  name: faf-cli
  goal: Universal AI context
  main_language: TypeScript
human_context:
  who: wolfejam
  what: AI context format
  why: Eliminate drift tax
  where: Global
  when: "2025"
  how: FAF specification
stack:
  frontend: SvelteKit
  css_framework: Tailwind
  ui_library: Skeleton
  state_management: Svelte stores
  backend: Node.js
  api_type: REST
  runtime: Bun
  database: Supabase
  connection: pg
  hosting: Vercel
  build: Vite
  cicd: GitHub Actions
"""
        result = score_faf(yaml_content)
        assert result.populated == 21
        assert result.total == 21
        assert result.score == 100
        assert result.tier == "\U0001f3c6"  # Trophy

    def test_enterprise_33_slots_total(self):
        result = score_faf("empty: true", LicenseTier.ENTERPRISE)
        assert result.total == 33


# =========================================================================
# SLOTIGNORED TESTS
# =========================================================================


class TestSlotignored:
    def test_slotignored_excluded_from_denominator(self):
        yaml_content = """
project:
  name: faf-cli
  goal: Universal AI context
  main_language: TypeScript
stack:
  frontend: slotignored
  css_framework: slotignored
  ui_library: slotignored
  state_management: slotignored
  backend: Node.js
  api_type: REST
  runtime: Bun
  database: Supabase
  connection: pg
  hosting: Vercel
  build: Vite
  cicd: GitHub Actions
human_context:
  who: wolfejam
  what: AI context format
  why: Eliminate drift tax
  where: Global
  when: "2025"
  how: FAF specification
"""
        result = score_faf(yaml_content)
        assert result.ignored == 4
        assert result.active == 17  # 21 - 4 = 17
        assert result.populated == 17
        assert result.score == 100  # 17/17 = 100%
        assert result.tier == "\U0001f3c6"  # Trophy

    def test_all_slotignored_scores_zero(self):
        yaml_content = """
project:
  name: slotignored
  goal: slotignored
  main_language: slotignored
human_context:
  who: slotignored
  what: slotignored
  why: slotignored
  where: slotignored
  when: slotignored
  how: slotignored
stack:
  frontend: slotignored
  css_framework: slotignored
  ui_library: slotignored
  state_management: slotignored
  backend: slotignored
  api_type: slotignored
  runtime: slotignored
  database: slotignored
  connection: slotignored
  hosting: slotignored
  build: slotignored
  cicd: slotignored
"""
        result = score_faf(yaml_content)
        assert result.ignored == 21
        assert result.active == 0
        assert result.populated == 0
        assert result.score == 0  # 0/0 -> 0, not panic/NaN


# =========================================================================
# PLACEHOLDER REJECTION TESTS
# =========================================================================


class TestPlaceholderRejection:
    def test_placeholder_describe_rejected(self):
        yaml_content = """
project:
  name: test
  goal: Describe your project goal
  main_language: TypeScript
"""
        result = score_faf(yaml_content)
        assert result.populated == 2  # name + main_language, NOT goal

    def test_placeholder_null_rejected(self):
        yaml_content = """
project:
  name: test
  goal: "null"
  main_language: "none"
"""
        result = score_faf(yaml_content)
        assert result.populated == 1  # only name

    def test_placeholder_na_rejected(self):
        yaml_content = """
project:
  name: test
  goal: n/a
  main_language: not applicable
"""
        result = score_faf(yaml_content)
        assert result.populated == 1  # only name

    def test_placeholder_unknown_rejected(self):
        yaml_content = """
project:
  name: test
  goal: unknown
  main_language: Unknown
"""
        result = score_faf(yaml_content)
        assert result.populated == 1  # only name

    def test_placeholder_case_insensitive(self):
        yaml_content = """
project:
  name: test
  goal: "NULL"
  main_language: "NONE"
"""
        result = score_faf(yaml_content)
        assert result.populated == 1  # only name, NULL/NONE rejected

    def test_empty_string_rejected(self):
        yaml_content = """
project:
  name: test
  goal: ""
  main_language: "  "
"""
        result = score_faf(yaml_content)
        assert result.populated == 1  # only name

    def test_all_8_placeholders_rejected(self):
        placeholders = [
            "describe your project goal",
            "development teams",
            "cloud platform",
            "null",
            "none",
            "unknown",
            "n/a",
            "not applicable",
        ]
        for p in placeholders:
            assert not _is_valid_populated(p), f"'{p}' should be rejected"

    def test_valid_strings_accepted(self):
        valid = [
            "faf-cli",
            "Universal AI context format",
            "TypeScript",
            "Rust",
            "SvelteKit",
            "wolfejam",
        ]
        for v in valid:
            assert _is_valid_populated(v), f"'{v}' should be accepted"

    def test_placeholder_with_extra_whitespace(self):
        yaml_content = """
project:
  name: test
  goal: "  null  "
  main_language: TypeScript
"""
        result = score_faf(yaml_content)
        assert result.populated == 2  # "  null  " trimmed = "null" = rejected


# =========================================================================
# VALUE TYPE TESTS
# =========================================================================


class TestValueTypes:
    def test_number_is_populated(self):
        yaml_content = """
project:
  name: test
  goal: 42
  main_language: TypeScript
"""
        result = score_faf(yaml_content)
        assert result.populated == 3

    def test_boolean_is_populated(self):
        yaml_content = """
project:
  name: test
  goal: true
  main_language: TypeScript
"""
        result = score_faf(yaml_content)
        assert result.populated == 3

    def test_sequence_is_populated(self):
        yaml_content = """
project:
  name: test
  goal:
    - item1
    - item2
  main_language: TypeScript
"""
        result = score_faf(yaml_content)
        assert result.populated == 3

    def test_empty_sequence_is_empty(self):
        yaml_content = """
project:
  name: test
  goal: []
  main_language: TypeScript
"""
        result = score_faf(yaml_content)
        assert result.populated == 2  # empty seq = Empty

    def test_empty_mapping_is_empty(self):
        yaml_content = """
project:
  name: test
  goal: {}
  main_language: TypeScript
"""
        result = score_faf(yaml_content)
        assert result.populated == 2  # {} = empty mapping = Empty

    def test_nested_mapping_is_populated(self):
        yaml_content = """
project:
  name: test
  goal:
    primary: Build things
  main_language: TypeScript
"""
        result = score_faf(yaml_content)
        assert result.populated == 3  # non-empty mapping = Populated


# =========================================================================
# TIER TESTS
# =========================================================================


class TestTiers:
    def test_tier_trophy_100(self):
        assert _score_to_tier(100) == "\U0001f3c6"

    def test_tier_gold_99(self):
        assert _score_to_tier(99) == "\U0001f947"

    def test_tier_silver_95(self):
        assert _score_to_tier(95) == "\U0001f948"

    def test_tier_bronze_85(self):
        assert _score_to_tier(85) == "\U0001f949"

    def test_tier_green_70(self):
        assert _score_to_tier(70) == "\U0001f7e2"

    def test_tier_yellow_55(self):
        assert _score_to_tier(55) == "\U0001f7e1"

    def test_tier_red_54(self):
        assert _score_to_tier(54) == "\U0001f534"

    def test_tier_red_0(self):
        assert _score_to_tier(0) == "\U0001f534"

    # Off-by-one boundaries
    def test_tier_boundary_98_is_silver(self):
        assert _score_to_tier(98) == "\U0001f948"

    def test_tier_boundary_94_is_bronze(self):
        assert _score_to_tier(94) == "\U0001f949"

    def test_tier_boundary_84_is_green(self):
        assert _score_to_tier(84) == "\U0001f7e2"

    def test_tier_boundary_69_is_yellow(self):
        assert _score_to_tier(69) == "\U0001f7e1"

    def test_tier_boundary_54_is_red(self):
        assert _score_to_tier(54) == "\U0001f534"


# =========================================================================
# SLOT COUNT TESTS
# =========================================================================


class TestSlotCounts:
    def test_base_has_21_slots(self):
        result = score_faf("empty: true")
        assert len(result.slots) == 21

    def test_enterprise_has_33_slots(self):
        result = score_faf("empty: true", LicenseTier.ENTERPRISE)
        assert len(result.slots) == 33

    def test_enterprise_includes_monorepo_slots(self):
        result = score_faf("empty: true", LicenseTier.ENTERPRISE)
        slot_names = [name for name, _ in result.slots]
        assert "monorepo.packages_count" in slot_names
        assert "monorepo.build_orchestrator" in slot_names
        assert "monorepo.versioning_strategy" in slot_names
        assert "monorepo.shared_configs" in slot_names
        assert "monorepo.remote_cache" in slot_names

    def test_base_slots_are_subset_of_enterprise(self):
        base = score_faf("empty: true", LicenseTier.BASE)
        enterprise = score_faf("empty: true", LicenseTier.ENTERPRISE)
        base_names = [name for name, _ in base.slots]
        enterprise_names = [name for name, _ in enterprise.slots]
        for name in base_names:
            assert name in enterprise_names, f"Base slot {name} missing from enterprise"


# =========================================================================
# EDGE CASE TESTS
# =========================================================================


class TestEdgeCases:
    def test_bare_yaml_null_is_empty(self):
        yaml_content = """
project:
  name: test
  goal: null
  main_language: TypeScript
"""
        result = score_faf(yaml_content)
        assert result.populated == 2  # name + main_language, NOT goal

    def test_bare_yaml_tilde_null_is_empty(self):
        yaml_content = """
project:
  name: test
  goal: ~
  main_language: TypeScript
"""
        result = score_faf(yaml_content)
        assert result.populated == 2

    def test_slotignored_case_sensitive(self):
        yaml_content = """
project:
  name: test
  goal: Slotignored
  main_language: SLOTIGNORED
"""
        result = score_faf(yaml_content)
        assert result.populated == 3  # capitalized = valid strings
        assert result.ignored == 0

    def test_to_dict_output(self):
        yaml_content = """
project:
  name: test
  goal: A real goal
  main_language: Rust
"""
        result = score_faf(yaml_content)
        d = result.to_dict()
        assert d["score"] == 14
        assert d["populated"] == 3
        assert d["total"] == 21
        assert d["slots"]["project.name"] == "populated"
        assert d["slots"]["project.goal"] == "populated"
        assert d["slots"]["human_context.who"] == "empty"

    def test_to_dict_shows_slotignored(self):
        yaml_content = """
project:
  name: test
  goal: slotignored
  main_language: Rust
"""
        result = score_faf(yaml_content)
        d = result.to_dict()
        assert d["slots"]["project.goal"] == "slotignored"
        assert d["ignored"] == 1


# =========================================================================
# PARITY SNAPSHOT TESTS
# =========================================================================


class TestParity:
    def test_parity_minimal_faf(self):
        result = score_faf("project:\n  name: test")
        assert result.populated == 1
        assert result.total == 21
        assert result.score == 5  # 1/21 = 4.76 -> 5

    def test_parity_score_rounding(self):
        yaml_content = """
project:
  name: test
  goal: real goal
  main_language: Rust
"""
        result = score_faf(yaml_content)
        assert result.score == 14  # 3/21 = 14.285... -> 14

    def test_parity_half_filled(self):
        yaml_content = """
project:
  name: test
  goal: real goal
  main_language: Rust
human_context:
  who: wolfejam
  what: AI context
  why: Drift tax
  where: Global
  when: "2025"
  how: FAF
stack:
  frontend: React
  backend: Node.js
"""
        result = score_faf(yaml_content)
        assert result.populated == 11
        assert result.score == 52  # 11/21 = 52.38 -> 52
        assert result.tier == "\U0001f534"  # Red

    def test_mixed_enterprise_base_plus_some_enterprise(self):
        yaml_content = """
project:
  name: mixed-test
  goal: Partial enterprise
  main_language: TypeScript
human_context:
  who: team
  what: platform
  why: scale
  where: cloud
  when: "2026"
  how: microservices
stack:
  frontend: React
  css_framework: Tailwind
  ui_library: Radix
  state_management: Zustand
  backend: Node.js
  api_type: REST
  runtime: Bun
  database: PostgreSQL
  connection: Prisma
  hosting: AWS
  build: Vite
  cicd: GitHub Actions
monorepo:
  packages_count: 5
  build_orchestrator: Lerna
  versioning_strategy: fixed
"""
        result = score_faf(yaml_content, LicenseTier.ENTERPRISE)
        assert result.populated == 24  # 21 base + 3 monorepo
        assert result.total == 33
        assert result.score == 73  # 24/33 = 72.7 -> 73
        assert result.tier == "\U0001f7e2"  # Green

    def test_enterprise_full_33_slots_populated(self):
        yaml_content = """
project:
  name: enterprise-test
  goal: Full monorepo
  main_language: TypeScript
human_context:
  who: team
  what: platform
  why: scale
  where: cloud
  when: "2026"
  how: microservices
stack:
  frontend: React
  css_framework: Tailwind
  ui_library: Radix
  state_management: Zustand
  backend: Node.js
  api_type: GraphQL
  runtime: Bun
  database: PostgreSQL
  connection: Prisma
  hosting: AWS
  build: Turborepo
  cicd: GitHub Actions
  monorepo_tool: pnpm workspaces
  package_manager: pnpm
  workspaces: "apps/*, packages/*"
  admin: Retool
  cache: Redis
  search: Elasticsearch
  storage: S3
monorepo:
  packages_count: 24
  build_orchestrator: Turborepo
  versioning_strategy: independent
  shared_configs: "eslint, tsconfig, prettier"
  remote_cache: Vercel Remote Cache
"""
        result = score_faf(yaml_content, LicenseTier.ENTERPRISE)
        assert result.populated == 33
        assert result.total == 33
        assert result.score == 100
        assert result.tier == "\U0001f3c6"  # Trophy
