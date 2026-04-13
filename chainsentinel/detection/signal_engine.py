"""
Signal Engine — discovers and runs ES|QL signal queries.

Loads all .esql files from detection/signals/ subdirectories.
Each file is one signal. The engine:
1. Discovers all .esql files grouped by family (subdirectory name)
2. Parses metadata from comment headers (signal name, severity, score, description)
3. Injects investigation_id filter into each query
4. Executes via ES|QL API
5. Converts results to signal documents (layer: signal)
6. Bulk ingests into forensics index
"""
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


SIGNALS_DIR = Path(__file__).parent / "signals"


def discover_signals(signals_dir: Optional[Path] = None) -> list[dict]:
    """
    Walk signal subdirectories and collect all .esql files.
    Returns list of dicts: {name, family, path, query_text}
    """
    base = signals_dir or SIGNALS_DIR
    signals = []

    for esql_file in sorted(base.rglob("*.esql")):
        family = esql_file.parent.name
        name = esql_file.stem
        query_text = esql_file.read_text(encoding="utf-8")

        signals.append({
            "name": name,
            "family": family,
            "path": str(esql_file),
            "query_text": query_text,
        })

    return signals


def parse_signal_metadata(
    query_text: str, signal_name: str, family: str
) -> dict:
    """
    Extract metadata from .esql comment headers.
    Format:
        -- signal: name
        -- severity: HIGH
        -- score: 0.8
        -- description: Human readable description
    Falls back to defaults if headers missing.
    """
    severity = "MED"
    score = 0.5
    description = f"Signal {signal_name} fired"

    for line in query_text.splitlines():
        line = line.strip()
        if not line.startswith("--"):
            continue
        content = line[2:].strip()

        if content.startswith("severity:"):
            severity = content.split(":", 1)[1].strip().upper()
        elif content.startswith("score:"):
            try:
                score = float(content.split(":", 1)[1].strip())
            except ValueError:
                pass
        elif content.startswith("description:"):
            description = content.split(":", 1)[1].strip()

    return {
        "signal_name": signal_name,
        "signal_family": family,
        "severity": severity,
        "score": score,
        "description": description,
    }


def build_esql_query(raw_query: str, investigation_id: str) -> str:
    """
    Inject investigation_id filter into an ES|QL query.
    Inserts after the FROM clause.
    """
    lines = raw_query.strip().splitlines()
    result = []
    from_seen = False

    for line in lines:
        stripped = line.strip()
        # Skip comment lines
        if stripped.startswith("--"):
            continue

        result.append(line)

        # After the FROM line, inject investigation_id filter
        if not from_seen and stripped.upper().startswith("FROM "):
            from_seen = True
            result.append(
                f'| WHERE investigation_id == "{investigation_id}"'
            )

    return "\n".join(result)


def run_signal(
    es_client,
    raw_query: str,
    metadata: dict,
    investigation_id: str,
    chain_id: int,
) -> list[dict]:
    """
    Execute a single signal query and convert results to signal documents.
    """
    query = build_esql_query(raw_query, investigation_id)

    response = es_client.esql.query(
        query=query,
        format="json",
    )

    columns = [col["name"] for col in response.get("columns", [])]
    rows = response.get("values", [])

    if not rows:
        return []

    now = datetime.now(timezone.utc).isoformat()
    documents = []

    for row in rows:
        row_dict = dict(zip(columns, row))

        doc = {
            "layer": "signal",
            "investigation_id": investigation_id,
            "chain_id": chain_id,
            "@timestamp": now,
            "signal_name": metadata["signal_name"],
            "signal_family": metadata["signal_family"],
            "severity": metadata["severity"],
            "score": metadata["score"],
            "description": metadata["description"],
            "tx_hash": row_dict.get("tx_hash"),
            "block_number": row_dict.get("block_number"),
            "from_address": row_dict.get("from_address"),
            "to_address": row_dict.get("to_address"),
            "value_eth": row_dict.get("value_eth"),
            "evidence_refs": [
                f"{investigation_id}_{metadata['signal_name']}_{row_dict.get('tx_hash', 'unknown')}"
            ],
        }

        documents.append(doc)

    return documents


def run_all_signals(
    es_client,
    ingest_fn,
    signals_dir: Optional[Path] = None,
    investigation_id: str = "",
    chain_id: int = 31337,
) -> list[dict]:
    """
    Discover all signals, run each, ingest results.
    Returns all signal documents produced.

    Args:
        es_client: Elasticsearch client
        ingest_fn: Callable that takes (es_client, documents, index) and bulk ingests
        signals_dir: Override path to signals directory
        investigation_id: Current investigation ID
        chain_id: Chain ID from config
    """
    signals = discover_signals(signals_dir)
    all_results = []

    for signal in signals:
        metadata = parse_signal_metadata(
            signal["query_text"], signal["name"], signal["family"]
        )

        results = run_signal(
            es_client, signal["query_text"],
            metadata, investigation_id, chain_id
        )

        if results:
            ingest_fn(es_client, results, "forensics")
            all_results.extend(results)

    return all_results
