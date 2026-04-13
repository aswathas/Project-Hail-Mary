"""Event Sequence — CRITICAL derived log.

Ordered decoded events within a single transaction by log_index.
Captures the exact sequence of events which is essential for detecting
order violations, missing events, and duplicate emissions.

Derives from: event_logs_raw + ABI
"""
from pipeline.derived._base import base_doc


async def derive(raw_data: dict, investigation_id: str, config: dict) -> list[dict]:
    """Derive event_sequence records from decoded events.

    Produces one record per event, ordered by log_index within the tx.
    The position_in_tx field provides the 0-based sequence number.

    raw_data keys:
      decoded_events (list) — decoded event log dicts with log_index
      tx_hash (str), block_number (int), block_datetime (str)
    """
    decoded_events = raw_data.get("decoded_events", [])
    if not decoded_events:
        return []

    tx_hash = raw_data.get("tx_hash", "")
    block_number = raw_data.get("block_number", 0)
    block_datetime = raw_data.get("block_datetime", "")

    # Sort by log_index to establish sequence
    sorted_events = sorted(decoded_events, key=lambda e: e.get("log_index", 0))

    results = []
    for position, event in enumerate(sorted_events):
        log_index = event.get("log_index", position)

        doc = base_doc(tx_hash, block_number, block_datetime,
                       investigation_id, "event_sequence",
                       source_log_index=log_index,
                       source_layer="decoded")
        doc.update({
            "contract_address": event.get("log_address", ""),
            "event_name": event.get("event_name", ""),
            "event_args": event.get("event_args", {}),
            "position_in_tx": position,
            "log_index": log_index,
            "decode_status": event.get("decode_status", "unknown"),
        })
        results.append(doc)

    return results
