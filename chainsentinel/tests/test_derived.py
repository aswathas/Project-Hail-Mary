import pytest


def test_derive_asset_transfer_from_decoded_transfer():
    from pipeline.derived import derive_events

    decoded_event = {
        "tx_hash": "0xabc",
        "block_number": 10,
        "block_datetime": "2026-01-15T12:00:00Z",
        "log_index": 0,
        "log_address": "0xtoken",
        "event_name": "Transfer",
        "event_args": {
            "from": "0xsender",
            "to": "0xreceiver",
            "value": 100000000,
        },
        "decode_status": "decoded",
        "token_symbol": "USDC",
        "token_decimals": 6,
    }

    results = derive_events([decoded_event], investigation_id="INV-001")

    transfers = [r for r in results if r["derived_type"] == "asset_transfer"]
    assert len(transfers) == 1
    assert transfers[0]["from_address"] == "0xsender"
    assert transfers[0]["to_address"] == "0xreceiver"
    assert transfers[0]["amount_decimal"] == 100.0
    assert transfers[0]["source_tx_hash"] == "0xabc"
    assert transfers[0]["source_log_index"] == 0
    assert transfers[0]["source_layer"] == "decoded"


def test_derive_native_transfer_from_tx():
    from pipeline.derived import derive_events_from_tx

    normalized_tx = {
        "tx_hash": "0xabc",
        "block_number": 10,
        "block_datetime": "2026-01-15T12:00:00Z",
        "from_address": "0xsender",
        "to_address": "0xreceiver",
        "value_eth": 5.0,
        "value_wei": "5000000000000000000",
        "success": True,
    }

    results = derive_events_from_tx(normalized_tx, investigation_id="INV-001")

    native = [r for r in results if r["derived_type"] == "native_transfer"]
    assert len(native) == 1
    assert native[0]["value_eth"] == 5.0
    assert native[0]["from_address"] == "0xsender"


def test_derive_admin_action_from_ownership_transfer():
    from pipeline.derived import derive_events

    decoded_event = {
        "tx_hash": "0xabc",
        "block_number": 10,
        "block_datetime": "2026-01-15T12:00:00Z",
        "log_index": 1,
        "log_address": "0xcontract",
        "event_name": "OwnershipTransferred",
        "event_args": {
            "previousOwner": "0xold_owner",
            "newOwner": "0xnew_owner",
        },
        "decode_status": "decoded",
    }

    results = derive_events([decoded_event], investigation_id="INV-001")

    admin = [r for r in results if r["derived_type"] == "admin_action"]
    assert len(admin) == 1
    assert admin[0]["action_type"] == "ownership_transfer"
    assert admin[0]["actor_address"] == "0xnew_owner"


def test_derive_execution_edge_from_trace():
    from pipeline.derived import derive_events_from_trace

    trace = {
        "type": "CALL",
        "from": "0xcaller",
        "to": "0xcallee",
        "value": "0xde0b6b3a7640000",
        "input": "0xa9059cbb",
        "gas": "0x5208",
        "gasUsed": "0x1388",
        "calls": [
            {
                "type": "DELEGATECALL",
                "from": "0xcallee",
                "to": "0ximpl",
                "value": "0x0",
                "input": "0x",
                "gas": "0x2710",
                "gasUsed": "0xbb8",
                "calls": [],
            }
        ],
    }

    results = derive_events_from_trace(
        trace, tx_hash="0xabc", block_number=10,
        block_datetime="2026-01-15T12:00:00Z", investigation_id="INV-001"
    )

    edges = [r for r in results if r["derived_type"] == "execution_edge"]
    assert len(edges) == 2  # root call + inner delegatecall
    assert edges[0]["call_type"] == "CALL"
    assert edges[0]["call_depth"] == 0
    assert edges[1]["call_type"] == "DELEGATECALL"
    assert edges[1]["call_depth"] == 1


def test_every_derived_event_has_chain_of_custody():
    from pipeline.derived import derive_events

    decoded_event = {
        "tx_hash": "0xabc",
        "block_number": 10,
        "block_datetime": "2026-01-15T12:00:00Z",
        "log_index": 0,
        "log_address": "0xtoken",
        "event_name": "Transfer",
        "event_args": {"from": "0xa", "to": "0xb", "value": 1000},
        "decode_status": "decoded",
    }

    results = derive_events([decoded_event], investigation_id="INV-001")

    for r in results:
        assert "source_tx_hash" in r
        assert "source_log_index" in r or r["derived_type"] == "balance_delta"
        assert "source_layer" in r
        assert r["investigation_id"] == "INV-001"
