import pytest
from unittest.mock import MagicMock


def test_cluster_by_funding_source():
    from correlation.clustering import cluster_by_funding_source

    mock_client = MagicMock()
    # Two wallets funded by the same source
    mock_client.search.return_value = {
        "aggregations": {
            "funding_sources": {
                "buckets": [
                    {
                        "key": "0xfunder",
                        "doc_count": 2,
                        "funded_wallets": {
                            "buckets": [
                                {"key": "0xwallet_a", "doc_count": 1},
                                {"key": "0xwallet_b", "doc_count": 1},
                            ]
                        },
                    }
                ]
            }
        }
    }

    clusters = cluster_by_funding_source(mock_client, "INV-001")

    assert len(clusters) == 1
    assert "0xwallet_a" in clusters[0]["wallets"]
    assert "0xwallet_b" in clusters[0]["wallets"]
    assert clusters[0]["funded_via"] == "0xfunder"


def test_cluster_by_timing():
    from correlation.clustering import cluster_by_timing

    mock_client = MagicMock()
    mock_client.search.return_value = {
        "aggregations": {
            "block_windows": {
                "buckets": [
                    {
                        "key": 100,
                        "doc_count": 3,
                        "active_wallets": {
                            "buckets": [
                                {"key": "0xwallet_a", "doc_count": 2},
                                {"key": "0xwallet_b", "doc_count": 1},
                                {"key": "0xwallet_c", "doc_count": 1},
                            ]
                        },
                    }
                ]
            }
        }
    }

    clusters = cluster_by_timing(mock_client, "INV-001", window_blocks=5)

    assert len(clusters) >= 1
    cluster_wallets = clusters[0]["wallets"]
    assert len(cluster_wallets) >= 2


def test_merge_clusters_deduplicates():
    from correlation.clustering import merge_clusters

    clusters = [
        {"wallets": {"0xa", "0xb"}, "method": "funding"},
        {"wallets": {"0xb", "0xc"}, "method": "timing"},
        {"wallets": {"0xd"}, "method": "funding"},
    ]

    merged = merge_clusters(clusters)

    # 0xa, 0xb, 0xc should be in same cluster (connected via 0xb)
    found = False
    for cluster in merged:
        if "0xa" in cluster["wallets"] and "0xc" in cluster["wallets"]:
            found = True
            assert "0xb" in cluster["wallets"]
    assert found


def test_merge_clusters_preserves_isolated():
    from correlation.clustering import merge_clusters

    clusters = [
        {"wallets": {"0xa", "0xb"}, "method": "funding"},
        {"wallets": {"0xd", "0xe"}, "method": "timing"},
    ]

    merged = merge_clusters(clusters)
    assert len(merged) == 2


def test_build_cluster_document():
    from correlation.clustering import build_cluster_document

    doc = build_cluster_document(
        cluster_id="CLUSTER-001",
        wallets=["0xa", "0xb", "0xc"],
        funded_via="0xfunder",
        investigation_id="INV-001",
        chain_id=31337,
        method="funding_source",
    )

    assert doc["layer"] == "attacker"
    assert doc["attacker_type"] == "cluster"
    assert doc["cluster_id"] == "CLUSTER-001"
    assert doc["cluster_size"] == 3
    assert "0xa" in doc["cluster_wallets"]
    assert doc["investigation_id"] == "INV-001"


def test_build_attacker_profile():
    from correlation.clustering import build_attacker_profile

    profile = build_attacker_profile(
        cluster_id="CLUSTER-001",
        wallets=["0xa", "0xb"],
        fund_trail_hops=3,
        exit_routes=["mixer:Tornado Cash", "cex:Binance"],
        total_stolen_eth=150.0,
        investigation_id="INV-001",
        chain_id=31337,
        first_seen_block=95,
        exploit_block=100,
    )

    assert profile["layer"] == "attacker"
    assert profile["attacker_type"] == "profile"
    assert profile["total_stolen_eth"] == 150.0
    assert profile["fund_trail_hops"] == 3
    assert "mixer:Tornado Cash" in profile["exit_routes"]
    assert profile["first_seen_block"] == 95
    assert profile["exploit_block"] == 100


def test_run_clustering_full_pipeline():
    from correlation.clustering import run_clustering

    mock_client = MagicMock()
    # Funding source query
    mock_client.search.side_effect = [
        {
            "aggregations": {
                "funding_sources": {
                    "buckets": [
                        {
                            "key": "0xfunder",
                            "doc_count": 2,
                            "funded_wallets": {
                                "buckets": [
                                    {"key": "0xwallet_a", "doc_count": 1},
                                    {"key": "0xwallet_b", "doc_count": 1},
                                ]
                            },
                        }
                    ]
                }
            }
        },
        # Timing query
        {
            "aggregations": {
                "block_windows": {
                    "buckets": []
                }
            }
        },
    ]

    mock_ingest = MagicMock()

    docs = run_clustering(mock_client, mock_ingest, "INV-001", 31337)

    assert len(docs) >= 1
    assert docs[0]["attacker_type"] == "cluster"
    mock_ingest.assert_called_once()
