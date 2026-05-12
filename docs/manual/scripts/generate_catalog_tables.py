#!/usr/bin/env python3
"""
Generate Markdown catalog tables from the ChainSentinel source tree.

Outputs to docs/manual/src/_generated/ — these files are included by the
authored docs (D4, D5, D6) so the reference catalogs stay in sync with code.

Generated files:
    signals_by_family.md       Signal catalog grouped by family (7 families)
    patterns_catalog.md        Attack-pattern catalog (38 patterns)
    derived_events.md          Derived event builders (one row each)
    abi_registry.md            ABI registry summary
    es_mappings_forensics.md   Field-by-field mapping for forensics index
    es_mappings_raw.md         Field-by-field mapping for forensics-raw index
    endpoints.md               FastAPI endpoint reference (parsed from server.py)
"""

from __future__ import annotations

import ast
import json
from pathlib import Path

REPO_ROOT     = Path(__file__).resolve().parents[3]
CHAINSENTINEL = REPO_ROOT / "chainsentinel"
OUT_DIR       = REPO_ROOT / "docs" / "manual" / "src" / "_generated"


# --------------------------------------------------------------------------- #
# Utilities
# --------------------------------------------------------------------------- #
def write(name: str, body: str) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUT_DIR / name
    path.write_text(body, encoding="utf-8")
    print(f"wrote {path.relative_to(REPO_ROOT)}")


def md_escape(s: str) -> str:
    return s.replace("|", "\\|").replace("\n", " ").strip()


# --------------------------------------------------------------------------- #
# Signals — 60 .esql files in 7 family folders
# --------------------------------------------------------------------------- #
def build_signals() -> None:
    signals_root = CHAINSENTINEL / "detection" / "signals"
    if not signals_root.exists():
        print(f"skip signals (missing {signals_root})")
        return

    lines: list[str] = ["# Signal Catalog (auto-generated)\n"]
    total = 0
    for family_dir in sorted(p for p in signals_root.iterdir() if p.is_dir()):
        family = family_dir.name
        esqls = sorted(family_dir.glob("*.esql"))
        lines.append(f"## Family: `{family}` ({len(esqls)} signals)\n")
        lines.append("| Signal | File | First line (query head) |")
        lines.append("|---|---|---|")
        for f in esqls:
            try:
                head = f.read_text(encoding="utf-8").strip().splitlines()[0]
            except Exception:
                head = "(unreadable)"
            lines.append(
                f"| `{f.stem}` | "
                f"`detection/signals/{family}/{f.name}` | "
                f"`{md_escape(head)[:120]}` |"
            )
            total += 1
        lines.append("")
    lines.insert(1, f"_Total signals catalogued: **{total}**._\n")
    write("signals_by_family.md", "\n".join(lines))


# --------------------------------------------------------------------------- #
# Patterns — 38 .eql files
# --------------------------------------------------------------------------- #
def build_patterns() -> None:
    patterns_root = CHAINSENTINEL / "detection" / "patterns"
    if not patterns_root.exists():
        print(f"skip patterns (missing {patterns_root})")
        return

    lines: list[str] = ["# Attack-Pattern Catalog (auto-generated)\n"]
    eqls = sorted(patterns_root.glob("*.eql"))
    lines.append(f"_Total patterns catalogued: **{len(eqls)}**._\n")
    lines.append("| Pattern ID | Slug | File | First line |")
    lines.append("|---|---|---|---|")
    for f in eqls:
        stem = f.stem  # e.g. AP-001_classic_reentrancy
        if "_" in stem:
            ap_id, _, slug = stem.partition("_")
        else:
            ap_id, slug = stem, ""
        try:
            head = f.read_text(encoding="utf-8").strip().splitlines()[0]
        except Exception:
            head = "(unreadable)"
        lines.append(
            f"| `{ap_id}` | `{slug}` | "
            f"`detection/patterns/{f.name}` | `{md_escape(head)[:100]}` |"
        )
    write("patterns_catalog.md", "\n".join(lines))


