"""Tests for FAF parser"""

import pytest
from faf_sdk import parse, stringify
from faf_sdk.parser import FafParseError


class TestParse:
    """Test parse function"""

    def test_parse_basic(self):
        """Parse minimal valid FAF"""
        content = """
faf_version: 2.5.0
project:
  name: test-project
"""
        faf = parse(content)
        assert faf.project_name == "test-project"
        assert faf.version == "2.5.0"

    def test_parse_full(self):
        """Parse FAF with all sections"""
        content = """
faf_version: 2.5.0
ai_score: 85%
ai_confidence: HIGH

project:
  name: full-project
  goal: Test all features

instant_context:
  what_building: Test app
  tech_stack: Python, pytest
  key_files:
    - src/main.py
    - tests/test.py

stack:
  backend: Python
  database: SQLite
"""
        faf = parse(content)
        assert faf.project_name == "full-project"
        assert faf.score == 85
        assert faf.data.ai_confidence == "HIGH"
        assert faf.data.instant_context.what_building == "Test app"
        assert faf.data.stack.backend == "Python"
        assert len(faf.data.instant_context.key_files) == 2

    def test_parse_null_content(self):
        """Reject null content"""
        with pytest.raises(FafParseError, match="null"):
            parse(None)

    def test_parse_empty_content(self):
        """Reject empty content"""
        with pytest.raises(FafParseError, match="empty"):
            parse("")

        with pytest.raises(FafParseError, match="empty"):
            parse("   \n\n  ")

    def test_parse_invalid_yaml(self):
        """Reject invalid YAML syntax"""
        content = """
faf_version: 2.5.0
project:
  name: [unclosed
"""
        with pytest.raises(FafParseError, match="YAML"):
            parse(content)

    def test_parse_non_object(self):
        """Reject non-object YAML"""
        with pytest.raises(FafParseError, match="object"):
            parse("just a string")

        with pytest.raises(FafParseError, match="object"):
            parse("- item1\n- item2")

    def test_parse_score_percent(self):
        """Parse score with percent sign"""
        content = """
faf_version: 2.5.0
ai_score: 75%
project:
  name: test
"""
        faf = parse(content)
        assert faf.score == 75

    def test_parse_score_number(self):
        """Parse score as number"""
        content = """
faf_version: 2.5.0
ai_score: 80
project:
  name: test
"""
        faf = parse(content)
        assert faf.data.raw.get("ai_score") == 80


class TestStringify:
    """Test stringify function"""

    def test_stringify_basic(self):
        """Convert back to YAML"""
        content = """
faf_version: 2.5.0
project:
  name: test
"""
        faf = parse(content)
        yaml_str = stringify(faf)
        assert "faf_version" in yaml_str
        assert "test" in yaml_str

    def test_stringify_dict(self):
        """Stringify raw dict"""
        data = {
            "faf_version": "2.5.0",
            "project": {"name": "test"}
        }
        yaml_str = stringify(data)
        assert "faf_version" in yaml_str


class TestFafFile:
    """Test FafFile properties"""

    def test_properties(self):
        """Test quick access properties"""
        content = """
faf_version: 2.5.0
ai_score: 90%
project:
  name: prop-test
"""
        faf = parse(content)
        assert faf.project_name == "prop-test"
        assert faf.score == 90
        assert faf.version == "2.5.0"
