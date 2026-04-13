"""Shared helpers for derived log builders."""
from datetime import datetime, timezone


def hex_to_int(val):
    if isinstance(val, str) and val.startswith("0x"):
        return int(val, 16)
    if isinstance(val, int):
        return val
    return 0


def base_doc(tx_hash, block_number, block_datetime, investigation_id, derived_type,
             source_log_index=None, source_layer="decoded"):
    return {
        "investigation_id": investigation_id,
        "layer": "derived",
        "derived_type": derived_type,
        "tx_hash": tx_hash,
        "block_number": block_number,
        "block_datetime": block_datetime,
        "@timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source_tx_hash": tx_hash,
        "source_log_index": source_log_index,
        "source_layer": source_layer,
    }
