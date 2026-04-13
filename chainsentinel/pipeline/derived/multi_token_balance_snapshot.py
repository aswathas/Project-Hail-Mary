"""Multi-Token Balance Snapshot — records token movements per Transfer event."""
from pipeline.derived._base import base_doc


async def derive(raw_data: dict, investigation_id: str, config: dict) -> list[dict]:
    """Derive multi_token_balance_snapshot records from decoded Transfer events.

    raw_data keys: decoded_events
    One record per Transfer event in the transaction.
    """
    results = []
    decoded_events = raw_data.get("decoded_events", [])

    for event in decoded_events:
        if event.get("event_name") != "Transfer":
            continue

        args = event.get("event_args", {})
        tx_hash = event.get("tx_hash", "")
        block_number = event.get("block_number", 0)
        block_datetime = event.get("block_datetime", "")
        log_index = event.get("log_index", 0)

        raw_value = args.get("value", 0)
        decimals = event.get("token_decimals", 18)
        amount_decimal = raw_value / (10 ** decimals) if decimals else raw_value

        doc = base_doc(tx_hash, block_number, block_datetime,
                       investigation_id, "multi_token_balance_snapshot", log_index)
        doc.update({
            "token_address": event.get("log_address", ""),
            "from_address": str(args.get("from", "")).lower(),
            "to_address": str(args.get("to", "")).lower(),
            "amount_decimal": amount_decimal,
            "token_symbol": event.get("token_symbol", ""),
        })
        results.append(doc)

    return results
