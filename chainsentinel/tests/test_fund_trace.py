import pytest
from unittest.mock import MagicMock, patch
from collections import deque


def _mock_es_transfer_response(transfers):
    """Helper to build mock ES search response from transfer tuples."""
    hits = []
    for (from_addr, to_addr, value_eth, tx_hash, block_num) in transfers:
        hits.append({
            "_source": {
                "from_address": from_addr,
                "to_address": to_addr,
                "value_eth": value_eth,
                "tx_hash": tx_hash,
                "block_number": block_num,
                "token_address": None,
                "derived_type": "native_transfer",
            }
        })
    return {"hits": {"hits": hits}}


def test_trace_forward_single_hop():
    from correlation.fund_trace import trace_funds

    mock_client = MagicMock()
    # Hop 1: attacker sends to intermediary
    mock_client.search.side_effect = [
        _mock_es_transfer_response([
            ("0xattacker", "0xintermediary", 10.0, "0xtx1", 100),
        ]),
        # Hop 2 from intermediary: no further transfers
        _mock_es_transfer_response([]),
    ]

    trail = trace_funds(
        mock_client, "0xattacker", "INV-001",
        direction="forward", max_hops=2
    )

    assert len(trail) == 1
    assert trail[0]["from_address"] == "0xattacker"
    assert trail[0]["to_address"] == "0xintermediary"
    assert trail[0]["hop_number"] == 1
    assert trail[0]["taint_score"] == pytest.approx(1.0)


def test_trace_forward_multi_hop():
    from correlation.fund_trace import trace_funds

    mock_client = MagicMock()
    mock_client.search.side_effect = [
        # Hop 1
        _mock_es_transfer_response([
            ("0xattacker", "0xhop1", 10.0, "0xtx1", 100),
        ]),
        # Hop 2
        _mock_es_transfer_response([
            ("0xhop1", "0xhop2", 8.0, "0xtx2", 101),
        ]),
        # Hop 3
        _mock_es_transfer_response([
            ("0xhop2", "0xhop3", 6.0, "0xtx3", 102),
        ]),
        # Hop 4: no more
        _mock_es_transfer_response([]),
    ]

    trail = trace_funds(
        mock_client, "0xattacker", "INV-001",
        direction="forward", max_hops=5
    )

    assert len(trail) == 3
    assert trail[0]["hop_number"] == 1
    assert trail[1]["hop_number"] == 2
    assert trail[2]["hop_number"] == 3


def test_trace_backward():
    from correlation.fund_trace import trace_funds

    mock_client = MagicMock()
    mock_client.search.side_effect = [
        # Hop 1 backward: who funded attacker?
        _mock_es_transfer_response([
            ("0xfunder", "0xattacker", 15.0, "0xtx0", 95),
        ]),
        # Hop 2: who funded funder?
        _mock_es_transfer_response([]),
    ]

    trail = trace_funds(
        mock_client, "0xattacker", "INV-001",
        direction="backward", max_hops=5
    )

    assert len(trail) == 1
    assert trail[0]["from_address"] == "0xfunder"
    assert trail[0]["to_address"] == "0xattacker"
    assert trail[0]["direction"] == "backward"


def test_trace_respects_max_hops():
    from correlation.fund_trace import trace_funds

    mock_client = MagicMock()
    # Create infinite chain of hops
    def make_response(call_count=[0]):
        call_count[0] += 1
        hop = call_count[0]
        return _mock_es_transfer_response([
            (f"0xhop{hop}", f"0xhop{hop+1}", 10.0, f"0xtx{hop}", 100 + hop),
        ])

    mock_client.search.side_effect = [make_response() for _ in range(6)]

    trail = trace_funds(
        mock_client, "0xhop1", "INV-001",
        direction="forward", max_hops=3
    )

    # Should stop at 3 hops
    assert len(trail) <= 3


def test_trace_applies_taint_haircut_through_mixer():
    from correlation.fund_trace import trace_funds

    mock_client = MagicMock()
    # Tornado Cash address
    tornado = "0xd90e2f925da726b50c4ed8d0fb90ad053324f31b"
    mock_client.search.side_effect = [
        # Hop 1: attacker -> tornado cash
        _mock_es_transfer_response([
            ("0xattacker", tornado, 10.0, "0xtx1", 100),
        ]),
        # Hop 2: tornado -> destination
        _mock_es_transfer_response([
            (tornado, "0xdest", 10.0, "0xtx2", 200),
        ]),
        # No more hops
        _mock_es_transfer_response([]),
    ]

    trail = trace_funds(
        mock_client, "0xattacker", "INV-001",
        direction="forward", max_hops=5
    )

    assert len(trail) == 2
    # First hop: taint reduced because destination is mixer (0.7)
    assert trail[0]["taint_score"] == pytest.approx(0.7)
    # Second hop: from mixer, destination is unknown (1.0 * 0.7 = 0.7)
    assert trail[1]["taint_score"] == pytest.approx(0.7)


def test_trace_avoids_cycles():
    from correlation.fund_trace import trace_funds

    mock_client = MagicMock()
    mock_client.search.side_effect = [
        # Hop 1: A -> B
        _mock_es_transfer_response([
            ("0xa", "0xb", 10.0, "0xtx1", 100),
        ]),
        # Hop 2: B -> A (cycle!)
        _mock_es_transfer_response([
            ("0xb", "0xa", 5.0, "0xtx2", 101),
        ]),
        # Should not re-process A
        _mock_es_transfer_response([]),
    ]

    trail = trace_funds(
        mock_client, "0xa", "INV-001",
        direction="forward", max_hops=5
    )

    # Should trace A->B and B->A but not revisit A
    visited_froms = [t["from_address"] for t in trail]
    assert visited_froms.count("0xa") <= 1


def test_trace_produces_fund_flow_edge_documents():
    from correlation.fund_trace import trace_funds

    mock_client = MagicMock()
    mock_client.search.side_effect = [
        _mock_es_transfer_response([
            ("0xattacker", "0xdest", 10.0, "0xtx1", 100),
        ]),
        _mock_es_transfer_response([]),
    ]

    trail = trace_funds(
        mock_client, "0xattacker", "INV-001",
        direction="forward", max_hops=5
    )

    doc = trail[0]
    assert doc["layer"] == "derived"
    assert doc["derived_type"] == "fund_flow_edge"
    assert "investigation_id" in doc
    assert "taint_score" in doc
    assert "hop_number" in doc
    assert "direction" in doc
    assert "tx_hash" in doc


def test_build_fund_trail_document():
    from correlation.fund_trace import build_fund_trail_document

    trail = [
        {"from_address": "0xa", "to_address": "0xb", "value_eth": 10.0, "hop_number": 1},
        {"from_address": "0xb", "to_address": "0xc", "value_eth": 8.0, "hop_number": 2},
    ]

    doc = build_fund_trail_document(
        "0xa", trail, "INV-001", 31337
    )

    assert doc["layer"] == "attacker"
    assert doc["attacker_type"] == "fund_trail"
    assert doc["fund_trail_hops"] == 2
    assert doc["investigation_id"] == "INV-001"
