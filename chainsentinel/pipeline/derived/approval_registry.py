"""Approval Registry — derives approval records from Approval events."""
from pipeline.derived._base import base_doc


async def derive(raw_data: dict, investigation_id: str, config: dict) -> list[dict]:
    """Derive approval_registry records from decoded Approval events.

    raw_data keys: decoded_events (list of decoded event log dicts)
    """
    results = []
    decoded_events = raw_data.get("decoded_events", [])

    MAX_UINT256 = (2 ** 256) - 1

    for event in decoded_events:
        if event.get("event_name") != "Approval":
            continue

        args = event.get("event_args", {})
        tx_hash = event.get("tx_hash", "")
        block_number = event.get("block_number", 0)
        block_datetime = event.get("block_datetime", "")
        log_index = event.get("log_index", 0)

        raw_value = args.get("value", 0)

        doc = base_doc(tx_hash, block_number, block_datetime,
                       investigation_id, "approval_registry", log_index)
        doc.update({
            "owner_address": str(args.get("owner", "")).lower(),
            "spender_address": str(args.get("spender", "")).lower(),
            "token_address": event.get("log_address", ""),
            "amount_decimal": raw_value,
            "is_max_approval": raw_value == MAX_UINT256,
            "is_infinite": raw_value == MAX_UINT256,
            "was_consumed": False,
            "consumed_tx_hash": None,
        })
        results.append(doc)

    return results
