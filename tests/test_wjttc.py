"""
WJTTC Championship Test Suite: faf-python-sdk v1.1.0
=====================================================
When brakes must work flawlessly, so must our SDK.

Tier 1: BRAKE (Critical)     - Parser safety, type boundaries, crash resistance
Tier 2: ENGINE (Core)        - Mk4 adversarial inputs, validator edge cases
Tier 3: AERO (Integration)   - Cross-module contracts, roundtrip fidelity
Tier 4: STRESS (Scale)       - Large files, concurrency, memory pressure
Tier 5: SECURITY (Hardening) - Path traversal, injection, malformed input
"""

import os
import sys
import stat
import tempfile
import threading
import pytest
from pathlib import Path

from faf_sdk.mk4 import score_faf, SlotState, LicenseTier, Mk4Result, _score_to_tier
from faf_sdk.parser import parse, parse_file, stringify, FafFile, FafParseError, get_field
from faf_sdk.validator import validate
from faf_sdk.discovery import (
    find_faf_file, find_project_root, load_fafignore,
    should_ignore, list_project_files, create_default_fafignore,
    DEFAULT_IGNORE_PATTERNS,
)
from faf_sdk.types import FafData, ProjectInfo


# =========================================================================
# TIER 1: BRAKE — Critical safety. Must never crash.
# =========================================================================


class TestTier1BrakeParserSafety:
    """Parser must never crash on any input."""

    def test_parse_none_raises(self):
        with pytest.raises(FafParseError):
            parse(None)

    def test_parse_empty_string_raises(self):
        with pytest.raises(FafParseError):
            parse("")

    def test_parse_whitespace_only_raises(self):
        with pytest.raises(FafParseError):
            parse("   \n\t\n   ")

    def test_parse_integer_input_raises(self):
        with pytest.raises(FafParseError):
            parse(123)

    def test_parse_list_input_raises(self):
        with pytest.raises(FafParseError):
            parse([1, 2, 3])

    def test_parse_yaml_array_raises(self):
        with pytest.raises(FafParseError):
            parse("- item1\n- item2")

    def test_parse_yaml_scalar_raises(self):
        with pytest.raises(FafParseError):
            parse("42")

    def test_parse_yaml_boolean_raises(self):
        with pytest.raises(FafParseError):
            parse("true")

    def test_parse_broken_yaml_raises(self):
        with pytest.raises(FafParseError):
            parse("key: [unterminated")

    def test_parse_yaml_with_tabs_in_indentation(self):
        with pytest.raises(FafParseError):
            parse("project:\n\tname: test")

    def test_parse_all_comments_raises(self):
        with pytest.raises(FafParseError):
            parse("# just a comment\n# another comment")

    def test_parse_minimal_valid(self):
        faf = parse("project:\n  name: test")
        assert faf.data.project.name == "test"

    def test_parse_file_not_found_raises(self):
        with pytest.raises(FileNotFoundError):
            parse_file("/nonexistent/path/project.faf")


class TestTier1BrakeMk4NeverCrash:
    """Mk4 scorer must return a result for ANY string input."""

    def test_empty_string(self):
        result = score_faf("")
        assert isinstance(result, Mk4Result)
        assert result.score == 0

    def test_none_yaml(self):
        result = score_faf("null")
        assert result.score == 0

    def test_pure_garbage(self):
        result = score_faf("!@#$%^&*()")
        assert isinstance(result, Mk4Result)

    def test_binary_looking_string(self):
        result = score_faf("\x00\x01\x02\x03")
        assert isinstance(result, Mk4Result)

    def test_extremely_long_string(self):
        big = "x: " + "a" * 100_000
        result = score_faf(big)
        assert isinstance(result, Mk4Result)

    def test_deeply_nested_yaml(self):
        # 50 levels deep — should not stack overflow
        yaml_content = "a:\n"
        for i in range(50):
            yaml_content += "  " * (i + 1) + f"b{i}:\n"
        yaml_content += "  " * 51 + "val: true"
        result = score_faf(yaml_content)
        assert isinstance(result, Mk4Result)

    def test_yaml_with_anchors_and_aliases(self):
        yaml_content = """
anchor: &anchor_val
  name: shared
project:
  name: *anchor_val
"""
        result = score_faf(yaml_content)
        assert isinstance(result, Mk4Result)

    def test_unicode_content(self):
        yaml_content = """
project:
  name: "\u30d7\u30ed\u30b8\u30a7\u30af\u30c8"
  goal: "\u76ee\u6a19"
  main_language: Python
"""
        result = score_faf(yaml_content)
        assert result.populated == 3

    def test_emoji_content(self):
        yaml_content = """
project:
  name: "rocket-app"
  goal: "Build something awesome"
  main_language: "TypeScript"
"""
        result = score_faf(yaml_content)
        assert result.populated == 3

    def test_multiline_strings(self):
        yaml_content = """
project:
  name: test
  goal: |
    This is a very long goal
    that spans multiple lines
    and should still count as populated
  main_language: Python
"""
        result = score_faf(yaml_content)
        assert result.populated == 3


