"""Enriched Event Logs — produces enriched records from decoded event logs."""
from pipeline.derived._base import base_doc


async def derive(raw_data: dict, investigation_id: str, config: dict) -> list[dict]:
    """Derive enriched event log records from decoded events.

    raw_data keys: decoded_events (list of decoded event log dicts)
    """
    results = []
    decoded_events = raw_data.get("decoded_events", [])

    for event in decoded_events:
        name = event.get("event_name")
        if not name:
            continue

        tx_hash = event.get("tx_hash", "")
        block_number = event.get("block_number", 0)
        block_datetime = event.get("block_datetime", "")
        log_index = event.get("log_index", 0)

        doc = base_doc(tx_hash, block_number, block_datetime,
                       investigation_id, "enriched_event_logs", log_index)
        doc.update({
            "event_name": name,
            "event_args": event.get("event_args", {}),
            "contract_address": event.get("log_address", ""),
            "decode_status": event.get("decode_status", "unknown"),
            "token_symbol": event.get("token_symbol", ""),
            "token_decimals": event.get("token_decimals"),
            "position_in_tx": log_index,
        })
        results.append(doc)

    return results
