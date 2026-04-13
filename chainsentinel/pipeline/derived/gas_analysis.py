"""Gas Analysis — derives gas usage records from transactions and receipts."""
from pipeline.derived._base import base_doc


async def derive(raw_data: dict, investigation_id: str, config: dict) -> list[dict]:
    """Derive gas_analysis records from normalized transactions.

    raw_data keys: normalized_tx (a single normalized transaction dict)
    """
    results = []
    normalized_tx = raw_data.get("normalized_tx")
    if not normalized_tx:
        return results

    gas_used = normalized_tx.get("gas_used", 0)
    gas_limit = normalized_tx.get("gas", 0)

    doc = base_doc(
        normalized_tx["tx_hash"],
        normalized_tx["block_number"],
        normalized_tx["block_datetime"],
        investigation_id, "gas_analysis",
        source_layer="raw",
    )

    gas_pct = (gas_used / gas_limit * 100) if gas_limit else 0.0
    gas_price = normalized_tx.get("gas_price", 0)
    gas_price_gwei = gas_price / 1e9 if gas_price else 0.0
    fee_eth = (gas_used * gas_price) / 1e18 if gas_price else 0.0

    doc.update({
        "from_address": normalized_tx.get("from_address", ""),
        "to_address": normalized_tx.get("to_address", ""),
        "gas_used": gas_used,
        "gas_limit": gas_limit,
        "gas_price_gwei": gas_price_gwei,
        "gas_utilisation_pct": gas_pct,
        "fee_eth": fee_eth,
        "success": normalized_tx.get("success", False),
    })
    results.append(doc)

    return results