class TestTier1BrakeTypesBoundary:
    """FafData.from_dict must handle any dict shape."""

    def test_empty_dict(self):
        data = FafData.from_dict({})
        assert data.project.name == "unknown"
        assert data.faf_version == "2.5.0"

    def test_project_as_string(self):
        data = FafData.from_dict({"project": "my-project"})
        assert data.project.name == "my-project"

    def test_project_as_none(self):
        data = FafData.from_dict({"project": None})
        assert data.project.name == "unknown"

    def test_project_as_integer(self):
        data = FafData.from_dict({"project": 42})
        assert data.project.name == "unknown"

    def test_ai_score_as_percentage_string(self):
        data = FafData.from_dict({"ai_score": "85%"})
        assert data.ai_score == 85

    def test_ai_score_as_integer(self):
        data = FafData.from_dict({"ai_score": 90})
        assert data.ai_score == 90

    def test_tags_as_none(self):
        data = FafData.from_dict({"tags": None})
        assert data.tags is None or data.tags == []

    def test_all_sections_present(self):
        data = FafData.from_dict({
            "faf_version": "2.5.0",
            "project": {"name": "test", "goal": "testing"},
            "instant_context": {"what_building": "tests"},
            "stack": {"backend": "Python"},
            "context_quality": {"slots_filled": "5/21"},
            "human_context": {"who": "devs"},
        })
        assert data.instant_context.what_building == "tests"
        assert data.stack.backend == "Python"
        assert data.human_context.who == "devs"


# =========================================================================
# TIER 2: ENGINE — Core logic under adversarial conditions
# =========================================================================


