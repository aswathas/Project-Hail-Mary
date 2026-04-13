"""Contract Interactions — derives contract call records from transactions."""
from pipeline.derived._base import base_doc


async def derive(raw_data: dict, investigation_id: str, config: dict) -> list[dict]:
    """Derive contract_interactions records from normalized transactions.

    raw_data keys: normalized_tx (a single normalized transaction dict)
    """
    results = []
    normalized_tx = raw_data.get("normalized_tx")
    if not normalized_tx:
        return results

    if normalized_tx.get("input", "0x") != "0x" and normalized_tx.get("to_address"):
        doc = base_doc(
            normalized_tx["tx_hash"],
            normalized_tx["block_number"],
            normalized_tx["block_datetime"],
            investigation_id, "contract_interactions",
            source_layer="raw",
        )
        doc.update({
            "user_address": normalized_tx.get("from_address", ""),
            "contract_address": normalized_tx.get("to_address", ""),
            "function_name": normalized_tx.get("function_name"),
            "func_selector": normalized_tx.get("input", "0x")[:10] if len(normalized_tx.get("input", "0x")) >= 10 else None,
            "protocol_name": None,
            "success": normalized_tx.get("success", False),
            "gas_used": normalized_tx.get("gas_used", 0),
        })
        results.append(doc)

    return results
