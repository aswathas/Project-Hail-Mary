"""Nonce Tracking — tracks transaction nonce per address."""
from pipeline.derived._base import base_doc


async def derive(raw_data: dict, investigation_id: str, config: dict) -> list[dict]:
    """Derive nonce_tracking records from normalized transactions.

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
    nonce = normalized_tx.get("nonce", 0)

    doc = base_doc(tx_hash, block_number, block_datetime,
                   investigation_id, "nonce_tracking",
                   source_layer="raw")
    doc.update({
        "from_address": from_address,
        "nonce_before": nonce,
        "nonce_delta": 1,
    })
    results.append(doc)

    return results
