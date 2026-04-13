"""Storage Mutations — derives storage slot change records from traces/state diffs."""
from pipeline.derived._base import base_doc, hex_to_int


async def derive(raw_data: dict, investigation_id: str, config: dict) -> list[dict]:
    """Derive storage_mutations records from trace state diffs.

    raw_data keys: normalized_tx, trace
    """
    results = []
    normalized_tx = raw_data.get("normalized_tx")
    if not normalized_tx:
        return results

    tx_hash = normalized_tx.get("tx_hash", "")
    block_number = normalized_tx.get("block_number", 0)
    block_datetime = normalized_tx.get("block_datetime", "")
    from_address = normalized_tx.get("from_address", "")

    trace = raw_data.get("trace") or {}

    # Extract state diffs if present (debug_traceTransaction with stateDiff)
    state_diff = trace.get("stateDiff") or trace.get("state_diff") or {}

    slot_index = 0
    for contract_address, contract_diff in state_diff.items():
        storage_diff = contract_diff.get("storage") or {}
        for slot_hex, change in storage_diff.items():
            value_before = change.get("*", {}).get("from", change.get("from", "0x0"))
            value_after = change.get("*", {}).get("to", change.get("to", "0x0"))

            if isinstance(value_before, dict):
                value_before = str(value_before.get("from", "0x0"))
            if isinstance(value_after, dict):
                value_after = str(value_after.get("to", "0x0"))

            # "+" key indicates new slot creation
            is_new_slot = "+" in change

            doc = base_doc(tx_hash, block_number, block_datetime,
                           investigation_id, "storage_mutations", slot_index,
                           source_layer="trace")
            doc.update({
                "from_address": from_address,
                "contract_address": str(contract_address).lower(),
                "slot_hex": slot_hex,
                "value_before": str(value_before),
                "value_after": str(value_after),
                "is_new_slot": is_new_slot,
            })
            results.append(doc)
            slot_index += 1

    return results
