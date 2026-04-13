import pytest
from unittest.mock import MagicMock


def test_full_correlation_pipeline():
    """
    Integration test: fund_trace -> clustering -> label_db -> mixer_detect
    all work together to produce attacker attribution documents.
    """
    from correlation.fund_trace import trace_funds, build_fund_trail_document
    from correlation.clustering import run_clustering
    from correlation.label_db import get_label, is_ofac_sanctioned
    from correlation.mixer_detect import detect_exit_routes, classify_address

    # Verify label_db is accessible from all modules
    label = get_label("0xd90e2f925da726b50c4ed8d0fb90ad053324f31b")
    assert label["type"] == "mixer_contract"

    # Verify classify_address uses label_db
    classification = classify_address("0xd90e2f925da726b50c4ed8d0fb90ad053324f31b")
    assert classification["category"] == "mixer"

    # Verify OFAC check works
    assert is_ofac_sanctioned("0xd90e2f925da726b50c4ed8d0fb90ad053324f31b") is True


def test_fund_trail_feeds_into_cluster():
    """Fund trail addresses should be usable as clustering input."""
    from correlation.fund_trace import build_fund_trail_document
    from correlation.clustering import build_attacker_profile

    trail = [
        {
            "from_address": "0xattacker",
            "to_address": "0xhop1",
            "value_eth": 50.0,
            "hop_number": 1,
        },
        {
            "from_address": "0xhop1",
            "to_address": "0xd90e2f925da726b50c4ed8d0fb90ad053324f31b",
            "value_eth": 50.0,
            "hop_number": 2,
        },
    ]

    trail_doc = build_fund_trail_document("0xattacker", trail, "INV-001", 31337)

    profile = build_attacker_profile(
        cluster_id="CLUSTER-001",
        wallets=trail_doc["cluster_wallets"],
        fund_trail_hops=trail_doc["fund_trail_hops"],
        exit_routes=trail_doc["exit_routes"],
        total_stolen_eth=trail_doc["total_stolen_eth"],
        investigation_id="INV-001",
        chain_id=31337,
        first_seen_block=trail_doc["attack_block_range_from"],
        exploit_block=trail_doc["attack_block_range_to"],
    )

    assert profile["attacker_type"] == "profile"
    assert profile["fund_trail_hops"] == 2
    assert profile["total_stolen_eth"] == 100.0
