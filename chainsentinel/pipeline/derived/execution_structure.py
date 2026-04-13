"""Execution Structure — derives call tree records from trace data.

Renamed from execution_edge to execution_structure per Bible v2.
"""
from pipeline.derived._base import base_doc, hex_to_int


def _derive_from_trace(trace, tx_hash, block_number, block_datetime,
                       investigation_id, depth=0, counter=None):
    """Recursively derive execution_structure events from a call trace."""
    if counter is None:
        counter = [0]

    results = []

    value_hex = trace.get("value", "0x0")
    value_int = hex_to_int(value_hex)
    value_eth = value_int / 1e18 if value_int else 0.0

    call_index = counter[0]
    counter[0] += 1

    doc = base_doc(tx_hash, block_number, block_datetime,
                   investigation_id, "execution_structure",
                   source_log_index=call_index,
                   source_layer="trace")
    doc.update({
        "caller_address": str(trace.get("from", "")).lower(),
        "callee_address": str(trace.get("to", "")).lower(),
        "call_type": trace.get("type", "CALL"),
        "function_name": None,
        "value_eth": value_eth,
        "call_depth": depth,
        "call_index": call_index,
        "gas_used": hex_to_int(trace.get("gasUsed", 0)),
        "success": True,
    })

    input_data = trace.get("input", "0x")
    if input_data and len(input_data) >= 10:
        doc["function_name"] = input_data[:10]
        doc["func_selector"] = input_data[:10]

    results.append(doc)

    for sub_call in trace.get("calls", []):
        results.extend(_derive_from_trace(
            sub_call, tx_hash, block_number, block_datetime,
            investigation_id, depth + 1, counter
        ))

    return results


async def derive(raw_data: dict, investigation_id: str, config: dict) -> list[dict]:
    """Derive execution_structure records from call traces.

    raw_data keys:
      trace (dict) — the raw call trace
      tx_hash (str), block_number (int), block_datetime (str)
    """
    trace = raw_data.get("trace")
    if not trace:
        return []

    return _derive_from_trace(
        trace,
        raw_data.get("tx_hash", ""),
        raw_data.get("block_number", 0),
        raw_data.get("block_datetime", ""),
        investigation_id,
    )
