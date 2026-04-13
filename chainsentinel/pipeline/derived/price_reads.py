"""Price Reads — Oracle function calls extracted from trace.

Detects common oracle price-reading function selectors in the call trace:
getPrice, getReserves, latestAnswer, latestRoundData, observe, slot0, etc.

Derives from: call_traces_raw, event_logs_raw
"""
from pipeline.derived._base import base_doc, hex_to_int

# Common oracle / price-reading function selectors
ORACLE_SELECTORS = {
    "0x98d5fdca": "getPrice",
    "0x0902f1ac": "getReserves",
    "0x50d25bcd": "latestAnswer",
    "0xfeaf968c": "latestRoundData",
    "0x252c09d7": "observe",
    "0x3850c7bd": "slot0",
    "0xd21220a7": "token1",
    "0x0dfe1681": "token0",
    "0x1a686502": "getSqrtPriceX96",
    "0x4622ab03": "getReserveData",
    "0x35ea6a75": "getReserveData",  # Aave v3 variant
    "0xb3596f07": "getAssetPrice",
    "0xb5ab58dc": "getRoundData",
    "0x668a0f02": "latestRound",
    "0x8205bf6a": "latestTimestamp",
    "0x07211ef7": "consult",
}


def _walk_trace_for_oracle_calls(trace, tx_hash, block_number, block_datetime,
                                  investigation_id, depth=0, counter=None):
    """Walk trace tree looking for oracle/price function calls."""
    if counter is None:
        counter = [0]

    results = []
    call_index = counter[0]
    counter[0] += 1

    input_data = trace.get("input", "0x")
    selector = input_data[:10] if input_data and len(input_data) >= 10 else None

    if selector and selector.lower() in ORACLE_SELECTORS:
        func_name = ORACLE_SELECTORS[selector.lower()]
        caller = str(trace.get("from", "")).lower()
        oracle = str(trace.get("to", "")).lower()

        output_data = trace.get("output", "0x")

        doc = base_doc(tx_hash, block_number, block_datetime,
                       investigation_id, "price_reads",
                       source_log_index=call_index,
                       source_layer="trace")
        doc.update({
            "oracle_contract": oracle,
            "caller_address": caller,
            "func_name": func_name,
            "func_selector": selector.lower(),
            "call_depth": depth,
            "call_type": trace.get("type", "CALL"),
            "return_value": output_data[:66] if output_data and len(output_data) > 2 else None,
            "gas_used": hex_to_int(trace.get("gasUsed", 0)),
            "success": trace.get("error") is None,
        })
        results.append(doc)

    for sub in trace.get("calls", []):
        results.extend(_walk_trace_for_oracle_calls(
            sub, tx_hash, block_number, block_datetime,
            investigation_id, depth + 1, counter
        ))

    return results


async def derive(raw_data: dict, investigation_id: str, config: dict) -> list[dict]:
    """Derive price_reads records from call traces.

    Walks the trace tree looking for known oracle function selectors
    and extracts the caller, oracle contract, function name, and return value.

    raw_data keys:
      trace (dict) — the raw call trace
      tx_hash (str), block_number (int), block_datetime (str)
    """
    trace = raw_data.get("trace")
    if not trace:
        return []

    return _walk_trace_for_oracle_calls(
        trace,
        raw_data.get("tx_hash", ""),
        raw_data.get("block_number", 0),
        raw_data.get("block_datetime", ""),
        investigation_id,
    )
