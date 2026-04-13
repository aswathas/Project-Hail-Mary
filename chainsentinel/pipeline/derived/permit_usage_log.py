"""Permit Usage Log — detects EIP-2612 permit() calls from trace data."""
from pipeline.derived._base import base_doc, hex_to_int

# permit() function selector: keccak256("permit(address,address,uint256,uint256,uint8,bytes32,bytes32)")[:4]
PERMIT_SELECTOR = "0xd505accf"


def _walk_trace_for_permit(trace: dict, tx_hash: str, block_number: int,
                            block_datetime: str, investigation_id: str,
                            results: list, idx: list) -> None:
    """Recursively scan trace calls for permit() invocations."""
    input_data = trace.get("input", "0x") or "0x"
    call_type = trace.get("type", "")

    if input_data.lower().startswith(PERMIT_SELECTOR) and call_type in ("CALL", "STATICCALL", ""):
        to_addr = str(trace.get("to", "")).lower()
        from_addr = str(trace.get("from", "")).lower()

        # Decode permit args from calldata (best-effort: fixed ABI layout)
        # permit(owner, spender, value, deadline, v, r, s)
        # Each param is 32 bytes; skip 4-byte selector
        calldata = input_data[10:]  # strip selector
        permit_owner = ""
        permit_spender = ""
        amount_decimal = 0.0
        deadline = 0

        try:
            params = [calldata[i:i+64] for i in range(0, len(calldata), 64)]
            if len(params) >= 4:
                permit_owner = "0x" + params[0][-40:]
                permit_spender = "0x" + params[1][-40:]
                amount_decimal = int(params[2], 16) / 1e18
                deadline = int(params[3], 16)
        except Exception:
            pass

        doc = base_doc(tx_hash, block_number, block_datetime,
                       investigation_id, "permit_usage_log", idx[0],
                       source_layer="trace")
        doc.update({
            "token_address": to_addr,
            "permit_owner": permit_owner.lower() if permit_owner else from_addr,
            "permit_spender": permit_spender.lower(),
            "amount_decimal": amount_decimal,
            "deadline": deadline,
        })
        results.append(doc)
        idx[0] += 1

    for sub in trace.get("calls", []):
        _walk_trace_for_permit(sub, tx_hash, block_number, block_datetime,
                               investigation_id, results, idx)


async def derive(raw_data: dict, investigation_id: str, config: dict) -> list[dict]:
    """Derive permit_usage_log records from permit() calls in trace data.

    raw_data keys: normalized_tx, trace
    Falls back to checking the top-level tx input if no trace is available.
    """
    results = []
    normalized_tx = raw_data.get("normalized_tx")
    if not normalized_tx:
        return results

    tx_hash = normalized_tx.get("tx_hash", "")
    block_number = normalized_tx.get("block_number", 0)
    block_datetime = normalized_tx.get("block_datetime", "")

    idx = [0]
    trace = raw_data.get("trace") or {}

    if trace:
        _walk_trace_for_permit(trace, tx_hash, block_number, block_datetime,
                               investigation_id, results, idx)
    else:
        # Fallback: check top-level tx input
        input_data = normalized_tx.get("input", "0x") or "0x"
        if input_data.lower().startswith(PERMIT_SELECTOR):
            to_addr = normalized_tx.get("to_address", "")
            from_addr = normalized_tx.get("from_address", "")
            calldata = input_data[10:]
            permit_owner = ""
            permit_spender = ""
            amount_decimal = 0.0
            deadline = 0
            try:
                params = [calldata[i:i+64] for i in range(0, len(calldata), 64)]
                if len(params) >= 4:
                    permit_owner = "0x" + params[0][-40:]
                    permit_spender = "0x" + params[1][-40:]
                    amount_decimal = int(params[2], 16) / 1e18
                    deadline = int(params[3], 16)
            except Exception:
                pass

            doc = base_doc(tx_hash, block_number, block_datetime,
                           investigation_id, "permit_usage_log", 0,
                           source_layer="raw")
            doc.update({
                "token_address": to_addr or "",
                "permit_owner": permit_owner.lower() if permit_owner else from_addr,
                "permit_spender": permit_spender.lower(),
                "amount_decimal": amount_decimal,
                "deadline": deadline,
            })
            results.append(doc)

    return results
