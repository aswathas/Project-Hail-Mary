import pytest


def test_normalizer_converts_hex_to_int(sample_raw_tx, sample_raw_receipt):
    from pipeline.normalizer import normalize_transaction

    result = normalize_transaction(sample_raw_tx, sample_raw_receipt, block_timestamp=1736942400, chain_id=31337)

    assert result["block_number"] == 10
    assert isinstance(result["block_number"], int)
    assert result["gas"] == 21000
    assert result["gas_used"] == 21000
    assert result["nonce"] == 5


def test_normalizer_lowercases_addresses(sample_raw_tx, sample_raw_receipt):
    from pipeline.normalizer import normalize_transaction

    result = normalize_transaction(sample_raw_tx, sample_raw_receipt, block_timestamp=1736942400, chain_id=31337)

    assert result["from_address"] == "0xdeadbeefdeadbeefdeadbeefdeadbeefdeadbeef"
    assert result["to_address"] == "0x1234567890abcdef1234567890abcdef12345678"
    assert result["from_address"] == result["from_address"].lower()


def test_normalizer_converts_wei_to_eth(sample_raw_tx, sample_raw_receipt):
    from pipeline.normalizer import normalize_transaction

    result = normalize_transaction(sample_raw_tx, sample_raw_receipt, block_timestamp=1736942400, chain_id=31337)

    assert result["value_eth"] == 1.0
    assert result["value_wei"] == "1000000000000000000"
    assert isinstance(result["value_wei"], str)


def test_normalizer_converts_timestamp_to_iso(sample_raw_tx, sample_raw_receipt):
    from pipeline.normalizer import normalize_transaction

    result = normalize_transaction(sample_raw_tx, sample_raw_receipt, block_timestamp=1736942400, chain_id=31337)

    assert result["block_datetime"].endswith("Z")
    assert result["block_timestamp_raw"] == 1736942400


def test_normalizer_sets_success_boolean(sample_raw_tx, sample_raw_receipt):
    from pipeline.normalizer import normalize_transaction

    result = normalize_transaction(sample_raw_tx, sample_raw_receipt, block_timestamp=1736942400, chain_id=31337)
    assert result["success"] is True

    sample_raw_receipt["status"] = "0x0"
    result2 = normalize_transaction(sample_raw_tx, sample_raw_receipt, block_timestamp=1736942400, chain_id=31337)
    assert result2["success"] is False


def test_normalizer_sets_decode_status_pending(sample_raw_tx, sample_raw_receipt):
    from pipeline.normalizer import normalize_transaction

    result = normalize_transaction(sample_raw_tx, sample_raw_receipt, block_timestamp=1736942400, chain_id=31337)

    assert result["decode_status"] == "pending"


def test_normalizer_preserves_unknown_fields(sample_raw_tx, sample_raw_receipt):
    from pipeline.normalizer import normalize_transaction

    sample_raw_tx["weirdNewField"] = "unexpected_data"
    result = normalize_transaction(sample_raw_tx, sample_raw_receipt, block_timestamp=1736942400, chain_id=31337)

    assert "weirdNewField" in result["raw_extra"]


def test_normalize_log(sample_raw_log):
    from pipeline.normalizer import normalize_log

    result = normalize_log(sample_raw_log, block_datetime="2026-01-15T12:00:00Z", chain_id=31337)

    assert result["log_address"] == "0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48"
    assert result["block_number"] == 10
    assert result["log_index"] == 0
    assert len(result["topics"]) == 3
