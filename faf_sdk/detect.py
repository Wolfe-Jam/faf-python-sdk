"""
Dart/Flutter detection — CONTENT-AWARE pubspec classification (Python).

PARITY: this mirrors faf-cli src/detect/dart.ts EXACTLY. A pubspec.yaml alone
does NOT mean Flutter — the same manifest backs Flutter apps, pure-Dart CLIs,
packages, servers (Dart Frog / Shelf / Serverpod) and MCP servers
(dart_mcp / mcp_server). We read the dependencies and branch.

The detection KNOWLEDGE (which deps mean what) lives in dart_detection.json —
a byte-identical, synced copy of faf-cli's src/detect/dart-detection.json (the
single source, A+B hybrid). To bolster Dart support, edit the spec in faf-cli
(the Truth) and re-run scripts/sync-dart-spec.sh. The thin per-language LOGIC
(pubspec parse, app-vs-package heuristic, priority branching) lives here.

Behavior parity with faf-cli is PROVEN by tests/test_dart_parity.py, which runs
the SAME shared fixtures faf-cli runs in tests/detect/dart-parity.test.ts.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

_SPEC: Dict[str, Any] = json.loads(
    (Path(__file__).parent / "dart_detection.json").read_text(encoding="utf-8")
)

# Detection KNOWLEDGE — sourced from dart_detection.json, never hand-listed here.
FLUTTER_DEPS: List[str] = list(_SPEC["flutterDeps"])
MCP_DEPS: List[str] = list(_SPEC["mcpDeps"])
SERVER_FRAMEWORKS: List[List[str]] = [list(e) for e in _SPEC["serverFrameworks"]]
STATE_MGMT: List[List[str]] = [list(e) for e in _SPEC["stateManagement"]]
ROUTING: List[List[str]] = [list(e) for e in _SPEC["routing"]]


@dataclass
class DartProject:
    """Classification of a Dart/Flutter project from its pubspec.yaml."""

    app_type: str  # 'mobile' | 'mcp' | 'backend' | 'cli' | 'library'
    is_flutter: bool
    framework: str  # 'Flutter' | 'Dart Frog' | 'Serverpod' | 'Shelf' | ... | ''
    state_management: str  # 'Riverpod' | 'Bloc' | 'Provider' | 'GetX' | ... | ''
    routing: str  # 'go_router' | 'auto_route' | ''
    testing: str  # 'flutter_test' | 'test' | ''
    found: str  # human-readable rationale for the .faf `# found:` comment

    def to_dict(self) -> Dict[str, object]:
        """Project to the faf-cli DartProject shape (camelCase) for parity checks."""
        return {
            "appType": self.app_type,
            "isFlutter": self.is_flutter,
            "framework": self.framework,
            "stateManagement": self.state_management,
            "routing": self.routing,
            "testing": self.testing,
            "found": self.found,
        }


def _pubspec_deps(content: str) -> Set[str]:
    """Collect dependency names from dependencies / dev_dependencies sections."""
    deps: Set[str] = set()
    in_deps = False
    for line in content.split("\n"):
        if re.match(r"^(dependencies|dev_dependencies|dependency_overrides):\s*$", line):
            in_deps = True
            continue
        # A new top-level key (no leading whitespace) ends the dependency section.
        if re.match(r"^\S", line):
            in_deps = False
        if in_deps:
            m = re.match(r"^\s{2}([a-zA-Z0-9_]+):", line)
            if m:
                deps.add(m.group(1).lower())
    return deps


def detect_dart_project(directory: str) -> Optional[DartProject]:
    """Classify a Dart/Flutter project from its pubspec.yaml. None if not Dart."""
    path = Path(directory) / "pubspec.yaml"
    if not path.exists():
        return None
    try:
        content = path.read_text(encoding="utf-8")
    except OSError:
        return None

    deps = _pubspec_deps(content)

    def has(dep: str) -> bool:
        return dep.lower() in deps

    # Flutter: the `flutter` SDK dep, a top-level `flutter:` section, or `sdk: flutter`.
    is_flutter = (
        any(has(d) for d in FLUTTER_DEPS)
        or re.search(r"^flutter:\s*$", content, re.MULTILINE) is not None
        or re.search(r"\bsdk:\s*flutter\b", content) is not None
    )

    mcp_dep = next((d for d in MCP_DEPS if has(d)), None)
    server = next((e for e in SERVER_FRAMEWORKS if has(e[0])), None)
    state_entry = next((e for e in STATE_MGMT if has(e[0])), None)
    state_management = state_entry[1] if state_entry else ""
    route_entry = next((e for e in ROUTING if has(e[0])), None)
    routing = route_entry[1] if route_entry else ""
    testing = "flutter_test" if has("flutter_test") else ("test" if has("test") else "")

    # CLI: a top-level `executables:` section, or bin/*.dart entry points.
    has_executables = re.search(r"^executables:\s*$", content, re.MULTILINE) is not None
    has_bin_dart = False
    bin_dir = Path(directory) / "bin"
    if bin_dir.is_dir():
        try:
            has_bin_dart = any(f.endswith(".dart") for f in os.listdir(bin_dir))
        except OSError:
            has_bin_dart = False
    is_cli = has_executables or has_bin_dart

    framework = ""
    app_type: str
    found: str

    if is_flutter:
        framework = "Flutter"
        # App vs package: an app has lib/main.dart (the entry) or `publish_to: none`;
        # a reusable Flutter package has neither — it's publishable, lib/ exports only.
        is_app = (Path(directory) / "lib" / "main.dart").exists() or (
            re.search(r"^publish_to:\s*['\"]?none\b", content, re.MULTILINE) is not None
        )
        if is_app:
            app_type = "mobile"
            found = "pubspec.yaml (Flutter app)"
        else:
            app_type = "library"
            found = "pubspec.yaml (Flutter package)"
    elif mcp_dep:
        app_type = "mcp"
        found = f"pubspec.yaml + {mcp_dep} (Dart MCP server)"
    elif server:
        app_type = "backend"
        framework = server[1]
        found = f"pubspec.yaml + {server[0]} (Dart backend)"
    elif is_cli:
        app_type = "cli"
        found = (
            "pubspec.yaml executables: (Dart CLI)"
            if has_executables
            else "pubspec.yaml + bin/*.dart (Dart CLI)"
        )
    else:
        app_type = "library"
        found = "pubspec.yaml (Dart package)"

    return DartProject(
        app_type=app_type,
        is_flutter=is_flutter,
        framework=framework,
        state_management=state_management,
        routing=routing,
        testing=testing,
        found=found,
    )
