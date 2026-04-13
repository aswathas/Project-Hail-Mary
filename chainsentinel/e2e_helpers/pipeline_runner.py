"""Execute ChainSentinel pipeline (collector → normalizer → decoder → derived → ingest)
for each simulation scenario's block range.
"""
import asyncio
import json
import logging
from pathlib import Path

from elasticsearch import AsyncElasticsearch
from web3 import AsyncWeb3
from web3.providers import AsyncHTTPProvider

from pipeline.runner import run_range_analysis
from pipeline.ingest import index_raw, index_derived
from es.setup import setup_elasticsearch

logger = logging.getLogger("chainsentinel.e2e.pipeline_runner")

ES_URL = "http://localhost:9200"
RPC_URL = "http://127.0.0.1:8545"
CHAIN_ID = 31337


def _make_investigation_id(scenario_name: str, block_from: int) -> str:
    """Return deterministic investigation ID matching validator expectations.

    Format: INV-{NAME[:4].upper()}-{block_from:04d}
    Examples: INV-REEN-0001, INV-FLAS-0101, INV-ADMI-0151, INV-MEVS-0201
    """
    prefix = scenario_name[:4].upper()
    return f"INV-{prefix}-{block_from:04d}"


async def run_pipeline_for_scenario(
    scenario_name: str,
    block_from: int,
    block_to: int,
    rpc_url: str = RPC_URL,
    es_url: str = ES_URL,
) -> dict:
    """Run the full pipeline for a single scenario's block range.

    Steps:
      1. Ensure ES indices exist (idempotent via setup_elasticsearch).
      2. Run run_range_analysis generator, drain all SSE events.
      3. Collect raw_docs, decoded_docs, derived_docs from the 'complete' event.
      4. Ingest raw docs into forensics-raw via index_raw.
      5. Ingest decoded + derived docs into forensics via index_derived.

    Returns:
        {
            "scenario": str,
            "investigation_id": str,
            "blocks": "N-M",
            "stats": {
                "raw_docs": int,       # count of raw collector docs
                "decoded_docs": int,   # count of decoded log docs
                "derived_docs": int,   # count of derived security event docs
                "raw_indexed": int,    # ES-confirmed indexed count for forensics-raw
                "raw_errors": int,
                "forensics_indexed": int,  # ES-confirmed indexed for forensics
                "forensics_errors": int,
                "runner_txs": int,
                "runner_blocks": int,
            }
        }
    """
    print(f"[Pipeline] Starting {scenario_name} (blocks {block_from}-{block_to})")
    investigation_id = _make_investigation_id(scenario_name, block_from)

    es_client = AsyncElasticsearch(hosts=[es_url])
    try:
        # 1. Ensure indices exist (idempotent)
        await setup_elasticsearch(es_client)

        # 2. Build Web3 provider
        w3 = AsyncWeb3(AsyncHTTPProvider(rpc_url))
        config = {
            "rpc_url": rpc_url,
            "chain_id": CHAIN_ID,
            "max_trace_hops": 5,
        }

        # 3. Drain the runner — documents arrive in the 'complete' event
        raw_docs: list[dict] = []
        decoded_docs: list[dict] = []
        derived_docs: list[dict] = []
        runner_stats: dict = {}

        async for event in run_range_analysis(
            w3, block_from, block_to, config, investigation_id
        ):
            phase = event.get("phase")
            if phase == "complete":
                raw_docs = event.get("raw_docs", [])
                decoded_docs = event.get("decoded_docs", [])
                derived_docs = event.get("derived_docs", [])
                runner_stats = event.get("stats", {})
                logger.info(
                    "[%s] Runner complete — raw=%d decoded=%d derived=%d",
                    scenario_name, len(raw_docs), len(decoded_docs), len(derived_docs),
                )
            else:
                logger.info(
                    "[%s] phase=%-12s  %s",
                    scenario_name, phase, event.get("msg", ""),
                )

        # 4. Ingest normalized documents into forensics-raw
        # Note: We use normalized_docs (from normalizer phase) not raw_docs (from collector)
        # because forensics-raw index mapping expects normalized field names
        # (from_address not from, to_address not to, block_timestamp_raw not block_timestamp)
        normalized_raw_docs = event.get("normalized_docs", [])
        raw_result: dict = {"indexed": 0, "errors": 0}
        if normalized_raw_docs:
            raw_result = await index_raw(es_client, normalized_raw_docs, investigation_id)
            logger.info("[%s] forensics-raw ingest: indexed=%d, errors=%d",
                       scenario_name, raw_result.get("indexed", 0), raw_result.get("errors", 0))
            if raw_result.get("error_details"):
                logger.warning("[%s] forensics-raw errors: %s",
                             scenario_name, raw_result.get("error_details", [])[:3])

        # 5. Ingest decoded + derived documents into forensics
        all_forensics_docs = decoded_docs + derived_docs
        forensics_result: dict = {"indexed": 0, "errors": 0}
        if all_forensics_docs:
            forensics_result = await index_derived(es_client, all_forensics_docs)
            logger.info("[%s] forensics ingest: indexed=%d, errors=%d",
                       scenario_name, forensics_result.get("indexed", 0), forensics_result.get("errors", 0))
            if forensics_result.get("error_details"):
                logger.warning("[%s] forensics errors: %s",
                             scenario_name, forensics_result.get("error_details", [])[:3])

        stats = {
            "raw_docs": len(raw_docs),
            "decoded_docs": len(decoded_docs),
            "derived_docs": len(derived_docs),
            "raw_indexed": raw_result.get("indexed", 0),
            "raw_errors": raw_result.get("errors", 0),
            "forensics_indexed": forensics_result.get("indexed", 0),
            "forensics_errors": forensics_result.get("errors", 0),
            "runner_txs": runner_stats.get("txs", 0),
            "runner_blocks": runner_stats.get("blocks", 0),
        }

        print(
            f"[Pipeline] {scenario_name} done | "
            f"raw={stats['raw_docs']}  decoded={stats['decoded_docs']}  "
            f"derived={stats['derived_docs']}  "
            f"es_raw={stats['raw_indexed']}  es_forensics={stats['forensics_indexed']}"
        )

        return {
            "scenario": scenario_name,
            "investigation_id": investigation_id,
            "blocks": f"{block_from}-{block_to}",
            "stats": stats,
        }

    finally:
        await es_client.close()


