"""
docker_run.py — Docker entrypoint for ChainSentinel pipeline container.

Sequence:
  1. Wait for Elasticsearch to be healthy
  2. Wait for Anvil RPC to be responsive
  3. Query Anvil for the latest block number
  4. Setup ES indices
  5. Run full range analysis (block 1 → latest)
  6. Ingest raw + decoded + derived docs
  7. Run signal engine
  8. Run pattern engine
"""
import asyncio
import json
import os
import sys
import time
import httpx
import logging
from pathlib import Path
from datetime import datetime, timezone

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s %(message)s")
logger = logging.getLogger("chainsentinel.docker_run")

HERE = Path(__file__).resolve().parent


def load_config() -> dict:
    with open(HERE / "config.json") as f:
        return json.load(f)


def _wait_http(url: str, label: str, max_wait: int = 300, interval: int = 5) -> None:
    logger.info("Waiting for %s at %s ...", label, url)
    deadline = time.time() + max_wait
    while time.time() < deadline:
        try:
            r = httpx.get(url, timeout=5)
            if r.status_code < 500:
                logger.info("  %s ready (%s)", label, r.status_code)
                return
        except Exception:
            pass
        logger.info("  %s not ready, retrying in %ds ...", label, interval)
        time.sleep(interval)
    raise TimeoutError(f"{label} at {url} did not become ready in {max_wait}s")


def wait_for_anvil(rpc_url: str) -> None:
    logger.info("Waiting for Anvil at %s ...", rpc_url)
    deadline = time.time() + 300
    while time.time() < deadline:
        try:
            r = httpx.post(rpc_url, json={
                "jsonrpc": "2.0", "method": "eth_blockNumber", "params": [], "id": 1
            }, timeout=5)
            if r.status_code == 200 and r.json().get("result"):
                logger.info("  Anvil ready (latest block: %s)", r.json()["result"])
                return
        except Exception:
            pass
        logger.info("  Anvil not ready, retrying ...")
        time.sleep(5)
    raise TimeoutError("Anvil not ready")


def get_latest_block(rpc_url: str) -> int:
    r = httpx.post(rpc_url, json={
        "jsonrpc": "2.0", "method": "eth_blockNumber", "params": [], "id": 1
    }, timeout=10)
    return int(r.json()["result"], 16)


async def main() -> None:
    config = load_config()
    es_url  = os.environ.get("ES_URL",  config.get("es_url",  "http://elasticsearch:9200"))
    rpc_url = os.environ.get("RPC_URL", config.get("rpc_url", "http://anvil:8545"))

    config["es_url"]  = es_url
    config["rpc_url"] = rpc_url

    logger.info("=== ChainSentinel Pipeline (Docker) ===")
    logger.info("ES:  %s", es_url)
    logger.info("RPC: %s", rpc_url)

    # 1. Wait for dependencies
    _wait_http(f"{es_url}/_cluster/health", "Elasticsearch")
    wait_for_anvil(rpc_url)

    from elasticsearch import AsyncElasticsearch
    from web3 import AsyncWeb3
    from web3.providers import AsyncHTTPProvider

    es = AsyncElasticsearch(es_url)

    # 2. Setup ES indices
    from es.setup import setup_elasticsearch as es_setup
    await es_setup(es)
    logger.info("[1/5] ES indices ready")

    # 3. Determine block range
    from_block = 1
    to_block   = get_latest_block(rpc_url)
    logger.info("[2/5] Block range: %d → %d (%d blocks)", from_block, to_block, to_block - from_block + 1)

    # 4. Run pipeline (range analysis)
    from pipeline.runner import run_range_analysis, generate_investigation_id
    from pipeline.ingest import index_raw, index_derived

    investigation_id = os.environ.get("INVESTIGATION_ID", generate_investigation_id())
    logger.info("      Investigation: %s", investigation_id)

    w3 = AsyncWeb3(AsyncHTTPProvider(rpc_url))

    raw_all     = []
    decoded_all = []
    derived_all = []

    async for event in run_range_analysis(w3, from_block, to_block, config, investigation_id):
        if event.get("phase") == "complete":
            raw_all     = event.get("raw_docs", [])
            decoded_all = event.get("decoded_docs", [])
            derived_all = event.get("derived_docs", [])
        else:
            logger.info("  [%s] %s", event.get("phase", "?"), event.get("msg", ""))

    # 5. Ingest to ES
    logger.info("[3/5] Ingesting: %d raw, %d decoded, %d derived",
                len(raw_all), len(decoded_all), len(derived_all))

    if raw_all:
        await index_raw(es, raw_all, investigation_id)

    all_derived = decoded_all + derived_all
    if all_derived:
        await index_derived(es, all_derived)

    await es.indices.refresh(index="forensics,forensics-raw")

    # 6. Signal engine
    logger.info("[4/5] Running signal engine ...")
    from elasticsearch import Elasticsearch
    sync_es = Elasticsearch(hosts=[es_url])

    from detection.signal_engine import run_all_signals
    chain_id = config.get("chain_id", 31337)

    def _noop_ingest(client, docs, index): pass

    sync_es.indices.refresh(index="forensics")
    sync_es.indices.refresh(index="forensics-raw")

    signal_docs = run_all_signals(sync_es, _noop_ingest,
                                  investigation_id=investigation_id,
                                  chain_id=chain_id)
    logger.info("      %d signals fired", len(signal_docs))

    if signal_docs:
        from pipeline.ingest import bulk_index
        await bulk_index(es, signal_docs, "forensics")
        await es.indices.refresh(index="forensics")

    # 7. Pattern engine
    logger.info("[5/5] Running pattern engine ...")
    sync_es.indices.refresh(index="forensics")

    from detection.pattern_engine import run_all_patterns
    pattern_docs = run_all_patterns(sync_es, _noop_ingest,
                                    investigation_id=investigation_id,
                                    chain_id=chain_id)
    logger.info("      %d alerts fired", len(pattern_docs))

    if pattern_docs:
        await bulk_index(es, pattern_docs, "forensics")
        await es.indices.refresh(index="forensics")

    await es.close()
    sync_es.close()

    logger.info("=== Pipeline complete ===")
    logger.info("  Investigation: %s", investigation_id)
    logger.info("  Blocks:   %d", to_block - from_block + 1)
    logger.info("  Raw txs:  %d", len(raw_all))
    logger.info("  Decoded:  %d", len(decoded_all))
    logger.info("  Derived:  %d", len(derived_all))
    logger.info("  Signals:  %d", len(signal_docs))
    logger.info("  Alerts:   %d", len(pattern_docs))


if __name__ == "__main__":
    asyncio.run(main())
