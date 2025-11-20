"""
FAF file discovery - find .faf files and project roots

Mirrors claude-faf-mcp/src/faf-core/utils/file-utils.ts and fafignore-parser.ts
"""

import os
import fnmatch
from pathlib import Path
from typing import List, Optional, Tuple


# Default ignore patterns (from TypeScript implementation)
DEFAULT_IGNORE_PATTERNS = [
    # Dependencies
    "node_modules/",
    "vendor/",
    "bower_components/",
    "__pycache__/",
    "*.pyc",
    ".pytest_cache/",
    "venv/",
    ".venv/",
    "env/",
    ".env/",

    # Build outputs
    "dist/",
    "build/",
    "out/",
    ".next/",
    ".nuxt/",
    ".svelte-kit/",
    "target/",
    "bin/",
    "obj/",

    # Version control
    ".git/",
    ".svn/",
    ".hg/",

    # IDE/Editor
    ".vscode/",
    ".idea/",
    "*.swp",
    "*.swo",
    "*~",

    # OS files
    ".DS_Store",
    "Thumbs.db",

    # Logs
    "*.log",
    "logs/",
    "npm-debug.log*",
    "yarn-debug.log*",
    "yarn-error.log*",

    # Secrets/Config
    ".env",
    ".env.*",
    "*.key",
    "*.pem",
    "*.p12",
    "credentials.json",
    "secrets/",

    # Test coverage
    "coverage/",
    ".nyc_output/",
    "htmlcov/",

    # Large media (usually not needed for context)
    "*.jpg",
    "*.jpeg",
    "*.png",
    "*.gif",
    "*.ico",
    "*.svg",
    "*.mp4",
    "*.mp3",
    "*.wav",
    "*.pdf",
    "*.zip",
    "*.tar.gz",
    "*.rar",

    # Lock files (verbose)
    "package-lock.json",
    "yarn.lock",
    "pnpm-lock.yaml",
    "poetry.lock",
    "Pipfile.lock",

    # Misc
    ".cache/",
    "tmp/",
    "temp/",
]


def find_faf_file(start_dir: Optional[str] = None,
                   max_depth: int = 10) -> Optional[str]:
    """
    Find project.faf or .faf file by walking up directory tree

    Args:
        start_dir: Directory to start search (default: cwd)
        max_depth: Maximum parent directories to check

    Returns:
        Absolute path to .faf file, or None if not found

    Example:
        >>> path = find_faf_file("/path/to/project/src")
        >>> if path:
        ...     print(f"Found: {path}")
    """
    if start_dir is None:
        start_dir = os.getcwd()

    current = Path(start_dir).resolve()

    for _ in range(max_depth):
        # Check for modern project.faf (preferred)
        project_faf = current / "project.faf"
        if project_faf.exists():
            return str(project_faf)

        # Check for legacy .faf
        legacy_faf = current / ".faf"
        if legacy_faf.exists():
            return str(legacy_faf)

        # Move up to parent
        parent = current.parent
        if parent == current:
            # Reached filesystem root
            break
        current = parent

    return None


def find_project_root(start_dir: Optional[str] = None,
                       max_depth: int = 10) -> Optional[str]:
    """
    Find project root by looking for common project markers

    Looks for: package.json, pyproject.toml, Cargo.toml, go.mod, etc.

    Args:
        start_dir: Directory to start search (default: cwd)
        max_depth: Maximum parent directories to check

    Returns:
        Absolute path to project root, or None if not found

    Example:
        >>> root = find_project_root()
        >>> print(f"Project root: {root}")
    """
    if start_dir is None:
        start_dir = os.getcwd()

    markers = [
        "package.json",
        "pyproject.toml",
        "setup.py",
        "requirements.txt",
        "Cargo.toml",
        "go.mod",
        "pom.xml",
        "build.gradle",
        "Gemfile",
        ".git",
        "project.faf",
        ".faf",
    ]

    current = Path(start_dir).resolve()

    for _ in range(max_depth):
        for marker in markers:
            if (current / marker).exists():
                return str(current)

        parent = current.parent
        if parent == current:
            break
        current = parent

    return None


