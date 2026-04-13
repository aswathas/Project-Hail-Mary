"""Reentrancy Patterns — pre-computed from execution_structure.

Detects same address appearing at multiple call depths within a single tx,
which is the hallmark of reentrancy. Produces one record per target address
that exhibits depth spread >= 1 (called at depth N and depth N+k in same tx).

Derives from: execution_structure (derived-from-derived)
"""
from collections import defaultdict

from pipeline.derived._base import base_doc, hex_to_int


def _extract_calls_from_trace(trace, depth=0):
    """Flatten a call trace into (address, depth, call_type) tuples."""
    calls = []
    callee = str(trace.get("to", "")).lower()
    if callee:
        calls.append((callee, depth, trace.get("type", "CALL")))

    for sub in trace.get("calls", []):
        calls.extend(_extract_calls_from_trace(sub, depth + 1))

    return calls


async def derive(raw_data: dict, investigation_id: str, config: dict) -> list[dict]:
    """Derive reentrancy_patterns from call trace data.

    Looks for any address that appears at 2+ different call depths within
    the same transaction. This is the structural fingerprint of reentrancy.

    raw_data keys:
      trace (dict) — the raw call trace
      tx_hash (str), block_number (int), block_datetime (str)
    """
    trace = raw_data.get("trace")
    if not trace:
        return []

    tx_hash = raw_data.get("tx_hash", "")
    block_number = raw_data.get("block_number", 0)
    block_datetime = raw_data.get("block_datetime", "")

    # Flatten trace into per-address depth sets
    calls = _extract_calls_from_trace(trace)
    addr_depths = defaultdict(list)
    for addr, depth, call_type in calls:
        addr_depths[addr].append(depth)

    results = []
    for addr, depths in addr_depths.items():
        unique_depths = sorted(set(depths))
        if len(unique_depths) < 2:
            continue

        depth_spread = unique_depths[-1] - unique_depths[0]
        if depth_spread < 1:
            continue

        doc = base_doc(tx_hash, block_number, block_datetime,
                       investigation_id, "reentrancy_patterns",
                       source_layer="trace")
        doc.update({
            "contract_address": addr,
            "call_count": len(depths),
            "call_depth": unique_depths[0],  # min depth
            "depth_spread": depth_spread,
            "metadata": {
                "depths": unique_depths,
                "min_depth": unique_depths[0],
                "max_depth": unique_depths[-1],
            },
        })
        results.append(doc)

    return results
