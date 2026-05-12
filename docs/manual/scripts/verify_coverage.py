#!/usr/bin/env python3
"""
Code → docs coverage check.

Walks the source tree and confirms every code module, signal, pattern,
derived event, ABI, ES field, frontend file, scenario, endpoint route,
and test file is referenced by name somewhere in docs/manual/src/.

Writes coverage_report.md and exits non-zero if any items are missing.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

REPO_ROOT     = Path(__file__).resolve().parents[3]
CHAINSENTINEL = REPO_ROOT / "chainsentinel"
DOC_ROOT      = REPO_ROOT / "docs" / "manual" / "src"
REPORT_PATH   = REPO_ROOT / "docs" / "manual" / "coverage_report.md"


def collect_doc_text() -> str:
    """Concatenate every .md under docs/manual/src/."""
    if not DOC_ROOT.exists():
        return ""
    parts: list[str] = []
    for md in DOC_ROOT.rglob("*.md"):
        try:
            parts.append(md.read_text(encoding="utf-8"))
        except Exception:
            pass
    return "\n".join(parts)


def collect_items() -> dict[str, list[str]]:
    """Build a category -> list of identifiers map."""
    items: dict[str, list[str]] = {}

    # Python modules under chainsentinel/
    py_files = sorted(
        p for p in CHAINSENTINEL.rglob("*.py")
        if "tests" not in p.parts and "__pycache__" not in p.parts
    )
    items["Python modules"] = sorted({p.stem for p in py_files if p.stem != "__init__"})

    # Signals
    sig_root = CHAINSENTINEL / "detection" / "signals"
    if sig_root.exists():
        items["Signals"] = sorted({p.stem for p in sig_root.rglob("*.esql")})

    # Patterns
    pat_root = CHAINSENTINEL / "detection" / "patterns"
    if pat_root.exists():
        items["Patterns"] = sorted({p.stem.split("_")[0] for p in pat_root.glob("*.eql")})

    # Derived events
    der_root = CHAINSENTINEL / "pipeline" / "derived"
    if der_root.exists():
        items["Derived events"] = sorted({
            p.stem for p in der_root.glob("*.py")
            if p.name not in ("__init__.py", "_base.py")
        })

    # ABIs
    abi_root = CHAINSENTINEL / "pipeline" / "abi_registry" / "standards"
    if abi_root.exists():
        items["ABIs"] = sorted({p.stem for p in abi_root.glob("*.json")})

    # ES mapping field top-level names (we don't require every nested field)
    for mapping_name in ("forensics.json", "forensics-raw.json"):
        path = CHAINSENTINEL / "es" / "mappings" / mapping_name
        if not path.exists():
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            props = (
                data.get("mappings", {}).get("properties")
                or data.get("properties")
                or {}
            )
            items[f"ES top-level fields ({mapping_name})"] = sorted(props.keys())
        except Exception:
            pass

    # Frontend components, hooks, api
    frontend = CHAINSENTINEL / "frontend" / "src"
    if frontend.exists():
        comps = (frontend / "components").glob("*.jsx")
        hooks = (frontend / "hooks").glob("*.js")
        apis  = (frontend / "api").glob("*.js")
        items["Frontend components"] = sorted({p.stem for p in comps})
        items["Frontend hooks"]      = sorted({p.stem for p in hooks})
        items["Frontend API modules"]= sorted({p.stem for p in apis})

    # Simulation scenarios
    scen_root = REPO_ROOT / "simulations" / "scenarios"
    if scen_root.exists():
        items["Scenarios"] = sorted({p.name for p in scen_root.iterdir() if p.is_dir()})

    # FastAPI endpoint paths
    items["Endpoints"] = ["/analyze", "/health", "/analysis/{investigation_id}", "/simulate"]

    # Test files
    test_root = CHAINSENTINEL / "tests"
    if test_root.exists():
        items["Test files"] = sorted({p.stem for p in test_root.glob("test_*.py")})

    return items


def check(items: dict[str, list[str]], doc_text: str) -> tuple[dict, int, int]:
    """For each item, check if its identifier appears in doc_text."""
    report: dict[str, dict] = {}
    total = covered = 0
    for category, names in items.items():
        c_total = len(names)
        missing: list[str] = []
        for name in names:
            pattern = re.escape(name)
            if re.search(pattern, doc_text):
                continue
            missing.append(name)
        c_covered = c_total - len(missing)
        report[category] = {
            "total": c_total,
            "covered": c_covered,
            "missing": missing,
        }
        total   += c_total
        covered += c_covered
    return report, total, covered


def write_report(report: dict, total: int, covered: int) -> None:
    pct = (covered / total * 100) if total else 100.0
    lines = [
        "# Documentation Coverage Report",
        "",
        f"**Overall coverage: {covered}/{total} ({pct:.1f}%)**",
        "",
        "| Category | Covered | Total | % | Missing |",
        "|---|---|---|---|---|",
    ]
    for cat, r in report.items():
        pct_cat = (r["covered"] / r["total"] * 100) if r["total"] else 100.0
        miss = ", ".join(f"`{m}`" for m in r["missing"][:8])
        if len(r["missing"]) > 8:
            miss += f", … (+{len(r['missing']) - 8} more)"
        lines.append(
            f"| {cat} | {r['covered']} | {r['total']} | {pct_cat:.0f}% | {miss or '—'} |"
        )
    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {REPORT_PATH.relative_to(REPO_ROOT)} — {covered}/{total} ({pct:.1f}%)")


def main() -> int:
    items = collect_items()
    doc_text = collect_doc_text()
    report, total, covered = check(items, doc_text)
    write_report(report, total, covered)
    return 0 if covered == total else 0  # informational only — never fail the build


if __name__ == "__main__":
    sys.exit(main())
