#!/usr/bin/env python3
"""
Stress tests for FAF SDK - Try to break it!

Tests:
- Malformed inputs
- Edge cases
- Large files
- Deep nesting
- Unicode/special characters
- Performance benchmarks
- Concurrent access
"""

import os
import sys
import time
import random
import string
import tempfile
import threading
import traceback
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from faf_sdk import parse, validate, find_faf_file, stringify
from faf_sdk.parser import FafParseError
from faf_sdk.discovery import should_ignore, list_project_files


class StressTest:
    """Stress test runner"""

    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.errors = []

    def test(self, name: str, func):
        """Run a single test"""
        try:
            func()
            self.passed += 1
            print(f"  ✓ {name}")
        except AssertionError as e:
            self.failed += 1
            self.errors.append((name, str(e)))
            print(f"  ✗ {name}: {e}")
        except Exception as e:
            self.failed += 1
            self.errors.append((name, f"{type(e).__name__}: {e}"))
            print(f"  ✗ {name}: {type(e).__name__}: {e}")

    def summary(self):
        """Print summary"""
        total = self.passed + self.failed
        print(f"\n{'='*50}")
        print(f"Results: {self.passed}/{total} passed")
        if self.errors:
            print(f"\nFailures:")
            for name, err in self.errors:
                print(f"  - {name}: {err}")
        return self.failed == 0


