"""Value Flow Graph — directed ETH flow edges from external tx and internal trace calls."""
from pipeline.derived._base import base_doc, hex_to_int


def _walk_trace(trace: dict, tx_hash: str, block_number: int, block_datetime: str,
                investigation_id: str, results: list, idx: list) -> None:
    """Recursively extract internal ETH value transfers from a call trace."""
    value_int = hex_to_int(trace.get("value", "0x0"))
    if value_int > 0:
        value_eth = value_int / 1e18
        from_addr = str(trace.get("from", "")).lower()
        to_addr = str(trace.get("to", "")).lower()
        if from_addr and to_addr:
            doc = base_doc(tx_hash, block_number, block_datetime,
                           investigation_id, "value_flow_graph", idx[0],
                           source_layer="trace")
            doc.update({
                "from_address": from_addr,
                "to_address": to_addr,
                "value_eth": value_eth,
                "edge_type": "internal",
            })
            results.append(doc)
            idx[0] += 1

    for sub in trace.get("calls", []):
        _walk_trace(sub, tx_hash, block_number, block_datetime, investigation_id, results, idx)


async def derive(raw_data: dict, investigation_id: str, config: dict) -> list[dict]:
    """Derive value_flow_graph edges from a transaction and its trace.

    raw_data keys: normalized_tx, trace
    """
    results = []
    normalized_tx = raw_data.get("normalized_tx")
    if not normalized_tx:
        return results

    tx_hash = normalized_tx.get("tx_hash", "")
    block_number = normalized_tx.get("block_number", 0)
    block_datetime = normalized_tx.get("block_datetime", "")
    value_eth = normalized_tx.get("value_eth", 0)
    from_address = normalized_tx.get("from_address", "")
    to_address = normalized_tx.get("to_address", "")

    idx = [0]

    # External (top-level) ETH transfer
    if value_eth > 0 and from_address and to_address:
        doc = base_doc(tx_hash, block_number, block_datetime,
                       investigation_id, "value_flow_graph", idx[0],
                       source_layer="raw")
        doc.update({
            "from_address": from_address,
            "to_address": to_address,
            "value_eth": value_eth,
            "edge_type": "external",
        })
        results.append(doc)
        idx[0] += 1

    # Internal calls from trace
    trace = raw_data.get("trace") or {}
    if trace:
        for sub in trace.get("calls", []):
            _walk_trace(sub, tx_hash, block_number, block_datetime, investigation_id, results, idx)

    return results
