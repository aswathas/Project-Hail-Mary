import pytest
import json
from pathlib import Path
from unittest.mock import MagicMock, patch, call


def test_discover_signals_finds_all_esql_files(tmp_path):
    from detection.signal_engine import discover_signals

    # Create mock signal files
    value_dir = tmp_path / "value"
    value_dir.mkdir()
    (value_dir / "large_outflow.esql").write_text("FROM forensics | WHERE layer == \"derived\"")
    (value_dir / "value_spike.esql").write_text("FROM forensics | WHERE layer == \"derived\"")

    flash_dir = tmp_path / "flash_loan"
    flash_dir.mkdir()
    (flash_dir / "flash_loan_detected.esql").write_text("FROM forensics | WHERE layer == \"decoded\"")

    signals = discover_signals(tmp_path)

    assert len(signals) == 3
    names = [s["name"] for s in signals]
    assert "large_outflow" in names
    assert "value_spike" in names
    assert "flash_loan_detected" in names


def test_discover_signals_extracts_family_from_directory(tmp_path):
    from detection.signal_engine import discover_signals

    access_dir = tmp_path / "access"
    access_dir.mkdir()
    (access_dir / "ownership_transferred.esql").write_text("FROM forensics")

    signals = discover_signals(tmp_path)

    assert signals[0]["family"] == "access"
    assert signals[0]["name"] == "ownership_transferred"


def test_discover_signals_ignores_non_esql_files(tmp_path):
    from detection.signal_engine import discover_signals

    value_dir = tmp_path / "value"
    value_dir.mkdir()
    (value_dir / "large_outflow.esql").write_text("FROM forensics")
    (value_dir / "readme.md").write_text("Not a signal")
    (value_dir / "notes.txt").write_text("Not a signal")

    signals = discover_signals(tmp_path)

    assert len(signals) == 1


def test_parse_signal_metadata_from_header():
    from detection.signal_engine import parse_signal_metadata

    query_text = """-- signal: large_outflow
-- severity: HIGH
-- score: 0.8
-- description: Detects ETH outflows exceeding 10 ETH in a single transaction
FROM forensics
| WHERE layer == "derived" AND derived_type == "native_transfer"
| WHERE value_eth > 10.0
"""
    meta = parse_signal_metadata(query_text, "large_outflow", "value")

    assert meta["signal_name"] == "large_outflow"
    assert meta["severity"] == "HIGH"
    assert meta["score"] == 0.8
    assert meta["signal_family"] == "value"
    assert "10 ETH" in meta["description"]


def test_parse_signal_metadata_defaults():
    from detection.signal_engine import parse_signal_metadata

    query_text = "FROM forensics | WHERE layer == \"derived\""
    meta = parse_signal_metadata(query_text, "unknown_signal", "misc")

    assert meta["severity"] == "MED"
    assert meta["score"] == 0.5
    assert meta["signal_family"] == "misc"


def test_build_esql_query_injects_investigation_id():
    from detection.signal_engine import build_esql_query

    raw_query = """FROM forensics
| WHERE layer == "derived" AND derived_type == "native_transfer"
| WHERE value_eth > 10.0"""

    result = build_esql_query(raw_query, "INV-2026-0001")

    assert 'investigation_id == "INV-2026-0001"' in result
    assert "FROM forensics" in result


def test_run_signal_returns_documents():
    from detection.signal_engine import run_signal

    mock_client = MagicMock()
    mock_client.esql.query.return_value = {
        "columns": [
            {"name": "tx_hash", "type": "keyword"},
            {"name": "from_address", "type": "keyword"},
            {"name": "to_address", "type": "keyword"},
            {"name": "value_eth", "type": "double"},
            {"name": "block_number", "type": "long"},
        ],
        "values": [
            ["0xabc123", "0xdead", "0x1234", 15.5, 10],
            ["0xdef456", "0xdead", "0x5678", 22.0, 11],
        ],
    }

    metadata = {
        "signal_name": "large_outflow",
        "signal_family": "value",
        "severity": "HIGH",
        "score": 0.8,
        "description": "Large ETH outflow detected",
    }

    results = run_signal(
        mock_client, "FROM forensics | WHERE value_eth > 10",
        metadata, "INV-2026-0001", 31337
    )

    assert len(results) == 2
    assert results[0]["layer"] == "signal"
    assert results[0]["signal_name"] == "large_outflow"
    assert results[0]["signal_family"] == "value"
    assert results[0]["severity"] == "HIGH"
    assert results[0]["score"] == 0.8
    assert results[0]["tx_hash"] == "0xabc123"
    assert results[0]["investigation_id"] == "INV-2026-0001"
    assert results[0]["chain_id"] == 31337


def test_run_signal_handles_empty_results():
    from detection.signal_engine import run_signal

    mock_client = MagicMock()
    mock_client.esql.query.return_value = {
        "columns": [
            {"name": "tx_hash", "type": "keyword"},
        ],
        "values": [],
    }

    metadata = {
        "signal_name": "large_outflow",
        "signal_family": "value",
        "severity": "HIGH",
        "score": 0.8,
        "description": "Large ETH outflow detected",
    }

    results = run_signal(
        mock_client, "FROM forensics | WHERE value_eth > 10",
        metadata, "INV-2026-0001", 31337
    )

    assert results == []


def test_run_all_signals_orchestrates_discovery_and_execution(tmp_path):
    from detection.signal_engine import run_all_signals

    value_dir = tmp_path / "value"
    value_dir.mkdir()
    (value_dir / "large_outflow.esql").write_text(
        "-- signal: large_outflow\n-- severity: HIGH\n-- score: 0.8\n"
        "-- description: Large ETH outflow\n"
        "FROM forensics\n| WHERE layer == \"derived\" AND value_eth > 10"
    )

    mock_client = MagicMock()
    mock_client.esql.query.return_value = {
        "columns": [{"name": "tx_hash", "type": "keyword"}],
        "values": [["0xabc"]],
    }

    mock_ingest = MagicMock()

    results = run_all_signals(
        mock_client, mock_ingest, tmp_path,
        "INV-2026-0001", 31337
    )

    assert len(results) == 1
    mock_client.esql.query.assert_called_once()
    mock_ingest.assert_called_once()
