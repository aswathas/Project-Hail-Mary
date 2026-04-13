import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch


def test_discover_patterns_finds_all_eql_files(tmp_path):
    from detection.pattern_engine import discover_patterns

    (tmp_path / "AP-001_flash_loan_oracle.eql").write_text("sequence by tx_hash")
    (tmp_path / "AP-005_reentrancy_drain.eql").write_text("sequence by tx_hash")
    (tmp_path / "readme.md").write_text("Not a pattern")

    patterns = discover_patterns(tmp_path)

    assert len(patterns) == 2
    ids = [p["pattern_id"] for p in patterns]
    assert "AP-001" in ids
    assert "AP-005" in ids


def test_discover_patterns_extracts_id_and_name(tmp_path):
    from detection.pattern_engine import discover_patterns

    (tmp_path / "AP-014_mev_sandwich.eql").write_text("sequence by tx_hash")

    patterns = discover_patterns(tmp_path)

    assert patterns[0]["pattern_id"] == "AP-014"
    assert patterns[0]["pattern_name"] == "mev_sandwich"


def test_parse_pattern_metadata_from_header():
    from detection.pattern_engine import parse_pattern_metadata

    query_text = """/* pattern: AP-001
   name: Flash Loan Oracle Manipulation
   confidence: 0.90
   description: Flash loan followed by price manipulation and drain
   required_signals: flash_loan_detected, large_price_impact_swap, large_token_transfer
*/
sequence by investigation_id with maxspan=1m
  [signal_name == "flash_loan_detected"]
  [signal_name == "large_price_impact_swap"]
  [signal_name == "large_token_transfer"]
"""
    meta = parse_pattern_metadata(query_text, "AP-001", "flash_loan_oracle")

    assert meta["pattern_id"] == "AP-001"
    assert meta["confidence"] == 0.90
    assert "flash_loan_detected" in meta["required_signals"]
    assert len(meta["required_signals"]) == 3


def test_parse_pattern_metadata_defaults():
    from detection.pattern_engine import parse_pattern_metadata

    query_text = "sequence by tx_hash [signal_name == \"test\"]"
    meta = parse_pattern_metadata(query_text, "AP-999", "unknown_pattern")

    assert meta["confidence"] == 0.5
    assert meta["required_signals"] == []


def test_run_pattern_returns_alert_documents():
    from detection.pattern_engine import run_pattern

    mock_client = MagicMock()
    mock_client.eql.search.return_value = {
        "hits": {
            "sequences": [
                {
                    "events": [
                        {
                            "_source": {
                                "signal_name": "flash_loan_detected",
                                "tx_hash": "0xabc",
                                "block_number": 10,
                                "from_address": "0xattacker",
                                "to_address": "0xvictim",
                                "value_eth": 100.0,
                            }
                        },
                        {
                            "_source": {
                                "signal_name": "large_token_transfer",
                                "tx_hash": "0xabc",
                                "block_number": 10,
                                "from_address": "0xvictim",
                                "to_address": "0xattacker",
                                "value_eth": 50.0,
                            }
                        },
                    ]
                }
            ]
        }
    }

    metadata = {
        "pattern_id": "AP-001",
        "pattern_name": "Flash Loan Oracle Manipulation",
        "confidence": 0.90,
        "description": "Flash loan oracle attack",
        "required_signals": ["flash_loan_detected", "large_token_transfer"],
    }

    results = run_pattern(
        mock_client, "sequence by tx_hash ...",
        metadata, "INV-2026-0001", 31337
    )

    assert len(results) == 1
    assert results[0]["layer"] == "alert"
    assert results[0]["pattern_id"] == "AP-001"
    assert results[0]["confidence"] == 0.90
    assert results[0]["investigation_id"] == "INV-2026-0001"
    assert "flash_loan_detected" in results[0]["signals_fired"]


def test_run_pattern_handles_no_matches():
    from detection.pattern_engine import run_pattern

    mock_client = MagicMock()
    mock_client.eql.search.return_value = {
        "hits": {"sequences": []}
    }

    metadata = {
        "pattern_id": "AP-001",
        "pattern_name": "test",
        "confidence": 0.9,
        "description": "test",
        "required_signals": [],
    }

    results = run_pattern(
        mock_client, "sequence by tx_hash ...",
        metadata, "INV-2026-0001", 31337
    )

    assert results == []


def test_run_all_patterns_orchestrates(tmp_path):
    from detection.pattern_engine import run_all_patterns

    (tmp_path / "AP-001_flash_loan_oracle.eql").write_text(
        "/* pattern: AP-001\n   name: Flash Loan Oracle\n   confidence: 0.9\n"
        "   description: Flash loan oracle attack\n"
        "   required_signals: flash_loan_detected\n*/\n"
        'sequence by investigation_id [signal_name == "flash_loan_detected"]'
    )

    mock_client = MagicMock()
    mock_client.eql.search.return_value = {
        "hits": {"sequences": []}
    }
    mock_ingest = MagicMock()

    results = run_all_patterns(
        mock_client, mock_ingest, tmp_path,
        "INV-2026-0001", 31337
    )

    assert results == []
    mock_client.eql.search.assert_called_once()
