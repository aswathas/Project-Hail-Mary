"""Balance Spike Registry — flags addresses receiving large ETH amounts in a single tx."""
from pipeline.derived._base import base_doc

# Threshold in ETH above which a receipt is flagged as a spike
SPIKE_THRESHOLD_ETH = 5.0


async def derive(raw_data: dict, investigation_id: str, config: dict) -> list[dict]:
    """Derive balance_spike_registry records from large-value ETH transfers.

    raw_data keys: normalized_tx
    Threshold: 5 ETH received in a single transaction (baseline; tunable via signals).
    """
    results = []
    normalized_tx = raw_data.get("normalized_tx")
    if not normalized_tx:
        return results

    value_eth = normalized_tx.get("value_eth", 0)
    to_address = normalized_tx.get("to_address", "")

    if value_eth < SPIKE_THRESHOLD_ETH or not to_address:
        return results

    tx_hash = normalized_tx.get("tx_hash", "")
    block_number = normalized_tx.get("block_number", 0)
    block_datetime = normalized_tx.get("block_datetime", "")

    doc = base_doc(tx_hash, block_number, block_datetime,
                   investigation_id, "balance_spike_registry",
                   source_layer="raw")
    doc.update({
        "recipient_address": to_address,
        "received_eth": value_eth,
        "is_spike": True,
    })
    results.append(doc)

    return results
