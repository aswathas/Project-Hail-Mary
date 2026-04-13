"""Failed Attempt History — records failed transactions for attack pattern analysis."""
from pipeline.derived._base import base_doc


async def derive(raw_data: dict, investigation_id: str, config: dict) -> list[dict]:
    """Derive failed_attempt_history records from failed transactions.

    raw_data keys: normalized_tx, decoded_events
    """
    results = []
    normalized_tx = raw_data.get("normalized_tx")
    if not normalized_tx:
        return results

    # Only failed transactions
    if normalized_tx.get("success", True):
        return results

    tx_hash = normalized_tx.get("tx_hash", "")
    block_number = normalized_tx.get("block_number", 0)
    block_datetime = normalized_tx.get("block_datetime", "")
    from_address = normalized_tx.get("from_address", "")
    to_address = normalized_tx.get("to_address", "")
    gas_used = normalized_tx.get("gas_used", 0)
    input_data = normalized_tx.get("input", "0x")

    # Attempt to get function name from decoded events or selector
    func_name = None
    decoded_events = raw_data.get("decoded_events", [])
    if decoded_events:
        func_name = decoded_events[0].get("function_name")
    if not func_name and input_data and len(input_data) >= 10:
        func_name = input_data[:10]

    doc = base_doc(tx_hash, block_number, block_datetime,
                   investigation_id, "failed_attempt_history",
                   source_layer="raw")
    doc.update({
        "from_address": from_address,
        "to_address": to_address or "",
        "func_name": func_name or "",
        "gas_used": gas_used,
        "status": 0,
    })
    results.append(doc)

    return results