def load_fafignore(project_root: str) -> List[str]:
    """
    Load .fafignore patterns from project root

    Falls back to default patterns if no .fafignore exists.

    Args:
        project_root: Path to project root directory

    Returns:
        List of ignore patterns

    Example:
        >>> patterns = load_fafignore("/path/to/project")
        >>> for p in patterns[:5]:
        ...     print(p)
    """
    fafignore_path = Path(project_root) / ".fafignore"

    if not fafignore_path.exists():
        return DEFAULT_IGNORE_PATTERNS.copy()

    patterns = []
    try:
        with open(fafignore_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                # Skip empty lines and comments
                if line and not line.startswith('#'):
                    patterns.append(line)
    except IOError:
        return DEFAULT_IGNORE_PATTERNS.copy()

    return patterns if patterns else DEFAULT_IGNORE_PATTERNS.copy()


def should_ignore(file_path: str, patterns: List[str]) -> bool:
    """
    Check if a file path should be ignored based on patterns

    Args:
        file_path: Relative file path to check
        patterns: List of ignore patterns

    Returns:
        True if file should be ignored

    Example:
        >>> patterns = load_fafignore(root)
        >>> if not should_ignore("src/main.py", patterns):
        ...     process_file("src/main.py")
    """
    # Normalize path separators
    file_path = file_path.replace('\\', '/')

    for pattern in patterns:
        # Handle directory patterns (ending with /)
        if pattern.endswith('/'):
            dir_pattern = pattern.rstrip('/')
            if file_path.startswith(dir_pattern + '/') or file_path == dir_pattern:
                return True
            # Check if any component matches
            parts = file_path.split('/')
            if dir_pattern in parts:
                return True
        else:
            # File pattern
            if fnmatch.fnmatch(file_path, pattern):
                return True
            # Also check basename
            if fnmatch.fnmatch(os.path.basename(file_path), pattern):
                return True

    return False


def list_project_files(project_root: str,
                        ignore_patterns: Optional[List[str]] = None,
                        extensions: Optional[List[str]] = None) -> List[str]:
    """
    List all project files, respecting .fafignore

    Args:
        project_root: Path to project root
        ignore_patterns: Custom ignore patterns (default: load from .fafignore)
        extensions: Filter by extensions (e.g., [".py", ".ts"])

    Returns:
        List of relative file paths

    Example:
        >>> files = list_project_files(root, extensions=[".py", ".ts"])
        >>> print(f"Found {len(files)} source files")
    """
    if ignore_patterns is None:
        ignore_patterns = load_fafignore(project_root)

    root = Path(project_root)
    files = []

    for path in root.rglob("*"):
        if not path.is_file():
            continue

        relative = str(path.relative_to(root))

        # Check ignore patterns
        if should_ignore(relative, ignore_patterns):
            continue

        # Check extensions filter
        if extensions:
            if path.suffix.lower() not in extensions:
                continue

        files.append(relative)

    return sorted(files)


def create_default_fafignore(project_root: str) -> str:
    """
    Create a default .fafignore file

    Args:
        project_root: Path to project root

    Returns:
        Path to created .fafignore file

    Example:
        >>> path = create_default_fafignore(root)
        >>> print(f"Created: {path}")
    """
    fafignore_path = Path(project_root) / ".fafignore"

    content = [
        "# .fafignore - Files to exclude from FAF context",
        "# Similar to .gitignore syntax",
        "",
        "# Dependencies",
        "node_modules/",
        "__pycache__/",
        "venv/",
        ".venv/",
        "",
        "# Build outputs",
        "dist/",
        "build/",
        ".next/",
        "",
        "# Version control",
        ".git/",
        "",
        "# IDE",
        ".vscode/",
        ".idea/",
        "",
        "# Secrets",
        ".env",
        ".env.*",
        "*.key",
        "*.pem",
        "",
        "# Large files",
        "*.jpg",
        "*.png",
        "*.mp4",
        "*.pdf",
        "*.zip",
        "",
        "# Lock files",
        "package-lock.json",
        "yarn.lock",
        "",
    ]

    with open(fafignore_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(content))

    return str(fafignore_path)
