"""
ChainSentinel FastAPI Server

Thin wrapper around the forensic pipeline. Exposes endpoints for
the React frontend to start analyses, check health, and retrieve results.
"""

import json
import logging
import traceback
from datetime import datetime, timezone
from pathlib import Path

import httpx
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sse_starlette.sse import EventSourceResponse
from typing import Optional, Union

from elasticsearch import AsyncElasticsearch
from web3 import AsyncWeb3
from web3.providers import AsyncHTTPProvider

from pipeline.runner import (
    run_tx_analysis,
    run_range_analysis,
    generate_investigation_id,
)
from pipeline.ingest import index_raw, index_derived, bulk_index
from es.setup import setup_elasticsearch
from detection.signal_engine import run_all_signals
from detection.pattern_engine import run_all_patterns

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("chainsentinel")

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
CONFIG_PATH = Path(__file__).resolve().parent / "config.json"


def load_config() -> dict:
    """Load config.json from the same directory as server.py."""
    with open(CONFIG_PATH, "r") as f:
        return json.load(f)


config = load_config()

# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------
app = FastAPI(
    title="ChainSentinel",
    description="EVM blockchain forensics API",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------


class AnalyzeRequest(BaseModel):
    mode: str = Field(
        ..., description="Analysis mode: tx, range, wallet, or watch"
    )
    target: Union[str, dict] = Field(
        ...,
        description=(
            "Transaction hash (tx mode), wallet address (wallet mode), "
            "or {from_block, to_block} dict (range mode). "
            "Ignored for watch mode."
        ),
    )
    rpc_url: Optional[str] = None
    es_url: Optional[str] = None
    ollama_url: Optional[str] = None


class SimulateRequest(BaseModel):
    attack_type: str


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _resolve(request_val: Optional[str], config_key: str) -> str:
    """Return the request-level override if provided, else config default."""
    if request_val is not None:
        return request_val
    return config[config_key]


async def _make_web3(rpc_url: str) -> AsyncWeb3:
    """Create an AsyncWeb3 instance and verify the connection."""
    provider = AsyncHTTPProvider(rpc_url)
    w3 = AsyncWeb3(provider)
    # Quick connectivity check
    await w3.eth.block_number
    return w3


# ---------------------------------------------------------------------------
# POST /analyze
# ---------------------------------------------------------------------------


@app.post("/analyze")
async def analyze(request: AnalyzeRequest):
    """
    Start a forensic analysis pipeline and stream progress as SSE events.
    """
    rpc_url = _resolve(request.rpc_url, "rpc_url")
    es_url = _resolve(request.es_url, "es_url")

    # Validate web3 connectivity before starting the stream
    try:
        w3 = await _make_web3(rpc_url)
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail=f"Cannot connect to RPC endpoint {rpc_url}: {exc}",
        )

    investigation_id = generate_investigation_id()
    es_client = AsyncElasticsearch(hosts=[es_url])

    # Ensure ES indices exist
    try:
        await setup_elasticsearch(es_client)
    except Exception as exc:
        logger.warning("ES index setup issue (non-fatal): %s", exc)

    async def event_generator():
        try:
            # Choose runner based on mode
            if request.mode == "tx":
                if not isinstance(request.target, str):
                    yield {
                        "event": "pipeline",
                        "data": json.dumps(
                            {
                                "phase": "error",
                                "msg": "tx mode requires a transaction hash string",
                                "severity": "crit",
                                "ts": _ts(),
                            }
                        ),
                    }
                    return

                runner = run_tx_analysis(
                    w3=w3,
                    tx_hash=request.target,
                    investigation_id=investigation_id,
                    config=config,
                )

            elif request.mode == "range":
                if not isinstance(request.target, dict):
                    yield {
                        "event": "pipeline",
                        "data": json.dumps(
                            {
                                "phase": "error",
                                "msg": "range mode requires {from_block, to_block}",
                                "severity": "crit",
                                "ts": _ts(),
                            }
                        ),
                    }
                    return

                from_block = request.target.get("from_block")
                to_block = request.target.get("to_block")
                if from_block is None or to_block is None:
                    yield {
                        "event": "pipeline",
                        "data": json.dumps(
                            {
                                "phase": "error",
                                "msg": "from_block and to_block are required for range mode",
                                "severity": "crit",
                                "ts": _ts(),
                            }
                        ),
                    }
                    return

                runner = run_range_analysis(
                    w3=w3,
                    from_block=int(from_block),
                    to_block=int(to_block),
                    investigation_id=investigation_id,
                    config=config,
                )

            elif request.mode in ("wallet", "watch"):
                # Wallet hunt and watch mode are planned but not yet wired
                yield {
                    "event": "pipeline",
                    "data": json.dumps(
                        {
                            "phase": "error",
                            "msg": f"{request.mode} mode is not yet implemented",
                            "severity": "warn",
                            "ts": _ts(),
                        }
                    ),
                }
                return

            else:
                yield {
                    "event": "pipeline",
                    "data": json.dumps(
                        {
                            "phase": "error",
                            "msg": f"Unknown mode: {request.mode}",
                            "severity": "crit",
                            "ts": _ts(),
                        }
                    ),
                }
                return

            # Stream pipeline events
            raw_docs = []
            derived_docs = []
            final_stats = {}

            async for event in runner:
                # The runner yields phase events, then a final 'complete'
                # event carrying all documents.
                if event.get("phase") == "complete":
                    raw_docs = event.pop("raw_docs", [])
                    derived_docs = event.pop("decoded_docs", []) + event.pop("derived_docs", [])
                    final_stats = event.get("stats", {})
                    # Don't yield the complete event yet — ingest first
                    continue

                yield {
                    "event": "pipeline",
                    "data": json.dumps(event),
                }

            # Bulk index to Elasticsearch
            try:
                if raw_docs:
                    await index_raw(es_client, raw_docs, investigation_id)
                if derived_docs:
                    await index_derived(es_client, derived_docs)
            except Exception as ingest_exc:
                logger.error("ES ingest error: %s", ingest_exc)
                yield {
                    "event": "pipeline",
                    "data": json.dumps(
                        {
                            "phase": "ingest",
                            "msg": f"ES ingest error: {ingest_exc}",
                            "severity": "warn",
                            "ts": _ts(),
                        }
                    ),
                }

            # Run signal engine (ES|QL queries against indexed data)
            signal_docs = []
            try:
                # Create a sync ES client for the sync signal/pattern engines
                from elasticsearch import Elasticsearch
                sync_es = Elasticsearch(hosts=[es_url])
                chain_id = config.get("chain_id", 31337)

                def sync_ingest(client, docs, index):
                    pass  # We collect docs and ingest async below

                signal_docs = run_all_signals(
                    sync_es, sync_ingest,
                    investigation_id=investigation_id,
                    chain_id=chain_id,
                )
                if signal_docs:
                    await bulk_index(es_client, signal_docs, "forensics")
                    final_stats["signals"] = len(signal_docs)

                yield {
                    "event": "pipeline",
                    "data": json.dumps(
                        {
                            "phase": "signals",
                            "msg": f"{len(signal_docs)} signals fired",
                            "severity": "crit" if any(
                                s.get("severity") == "CRIT" for s in signal_docs
                            ) else "ok" if signal_docs else "gray",
                            "esIndex": "forensics",
                            "ts": _ts(),
                        }
                    ),
                }

                # Run pattern engine (EQL sequences against signals + derived)
                pattern_docs = run_all_patterns(
                    sync_es, sync_ingest,
                    investigation_id=investigation_id,
                    chain_id=chain_id,
                )
                if pattern_docs:
                    await bulk_index(es_client, pattern_docs, "forensics")

                yield {
                    "event": "pipeline",
                    "data": json.dumps(
                        {
                            "phase": "patterns",
                            "msg": f"{len(pattern_docs)} attack patterns matched"
                            if pattern_docs else "No patterns matched",
                            "severity": "crit" if pattern_docs else "gray",
                            "esIndex": "forensics",
                            "ts": _ts(),
                        }
                    ),
                }

                sync_es.close()
            except Exception as det_exc:
                logger.warning("Detection engine error (non-fatal): %s", det_exc)
                yield {
                    "event": "pipeline",
                    "data": json.dumps(
                        {
                            "phase": "signals",
                            "msg": f"Detection skipped: {det_exc}",
                            "severity": "warn",
                            "ts": _ts(),
                        }
                    ),
                }

            # Final complete event
            final_stats["indexed"] = (
                final_stats.get("indexed", 0)
                + len(signal_docs)
                + len(pattern_docs if 'pattern_docs' in dir() else [])
            )
            yield {
                "event": "pipeline",
                "data": json.dumps(
                    {
                        "phase": "complete",
                        "investigationId": investigation_id,
                        "stats": final_stats,
                    }
                ),
            }

        except Exception as exc:
            logger.error("Pipeline error: %s\n%s", exc, traceback.format_exc())
            yield {
                "event": "pipeline",
                "data": json.dumps(
                    {
                        "phase": "error",
                        "msg": f"Pipeline crashed: {exc}",
                        "severity": "crit",
                        "ts": _ts(),
                    }
                ),
            }
        finally:
            await es_client.close()

    return EventSourceResponse(event_generator())


