"""Address Interaction Graph — who-called-whom records for address relationship analysis."""
from pipeline.derived._base import base_doc


async def derive(raw_data: dict, investigation_id: str, config: dict) -> list[dict]:
    """Derive address_interaction_graph edges from a transaction.

    raw_data keys: normalized_tx
    """
    results = []
    normalized_tx = raw_data.get("normalized_tx")
    if not normalized_tx:
        return results

    from_address = normalized_tx.get("from_address", "")
    to_address = normalized_tx.get("to_address", "")
    if not from_address or not to_address:
        return results

    tx_hash = normalized_tx.get("tx_hash", "")
    block_number = normalized_tx.get("block_number", 0)
    block_datetime = normalized_tx.get("block_datetime", "")
    value_eth = normalized_tx.get("value_eth", 0)
    input_data = normalized_tx.get("input", "0x")
    edge_type = "contract_call" if (input_data and input_data != "0x") else "transfer"

    doc = base_doc(tx_hash, block_number, block_datetime,
                   investigation_id, "address_interaction_graph",
                   source_layer="raw")
    doc.update({
        "from_address": from_address,
        "to_address": to_address,
        "call_count": 1,
        "value_eth": value_eth,
        "edge_type": edge_type,
    })
    results.append(doc)

    return results