async def run_all_pipelines(
    simulator_results: dict,
    rpc_url: str = RPC_URL,
    es_url: str = ES_URL,
) -> dict:
    """Execute pipeline for all scenarios sequentially.

    Args:
        simulator_results: {scenario_name: {"block_from": int, "block_to": int, ...}}
        rpc_url: Anvil / testnet / mainnet RPC endpoint.
        es_url: Elasticsearch base URL.

    Returns:
        {scenario_name: {investigation_id, blocks, stats}}
    """
    pipeline_results = {}
    for scenario_name, sim_data in simulator_results.items():
        result = await run_pipeline_for_scenario(
            scenario_name=scenario_name,
            block_from=sim_data["block_from"],
            block_to=sim_data["block_to"],
            rpc_url=rpc_url,
            es_url=es_url,
        )
        pipeline_results[scenario_name] = result
    return pipeline_results


if __name__ == "__main__":
    sim_results = {
        "reentrancy-drain":  {"block_from": 1,   "block_to": 100},
        "flash-loan-oracle": {"block_from": 101,  "block_to": 150},
        "admin-key-abuse":   {"block_from": 151,  "block_to": 200},
        "mev-sandwich":      {"block_from": 201,  "block_to": 250},
    }
    results = asyncio.run(run_all_pipelines(sim_results))
    print(json.dumps(results, indent=2, default=str))