# ---------------------------------------------------------------------------
# GET /health
# ---------------------------------------------------------------------------


@app.get("/health")
async def health():
    """
    Check connectivity to RPC, Elasticsearch, and Ollama.
    Each check is independent -- one failing does not block others.
    """
    result = {"rpc": "error", "elasticsearch": "error", "ollama": "error"}

    # RPC check
    try:
        provider = AsyncHTTPProvider(config["rpc_url"])
        w3 = AsyncWeb3(provider)
        await w3.eth.block_number
        result["rpc"] = "ok"
    except Exception as exc:
        logger.debug("RPC health check failed: %s", exc)

    # Elasticsearch check
    try:
        es = AsyncElasticsearch(hosts=[config["es_url"]])
        health_resp = await es.cluster.health()
        if health_resp.get("status") in ("green", "yellow"):
            result["elasticsearch"] = "ok"
        await es.close()
    except Exception as exc:
        logger.debug("ES health check failed: %s", exc)

    # Ollama check
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{config['ollama_url']}/api/tags")
            if resp.status_code == 200:
                result["ollama"] = "ok"
    except Exception as exc:
        logger.debug("Ollama health check failed: %s", exc)

    return result


# ---------------------------------------------------------------------------
# GET /analysis/{investigation_id}
# ---------------------------------------------------------------------------