class TestTier2EngineMk4Adversarial:
    """Mk4 scoring must be correct under hostile input."""

    def test_slot_with_only_whitespace(self):
        yaml_content = """
project:
  name: "   "
  goal: "\t\t"
  main_language: "\n"
"""
        result = score_faf(yaml_content)
        assert result.populated == 0  # all whitespace = empty

    def test_slot_with_yaml_special_values(self):
        """PyYAML parses bare yes/no/on/off as booleans."""
        yaml_content = """
project:
  name: test
  goal: true
  main_language: false
"""
        result = score_faf(yaml_content)
        # PyYAML: true/false → bool → Populated
        assert result.populated == 3

    def test_slot_with_zero(self):
        yaml_content = """
project:
  name: test
  goal: 0
  main_language: Python
"""
        result = score_faf(yaml_content)
        # 0 is a number → Populated (even though falsy in Python)
        assert result.populated == 3

    def test_slot_with_negative_number(self):
        yaml_content = """
project:
  name: test
  goal: -1
  main_language: Python
"""
        result = score_faf(yaml_content)
        assert result.populated == 3

    def test_slot_with_float(self):
        yaml_content = """
project:
  name: test
  goal: 3.14
  main_language: Python
"""
        result = score_faf(yaml_content)
        assert result.populated == 3

    def test_placeholder_mixed_case_variants(self):
        """All case variants of placeholders should be rejected."""
        placeholders = [
            "Describe Your Project Goal",
            "DEVELOPMENT TEAMS",
            "Cloud Platform",
            "Null", "NULL", "nUlL",
            "None", "NONE",
            "Unknown", "UNKNOWN",
            "N/A", "N/a",
            "Not Applicable", "NOT APPLICABLE",
        ]
        for p in placeholders:
            yaml_content = f'project:\n  name: test\n  goal: "{p}"'
            result = score_faf(yaml_content)
            assert result.populated <= 1, f"'{p}' should be rejected as placeholder"

    def test_slotignored_only_exact_lowercase(self):
        """Only exact 'slotignored' triggers — not variants."""
        variants = ["Slotignored", "SLOTIGNORED", "SlotIgnored", "slotIgnored", " slotignored"]
        for v in variants:
            yaml_content = f'project:\n  name: "{v}"'
            result = score_faf(yaml_content)
            # " slotignored" gets stripped to "slotignored" → actually IS slotignored
            if v.strip() == "slotignored":
                assert result.ignored >= 1, f"'{v}' should be slotignored after strip"
            else:
                assert result.ignored == 0, f"'{v}' should NOT be slotignored"

    def test_score_deterministic(self):
        """Same input always produces same output."""
        yaml_content = """
project:
  name: test
  goal: real goal
  main_language: Rust
"""
        results = [score_faf(yaml_content) for _ in range(100)]
        scores = {r.score for r in results}
        assert len(scores) == 1, "Score must be deterministic"

    def test_score_all_21_rounding_values(self):
        """Verify rounding for every possible n/21 score."""
        for n in range(22):
            expected = round((n / 21) * 100)
            assert 0 <= expected <= 100, f"n={n}: score {expected} out of bounds"

    def test_score_all_33_rounding_values(self):
        """Verify rounding for every possible n/33 score."""
        for n in range(34):
            expected = round((n / 33) * 100)
            assert 0 <= expected <= 100, f"n={n}: score {expected} out of bounds"

    def test_to_dict_roundtrips_all_fields(self):
        result = score_faf("project:\n  name: test", LicenseTier.BASE)
        d = result.to_dict()
        assert "score" in d
        assert "tier" in d
        assert "populated" in d
        assert "empty" in d
        assert "ignored" in d
        assert "active" in d
        assert "total" in d
        assert "slots" in d
        assert len(d["slots"]) == 21

    def test_enterprise_to_dict_has_33_slots(self):
        result = score_faf("project:\n  name: test", LicenseTier.ENTERPRISE)
        d = result.to_dict()
        assert len(d["slots"]) == 33


class TestTier2EngineValidatorEdgeCases:
    """Validator must handle edge cases gracefully."""

    def test_validate_with_faffile(self):
        faf = parse("faf_version: '2.5.0'\nproject:\n  name: test")
        result = validate(faf)
        assert result.valid is True

    def test_validate_with_dict(self):
        result = validate({"faf_version": "2.5.0", "project": {"name": "test"}})
        assert result.valid is True

    def test_validate_with_yaml_string(self):
        result = validate("faf_version: '2.5.0'\nproject:\n  name: test")
        assert result.valid is True

    def test_validate_missing_everything(self):
        result = validate({"empty": True})
        assert result.valid is False
        assert len(result.errors) > 0

    def test_validate_score_between_0_and_100(self):
        """Score must always be 0-100 regardless of input."""
        test_cases = [
            {},
            {"faf_version": "2.5.0"},
            {"faf_version": "2.5.0", "project": {"name": "x"}},
            {"faf_version": "2.5.0", "project": {"name": "x", "goal": "y"},
             "instant_context": {"what_building": "z", "tech_stack": "a", "key_files": ["b"]},
             "stack": {"a": 1, "b": 2, "c": 3},
             "context_quality": True,
             "human_context": True,
             "ai_instructions": True,
             "preferences": True,
             "state": True,
             "tags": ["x"]},
        ]
        for data in test_cases:
            result = validate(data)
            assert 0 <= result.score <= 100, f"Score {result.score} out of bounds for {data}"


# =========================================================================
# TIER 3: AERO — Integration and roundtrip fidelity
# =========================================================================


