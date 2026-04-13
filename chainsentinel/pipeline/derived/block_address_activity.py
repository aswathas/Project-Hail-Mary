"""Block Address Activity — records all addresses active in a tx within a block."""
from pipeline.derived._base import base_doc


async def derive(raw_data: dict, investigation_id: str, config: dict) -> list[dict]:
    """Derive block_address_activity records from normalized transactions.

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
    tx_index = normalized_tx.get("transaction_index", normalized_tx.get("tx_index", 0))
    gas_price = normalized_tx.get("gas_price", 0)
    gas_price_gwei = gas_price / 1e9 if gas_price else 0.0
    input_data = normalized_tx.get("input", "0x")
    is_contract_call = bool(input_data and input_data != "0x" and to_address)

    doc = base_doc(tx_hash, block_number, block_datetime,
                   investigation_id, "block_address_activity",
                   source_layer="raw")
    doc.update({
        "from_address": from_address,
        "to_address": to_address or "",
        "tx_index": tx_index,
        "gas_price_gwei": gas_price_gwei,
        "is_contract_call": is_contract_call,
    })
    results.append(doc)

    return results
