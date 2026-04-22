"""
Pattern Engine — discovers and runs EQL pattern queries.

Loads all .eql files from detection/patterns/.
Each file defines an attack pattern as an EQL sequence query.
The engine:
1. Discovers all .eql files
2. Parses metadata from block comment headers
3. Executes via EQL search API against forensics index
4. Converts matched sequences to alert documents (layer: alert)
5. Bulk ingests into forensics index
"""
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


PATTERNS_DIR = Path(__file__).parent / "patterns"


def discover_patterns(patterns_dir: Optional[Path] = None) -> list[dict]:
    """
    Find all .eql files in patterns directory.
    Returns list of dicts: {pattern_id, pattern_name, path, query_text}
    """
    base = patterns_dir or PATTERNS_DIR
    patterns = []

    for eql_file in sorted(base.glob("*.eql")):
        filename = eql_file.stem  # e.g. AP-001_flash_loan_oracle
        parts = filename.split("_", 1)
        pattern_id = parts[0]  # AP-001
        pattern_name = parts[1] if len(parts) > 1 else filename
        query_text = eql_file.read_text(encoding="utf-8")

        patterns.append({
            "pattern_id": pattern_id,
            "pattern_name": pattern_name,
            "path": str(eql_file),
            "query_text": query_text,
        })

    return patterns


def parse_pattern_metadata(
    query_text: str, pattern_id: str, pattern_name: str
) -> dict:
    """
    Extract metadata from .eql comment headers.
    Supports two formats:

    Block comment style:
        /* pattern: AP-001
           name: Flash Loan Oracle Manipulation
           confidence: 0.90
           description: ...
           required_signals: signal1, signal2, signal3
        */

    Line comment style (used by current .eql files):
        // pattern: AP-001
        // name: Classic Reentrancy
        // confidence: 0.95
        // description: ...
    """
    confidence = 0.5
    description = f"Pattern {pattern_id} matched"
    required_signals = []
    display_name = pattern_name.replace("_", " ").title()

    def _parse_lines(lines: list[str]) -> None:
        nonlocal confidence, description, display_name, required_signals
        for line in lines:
            line = line.strip()
            if line.startswith("name:"):
                display_name = line.split(":", 1)[1].strip()
            elif line.startswith("confidence:"):
                try:
                    confidence = float(line.split(":", 1)[1].strip())
                except ValueError:
                    pass
            elif line.startswith("description:"):
                description = line.split(":", 1)[1].strip()
            elif line.startswith("required_signals:"):
                signals_str = line.split(":", 1)[1].strip()
                required_signals = [
                    s.strip() for s in signals_str.split(",") if s.strip()
                ]

    # Try block comment /* ... */ first
    block_match = re.search(r"/\*(.*?)\*/", query_text, re.DOTALL)
    if block_match:
        _parse_lines(block_match.group(1).splitlines())
    else:
        # Fall back to // line comments at the top of the file
        line_comment_lines = []
        for line in query_text.splitlines():
            stripped = line.strip()
            if stripped.startswith("//"):
                # Strip leading "// " or "//"
                line_comment_lines.append(stripped.lstrip("/").strip())
            elif stripped:
                # First non-comment, non-blank line ends the header block
                break
        _parse_lines(line_comment_lines)

    return {
        "pattern_id": pattern_id,
        "pattern_name": display_name,
        "confidence": confidence,
        "description": description,
        "required_signals": required_signals,
    }


def _extract_query_body(query_text: str) -> str:
    """
    Strip comment headers from EQL query and return just the executable body.

    Handles two comment styles used in .eql files:
    - Block comments: /* ... */
    - Line comments:  // key: value  (leading comment lines only)

    EQL itself supports // comments, but stripping them ensures a clean query
    string is sent to Elasticsearch regardless of ES version tolerance.
    """
    # Remove block comments
    cleaned = re.sub(r"/\*.*?\*/", "", query_text, flags=re.DOTALL)
    # Remove leading // comment lines (header metadata)
    lines = cleaned.splitlines()
    body_lines = []
    in_header = True
    for line in lines:
        stripped = line.strip()
        if in_header and (stripped.startswith("//") or stripped == ""):
            continue  # skip header comment lines and blank separator lines
        else:
            in_header = False
            body_lines.append(line)
    return "\n".join(body_lines).strip()


def run_pattern(
    es_client,
    raw_query: str,
    metadata: dict,
    investigation_id: str,
    chain_id: int,
) -> list[dict]:
    """
    Execute a single EQL pattern query and convert matched sequences to alert documents.
    """
    query_body = _extract_query_body(raw_query)

    response = es_client.eql.search(
        index="forensics",
        query=query_body,
        filter={
            "bool": {
                "must": [
                    {"term": {"investigation_id": investigation_id}},
                    {"terms": {"layer": ["signal", "derived"]}},
                ]
            }
        },
        timestamp_field="@timestamp",
        event_category_field="layer",
    )

    sequences = response.get("hits", {}).get("sequences", [])
    if not sequences:
        return []

    now = datetime.now(timezone.utc).isoformat()
    documents = []

    for seq in sequences:
        events = seq.get("events", [])
        if not events:
            continue

        # Extract signals fired from the sequence
        signals_fired = []
        tx_hashes = set()
        blocks = set()
        attacker_wallet = None
        victim_contract = None
        total_value = 0.0

        for event in events:
            src = event.get("_source", {})
            sig_name = src.get("signal_name")
            if sig_name:
                signals_fired.append(sig_name)
            tx = src.get("tx_hash")
            if tx:
                tx_hashes.add(tx)
            bn = src.get("block_number")
            if bn:
                blocks.add(bn)
            # Heuristic: first from_address is attacker, first to_address is victim
            if not attacker_wallet and src.get("from_address"):
                attacker_wallet = src["from_address"]
            if not victim_contract and src.get("to_address"):
                victim_contract = src["to_address"]
            if src.get("value_eth"):
                total_value += float(src["value_eth"])

        doc = {
            "layer": "alert",
            "investigation_id": investigation_id,
            "chain_id": chain_id,
            "@timestamp": now,
            "pattern_id": metadata["pattern_id"],
            "pattern_name": metadata["pattern_name"],
            "confidence": metadata["confidence"],
            "description": metadata["description"],
            "signals_fired": signals_fired or metadata["required_signals"],
            "tx_hash": list(tx_hashes)[0] if tx_hashes else None,
            "block_number": min(blocks) if blocks else None,
            "attacker_wallet": attacker_wallet,
            "victim_contract": victim_contract,
            "funds_drained_eth": total_value,
            "attack_block_range_from": min(blocks) if blocks else None,
            "attack_block_range_to": max(blocks) if blocks else None,
        }

        documents.append(doc)

    return documents


def run_all_patterns(
    es_client,
    ingest_fn,
    patterns_dir: Optional[Path] = None,
    investigation_id: str = "",
    chain_id: int = 31337,
) -> list[dict]:
    """
    Discover all patterns, run each, ingest results.
    Returns all alert documents produced.
    """
    patterns = discover_patterns(patterns_dir)
    all_results = []

    for pattern in patterns:
        metadata = parse_pattern_metadata(
            pattern["query_text"],
            pattern["pattern_id"],
            pattern["pattern_name"],
        )

        results = run_pattern(
            es_client, pattern["query_text"],
            metadata, investigation_id, chain_id
        )

        if results:
            ingest_fn(es_client, results, "forensics")
            all_results.extend(results)

    return all_results