@app.get("/analysis/{investigation_id}")
async def get_analysis(investigation_id: str):
    """
    Fetch the completed investigation document from Elasticsearch.
    """
    es = AsyncElasticsearch(hosts=[config["es_url"]])
    try:
        resp = await es.search(
            index="forensics-investigations-*",
            body={
                "query": {
                    "term": {"investigation_id": investigation_id}
                },
                "size": 1,
            },
        )
        hits = resp.get("hits", {}).get("hits", [])
        if not hits:
            raise HTTPException(
                status_code=404,
                detail=f"Investigation {investigation_id} not found",
            )
        return hits[0]["_source"]
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Error querying Elasticsearch: {exc}",
        )
    finally:
        await es.close()


# ---------------------------------------------------------------------------
# POST /simulate
# ---------------------------------------------------------------------------


@app.post("/simulate")
async def simulate(request: SimulateRequest):
    """
    Placeholder -- will eventually deploy Foundry simulation contracts.
    """
    return {"status": "not_implemented", "attack_type": request.attack_type}


# ---------------------------------------------------------------------------
# Utility
# ---------------------------------------------------------------------------


def _ts() -> str:
    """Return a short timestamp string for SSE events."""
    return datetime.now(timezone.utc).strftime("%H:%M:%S")


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)
