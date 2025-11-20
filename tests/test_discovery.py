"""Tests for FAF discovery"""

import os
import tempfile
import pytest
from pathlib import Path

from faf_sdk import find_faf_file, find_project_root, load_fafignore
from faf_sdk.discovery import should_ignore, list_project_files, DEFAULT_IGNORE_PATTERNS


class TestFindFafFile:
    """Test find_faf_file function"""

    def test_find_project_faf(self, tmp_path):
        """Find project.faf in directory"""
        faf_file = tmp_path / "project.faf"
        faf_file.write_text("faf_version: 2.5.0\nproject:\n  name: test")

        result = find_faf_file(str(tmp_path))
        # Use realpath to resolve macOS /var -> /private/var symlink
        assert result == os.path.realpath(str(faf_file))

    def test_find_legacy_faf(self, tmp_path):
        """Find .faf (legacy) in directory"""
        faf_file = tmp_path / ".faf"
        faf_file.write_text("faf_version: 2.5.0\nproject:\n  name: test")

        result = find_faf_file(str(tmp_path))
        assert result == os.path.realpath(str(faf_file))

    def test_prefer_project_faf(self, tmp_path):
        """Prefer project.faf over .faf"""
        project_faf = tmp_path / "project.faf"
        legacy_faf = tmp_path / ".faf"
        project_faf.write_text("faf_version: 2.5.0\nproject:\n  name: new")
        legacy_faf.write_text("faf_version: 2.5.0\nproject:\n  name: old")

        result = find_faf_file(str(tmp_path))
        assert result == os.path.realpath(str(project_faf))

    def test_walk_up_tree(self, tmp_path):
        """Find FAF by walking up directory tree"""
        # Create nested structure
        subdir = tmp_path / "src" / "lib"
        subdir.mkdir(parents=True)

        faf_file = tmp_path / "project.faf"
        faf_file.write_text("faf_version: 2.5.0\nproject:\n  name: test")

        result = find_faf_file(str(subdir))
        assert result == os.path.realpath(str(faf_file))

    def test_not_found(self, tmp_path):
        """Return None when not found"""
        result = find_faf_file(str(tmp_path))
        assert result is None


class TestFindProjectRoot:
    """Test find_project_root function"""

    def test_find_by_package_json(self, tmp_path):
        """Find root by package.json"""
        pkg = tmp_path / "package.json"
        pkg.write_text("{}")

        result = find_project_root(str(tmp_path))
        assert result == os.path.realpath(str(tmp_path))

    def test_find_by_pyproject(self, tmp_path):
        """Find root by pyproject.toml"""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text("[project]")

        result = find_project_root(str(tmp_path))
        assert result == os.path.realpath(str(tmp_path))

    def test_find_by_git(self, tmp_path):
        """Find root by .git directory"""
        git = tmp_path / ".git"
        git.mkdir()

        result = find_project_root(str(tmp_path))
        assert result == os.path.realpath(str(tmp_path))


class TestShouldIgnore:
    """Test should_ignore function"""

    def test_ignore_node_modules(self):
        """Ignore node_modules directory"""
        patterns = ["node_modules/"]
        assert should_ignore("node_modules/package/index.js", patterns)
        assert not should_ignore("src/modules/index.js", patterns)

    def test_ignore_extension(self):
        """Ignore by file extension"""
        patterns = ["*.pyc", "*.log"]
        assert should_ignore("cache/main.pyc", patterns)
        assert should_ignore("app.log", patterns)
        assert not should_ignore("main.py", patterns)

    def test_ignore_exact_file(self):
        """Ignore exact filename"""
        patterns = [".env", ".DS_Store"]
        assert should_ignore(".env", patterns)
        assert should_ignore("project/.DS_Store", patterns)
        assert not should_ignore("config.env", patterns)

    def test_default_patterns(self):
        """Test default ignore patterns"""
        patterns = DEFAULT_IGNORE_PATTERNS
        assert should_ignore("node_modules/lodash/index.js", patterns)
        assert should_ignore("dist/bundle.js", patterns)
        assert should_ignore(".git/config", patterns)
        assert should_ignore("secret.key", patterns)


class TestLoadFafignore:
    """Test load_fafignore function"""

    def test_load_custom(self, tmp_path):
        """Load custom .fafignore"""
        fafignore = tmp_path / ".fafignore"
        fafignore.write_text("custom/\n*.secret\n# comment\n")

        patterns = load_fafignore(str(tmp_path))
        assert "custom/" in patterns
        assert "*.secret" in patterns
        assert "# comment" not in patterns

    def test_default_when_missing(self, tmp_path):
        """Use defaults when no .fafignore"""
        patterns = load_fafignore(str(tmp_path))
        assert patterns == DEFAULT_IGNORE_PATTERNS


class TestListProjectFiles:
    """Test list_project_files function"""

    def test_list_files(self, tmp_path):
        """List project files"""
        # Create files
        src = tmp_path / "src"
        src.mkdir()
        (src / "main.py").write_text("print('hello')")
        (src / "utils.py").write_text("# utils")
        (tmp_path / "README.md").write_text("# Readme")

        files = list_project_files(str(tmp_path))
        assert "src/main.py" in files
        assert "src/utils.py" in files
        assert "README.md" in files

    def test_filter_by_extension(self, tmp_path):
        """Filter files by extension"""
        (tmp_path / "main.py").write_text("")
        (tmp_path / "app.js").write_text("")
        (tmp_path / "style.css").write_text("")

        files = list_project_files(str(tmp_path), extensions=[".py"])
        assert "main.py" in files
        assert "app.js" not in files
        assert "style.css" not in files

    def test_respect_ignore(self, tmp_path):
        """Respect ignore patterns"""
        (tmp_path / "main.py").write_text("")
        nm = tmp_path / "node_modules"
        nm.mkdir()
        (nm / "lodash.js").write_text("")

        files = list_project_files(str(tmp_path))
        assert "main.py" in files
        assert "node_modules/lodash.js" not in files


# Fixtures
@pytest.fixture
def tmp_path():
    """Create temporary directory"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)
