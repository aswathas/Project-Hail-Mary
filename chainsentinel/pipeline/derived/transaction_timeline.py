"""Transaction Timeline — single unified record per tx with type classification."""
from pipeline.derived._base import base_doc


def _classify_tx(normalized_tx: dict) -> str:
    to_address = normalized_tx.get("to_address", "")
    input_data = normalized_tx.get("input", "0x")
    success = normalized_tx.get("success", True)

    if not success:
        return "failed"
    if not to_address or to_address == "0x" + "0" * 40:
        return "deploy"
    if input_data and input_data != "0x":
        return "contract_call"
    return "transfer"


async def derive(raw_data: dict, investigation_id: str, config: dict) -> list[dict]:
    """Derive transaction_timeline records from a normalized transaction.

    raw_data keys: normalized_tx, decoded_events
    """
    results = []
    normalized_tx = raw_data.get("normalized_tx")
    if not normalized_tx:
        return results

    tx_hash = normalized_tx.get("tx_hash", "")
    block_number = normalized_tx.get("block_number", 0)
    block_datetime = normalized_tx.get("block_datetime", "")
    decoded_events = raw_data.get("decoded_events", [])

    doc = base_doc(tx_hash, block_number, block_datetime,
                   investigation_id, "transaction_timeline",
                   source_layer="raw")
    doc.update({
        "from_address": normalized_tx.get("from_address", ""),
        "to_address": normalized_tx.get("to_address", ""),
        "value_eth": normalized_tx.get("value_eth", 0),
        "tx_type": _classify_tx(normalized_tx),
        "status": 1 if normalized_tx.get("success", False) else 0,
        "events_count": len(decoded_events),
        "gas_used": normalized_tx.get("gas_used", 0),
    })
    results.append(doc)

    return results
