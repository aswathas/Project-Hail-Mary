import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path


def test_detection_phase_runs_after_ingest():
    """Detection engines should be called after derived events are ingested."""
    from detection.signal_engine import run_all_signals
    from detection.pattern_engine import run_all_patterns

    mock_client = MagicMock()
    mock_client.esql.query.return_value = {"columns": [], "values": []}
    mock_client.eql.search.return_value = {"hits": {"sequences": []}}
    mock_ingest = MagicMock()

    signals_dir = Path(__file__).parent.parent / "detection" / "signals"
    patterns_dir = Path(__file__).parent.parent / "detection" / "patterns"

    # Should not raise
    signals = run_all_signals(
        mock_client, mock_ingest, signals_dir,
        "INV-TEST-001", 31337
    )
    patterns = run_all_patterns(
        mock_client, mock_ingest, patterns_dir,
        "INV-TEST-001", 31337
    )

    # Signal engine should have called esql.query for each .esql file
    assert mock_client.esql.query.call_count == 60
    # Pattern engine should have called eql.search for each .eql file
    assert mock_client.eql.search.call_count == 38


def test_signal_documents_have_correct_id_format():
    """Signal document IDs should follow {investigation_id}_{signal_name}_{tx_hash} format."""
    from detection.signal_engine import run_signal

    mock_client = MagicMock()
    mock_client.esql.query.return_value = {
        "columns": [
            {"name": "tx_hash", "type": "keyword"},
            {"name": "block_number", "type": "long"},
        ],
        "values": [["0xabc123", 10]],
    }

    metadata = {
        "signal_name": "reentrancy_pattern",
        "signal_family": "structural",
        "severity": "CRIT",
        "score": 0.95,
        "description": "Test",
    }

    results = run_signal(
        mock_client, "FROM forensics", metadata, "INV-2026-0001", 31337
    )

    assert len(results) == 1
    assert results[0]["signal_name"] == "reentrancy_pattern"
    assert results[0]["investigation_id"] == "INV-2026-0001"
    # Verify evidence ref follows ID convention
    assert "INV-2026-0001_reentrancy_pattern_0xabc123" in results[0]["evidence_refs"]
