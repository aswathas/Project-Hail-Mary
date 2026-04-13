"""Donation Tracker — detects direct ETH sends with empty calldata to contracts."""
from pipeline.derived._base import base_doc


async def derive(raw_data: dict, investigation_id: str, config: dict) -> list[dict]:
    """Derive donation_tracker records from direct ETH sends to contracts.

    Donations: input == "0x" (or empty), value > 0, to_address is set (contract).
    raw_data keys: normalized_tx
    """
    results = []
    normalized_tx = raw_data.get("normalized_tx")
    if not normalized_tx:
        return results

    value_eth = normalized_tx.get("value_eth", 0)
    to_address = normalized_tx.get("to_address", "")
    input_data = normalized_tx.get("input", "0x") or "0x"

    # Must have value, a recipient, and empty calldata (plain ETH send)
    if value_eth <= 0 or not to_address or input_data.lower() not in ("0x", ""):
        return results

    tx_hash = normalized_tx.get("tx_hash", "")
    block_number = normalized_tx.get("block_number", 0)
    block_datetime = normalized_tx.get("block_datetime", "")
    from_address = normalized_tx.get("from_address", "")

    doc = base_doc(tx_hash, block_number, block_datetime,
                   investigation_id, "donation_tracker",
                   source_layer="raw")
    doc.update({
        "from_address": from_address,
        "recipient_address": to_address,
        "value_eth": value_eth,
        "is_donation": True,
    })
    results.append(doc)

    return results
