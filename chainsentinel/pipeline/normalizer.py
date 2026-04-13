"""
Normalizer — converts blockchain-native types into a stable typed schema.
Hex → int. Addresses → lowercase. Wei → ETH. Timestamps → ISO 8601.
Unknown fields preserved in raw_extra.
"""
from datetime import datetime, timezone


KNOWN_TX_FIELDS = {
    "hash", "blockNumber", "blockHash", "transactionIndex", "from", "to",
    "value", "gas", "gasPrice", "nonce", "input", "type", "chainId",
    "maxFeePerGas", "maxPriorityFeePerGas", "accessList",
    "transactionHash", "status", "gasUsed", "cumulativeGasUsed",
    "contractAddress", "logs", "logsBloom",
}


def _hex_to_int(val):
    if isinstance(val, str) and val.startswith("0x"):
        return int(val, 16)
    if isinstance(val, int):
        return val
    return val


def _to_iso8601(timestamp_int: int) -> str:
    return datetime.fromtimestamp(timestamp_int, tz=timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )


def normalize_transaction(
    raw_tx: dict, raw_receipt: dict, block_timestamp: int, chain_id: int
) -> dict:
    """Normalize a raw tx + receipt into a stable schema."""
    value_wei = _hex_to_int(raw_tx.get("value", 0))
    value_eth = value_wei / 1e18 if isinstance(value_wei, (int, float)) else 0.0

    status_raw = _hex_to_int(raw_receipt.get("status", 0))
    success = bool(status_raw)

    block_datetime = _to_iso8601(block_timestamp)

    contract_addr = raw_receipt.get("contractAddress", raw_receipt.get("contract_address"))

    # Collect unknown fields into raw_extra
    all_keys = set(raw_tx.keys()) | set(raw_receipt.keys())
    raw_extra = {}
    for key in all_keys:
        if key not in KNOWN_TX_FIELDS:
            val = raw_tx.get(key, raw_receipt.get(key))
            if val is not None:
                raw_extra[key] = val

    from_addr = str(raw_tx.get("from", "")).lower()
    to_addr = str(raw_tx.get("to", "")).lower() if raw_tx.get("to") else ""

    logs = []
    for log in raw_receipt.get("logs", []):
        logs.append(normalize_log(log, block_datetime=block_datetime, chain_id=chain_id))

    return {
        "tx_hash": str(raw_tx.get("hash", raw_receipt.get("transactionHash", ""))).lower(),
        "block_number": _hex_to_int(raw_tx.get("blockNumber", 0)),
        "block_datetime": block_datetime,
        "block_timestamp_raw": block_timestamp,
        "tx_index": _hex_to_int(raw_tx.get("transactionIndex", 0)),
        "from_address": from_addr,
        "to_address": to_addr,
        "value_eth": value_eth,
        "value_wei": str(value_wei),
        "gas": _hex_to_int(raw_tx.get("gas", 0)),
        "gas_price": _hex_to_int(raw_tx.get("gasPrice", 0)),
        "gas_used": _hex_to_int(raw_receipt.get("gasUsed", 0)),
        "cumulative_gas_used": _hex_to_int(raw_receipt.get("cumulativeGasUsed", 0)),
        "nonce": _hex_to_int(raw_tx.get("nonce", 0)),
        "input": str(raw_tx.get("input", "0x")),
        "success": success,
        "contract_address": str(contract_addr).lower() if contract_addr else None,
        "logs": logs,
        "chain_id": chain_id,
        "decode_status": "pending",
        "raw_extra": raw_extra,
    }


def normalize_log(raw_log: dict, block_datetime: str, chain_id: int) -> dict:
    """Normalize a raw event log."""

    def _extract_topic(t):
        if hasattr(t, "hex"):
            h = t.hex()
            return h if h.startswith("0x") else "0x" + h
        if isinstance(t, bytes):
            return "0x" + t.hex()
        return str(t)

    return {
        "tx_hash": str(
            raw_log.get("transactionHash", raw_log.get("transaction_hash", ""))
        ).lower(),
        "block_number": _hex_to_int(
            raw_log.get("blockNumber", raw_log.get("block_number", 0))
        ),
        "block_datetime": block_datetime,
        "log_index": _hex_to_int(
            raw_log.get("logIndex", raw_log.get("log_index", 0))
        ),
        "log_address": str(raw_log.get("address", "")).lower(),
        "topics": [_extract_topic(t) for t in raw_log.get("topics", [])],
        "data": str(raw_log.get("data", "0x")),
        "chain_id": chain_id,
    }