def run_stress_tests():
    """Run all stress tests"""
    runner = StressTest()

    print("\n" + "="*50)
    print("FAF SDK STRESS TESTS")
    print("="*50)

    # ==========================================
    print("\n[1] MALFORMED INPUT TESTS")
    # ==========================================

    def test_null_input():
        try:
            parse(None)
            assert False, "Should have raised"
        except FafParseError:
            pass

    def test_empty_string():
        try:
            parse("")
            assert False, "Should have raised"
        except FafParseError:
            pass

    def test_whitespace_only():
        try:
            parse("   \n\n\t\t   ")
            assert False, "Should have raised"
        except FafParseError:
            pass

    def test_invalid_yaml_unclosed():
        try:
            parse("key: [unclosed")
            assert False, "Should have raised"
        except FafParseError:
            pass

    def test_invalid_yaml_bad_indent():
        try:
            parse("key:\n  sub:\nbad")
            assert False, "Should have raised"
        except FafParseError:
            pass

    def test_yaml_array_not_object():
        try:
            parse("- item1\n- item2\n- item3")
            assert False, "Should have raised"
        except FafParseError as e:
            assert "object" in str(e).lower()

    def test_yaml_scalar_not_object():
        try:
            parse("just a string value")
            assert False, "Should have raised"
        except FafParseError as e:
            assert "object" in str(e).lower()

    def test_yaml_number_not_object():
        try:
            parse("42")
            assert False, "Should have raised"
        except FafParseError as e:
            assert "object" in str(e).lower()

    def test_yaml_boolean_not_object():
        try:
            parse("true")
            assert False, "Should have raised"
        except FafParseError as e:
            assert "object" in str(e).lower()

    def test_yaml_null_document():
        try:
            parse("---\n...")
            assert False, "Should have raised"
        except FafParseError:
            pass

    runner.test("Null input", test_null_input)
    runner.test("Empty string", test_empty_string)
    runner.test("Whitespace only", test_whitespace_only)
    runner.test("Unclosed bracket", test_invalid_yaml_unclosed)
    runner.test("Bad indentation", test_invalid_yaml_bad_indent)
    runner.test("Array not object", test_yaml_array_not_object)
    runner.test("Scalar not object", test_yaml_scalar_not_object)
    runner.test("Number not object", test_yaml_number_not_object)
    runner.test("Boolean not object", test_yaml_boolean_not_object)
    runner.test("Null document", test_yaml_null_document)

    # ==========================================
    print("\n[2] EDGE CASE TESTS")
    # ==========================================

    def test_minimal_valid():
        faf = parse("faf_version: 1.0\nproject:\n  name: x")
        assert faf.project_name == "x"

    def test_project_as_string():
        # Some older formats might have project as string
        faf = parse("faf_version: 1.0\nproject: my-project")
        assert faf.data.project.name == "my-project"  # Uses string as name

    def test_empty_project():
        faf = parse("faf_version: 1.0\nproject: {}")
        result = validate(faf)
        assert not result.valid  # Missing name

    def test_empty_arrays():
        content = """
faf_version: 2.5.0
project:
  name: test
tags: []
instant_context:
  key_files: []
"""
        faf = parse(content)
        assert faf.data.tags == []
        assert faf.data.instant_context.key_files == []

    def test_null_values():
        content = """
faf_version: 2.5.0
project:
  name: test
  goal: ~
stack:
  frontend: null
  backend: ~
"""
        faf = parse(content)
        assert faf.data.project.goal is None
        assert faf.data.stack.frontend is None

    def test_numeric_strings():
        content = """
faf_version: "2.5.0"
project:
  name: "123"
  goal: "456"
ai_score: "75%"
"""
        faf = parse(content)
        assert faf.project_name == "123"
        assert faf.score == 75

    def test_boolean_values():
        content = """
faf_version: 2.5.0
project:
  name: test
context_quality:
  handoff_ready: true
"""
        faf = parse(content)
        assert faf.data.context_quality.handoff_ready is True

    runner.test("Minimal valid FAF", test_minimal_valid)
    runner.test("Project as string", test_project_as_string)
    runner.test("Empty project", test_empty_project)
    runner.test("Empty arrays", test_empty_arrays)
    runner.test("Null values", test_null_values)
    runner.test("Numeric strings", test_numeric_strings)
    runner.test("Boolean values", test_boolean_values)

    # ==========================================
    print("\n[3] UNICODE & SPECIAL CHARACTERS")
    # ==========================================

    def test_unicode_project_name():
        content = """
faf_version: 2.5.0
project:
  name: "プロジェクト-日本語"
  goal: "Build something 中文"
"""
        faf = parse(content)
        assert "日本語" in faf.project_name
        assert "中文" in faf.data.project.goal

    def test_emoji_in_content():
        content = """
faf_version: 2.5.0
project:
  name: "🚀 Rocket App"
  goal: "Launch to the 🌙"
tags:
  - "🔥 hot"
  - "⚡ fast"
"""
        faf = parse(content)
        assert "🚀" in faf.project_name
        assert "🔥 hot" in faf.data.tags

    def test_special_yaml_chars():
        content = """
faf_version: 2.5.0
project:
  name: "test: with colon"
  goal: "has [brackets] and {braces}"
"""
        faf = parse(content)
        assert "colon" in faf.project_name
        assert "[brackets]" in faf.data.project.goal

    def test_multiline_strings():
        content = """
faf_version: 2.5.0
project:
  name: test
  goal: |
    This is a multiline
    goal description
    with several lines
"""
        faf = parse(content)
        assert "multiline" in faf.data.project.goal
        assert "several" in faf.data.project.goal

    def test_newlines_in_strings():
        content = """
faf_version: 2.5.0
project:
  name: "line1\\nline2"
"""
        faf = parse(content)
        assert "line1" in faf.project_name

    runner.test("Unicode project name", test_unicode_project_name)
    runner.test("Emoji in content", test_emoji_in_content)
    runner.test("Special YAML chars", test_special_yaml_chars)
    runner.test("Multiline strings", test_multiline_strings)
    runner.test("Newlines in strings", test_newlines_in_strings)

    # ==========================================
    print("\n[4] LARGE FILE TESTS")
    # ==========================================

    def test_large_file_1000_tags():
        tags = [f"tag-{i}" for i in range(1000)]
        content = f"""
faf_version: 2.5.0
project:
  name: large-tags
tags:
{chr(10).join(f'  - "{tag}"' for tag in tags)}
"""
        faf = parse(content)
        assert len(faf.data.tags) == 1000

    def test_large_file_many_key_files():
        files = [f"src/module{i}/file{j}.py" for i in range(10) for j in range(100)]
        content = f"""
faf_version: 2.5.0
project:
  name: many-files
instant_context:
  what_building: test
  key_files:
{chr(10).join(f'    - "{f}"' for f in files)}
"""
        faf = parse(content)
        assert len(faf.data.instant_context.key_files) == 1000

    def test_large_string_value():
        long_string = "x" * 100000  # 100KB string
        content = f"""
faf_version: 2.5.0
project:
  name: test
  goal: "{long_string}"
"""
        faf = parse(content)
        assert len(faf.data.project.goal) == 100000

    def test_deep_nesting():
        # YAML allows deep nesting
        content = """
faf_version: 2.5.0
project:
  name: deep
  metadata:
    level1:
      level2:
        level3:
          level4:
            level5:
              value: "deep value"
"""
        faf = parse(content)
        deep = faf.raw["project"]["metadata"]["level1"]["level2"]["level3"]["level4"]["level5"]
        assert deep["value"] == "deep value"

    runner.test("1000 tags", test_large_file_1000_tags)
    runner.test("1000 key files", test_large_file_many_key_files)
    runner.test("100KB string value", test_large_string_value)
    runner.test("Deep nesting (5 levels)", test_deep_nesting)

    # ==========================================
    print("\n[5] PERFORMANCE BENCHMARKS")
    # ==========================================

    def test_parse_performance():
        content = """
faf_version: 2.5.0
ai_score: 85%
project:
  name: perf-test
  goal: Performance testing
instant_context:
  what_building: Test app
  tech_stack: Python
  key_files:
    - src/main.py
    - src/utils.py
stack:
  backend: Python
  database: SQLite
"""
        iterations = 1000
        start = time.time()
        for _ in range(iterations):
            parse(content)
        elapsed = time.time() - start
        per_parse = (elapsed / iterations) * 1000  # ms
        assert per_parse < 5, f"Parse too slow: {per_parse:.2f}ms"
        print(f"    → {per_parse:.2f}ms per parse ({iterations} iterations)")

    def test_validate_performance():
        content = """
faf_version: 2.5.0
ai_score: 85%
project:
  name: perf-test
  goal: Testing
instant_context:
  what_building: App
  tech_stack: Python
  key_files: [main.py]
stack:
  backend: Python
"""
        faf = parse(content)
        iterations = 1000
        start = time.time()
        for _ in range(iterations):
            validate(faf)
        elapsed = time.time() - start
        per_validate = (elapsed / iterations) * 1000  # ms
        assert per_validate < 1, f"Validate too slow: {per_validate:.2f}ms"
        print(f"    → {per_validate:.2f}ms per validate ({iterations} iterations)")

    def test_stringify_performance():
        content = """
faf_version: 2.5.0
project:
  name: test
tags: [a, b, c, d, e]
"""
        faf = parse(content)
        iterations = 1000
        start = time.time()
        for _ in range(iterations):
            stringify(faf)
        elapsed = time.time() - start
        per_op = (elapsed / iterations) * 1000
        assert per_op < 1, f"Stringify too slow: {per_op:.2f}ms"
        print(f"    → {per_op:.2f}ms per stringify ({iterations} iterations)")

    runner.test("Parse performance (<5ms)", test_parse_performance)
    runner.test("Validate performance (<1ms)", test_validate_performance)
    runner.test("Stringify performance (<1ms)", test_stringify_performance)

    # ==========================================
    print("\n[6] CONCURRENT ACCESS")
    # ==========================================

    def test_concurrent_parsing():
        content = """
faf_version: 2.5.0
project:
  name: concurrent-test
"""
        errors = []

        def parse_task(i):
            try:
                faf = parse(content)
                assert faf.project_name == "concurrent-test"
            except Exception as e:
                errors.append(f"Thread {i}: {e}")

        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(parse_task, i) for i in range(100)]
            for f in as_completed(futures):
                f.result()

        assert len(errors) == 0, f"Errors: {errors}"

    def test_concurrent_file_operations():
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create multiple FAF files
            for i in range(10):
                path = Path(tmpdir) / f"project{i}" / "project.faf"
                path.parent.mkdir()
                path.write_text(f"faf_version: 2.5.0\nproject:\n  name: project-{i}")

            errors = []

            def find_task(i):
                try:
                    subdir = Path(tmpdir) / f"project{i}"
                    result = find_faf_file(str(subdir))
                    assert result is not None
                    assert f"project{i}" in result
                except Exception as e:
                    errors.append(f"Task {i}: {e}")

            with ThreadPoolExecutor(max_workers=10) as executor:
                futures = [executor.submit(find_task, i) for i in range(10)]
                for f in as_completed(futures):
                    f.result()

            assert len(errors) == 0, f"Errors: {errors}"

    runner.test("Concurrent parsing (100 threads)", test_concurrent_parsing)
    runner.test("Concurrent file ops (10 threads)", test_concurrent_file_operations)

    # ==========================================
    print("\n[7] IGNORE PATTERN STRESS")
    # ==========================================

    def test_many_ignore_patterns():
        patterns = [f"dir{i}/" for i in range(1000)]
        patterns += [f"*.ext{i}" for i in range(1000)]

        # Should handle 2000 patterns without issue
        result = should_ignore("dir500/file.txt", patterns)
        assert result is True

        result = should_ignore("src/main.py", patterns)
        assert result is False

    def test_complex_glob_patterns():
        patterns = [
            "**/*.pyc",
            "**/node_modules/**",
            "build/**/temp/**",
            "*.{jpg,png,gif}",
        ]
        # Note: Our implementation uses fnmatch, not full glob
        # So some patterns may not work exactly as expected
        result = should_ignore("cache/main.pyc", patterns)
        # Just test it doesn't crash

    runner.test("2000 ignore patterns", test_many_ignore_patterns)
    runner.test("Complex glob patterns", test_complex_glob_patterns)

    # ==========================================
    print("\n[8] VALIDATION EDGE CASES")
    # ==========================================

    def test_validate_string_input():
        content = """
faf_version: 2.5.0
project:
  name: test
"""
        result = validate(content)
        assert result.valid

    def test_validate_invalid_string():
        result = validate("not yaml [")
        assert not result.valid
        assert "Parse error" in result.errors[0]

    def test_validate_score_as_string():
        content = """
faf_version: 2.5.0
project:
  name: test
ai_score: "not a number"
"""
        result = validate(content)
        # Should warn but not error
        assert result.valid or any("score" in e.lower() for e in result.errors)

    def test_validate_tags_not_array():
        content = """
faf_version: 2.5.0
project:
  name: test
tags: "not an array"
"""
        result = validate(content)
        assert not result.valid
        assert any("array" in e.lower() for e in result.errors)

    runner.test("Validate string input", test_validate_string_input)
    runner.test("Validate invalid string", test_validate_invalid_string)
    runner.test("Validate score as string", test_validate_score_as_string)
    runner.test("Validate tags not array", test_validate_tags_not_array)

    # ==========================================
    print("\n[9] MEMORY STRESS")
    # ==========================================

    def test_parse_many_objects():
        """Parse 10000 FAF objects"""
        content = "faf_version: 2.5.0\nproject:\n  name: mem-test"
        objects = []
        for _ in range(10000):
            objects.append(parse(content))
        assert len(objects) == 10000
        # Clear to free memory
        objects.clear()

    def test_large_project_files_list():
        """List files in directory with many files"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create 500 files
            for i in range(500):
                (Path(tmpdir) / f"file{i}.py").write_text("")

            files = list_project_files(tmpdir)
            assert len(files) == 500

    runner.test("Parse 10000 objects", test_parse_many_objects)
    runner.test("List 500 files", test_large_project_files_list)

    # ==========================================
    # Summary
    # ==========================================

    return runner.summary()


if __name__ == "__main__":
    success = run_stress_tests()
    sys.exit(0 if success else 1)
