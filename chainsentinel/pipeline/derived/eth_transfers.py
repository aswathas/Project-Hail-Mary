"""ETH Transfers — derives native ETH transfer records from transactions."""
from pipeline.derived._base import base_doc


async def derive(raw_data: dict, investigation_id: str, config: dict) -> list[dict]:
    """Derive eth_transfers records from normalized transactions.

    raw_data keys: normalized_tx (a single normalized transaction dict)
    """
    results = []
    normalized_tx = raw_data.get("normalized_tx")
    if not normalized_tx:
        return results

    value_eth = normalized_tx.get("value_eth", 0)
    if value_eth > 0 and normalized_tx.get("success", False):
        doc = base_doc(
            normalized_tx["tx_hash"],
            normalized_tx["block_number"],
            normalized_tx["block_datetime"],
            investigation_id, "eth_transfers",
            source_layer="raw",
        )
        doc.update({
            "from_address": normalized_tx.get("from_address", ""),
            "to_address": normalized_tx.get("to_address", ""),
            "value_eth": value_eth,
            "value_wei": normalized_tx.get("value_wei", "0"),
        })
        results.append(doc)

    return results
