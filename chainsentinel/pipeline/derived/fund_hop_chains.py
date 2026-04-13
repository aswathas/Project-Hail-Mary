"""Fund Hop Chains — records value transfers as potential fund hops for BFS tracing."""
from pipeline.derived._base import base_doc


async def derive(raw_data: dict, investigation_id: str, config: dict) -> list[dict]:
    """Derive fund_hop_chains records from value-bearing transactions.

    raw_data keys: normalized_tx
    hop_index=0 is set here; full BFS chain is computed at query/correlation time.
    """
    results = []
    normalized_tx = raw_data.get("normalized_tx")
    if not normalized_tx:
        return results

    value_eth = normalized_tx.get("value_eth", 0)
    from_address = normalized_tx.get("from_address", "")
    to_address = normalized_tx.get("to_address", "")

    if value_eth <= 0 or not from_address or not to_address:
        return results

    tx_hash = normalized_tx.get("tx_hash", "")
    block_number = normalized_tx.get("block_number", 0)
    block_datetime = normalized_tx.get("block_datetime", "")

    doc = base_doc(tx_hash, block_number, block_datetime,
                   investigation_id, "fund_hop_chains",
                   source_layer="raw")
    doc.update({
        "from_address": from_address,
        "to_address": to_address,
        "value_eth": value_eth,
        "hop_index": 0,
    })
    results.append(doc)

    return results
