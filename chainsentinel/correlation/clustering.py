"""
Wallet Clustering — groups related wallets by shared patterns.

Clustering methods:
1. Same funding source — wallets funded by the same address
2. Timing correlation — wallets active in the same block window relative to exploit
3. Shared contract interaction — wallets interacting with the same unusual contracts
4. Common trace address — wallets appearing in each other's call traces

Output: cluster documents (layer: attacker, attacker_type: cluster)
and attacker profile documents (layer: attacker, attacker_type: profile).
"""
import hashlib
from datetime import datetime, timezone
from typing import Optional


def cluster_by_funding_source(
    es_client,
    investigation_id: str,
) -> list[dict]:
    """
    Find wallets that share a common funding source.
    Uses ES aggregation on from_address -> to_address pairs.
    """
    query = {
        "bool": {
            "must": [
                {"term": {"investigation_id": investigation_id}},
                {"term": {"layer": "derived"}},
                {"terms": {"derived_type": ["native_transfer", "asset_transfer"]}},
            ]
        }
    }

    aggs = {
        "funding_sources": {
            "terms": {"field": "from_address", "size": 100},
            "aggs": {
                "funded_wallets": {
                    "terms": {"field": "to_address", "size": 100}
                }
            },
        }
    }

    response = es_client.search(
        index="forensics",
        query=query,
        aggs=aggs,
        size=0,
    )

    clusters = []
    buckets = response.get("aggregations", {}).get("funding_sources", {}).get("buckets", [])

    for bucket in buckets:
        funder = bucket["key"]
        funded = bucket.get("funded_wallets", {}).get("buckets", [])

        if len(funded) >= 2:
            wallets = [w["key"] for w in funded]
            clusters.append({
                "wallets": set(wallets),
                "funded_via": funder,
                "method": "funding_source",
            })

    return clusters


def cluster_by_timing(
    es_client,
    investigation_id: str,
    window_blocks: int = 5,
) -> list[dict]:
    """
    Find wallets active in the same narrow block window.
    Uses histogram aggregation on block_number.
    """
    query = {
        "bool": {
            "must": [
                {"term": {"investigation_id": investigation_id}},
                {"term": {"layer": "derived"}},
            ]
        }
    }

    aggs = {
        "block_windows": {
            "histogram": {"field": "block_number", "interval": window_blocks},
            "aggs": {
                "active_wallets": {
                    "terms": {"field": "from_address", "size": 50}
                }
            },
        }
    }

    response = es_client.search(
        index="forensics",
        query=query,
        aggs=aggs,
        size=0,
    )

    clusters = []
    buckets = response.get("aggregations", {}).get("block_windows", {}).get("buckets", [])

    for bucket in buckets:
        wallets_in_window = bucket.get("active_wallets", {}).get("buckets", [])
        if len(wallets_in_window) >= 2:
            wallet_set = set(w["key"] for w in wallets_in_window)
            clusters.append({
                "wallets": wallet_set,
                "method": "timing",
                "block_window": bucket["key"],
            })

    return clusters


def merge_clusters(clusters: list[dict]) -> list[dict]:
    """
    Merge overlapping clusters using union-find.
    Two clusters merge if they share at least one wallet.
    """
    if not clusters:
        return []

    # Union-Find
    parent = {}

    def find(x):
        if x not in parent:
            parent[x] = x
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb

    # Build union-find from cluster wallet sets
    for cluster in clusters:
        wallets = list(cluster["wallets"])
        for i in range(1, len(wallets)):
            union(wallets[0], wallets[i])

    # Group wallets by their root
    groups = {}
    all_wallets = set()
    for cluster in clusters:
        all_wallets.update(cluster["wallets"])

    for wallet in all_wallets:
        root = find(wallet)
        if root not in groups:
            groups[root] = set()
        groups[root].add(wallet)

    # Collect methods used per group
    methods_per_group = {root: set() for root in groups}
    for cluster in clusters:
        wallets = list(cluster["wallets"])
        if wallets:
            root = find(wallets[0])
            methods_per_group[root].add(cluster.get("method", "unknown"))

    merged = []
    for root, wallet_set in groups.items():
        merged.append({
            "wallets": wallet_set,
            "methods": list(methods_per_group.get(root, set())),
        })

    return merged


def _generate_cluster_id(wallets: set[str]) -> str:
    """Generate a deterministic cluster ID from sorted wallet addresses."""
    sorted_wallets = sorted(wallets)
    hash_input = ",".join(sorted_wallets).encode()
    return "CLUSTER-" + hashlib.sha256(hash_input).hexdigest()[:12].upper()


def build_cluster_document(
    cluster_id: str,
    wallets: list[str],
    funded_via: str,
    investigation_id: str,
    chain_id: int,
    method: str = "unknown",
) -> dict:
    """Build an attacker cluster document for ES."""
    now = datetime.now(timezone.utc).isoformat()

    return {
        "layer": "attacker",
        "attacker_type": "cluster",
        "investigation_id": investigation_id,
        "chain_id": chain_id,
        "@timestamp": now,
        "cluster_id": cluster_id,
        "cluster_wallets": wallets,
        "cluster_size": len(wallets),
        "funded_via": funded_via,
        "labels": [method],
    }


def build_attacker_profile(
    cluster_id: str,
    wallets: list[str],
    fund_trail_hops: int,
    exit_routes: list[str],
    total_stolen_eth: float,
    investigation_id: str,
    chain_id: int,
    first_seen_block: Optional[int] = None,
    exploit_block: Optional[int] = None,
) -> dict:
    """Build an attacker profile document summarizing attribution data."""
    now = datetime.now(timezone.utc).isoformat()

    return {
        "layer": "attacker",
        "attacker_type": "profile",
        "investigation_id": investigation_id,
        "chain_id": chain_id,
        "@timestamp": now,
        "cluster_id": cluster_id,
        "cluster_wallets": wallets,
        "cluster_size": len(wallets),
        "fund_trail_hops": fund_trail_hops,
        "exit_routes": exit_routes,
        "total_stolen_eth": total_stolen_eth,
        "first_seen_block": first_seen_block,
        "exploit_block": exploit_block,
    }


def run_clustering(
    es_client,
    ingest_fn,
    investigation_id: str,
    chain_id: int,
) -> list[dict]:
    """
    Run all clustering methods, merge results, build cluster documents.
    """
    # Gather clusters from different methods
    funding_clusters = cluster_by_funding_source(es_client, investigation_id)
    timing_clusters = cluster_by_timing(es_client, investigation_id)

    all_clusters = funding_clusters + timing_clusters

    if not all_clusters:
        return []

    merged = merge_clusters(all_clusters)

    documents = []
    for cluster in merged:
        wallets = list(cluster["wallets"])
        cluster_id = _generate_cluster_id(cluster["wallets"])

        # Find funding source if available
        funded_via = ""
        for fc in funding_clusters:
            if fc["wallets"] & cluster["wallets"]:
                funded_via = fc.get("funded_via", "")
                break

        doc = build_cluster_document(
            cluster_id=cluster_id,
            wallets=wallets,
            funded_via=funded_via,
            investigation_id=investigation_id,
            chain_id=chain_id,
            method=", ".join(cluster.get("methods", ["unknown"])),
        )
        documents.append(doc)

    if documents:
        ingest_fn(es_client, documents, "forensics")

    return documents
