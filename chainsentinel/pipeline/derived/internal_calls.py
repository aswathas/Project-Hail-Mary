"""Internal Calls — every sub-call flattened from call traces.

Produces one record per internal call (CALL, DELEGATECALL, STATICCALL,
CREATE, CREATE2) found in the trace tree. Unlike execution_structure
which preserves the tree hierarchy, this is a flat list of all calls
for easy querying.

Derives from: call_traces_raw
"""
from pipeline.derived._base import base_doc, hex_to_int


def _flatten_calls(trace, tx_hash, block_number, block_datetime,
                   investigation_id, depth=0, counter=None):
    """Recursively flatten all internal calls from trace."""
    if counter is None:
        counter = [0]

    results = []

    # Skip the root call (depth 0) — that's the external transaction itself
    if depth > 0:
        call_index = counter[0]
        counter[0] += 1

        value_int = hex_to_int(trace.get("value", "0x0"))
        value_eth = value_int / 1e18 if value_int else 0.0

        input_data = trace.get("input", "0x")
        selector = input_data[:10] if input_data and len(input_data) >= 10 else None

        doc = base_doc(tx_hash, block_number, block_datetime,
                       investigation_id, "internal_calls",
                       source_log_index=call_index,
                       source_layer="trace")
        doc.update({
            "caller_address": str(trace.get("from", "")).lower(),
            "callee_address": str(trace.get("to", "")).lower(),
            "call_type": trace.get("type", "CALL"),
            "func_selector": selector,
            "function_name": None,
            "value_eth": value_eth,
            "call_depth": depth,
            "call_index": call_index,
            "gas_used": hex_to_int(trace.get("gasUsed", 0)),
            "success": trace.get("error") is None,
            "has_error": trace.get("error") is not None,
            "revert_reason": trace.get("error"),
            "parent_type": trace.get("type", "CALL"),
        })
        results.append(doc)
    else:
        counter[0] += 1  # still increment for root

    for sub in trace.get("calls", []):
        results.extend(_flatten_calls(
            sub, tx_hash, block_number, block_datetime,
            investigation_id, depth + 1, counter
        ))

    return results


async def derive(raw_data: dict, investigation_id: str, config: dict) -> list[dict]:
    """Derive internal_calls records from call traces.

    Produces one flat record per internal call (depth > 0) in the trace.

    raw_data keys:
      trace (dict) — the raw call trace
      tx_hash (str), block_number (int), block_datetime (str)
    """
    trace = raw_data.get("trace")
    if not trace:
        return []

    return _flatten_calls(
        trace,
        raw_data.get("tx_hash", ""),
        raw_data.get("block_number", 0),
        raw_data.get("block_datetime", ""),
        investigation_id,
    )
