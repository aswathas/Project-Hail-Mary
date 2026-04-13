"""Failed Transactions — derives records from failed (reverted) transactions."""
from pipeline.derived._base import base_doc


async def derive(raw_data: dict, investigation_id: str, config: dict) -> list[dict]:
    """Derive failed_transactions records from normalized transactions.

    raw_data keys: normalized_tx (a single normalized transaction dict)
    """
    results = []
    normalized_tx = raw_data.get("normalized_tx")
    if not normalized_tx:
        return results

    if not normalized_tx.get("success", True):
        doc = base_doc(
            normalized_tx["tx_hash"],
            normalized_tx["block_number"],
            normalized_tx["block_datetime"],
            investigation_id, "failed_transactions",
            source_layer="raw",
        )
        doc.update({
            "from_address": normalized_tx.get("from_address", ""),
            "to_address": normalized_tx.get("to_address", ""),
            "contract_address": normalized_tx.get("to_address", ""),
            "func_selector": normalized_tx.get("input", "0x")[:10] if len(normalized_tx.get("input", "0x")) >= 10 else None,
            "function_name": normalized_tx.get("function_name"),
            "gas_used": normalized_tx.get("gas_used", 0),
            "has_error": True,
            "revert_reason": normalized_tx.get("revert_reason"),
            "value_eth": normalized_tx.get("value_eth", 0),
        })
        results.append(doc)

    return results
