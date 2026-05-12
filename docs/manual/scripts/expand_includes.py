#!/usr/bin/env python3
"""
Pre-pass for Pandoc: inline `{{< include path >}}` shortcodes.

Usage: expand_includes.py <input.md> <output.md>

Resolves the include path relative to the input file's directory.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

INCLUDE_RE = re.compile(r"\{\{<\s*include\s+([^>\s]+)\s*>\}\}")


def expand(text: str, base_dir: Path) -> str:
    def repl(match: re.Match) -> str:
        rel = match.group(1).strip()
        target = (base_dir / rel).resolve()
        if not target.exists():
            return f"> _missing include: {rel}_\n"
        return target.read_text(encoding="utf-8")
    return INCLUDE_RE.sub(repl, text)


def main() -> int:
    if len(sys.argv) != 3:
        print("usage: expand_includes.py <input.md> <output.md>", file=sys.stderr)
        return 2
    in_path = Path(sys.argv[1])
    out_path = Path(sys.argv[2])
    text = in_path.read_text(encoding="utf-8")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(expand(text, in_path.parent), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