# --------------------------------------------------------------------------- #
# Derived event builders — .py modules under pipeline/derived/
# --------------------------------------------------------------------------- #
def build_derived() -> None:
    derived_root = CHAINSENTINEL / "pipeline" / "derived"
    if not derived_root.exists():
        print(f"skip derived (missing {derived_root})")
        return

    lines: list[str] = ["# Derived Event Builders (auto-generated)\n"]
    files = sorted(
        p for p in derived_root.glob("*.py")
        if p.name not in ("__init__.py", "_base.py")
    )
    lines.append(f"_Total builders catalogued: **{len(files)}**._\n")
    lines.append("| Builder | File | Module docstring (first paragraph) |")
    lines.append("|---|---|---|")
    for f in files:
        try:
            tree = ast.parse(f.read_text(encoding="utf-8"))
            doc = ast.get_docstring(tree) or ""
            first_para = doc.split("\n\n", 1)[0].replace("\n", " ").strip()
        except Exception:
            first_para = "(parse error)"
        lines.append(
            f"| `{f.stem}` | `pipeline/derived/{f.name}` | "
            f"{md_escape(first_para)[:240]} |"
        )
    write("derived_events.md", "\n".join(lines))


# --------------------------------------------------------------------------- #
# ABI registry
# --------------------------------------------------------------------------- #
def build_abis() -> None:
    abi_root = CHAINSENTINEL / "pipeline" / "abi_registry" / "standards"
    if not abi_root.exists():
        print(f"skip ABIs (missing {abi_root})")
        return

    lines: list[str] = ["# ABI Registry (auto-generated)\n"]
    files = sorted(abi_root.glob("*.json"))
    lines.append(f"_Total ABIs catalogued: **{len(files)}**._\n")
    lines.append("| ABI | File | Events | Functions |")
    lines.append("|---|---|---|---|")
    for f in files:
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            if isinstance(data, dict) and "abi" in data:
                items = data["abi"]
            else:
                items = data
            events = sum(1 for x in items if isinstance(x, dict) and x.get("type") == "event")
            funcs  = sum(1 for x in items if isinstance(x, dict) and x.get("type") == "function")
        except Exception:
            events = funcs = 0
        lines.append(
            f"| `{f.stem}` | `pipeline/abi_registry/standards/{f.name}` | "
            f"{events} | {funcs} |"
        )
    write("abi_registry.md", "\n".join(lines))


# --------------------------------------------------------------------------- #
# ES mappings — full field-by-field tables for forensics + forensics-raw
# --------------------------------------------------------------------------- #
def _walk_mapping(props: dict, prefix: str = "") -> list[tuple[str, str, str]]:
    """Recursive walk of an ES mapping properties dict.

    Yields (field_path, type, extras) tuples.
    """
    rows: list[tuple[str, str, str]] = []
    for name, spec in (props or {}).items():
        path = f"{prefix}.{name}" if prefix else name
        if not isinstance(spec, dict):
            continue
        field_type = spec.get("type", "object" if "properties" in spec else "")
        extras_parts = []
        if "format" in spec:
            extras_parts.append(f"format={spec['format']}")
        if "dynamic" in spec:
            extras_parts.append(f"dynamic={spec['dynamic']}")
        if "index" in spec:
            extras_parts.append(f"index={spec['index']}")
        if "doc_values" in spec:
            extras_parts.append(f"doc_values={spec['doc_values']}")
        if "ignore_above" in spec:
            extras_parts.append(f"ignore_above={spec['ignore_above']}")
        extras = ", ".join(extras_parts)
        rows.append((path, field_type, extras))
        if "properties" in spec:
            rows.extend(_walk_mapping(spec["properties"], path))
    return rows


