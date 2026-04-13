"""Address First Contact — records when an address first interacts with a contract."""
from pipeline.derived._base import base_doc


async def derive(raw_data: dict, investigation_id: str, config: dict) -> list[dict]:
    """Derive address_first_contact records from normalized transactions.

    raw_data keys: normalized_tx, decoded_events
    Deduplication (true first interaction) is computed at query time via ES aggregation.
    """
    results = []
    normalized_tx = raw_data.get("normalized_tx")
    if not normalized_tx:
        return results

    to_address = normalized_tx.get("to_address", "")
    input_data = normalized_tx.get("input", "0x")

    # Only record contract interactions (not plain ETH transfers or deployments)
    if not to_address or to_address == "0x" + "0" * 40:
        return results
    if not input_data or input_data == "0x":
        return results

    tx_hash = normalized_tx.get("tx_hash", "")
    block_number = normalized_tx.get("block_number", 0)
    block_datetime = normalized_tx.get("block_datetime", "")
    from_address = normalized_tx.get("from_address", "")

    # Attempt to extract func_name from decoded events or input selector
    func_name = None
    decoded_events = raw_data.get("decoded_events", [])
    if decoded_events:
        func_name = decoded_events[0].get("function_name")

    if not func_name and len(input_data) >= 10:
        func_name = input_data[:10]

    doc = base_doc(tx_hash, block_number, block_datetime,
                   investigation_id, "address_first_contact",
                   source_layer="raw")
    doc.update({
        "from_address": from_address,
        "contract_address": to_address,
        "func_name": func_name or "",
        "is_first_interaction": True,
    })
    results.append(doc)

    return results
