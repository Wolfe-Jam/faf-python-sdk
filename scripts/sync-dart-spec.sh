#!/usr/bin/env bash
#
# sync-dart-spec.sh — vendor the Dart-detection assets from faf-cli (the Truth).
#
# The .faf detection KNOWLEDGE lives ONCE, in faf-cli. This script copies it,
# byte-for-byte, into faf-python-sdk so the Python detector and its parity
# fixtures stay identical to the TypeScript source (A+B hybrid).
#
#   ./scripts/sync-dart-spec.sh          # copy faf-cli -> sdk (default)
#   ./scripts/sync-dart-spec.sh --check  # verify identical, exit 1 on drift (CI)
#
# Override the faf-cli location with FAF_CLI=/path/to/cli
set -euo pipefail

SDK_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CLI="${FAF_CLI:-$HOME/FAF/cli}"

# source (faf-cli, the Truth)  ->  dest (sdk, vendored)
SPEC_SRC="$CLI/src/detect/dart-detection.json"
SPEC_DST="$SDK_ROOT/faf_sdk/dart_detection.json"
FIX_SRC="$CLI/tests/detect/dart-parity-fixtures.json"
FIX_DST="$SDK_ROOT/tests/dart_parity_fixtures.json"

mode="${1:-copy}"

check_pair() {
  local src="$1" dst="$2"
  if [ ! -f "$src" ]; then
    echo "❌ source missing: $src (set FAF_CLI=/path/to/cli)"; exit 1
  fi
  if [ ! -f "$dst" ] || ! diff -q "$src" "$dst" >/dev/null 2>&1; then
    echo "❌ DRIFT: $dst differs from faf-cli source $src"
    echo "   run: ./scripts/sync-dart-spec.sh"
    exit 1
  fi
  echo "✅ identical: $(basename "$dst")"
}

if [ "$mode" = "--check" ]; then
  echo "Checking Dart-spec parity against faf-cli ($CLI)…"
  check_pair "$SPEC_SRC" "$SPEC_DST"
  check_pair "$FIX_SRC" "$FIX_DST"
  echo "✅ vendored Dart assets are in sync with faf-cli"
else
  for pair in "$SPEC_SRC:$SPEC_DST" "$FIX_SRC:$FIX_DST"; do
    src="${pair%%:*}"; dst="${pair##*:}"
    [ -f "$src" ] || { echo "❌ source missing: $src (set FAF_CLI=/path/to/cli)"; exit 1; }
    cp "$src" "$dst"
    echo "synced: $src -> $dst"
  done
  echo "✅ Dart assets vendored from faf-cli. Commit the changes."
fi
