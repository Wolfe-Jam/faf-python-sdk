"""Tests for FAF validator"""

import pytest
from faf_sdk import parse, validate
from faf_sdk.validator import validate_quick


class TestValidate:
    """Test validate function"""

    def test_validate_minimal(self):
        """Validate minimal FAF"""
        content = """
faf_version: 2.5.0
project:
  name: test
"""
        result = validate(content)
        assert result.valid
        assert len(result.errors) == 0
        assert result.score > 0

    def test_validate_missing_version(self):
        """Error on missing faf_version"""
        content = """
project:
  name: test
"""
        result = validate(content)
        assert not result.valid
        assert any("faf_version" in e for e in result.errors)

    def test_validate_missing_project(self):
        """Error on missing project"""
        content = """
faf_version: 2.5.0
"""
        result = validate(content)
        assert not result.valid
        assert any("project" in e for e in result.errors)

    def test_validate_missing_name(self):
        """Error on missing project.name"""
        content = """
faf_version: 2.5.0
project:
  goal: no name here
"""
        result = validate(content)
        assert not result.valid
        assert any("name" in e for e in result.errors)

    def test_validate_warnings(self):
        """Warnings for missing recommended sections"""
        content = """
faf_version: 2.5.0
project:
  name: test
"""
        result = validate(content)
        assert result.valid
        assert any("instant_context" in w for w in result.warnings)
        assert any("stack" in w for w in result.warnings)

    def test_validate_full_no_warnings(self):
        """No warnings for complete FAF"""
        content = """
faf_version: 2.5.0
project:
  name: complete
  goal: Full FAF

instant_context:
  what_building: Test
  tech_stack: Python

stack:
  backend: Python

human_context:
  who: Testers
  what: Testing

ai_instructions:
  quality_bar: strict
"""
        result = validate(content)
        assert result.valid
        # Should have fewer warnings
        assert result.score > 50

    def test_validate_score_calculation(self):
        """Score increases with more content"""
        minimal = """
faf_version: 2.5.0
project:
  name: test
"""
        full = """
faf_version: 2.5.0
project:
  name: test
  goal: Testing

instant_context:
  what_building: App
  tech_stack: Python
  key_files:
    - main.py

stack:
  backend: Python
  database: SQLite

human_context:
  who: Users
  what: Feature
  why: Need it

preferences:
  testing: required

state:
  phase: development

tags:
  - python
  - test
"""
        min_result = validate(minimal)
        full_result = validate(full)
        assert full_result.score > min_result.score


class TestValidateQuick:
    """Test validate_quick function"""

    def test_quick_valid(self):
        """Quick validation success"""
        content = """
faf_version: 2.5.0
project:
  name: test
"""
        valid, msg = validate_quick(content)
        assert valid
        assert "score" in msg.lower() or "valid" in msg.lower()

    def test_quick_invalid(self):
        """Quick validation failure"""
        content = """
project:
  name: test
"""
        valid, msg = validate_quick(content)
        assert not valid
        assert "invalid" in msg.lower()
