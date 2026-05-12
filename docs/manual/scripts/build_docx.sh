#!/usr/bin/env bash
# Build one .docx from a document folder under src/.
#
# Usage: build_docx.sh <doc-id> <out-name>
#   build_docx.sh d4 ChainSentinel-D4-Detection-Reference

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DOC_ID="$1"
OUT_NAME="$2"
SRC_DIR="$ROOT/src/$DOC_ID-"*
BUILD_DIR="$ROOT/build"
STAGE_DIR="$ROOT/build/_stage/$DOC_ID"

mkdir -p "$BUILD_DIR" "$STAGE_DIR"

# Expand `{{< include >}}` shortcodes for each chapter
shopt -s nullglob
i=0
declare -a inputs=()
for f in $(ls $SRC_DIR/*.md 2>/dev/null | sort); do
  i=$((i+1))
  stage_file="$STAGE_DIR/$(printf '%03d' $i)_$(basename "$f")"
  python3 "$ROOT/scripts/expand_includes.py" "$f" "$stage_file"
  inputs+=("$stage_file")
done

if [ ${#inputs[@]} -eq 0 ]; then
  echo "no chapters found for $DOC_ID"
  exit 1
fi

# Compute resource paths so relative image refs like ../../diagrams/rendered/*.png
# resolve from any document folder (src/d*-*).
RESOURCE_PATHS="$ROOT:$ROOT/src/$DOC_ID-_doc:$ROOT/diagrams/rendered"
# Add every actual src/d*-* folder so includes inside them resolve their images too
for d in "$ROOT"/src/d*-*; do
  RESOURCE_PATHS="$RESOURCE_PATHS:$d"
done

pandoc \
  --reference-doc="$ROOT/pandoc/reference.docx" \
  --resource-path="$RESOURCE_PATHS" \
  --toc --toc-depth=3 \
  "${inputs[@]}" \
  -o "$BUILD_DIR/$OUT_NAME.docx"

echo "built $BUILD_DIR/$OUT_NAME.docx"