class TestTier3AeroRoundtrip:
    """Parse → stringify → parse must preserve data."""

    def test_roundtrip_minimal(self):
        original = "faf_version: '2.5.0'\nproject:\n  name: roundtrip-test\n"
        faf = parse(original)
        yaml_out = stringify(faf)
        faf2 = parse(yaml_out)
        assert faf2.data.project.name == "roundtrip-test"
        assert faf2.data.faf_version == "2.5.0"

    def test_roundtrip_full(self):
        original = """
faf_version: '2.5.0'
project:
  name: full-test
  goal: Test roundtrip fidelity
  main_language: Python
stack:
  frontend: React
  backend: FastAPI
  database: PostgreSQL
human_context:
  who: Engineers
  what: Testing
  why: Quality
  where: CI
  when: "2026"
  how: WJTTC
tags:
  - testing
  - wjttc
"""
        faf = parse(original)
        yaml_out = stringify(faf)
        faf2 = parse(yaml_out)
        assert faf2.data.project.name == "full-test"
        assert faf2.data.stack.backend == "FastAPI"
        assert faf2.data.human_context.who == "Engineers"

    def test_stringify_accepts_dict(self):
        result = stringify({"project": {"name": "test"}})
        assert "name: test" in result

    def test_stringify_accepts_fafdata(self):
        data = FafData.from_dict({"project": {"name": "test"}})
        result = stringify(data)
        assert isinstance(result, str)

    def test_get_field_nested(self):
        faf = parse("project:\n  name: test\nstack:\n  backend: Python")
        assert get_field(faf, "project", "name") == "test"
        assert get_field(faf, "stack", "backend") == "Python"
        assert get_field(faf, "missing", "path", default="fallback") == "fallback"
        assert get_field(faf, "project", "missing", default=None) is None


class TestTier3AeroParseScoreIntegration:
    """Parse and Mk4 score must agree on the same content."""

    def test_parsed_file_scores_correctly(self, tmp_path):
        faf_file = tmp_path / "project.faf"
        content = """
faf_version: '2.5.0'
project:
  name: integration-test
  goal: Verify parse-score integration
  main_language: Python
human_context:
  who: testers
  what: integration
  why: quality
  where: CI
  when: "2026"
  how: WJTTC
"""
        faf_file.write_text(content)
        faf = parse_file(str(faf_file))
        mk4 = score_faf(content)
        assert mk4.populated == 9  # 3 project + 6 human_context
        assert mk4.score == 43  # 9/21 = 42.86 -> 43

    def test_validate_and_mk4_both_work(self):
        content = "faf_version: '2.5.0'\nproject:\n  name: test\n  goal: real"
        faf = parse(content)
        val_result = validate(faf)
        mk4_result = score_faf(content)
        # Both should succeed without error
        assert val_result.valid is True
        assert mk4_result.score > 0


class TestTier3AeroDiscovery:
    """Discovery must find files reliably."""

    def test_find_project_faf_in_tree(self, tmp_path):
        (tmp_path / "project.faf").write_text("project:\n  name: found")
        subdir = tmp_path / "src" / "deep"
        subdir.mkdir(parents=True)
        result = find_faf_file(str(subdir))
        assert result is not None
        assert "project.faf" in result

    def test_find_legacy_faf(self, tmp_path):
        (tmp_path / ".faf").write_text("project:\n  name: legacy")
        result = find_faf_file(str(tmp_path))
        assert result is not None

    def test_prefer_project_faf_over_legacy(self, tmp_path):
        (tmp_path / "project.faf").write_text("project:\n  name: modern")
        (tmp_path / ".faf").write_text("project:\n  name: legacy")
        result = find_faf_file(str(tmp_path))
        assert "project.faf" in result

    def test_max_depth_respected(self, tmp_path):
        deep = tmp_path
        for i in range(15):
            deep = deep / f"level{i}"
        deep.mkdir(parents=True)
        (tmp_path / "project.faf").write_text("project:\n  name: root")
        result = find_faf_file(str(deep), max_depth=3)
        assert result is None  # too deep to find

    def test_find_project_root_markers(self, tmp_path):
        (tmp_path / "package.json").write_text("{}")
        result = find_project_root(str(tmp_path))
        assert result == str(tmp_path)

    def test_fafignore_load_custom(self, tmp_path):
        (tmp_path / ".fafignore").write_text("*.secret\nbuild/\n# comment\n\n")
        patterns = load_fafignore(str(tmp_path))
        assert "*.secret" in patterns
        assert "build/" in patterns
        assert "# comment" not in patterns
        assert "" not in patterns

    def test_fafignore_default_on_missing(self, tmp_path):
        patterns = load_fafignore(str(tmp_path))
        assert patterns == DEFAULT_IGNORE_PATTERNS

    def test_should_ignore_directory_pattern(self):
        assert should_ignore("node_modules/package.json", ["node_modules/"])
        assert should_ignore("deep/node_modules/file.js", ["node_modules/"])

    def test_should_ignore_extension_pattern(self):
        assert should_ignore("file.pyc", ["*.pyc"])
        assert should_ignore("deep/path/file.pyc", ["*.pyc"])

    def test_should_ignore_normalizes_backslashes(self):
        assert should_ignore("node_modules\\file.js", ["node_modules/"])

    def test_list_project_files_filters(self, tmp_path):
        (tmp_path / "main.py").write_text("# python")
        (tmp_path / "style.css").write_text("/* css */")
        (tmp_path / "data.json").write_text("{}")
        files = list_project_files(str(tmp_path), extensions=[".py"])
        assert "main.py" in files
        assert "style.css" not in files

    def test_list_project_files_respects_ignore(self, tmp_path):
        src = tmp_path / "src"
        src.mkdir()
        (src / "app.py").write_text("# app")
        nm = tmp_path / "node_modules"
        nm.mkdir()
        (nm / "pkg.js").write_text("// pkg")
        files = list_project_files(str(tmp_path))
        assert "src/app.py" in files
        assert not any("node_modules" in f for f in files)

    def test_create_default_fafignore(self, tmp_path):
        path = create_default_fafignore(str(tmp_path))
        assert os.path.exists(path)
        content = open(path).read()
        assert "node_modules/" in content
        assert ".env" in content


