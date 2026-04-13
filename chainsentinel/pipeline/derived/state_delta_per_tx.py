"""State Delta Per Tx — CRITICAL derived log.

Before/after snapshot of storage slots per transaction. On Anvil, uses
debug_traceTransaction with prestateTracer to get state diffs. On nodes
without trace support, this builder produces no output (graceful degradation).

Derives from: storage_diffs, state_diffs
"""
from pipeline.derived._base import base_doc, hex_to_int


async def derive(raw_data: dict, investigation_id: str, config: dict) -> list[dict]:
    """Derive state_delta_per_tx records from trace state diffs.

    The collector may provide state_diffs from debug_traceTransaction
    with prestateTracer or defaultTracer. This builder processes them
    into per-slot before/after records.

    raw_data keys:
      trace (dict) — the raw call trace (may contain structLogs or state diffs)
      state_diffs (dict) — optional, pre-extracted state diffs from collector
      tx_hash (str), block_number (int), block_datetime (str)
    """
    tx_hash = raw_data.get("tx_hash", "")
    block_number = raw_data.get("block_number", 0)
    block_datetime = raw_data.get("block_datetime", "")

    # Try explicit state_diffs first (from enhanced collector)
    state_diffs = raw_data.get("state_diffs")
    if not state_diffs:
        # Try extracting from trace structLogs (Anvil debug_traceTransaction)
        trace = raw_data.get("trace")
        if not trace:
            return []
        state_diffs = _extract_state_diffs_from_trace(trace)

    if not state_diffs:
        return []

    results = []
    for contract_addr, slots in state_diffs.items():
        contract_addr = str(contract_addr).lower()
        if not isinstance(slots, dict):
            continue

        storage = slots.get("storage", slots.get("stateDiff", {}))
        if not isinstance(storage, dict):
            continue

        for slot_hex, values in storage.items():
            if isinstance(values, dict):
                value_before = values.get("from", values.get("*", {}).get("from", "0x0"))
                value_after = values.get("to", values.get("*", {}).get("to", "0x0"))
            else:
                value_before = "0x0"
                value_after = str(values)

            is_new = value_before in ("0x0", "0x" + "0" * 64, None)

            doc = base_doc(tx_hash, block_number, block_datetime,
                           investigation_id, "state_delta_per_tx",
                           source_layer="trace")
            doc.update({
                "contract_address": contract_addr,
                "slot_hex": str(slot_hex),
                "value_before": str(value_before) if value_before else "0x0",
                "value_after": str(value_after) if value_after else "0x0",
                "is_new_slot": is_new,
                "slot_type": _infer_slot_type(slot_hex),
                "updated_before_call": False,
                "updated_after_call": False,
                "updated_between_calls": False,
            })
            results.append(doc)

    return results


def _extract_state_diffs_from_trace(trace):
    """Try to extract state diff info from trace structure.

    Anvil debug_traceTransaction with prestateTracer returns account state.
    This handles the common formats.
    """
    # prestateTracer format: {address: {balance, nonce, storage: {slot: value}}}
    if isinstance(trace, dict) and not trace.get("type"):
        # Looks like a prestateTracer result (no "type" field like CALL)
        result = {}
        for addr, state in trace.items():
            if isinstance(state, dict) and "storage" in state:
                result[addr] = state
        if result:
            return result

    return None


def _infer_slot_type(slot_hex):
    """Heuristic slot type classification."""
    slot_hex = str(slot_hex)

    # EIP-1967 implementation slot
    if slot_hex == "0x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc":
        return "eip1967_implementation"
    # EIP-1967 admin slot
    if slot_hex == "0xb53127684a568b3173ae13b9f8a6016e243e63b6e8ee1178d6a717850b5d6103":
        return "eip1967_admin"
    # Low slots (0-10) are often simple state vars
    try:
        slot_int = int(slot_hex, 16)
        if slot_int < 20:
            return "state_variable"
    except (ValueError, TypeError):
        pass

    return "unknown"
