"""Address Activity Summary — aggregates per-address stats from a transaction."""
from pipeline.derived._base import base_doc


async def derive(raw_data: dict, investigation_id: str, config: dict) -> list[dict]:
    """Derive address_activity_summary records from a normalized transaction.

    raw_data keys: normalized_tx
    """
    results = []
    normalized_tx = raw_data.get("normalized_tx")
    if not normalized_tx:
        return results

    tx_hash = normalized_tx.get("tx_hash", "")
    block_number = normalized_tx.get("block_number", 0)
    block_datetime = normalized_tx.get("block_datetime", "")
    from_address = normalized_tx.get("from_address", "")
    to_address = normalized_tx.get("to_address", "")
    value_eth = normalized_tx.get("value_eth", 0)
    gas_used = normalized_tx.get("gas_used", 0)
    input_data = normalized_tx.get("input", "0x")
    success = normalized_tx.get("success", False)

    is_deployment = not to_address or to_address == "0x" + "0" * 40
    is_contract_call = bool(input_data and input_data != "0x" and to_address)

    doc = base_doc(tx_hash, block_number, block_datetime,
                   investigation_id, "address_activity_summary",
                   source_layer="raw")
    doc.update({
        "from_address": from_address,
        "to_address": to_address or "",
        "value_eth": value_eth,
        "gas_used": gas_used,
        "is_deployment": is_deployment,
        "is_contract_call": is_contract_call,
        "success": success,
    })
    results.append(doc)

    return results
