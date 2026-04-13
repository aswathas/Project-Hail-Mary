import pytest
from unittest.mock import MagicMock


def _mock_es_search(hits):
    """Build a mock ES search response."""
    return {
        "hits": {
            "total": {"value": len(hits)},
            "hits": [{"_source": h} for h in hits],
        }
    }


def test_build_context_returns_all_sections():
    from ollama.report_template import build_report_context

    mock_client = MagicMock()
    mock_client.search.return_value = _mock_es_search([])

    ctx = build_report_context(mock_client, "INV-001", 31337)

    assert "case_id" in ctx
    assert "signals" in ctx
    assert "alerts" in ctx
    assert "attacker_profile" in ctx
    assert "fund_trail" in ctx
    assert "timeline" in ctx
    assert "stats" in ctx
    assert ctx["case_id"] == "INV-001"


def test_build_context_populates_signals():
    from ollama.report_template import build_report_context

    mock_client = MagicMock()
    signals = [
        {"signal_name": "reentrancy_pattern", "severity": "CRIT", "score": 0.95,
         "description": "Recursive calls detected", "tx_hash": "0xabc", "block_number": 10},
        {"signal_name": "internal_eth_drain", "severity": "CRIT", "score": 0.85,
         "description": "ETH drained via internal calls", "tx_hash": "0xabc", "block_number": 10},
    ]
    alerts = [
        {"pattern_id": "AP-005", "pattern_name": "Reentrancy Drain", "confidence": 0.9,
         "attacker_wallet": "0xattacker", "victim_contract": "0xvictim",
         "funds_drained_eth": 17.0, "signals_fired": ["reentrancy_pattern", "internal_eth_drain"]},
    ]
    attacker = [
        {"attacker_type": "profile", "cluster_wallets": ["0xattacker"],
         "total_stolen_eth": 17.0, "exit_routes": ["mixer:Tornado Cash"],
         "fund_trail_hops": 3},
    ]

    def search_side_effect(index, query, size=100, sort=None):
        layer_filter = None
        for clause in query.get("bool", {}).get("must", []):
            if "term" in clause and "layer" in clause["term"]:
                layer_filter = clause["term"]["layer"]

        if layer_filter == "signal":
            return _mock_es_search(signals)
        elif layer_filter == "alert":
            return _mock_es_search(alerts)
        elif layer_filter == "attacker":
            return _mock_es_search(attacker)
        return _mock_es_search([])

    mock_client.search.side_effect = search_side_effect

    ctx = build_report_context(mock_client, "INV-001", 31337)

    assert len(ctx["signals"]) == 2
    assert ctx["signals"][0]["signal_name"] == "reentrancy_pattern"
    assert len(ctx["alerts"]) == 1
    assert ctx["alerts"][0]["pattern_name"] == "Reentrancy Drain"
    assert ctx["attacker_profile"]["total_stolen_eth"] == 17.0
    assert ctx["stats"]["signal_count"] == 2
    assert ctx["stats"]["alert_count"] == 1


def test_build_context_handles_empty_investigation():
    from ollama.report_template import build_report_context

    mock_client = MagicMock()
    mock_client.search.return_value = _mock_es_search([])

    ctx = build_report_context(mock_client, "INV-EMPTY", 31337)

    assert ctx["signals"] == []
    assert ctx["alerts"] == []
    assert ctx["attacker_profile"] is None
    assert ctx["stats"]["signal_count"] == 0


def test_format_context_as_prompt():
    from ollama.report_template import format_context_as_prompt

    ctx = {
        "case_id": "INV-001",
        "chain_id": 31337,
        "signals": [
            {"signal_name": "reentrancy_pattern", "severity": "CRIT", "score": 0.95,
             "description": "Recursive calls"},
        ],
        "alerts": [
            {"pattern_name": "Reentrancy Drain", "confidence": 0.9,
             "attacker_wallet": "0xattacker", "victim_contract": "0xvictim",
             "funds_drained_eth": 17.0},
        ],
        "attacker_profile": {
            "cluster_wallets": ["0xattacker"],
            "total_stolen_eth": 17.0,
            "exit_routes": ["mixer:Tornado Cash"],
        },
        "fund_trail": [],
        "timeline": [],
        "stats": {"signal_count": 1, "alert_count": 1, "block_count": 8, "tx_count": 47},
    }

    prompt = format_context_as_prompt(ctx)

    assert "INV-001" in prompt
    assert "reentrancy_pattern" in prompt
    assert "Reentrancy Drain" in prompt
    assert "0xattacker" in prompt
    assert "17.0" in prompt
    assert isinstance(prompt, str)
    assert len(prompt) > 100