def build_mapping(filename: str, out_name: str) -> None:
    mapping_path = CHAINSENTINEL / "es" / "mappings" / filename
    if not mapping_path.exists():
        print(f"skip {filename} (missing {mapping_path})")
        return

    data = json.loads(mapping_path.read_text(encoding="utf-8"))
    props = (
        data.get("mappings", {}).get("properties")
        or data.get("properties")
        or {}
    )
    dynamic = data.get("mappings", {}).get("dynamic", data.get("dynamic", "—"))
    rows = _walk_mapping(props)

    lines: list[str] = [f"# ES Mapping: `{filename.replace('.json','')}` (auto-generated)\n"]
    lines.append(f"_Source: `es/mappings/{filename}` — dynamic={dynamic}, fields catalogued: **{len(rows)}**._\n")
    lines.append("| Field path | Type | Extras |")
    lines.append("|---|---|---|")
    for path, typ, extras in rows:
        lines.append(f"| `{path}` | `{typ}` | {md_escape(extras)} |")
    write(out_name, "\n".join(lines))


# --------------------------------------------------------------------------- #
# FastAPI endpoints — parsed from server.py
# --------------------------------------------------------------------------- #
def build_endpoints() -> None:
    server = CHAINSENTINEL / "server.py"
    if not server.exists():
        print(f"skip endpoints (missing {server})")
        return

    tree = ast.parse(server.read_text(encoding="utf-8"))
    endpoints: list[tuple[str, str, str, str]] = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for dec in node.decorator_list:
            method = path = None
            target = dec.func if isinstance(dec, ast.Call) else dec
            if isinstance(target, ast.Attribute) and isinstance(target.value, ast.Name) and target.value.id == "app":
                method = target.attr.upper()
                if isinstance(dec, ast.Call) and dec.args and isinstance(dec.args[0], ast.Constant):
                    path = dec.args[0].value
            if method and path:
                doc = ast.get_docstring(node) or ""
                summary = doc.strip().split("\n\n", 1)[0].replace("\n", " ").strip()
                endpoints.append((method, path, node.name, summary))

    lines: list[str] = ["# FastAPI Endpoint Reference (auto-generated)\n"]
    lines.append(f"_Source: `chainsentinel/server.py` — endpoints catalogued: **{len(endpoints)}**._\n")
    lines.append("| Method | Path | Handler | Summary |")
    lines.append("|---|---|---|---|")
    for method, path, handler, summary in endpoints:
        lines.append(f"| `{method}` | `{path}` | `{handler}` | {md_escape(summary)[:200]} |")
    write("endpoints.md", "\n".join(lines))


# --------------------------------------------------------------------------- #
# Scenarios — Foundry simulation folders
# --------------------------------------------------------------------------- #
def build_scenarios() -> None:
    scen_root = REPO_ROOT / "simulations" / "scenarios"
    if not scen_root.exists():
        print(f"skip scenarios (missing {scen_root})")
        return

    lines: list[str] = ["# Simulation Scenarios (auto-generated)\n"]
    scens = sorted(p for p in scen_root.iterdir() if p.is_dir())
    lines.append(f"_Scenarios catalogued: **{len(scens)}**._\n")
    lines.append("| Scenario | Contracts | Scripts |")
    lines.append("|---|---|---|")
    for s in scens:
        src = s / "src"
        script = s / "script"
        contracts = sorted(src.glob("*.sol")) if src.exists() else []
        scripts = sorted(script.glob("*.s.sol")) if script.exists() else []
        c_names = ", ".join(f"`{p.name}`" for p in contracts) or "—"
        s_names = ", ".join(f"`{p.name}`" for p in scripts) or "—"
        lines.append(f"| `{s.name}` | {c_names} | {s_names} |")
    write("scenarios.md", "\n".join(lines))


# --------------------------------------------------------------------------- #
def main() -> None:
    build_signals()
    build_patterns()
    build_derived()
    build_abis()
    build_mapping("forensics.json", "es_mappings_forensics.md")
    build_mapping("forensics-raw.json", "es_mappings_raw.md")
    build_endpoints()
    build_scenarios()


if __name__ == "__main__":
    main()
