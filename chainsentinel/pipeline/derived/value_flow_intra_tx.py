"""Value Flow Intra-Tx — CRITICAL derived log.

Computes ETH flow per address within a single transaction by walking
the call trace. Produces net in/out and drain_ratio per contract.

Derives from: call_traces_raw, balance_diffs
"""
from collections import defaultdict

from pipeline.derived._base import base_doc, hex_to_int


def _walk_trace_values(trace, flows):
    """Walk trace tree accumulating ETH sent/received per address."""
    caller = str(trace.get("from", "")).lower()
    callee = str(trace.get("to", "")).lower()

    value_int = hex_to_int(trace.get("value", "0x0"))
    value_eth = value_int / 1e18 if value_int else 0.0

    if value_eth > 0 and caller and callee:
        flows[caller]["out"] += value_eth
        flows[callee]["in"] += value_eth
        # Track max single hop
        flows[caller]["max_hop"] = max(flows[caller]["max_hop"], value_eth)
        flows[callee]["max_hop"] = max(flows[callee]["max_hop"], value_eth)

    for sub in trace.get("calls", []):
        _walk_trace_values(sub, flows)


async def derive(raw_data: dict, investigation_id: str, config: dict) -> list[dict]:
    """Derive value_flow_intra_tx records from call traces.

    Produces one record per address involved in ETH transfers within
    the transaction. Includes net flow and drain_ratio.

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

    # Accumulate flows
    flows = defaultdict(lambda: {"in": 0.0, "out": 0.0, "max_hop": 0.0})
    _walk_trace_values(trace, flows)

    results = []
    for addr, f in flows.items():
        total_in = f["in"]
        total_out = f["out"]
        net = total_in - total_out

        # drain_ratio: how much of inflow was drained (outflow / inflow)
        drain_ratio = total_out / total_in if total_in > 0 else 0.0

        doc = base_doc(tx_hash, block_number, block_datetime,
                       investigation_id, "value_flow_intra_tx",
                       source_layer="trace")
        doc.update({
            "contract_address": addr,
            "from_address": addr,
            "total_in_eth": round(total_in, 18),
            "total_out_eth": round(total_out, 18),
            "net_eth": round(net, 18),
            "drain_ratio": round(drain_ratio, 6),
            "max_single_hop_eth": round(f["max_hop"], 18),
        })
        results.append(doc)

    return results