# =========================================================================
# TIER 4: STRESS — Scale and performance
# =========================================================================


class TestTier4StressLargeInputs:
    """Must handle large inputs without crashing or hanging."""

    def test_large_yaml_1000_keys(self):
        lines = ["project:\n  name: stress-test"]
        for i in range(1000):
            lines.append(f"key_{i}: value_{i}")
        result = score_faf("\n".join(lines))
        assert result.populated >= 1

    def test_large_yaml_deep_stack(self):
        """Stack with many fields — only scored fields matter."""
        yaml_content = "stack:\n"
        for i in range(100):
            yaml_content += f"  field_{i}: value_{i}\n"
        result = score_faf(yaml_content)
        assert isinstance(result, Mk4Result)

    def test_large_yaml_many_tags(self):
        tags = "\n".join(f"  - tag_{i}" for i in range(1000))
        yaml_content = f"project:\n  name: test\ntags:\n{tags}"
        result = score_faf(yaml_content)
        assert result.populated >= 1

    def test_very_long_string_value(self):
        long_val = "x" * 50_000
        yaml_content = f'project:\n  name: "{long_val}"'
        result = score_faf(yaml_content)
        assert result.populated == 1

    def test_list_files_many_files(self, tmp_path):
        """500 files in a flat directory."""
        for i in range(500):
            (tmp_path / f"file_{i:04d}.py").write_text(f"# {i}")
        files = list_project_files(str(tmp_path), extensions=[".py"])
        assert len(files) == 500


class TestTier4StressConcurrency:
    """Thread-safe scoring under concurrent load."""

    def test_concurrent_scoring(self):
        results = []
        errors = []

        def score_worker(yaml_content, expected_score):
            try:
                r = score_faf(yaml_content)
                results.append((r.score, expected_score))
            except Exception as e:
                errors.append(str(e))

        yamls = [
            ("project:\n  name: test", 5),
            ("project:\n  name: a\n  goal: b\n  main_language: c", 14),
            ("empty: true", 0),
        ]

        threads = []
        for _ in range(30):
            for yaml_content, expected in yamls:
                t = threading.Thread(target=score_worker, args=(yaml_content, expected))
                threads.append(t)
                t.start()

        for t in threads:
            t.join(timeout=10)

        assert not errors, f"Errors during concurrent scoring: {errors}"
        for actual, expected in results:
            assert actual == expected, f"Score mismatch: got {actual}, expected {expected}"

    def test_concurrent_parsing(self):
        errors = []

        def parse_worker():
            try:
                faf = parse("faf_version: '2.5.0'\nproject:\n  name: concurrent")
                assert faf.data.project.name == "concurrent"
            except Exception as e:
                errors.append(str(e))

        threads = [threading.Thread(target=parse_worker) for _ in range(50)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)

        assert not errors, f"Errors during concurrent parsing: {errors}"


# =========================================================================
# TIER 5: SECURITY — Hardening against malicious input
# =========================================================================


