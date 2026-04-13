"""
Fund Tracing — BFS fund tracing with haircut taint scoring.

Starting from a seed wallet, traces funds forward (where did they go)
or backward (where did they come from) up to max_hops (default 5).

Taint scoring: funds passing through a mixer receive taint * 0.7,
through a bridge * 0.8. Taint never reaches zero (min 0.01).

Output: fund_flow_edge documents (layer: derived, derived_type: fund_flow_edge)
and a fund_trail summary document (layer: attacker, attacker_type: fund_trail).
"""
from collections import deque
from datetime import datetime, timezone
from typing import Optional

from correlation.mixer_detect import classify_address, compute_taint_haircut


def _query_transfers(
    es_client,
    address: str,
    investigation_id: str,
    direction: str,
) -> list[dict]:
    """
    Query ES for transfers to/from an address.
    direction='forward': address is the sender (from_address)
    direction='backward': address is the receiver (to_address)
    """
    if direction == "forward":
        address_field = "from_address"
    else:
        address_field = "to_address"

    query = {
        "bool": {
            "must": [
                {"term": {"investigation_id": investigation_id}},
                {"term": {address_field: address.lower()}},
                {"term": {"layer": "derived"}},
                {"terms": {"derived_type": ["native_transfer", "asset_transfer"]}},
            ]
        }
    }

    response = es_client.search(
        index="forensics",
        query=query,
        size=500,
        sort=[{"block_number": "asc"}],
    )

    transfers = []
    for hit in response.get("hits", {}).get("hits", []):
        transfers.append(hit["_source"])

    return transfers


def trace_funds(
    es_client,
    seed_address: str,
    investigation_id: str,
    direction: str = "forward",
    max_hops: int = 5,
    chain_id: int = 31337,
) -> list[dict]:
    """
    BFS fund tracing from seed address.

    Args:
        es_client: Elasticsearch client
        seed_address: Starting wallet address
        investigation_id: Current investigation ID
        direction: 'forward' (where funds went) or 'backward' (where funds came from)
        max_hops: Maximum trace depth (default 5)
        chain_id: Chain ID from config

    Returns:
        List of fund_flow_edge documents
    """
    now = datetime.now(timezone.utc).isoformat()
    trail = []
    visited = set()
    visited.add(seed_address.lower())

    # BFS queue: (address, hop_number, current_taint)
    queue = deque([(seed_address.lower(), 0, 1.0)])

    while queue:
        current_address, current_hop, current_taint = queue.popleft()

        if current_hop >= max_hops:
            continue

        transfers = _query_transfers(
            es_client, current_address, investigation_id, direction
        )

        for transfer in transfers:
            if direction == "forward":
                next_address = transfer.get("to_address", "").lower()
            else:
                next_address = transfer.get("from_address", "").lower()

            if not next_address:
                continue

            # Classify the next address for taint calculation
            classification = classify_address(next_address)
            new_taint = compute_taint_haircut(
                current_taint, classification["category"]
            )

            hop_number = current_hop + 1

            edge_doc = {
                "layer": "derived",
                "derived_type": "fund_flow_edge",
                "investigation_id": investigation_id,
                "chain_id": chain_id,
                "@timestamp": now,
                "from_address": transfer.get("from_address", ""),
                "to_address": transfer.get("to_address", ""),
                "value_eth": transfer.get("value_eth", 0.0),
                "token_address": transfer.get("token_address"),
                "tx_hash": transfer.get("tx_hash"),
                "block_number": transfer.get("block_number"),
                "hop_number": hop_number,
                "direction": direction,
                "taint_score": new_taint,
            }

            trail.append(edge_doc)

            # Only continue BFS if we haven't visited this address
            if next_address not in visited:
                visited.add(next_address)
                queue.append((next_address, hop_number, new_taint))

    return trail


def build_fund_trail_document(
    seed_address: str,
    trail: list[dict],
    investigation_id: str,
    chain_id: int,
) -> dict:
    """
    Build a summary fund_trail document from the traced edges.
    Stored as layer: attacker, attacker_type: fund_trail.
    """
    now = datetime.now(timezone.utc).isoformat()

    # Collect all unique addresses in trail
    all_addresses = set()
    exit_routes = []
    total_value = 0.0

    for edge in trail:
        all_addresses.add(edge.get("from_address", ""))
        all_addresses.add(edge.get("to_address", ""))
        total_value += edge.get("value_eth", 0.0)

        to_class = classify_address(edge.get("to_address", ""))
        if to_class["category"] in ("mixer", "bridge", "cex"):
            exit_routes.append(
                f"{to_class['category']}:{to_class['protocol']}"
            )

    max_hop = max((e.get("hop_number", 0) for e in trail), default=0)
    min_block = min((e.get("block_number", 0) for e in trail if e.get("block_number")), default=0)
    max_block = max((e.get("block_number", 0) for e in trail if e.get("block_number")), default=0)

    return {
        "layer": "attacker",
        "attacker_type": "fund_trail",
        "investigation_id": investigation_id,
        "chain_id": chain_id,
        "@timestamp": now,
        "from_address": seed_address.lower(),
        "fund_trail_hops": max_hop,
        "total_stolen_eth": total_value,
        "exit_routes": list(set(exit_routes)),
        "cluster_wallets": list(all_addresses),
        "cluster_size": len(all_addresses),
        "attack_block_range_from": min_block,
        "attack_block_range_to": max_block,
    }
