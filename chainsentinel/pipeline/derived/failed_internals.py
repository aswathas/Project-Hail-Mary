"""Failed Internals — internal reverts within an otherwise successful transaction.

Detects sub-calls that reverted (have "error" field) inside a transaction
whose top-level receipt status is success. These hidden failures are
forensically important: attackers often use try/catch to probe contracts.

Derives from: call_traces_raw, receipts
"""
from pipeline.derived._base import base_doc, hex_to_int


def _find_failed_internals(trace, tx_hash, block_number, block_datetime,
                           investigation_id, depth=0, counter=None):
    """Walk trace tree collecting calls that have an error field."""
    if counter is None:
        counter = [0]

    results = []
    call_index = counter[0]
    counter[0] += 1

    error = trace.get("error")
    if error and depth > 0:
        value_int = hex_to_int(trace.get("value", "0x0"))
        value_eth = value_int / 1e18 if value_int else 0.0

        input_data = trace.get("input", "0x")
        selector = input_data[:10] if input_data and len(input_data) >= 10 else None

        doc = base_doc(tx_hash, block_number, block_datetime,
                       investigation_id, "failed_internals",
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
            "success": False,
            "has_error": True,
            "revert_reason": str(error),
        })
        results.append(doc)

    for sub in trace.get("calls", []):
        results.extend(_find_failed_internals(
            sub, tx_hash, block_number, block_datetime,
            investigation_id, depth + 1, counter
        ))

    return results


async def derive(raw_data: dict, investigation_id: str, config: dict) -> list[dict]:
    """Derive failed_internals records from call traces.

    Only produces records when the top-level transaction succeeded
    but internal calls reverted. If the tx itself failed, use
    failed_transactions instead.

    raw_data keys:
      trace (dict) — the raw call trace
      normalized_tx (dict) — to check top-level success status
      tx_hash (str), block_number (int), block_datetime (str)
    """
    trace = raw_data.get("trace")
    if not trace:
        return []

    # Only look for failed internals in successful transactions
    normalized_tx = raw_data.get("normalized_tx")
    if normalized_tx and not normalized_tx.get("success", True):
        return []

    return _find_failed_internals(
        trace,
        raw_data.get("tx_hash", ""),
        raw_data.get("block_number", 0),
        raw_data.get("block_datetime", ""),
        investigation_id,
    )
