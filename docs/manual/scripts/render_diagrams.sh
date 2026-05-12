#!/usr/bin/env bash
# Render every Mermaid source under diagrams/src/ to SVG + PNG.
#
# Requires: @mermaid-js/mermaid-cli (mmdc).
# Install:  npm install -g @mermaid-js/mermaid-cli

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SRC="$ROOT/diagrams/src"
OUT="$ROOT/diagrams/rendered"

mkdir -p "$OUT"

if ! command -v mmdc >/dev/null 2>&1; then
  echo "ERROR: mmdc (mermaid-cli) not found." >&2
  echo "Install with: npm install -g @mermaid-js/mermaid-cli" >&2
  exit 1
fi

shopt -s nullglob
files=("$SRC"/*.mmd)
if [ ${#files[@]} -eq 0 ]; then
  echo "No .mmd files under $SRC"
  exit 0
fi

PUPPETEER_CONFIG="$ROOT/scripts/puppeteer.json"

for f in "${files[@]}"; do
  base="$(basename "$f" .mmd)"
  echo "Rendering $base..."
  mmdc -i "$f" -o "$OUT/$base.svg" --backgroundColor transparent -p "$PUPPETEER_CONFIG"
  mmdc -i "$f" -o "$OUT/$base.png" --backgroundColor white --width 1600 -p "$PUPPETEER_CONFIG"
done

echo "Rendered ${#files[@]} diagram(s) to $OUT"
