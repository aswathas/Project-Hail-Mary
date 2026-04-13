"""Token Transfer Graph — derives token flow records from Transfer events."""
from pipeline.derived._base import base_doc


async def derive(raw_data: dict, investigation_id: str, config: dict) -> list[dict]:
    """Derive asset_transfer records from decoded Transfer events.

    raw_data keys: decoded_events (list of decoded event log dicts)
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

        doc = base_doc(tx_hash, block_number, block_datetime,
                       investigation_id, "token_transfer_graph", log_index)

        from_addr = str(args.get("from", "")).lower()
        to_addr = str(args.get("to", "")).lower()
        raw_value = args.get("value", 0)
        decimals = event.get("token_decimals", 18)
        amount = raw_value / (10 ** decimals) if decimals else raw_value

        doc.update({
            "from_address": from_addr,
            "to_address": to_addr,
            "token_address": event.get("log_address", ""),
            "token_symbol": event.get("token_symbol", ""),
            "amount_decimal": amount,
            "value_wei": str(raw_value),
            "transfer_type": "erc20",
        })

        if from_addr == "0x" + "0" * 40:
            doc["transfer_type"] = "mint"
        elif to_addr == "0x" + "0" * 40:
            doc["transfer_type"] = "burn"

        results.append(doc)

    return results