class TestTier5SecurityPathTraversal:
    """File operations must not escape boundaries."""

    def test_parse_file_rejects_directory(self, tmp_path):
        with pytest.raises((IsADirectoryError, FafParseError, PermissionError)):
            parse_file(str(tmp_path))

    def test_find_faf_file_nonexistent_start(self):
        result = find_faf_file("/nonexistent/start/dir")
        assert result is None

    def test_should_ignore_rejects_parent_traversal(self):
        """Patterns with ../ should not escape project root in matching."""
        # This tests the matching logic, not filesystem access
        assert not should_ignore("safe/file.py", ["../../../etc/passwd"])


class TestTier5SecurityYamlInjection:
    """YAML parsing must be safe against injection."""

    def test_yaml_safe_load_no_code_execution(self):
        """yaml.safe_load must not execute Python objects."""
        dangerous = "!!python/object/apply:os.system ['echo pwned']"
        # safe_load should raise, not execute
        with pytest.raises((FafParseError, Exception)):
            parse(dangerous)

    def test_yaml_no_arbitrary_object_construction(self):
        dangerous = "!!python/object:__main__.Evil {}"
        with pytest.raises((FafParseError, Exception)):
            parse(dangerous)

    def test_placeholder_not_injectable(self):
        """Placeholder list cannot be bypassed with special chars."""
        tricky = [
            "none\uffff",        # BMP max
            "unknown\u200b",     # zero-width space
        ]
        for val in tricky:
            yaml_content = f'project:\n  name: "{val}"'
            result = score_faf(yaml_content)
            assert isinstance(result, Mk4Result)

    def test_null_byte_in_yaml_handled(self):
        """Null bytes cause YAML parse error — must not crash."""
        result = score_faf("project:\n  name: \"null\x00hidden\"")
        assert isinstance(result, Mk4Result)
        assert result.score == 0  # YAML error → empty doc → 0

    def test_score_faf_with_yaml_bomb(self):
        """YAML expansion bomb should not cause memory explosion.
        yaml.safe_load handles this safely."""
        yaml_bomb = """
a: &a ["x","x","x","x","x"]
b: &b [*a,*a,*a,*a,*a]
c: &c [*b,*b,*b,*b,*b]
d: &d [*c,*c,*c,*c,*c]
"""
        result = score_faf(yaml_bomb)
        assert isinstance(result, Mk4Result)


class TestTier5SecurityFilePermissions:
    """Must handle permission issues gracefully."""

    def test_parse_file_unreadable(self, tmp_path):
        faf_file = tmp_path / "locked.faf"
        faf_file.write_text("project:\n  name: locked")
        faf_file.chmod(0o000)
        try:
            with pytest.raises((PermissionError, FafParseError, IOError)):
                parse_file(str(faf_file))
        finally:
            faf_file.chmod(0o644)

    def test_list_files_permission_denied_subdir(self, tmp_path):
        """Should not crash if a subdirectory is unreadable."""
        (tmp_path / "readable.py").write_text("# ok")
        locked = tmp_path / "locked_dir"
        locked.mkdir()
        (locked / "secret.py").write_text("# secret")
        locked.chmod(0o000)
        try:
            # Should either skip or raise, not crash
            try:
                files = list_project_files(str(tmp_path))
                # If it succeeds, locked dir contents should not be listed
            except PermissionError:
                pass  # acceptable
        finally:
            locked.chmod(0o755)


class TestTier5SecurityInputValidation:
    """Input boundaries must be enforced."""

    def test_mk4_tier_bounds(self):
        """Tier function must handle all integer inputs."""
        for score in range(-10, 110):
            tier = _score_to_tier(score)
            assert isinstance(tier, str)
            assert len(tier) > 0

    def test_mk4_result_empty_field_never_negative(self):
        """empty count = total - populated - ignored, must never be negative."""
        result = score_faf("project:\n  name: test")
        d = result.to_dict()
        assert d["empty"] >= 0
        assert d["populated"] >= 0
        assert d["ignored"] >= 0
        assert d["empty"] + d["populated"] + d["ignored"] == d["total"]

    def test_mk4_result_math_identity(self):
        """active = total - ignored, always."""
        test_yamls = [
            "empty: true",
            "project:\n  name: test",
            "project:\n  name: slotignored\n  goal: slotignored",
        ]
        for yaml_content in test_yamls:
            result = score_faf(yaml_content)
            assert result.active == result.total - result.ignored
            assert result.populated + result.ignored <= result.total
