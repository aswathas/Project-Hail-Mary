"""
Runner — orchestrates the pipeline layers and yields SSE-compatible events.

Chains collector → normalizer → decoder → derived for each analysis mode.
Does not perform ES indexing — collects all documents and returns them
in the final 'complete' event for the server to ingest.
"""
import logging
import random
import string
from collections import Counter

logger = logging.getLogger("chainsentinel.runner")
from datetime import datetime, timezone
from typing import AsyncGenerator

from pipeline.collector import collect_transaction, collect_block_range
from pipeline.normalizer import normalize_transaction, normalize_log
from pipeline.decoder import load_decoder
from pipeline.derived import (
    derive_events, derive_events_from_tx, derive_events_from_trace,
    get_all_derived_builders as _get_new_builders,
)
import asyncio


def generate_investigation_id() -> str:
    """Return an investigation ID in 'INV-{YYYY}-{NNNN}' format."""
    year = datetime.now(timezone.utc).strftime("%Y")
    suffix = "".join(random.choices(string.digits, k=4))
    return f"INV-{year}-{suffix}"


def _now() -> str:
    """Return current UTC time as HH:MM:SS for SSE timestamps."""
    return datetime.now(timezone.utc).strftime("%H:%M:%S")


def _sse(phase: str, msg: str, severity: str = "gray",
         es_index: str = None, **extra) -> dict:
    """Build an SSE event dict."""
    event = {
        "phase": phase,
        "msg": msg,
        "severity": severity,
        "esIndex": es_index,
        "ts": _now(),
    }
    event.update(extra)
    return event


async def _run_new_derived_builders(
    normalized_tx: dict,
    decoded_events: list[dict],
    collector_doc: dict,
    investigation_id: str,
    config: dict,
) -> list[dict]:
    """Call all new-style derived builders from the derived/ package.

    Assembles the raw_data dict each builder expects and collects results.
    """
    builders = _get_new_builders()
    if not builders:
        return []

    results = []
    for name, derive_fn in builders.items():
        raw_data = {
            "normalized_tx": normalized_tx,
            "decoded_events": decoded_events,
            "trace": collector_doc.get("trace"),
            "tx_hash": normalized_tx.get("tx_hash", ""),
            "block_number": normalized_tx.get("block_number", 0),
            "block_datetime": normalized_tx.get("block_datetime", ""),
        }
        try:
            if asyncio.iscoroutinefunction(derive_fn):
                docs = await derive_fn(raw_data, investigation_id, config)
            else:
                docs = derive_fn(raw_data, investigation_id, config)
            if docs:
                results.extend(docs)
        except Exception as exc:
            logger.warning("Derived builder %s failed: %s", name, exc)

    return results


def _split_collector_doc(doc: dict) -> tuple[dict, dict, int]:
    """
    Split a merged collector document back into raw_tx and raw_receipt dicts
    that the normalizer expects.

    The collector merges tx + receipt into one flat dict with keys:
      tx_hash, block_number, block_timestamp, tx_index, from, to, value,
      gas, gas_price, nonce, input, status, gas_used, cumulative_gas_used,
      contract_address, logs, trace

    The normalizer expects:
      raw_tx:  hash, blockNumber, transactionIndex, from, to, value, gas,
               gasPrice, nonce, input
      raw_receipt: status, gasUsed, cumulativeGasUsed, contractAddress, logs
    """
    raw_tx = {
        "hash": doc.get("tx_hash", ""),
        "blockNumber": doc.get("block_number", 0),
        "transactionIndex": doc.get("tx_index", 0),
        "from": doc.get("from", ""),
        "to": doc.get("to", ""),
        "value": doc.get("value", 0),
        "gas": doc.get("gas", 0),
        "gasPrice": doc.get("gas_price", 0),
        "nonce": doc.get("nonce", 0),
        "input": doc.get("input", "0x"),
    }

    raw_receipt = {
        "status": doc.get("status", 0),
        "gasUsed": doc.get("gas_used", 0),
        "cumulativeGasUsed": doc.get("cumulative_gas_used", 0),
        "contractAddress": doc.get("contract_address"),
        "logs": doc.get("logs", []),
    }

    block_timestamp = doc.get("block_timestamp", 0)

    return raw_tx, raw_receipt, block_timestamp


async def run_tx_analysis(
    w3, tx_hash: str, config: dict, investigation_id: str
) -> AsyncGenerator[dict, None]:
    """
    Single transaction analysis mode.

    Runs the full pipeline for one transaction and yields SSE events
    at each stage. The final 'complete' event carries all produced
    documents for the server to ingest into Elasticsearch.
    """
    chain_id = config.get("chain_id", 31337)
    rpc_url = config.get("rpc_url", "http://127.0.0.1:8545")
    raw_docs = []
    decoded_docs = []
    derived_docs = []

    # --- A. Collect -----------------------------------------------------------
    collector_doc = await collect_transaction(w3, tx_hash, include_trace=True, rpc_url=rpc_url)
    raw_docs.append(collector_doc)

    log_count = len(collector_doc.get("logs", []))
    has_trace = collector_doc.get("trace") is not None
    trace_msg = " · trace captured" if has_trace else ""

    yield _sse(
        "collector",
        f"Tx {tx_hash[:10]}... fetched · {log_count} logs{trace_msg}",
        "gray",
        "forensics-raw-transactions-*",
    )

    # --- B. Normalize ---------------------------------------------------------
    raw_tx, raw_receipt, block_timestamp = _split_collector_doc(collector_doc)
    normalized_tx = normalize_transaction(raw_tx, raw_receipt, block_timestamp, chain_id)

    yield _sse(
        "normalizer",
        f"Tx normalised · hex→int · wei→ETH · {log_count} logs",
        "ok",
        "forensics-raw-transactions-*",
    )

    # --- C. Decode ------------------------------------------------------------
    decoder = load_decoder(investigation_id)

    decoded_count = 0
    unknown_count = 0
    all_decoded_events = []

    for log in normalized_tx.get("logs", []):
        result = decoder.decode_log(log)
        merged = {**log, **result}
        all_decoded_events.append(merged)
        decoded_docs.append(merged)

        if result.get("decode_status") == "decoded":
            decoded_count += 1
        else:
            unknown_count += 1

    # Decode function input on the transaction itself
    func_result = decoder.decode_function_input(normalized_tx.get("input", "0x"))
    normalized_tx["function_name"] = func_result.get("function_name")
    normalized_tx["function_args"] = func_result.get("function_args", {})
    normalized_tx["decode_status"] = func_result.get("decode_status", "unknown")

    yield _sse(
        "decoder",
        f"{decoded_count} events decoded · {unknown_count} unknown selectors",
        "info",
        "forensics-decoded-events-*",
    )

    # --- D. Derive security events --------------------------------------------
    # Legacy derived builders (backward compatible)
    events_from_logs = derive_events(all_decoded_events, investigation_id)
    derived_docs.extend(events_from_logs)

    events_from_tx = derive_events_from_tx(normalized_tx, investigation_id)
    derived_docs.extend(events_from_tx)

    if collector_doc.get("trace"):
        events_from_trace = derive_events_from_trace(
            collector_doc["trace"],
            normalized_tx["tx_hash"],
            normalized_tx["block_number"],
            normalized_tx["block_datetime"],
            investigation_id,
        )
        derived_docs.extend(events_from_trace)

    # New-style derived builders from derived/ package
    new_derived = await _run_new_derived_builders(
        normalized_tx, all_decoded_events, collector_doc,
        investigation_id, config,
    )
    derived_docs.extend(new_derived)

    # Count derived event types
    type_counts = Counter(d.get("derived_type", "unknown") for d in derived_docs)
    type_summary = " · ".join(f"{count} {dtype}" for dtype, count in type_counts.items())

    yield _sse(
        "derived",
        type_summary or "No derived events",
        "ok",
        "forensics-derived-*",
    )

    # --- Complete -------------------------------------------------------------
    stats = {
        "blocks": 1,
        "txs": 1,
        "signals": 0,
        "indexed": len(raw_docs) + len(decoded_docs) + len(derived_docs),
    }

    yield {
        "phase": "complete",
        "investigationId": investigation_id,
        "stats": stats,
        "ts": _now(),
        "raw_docs": raw_docs,
        "normalized_docs": [normalized_tx],
        "decoded_docs": decoded_docs,
        "derived_docs": derived_docs,
    }


async def run_range_analysis(
    w3, from_block: int, to_block: int, config: dict, investigation_id: str
) -> AsyncGenerator[dict, None]:
    """
    Block range analysis mode.

    Batch-fetches all transactions in the range and processes the entire
    set through normalize → decode → derive. Yields SSE events at each
    phase.
    """
    chain_id = config.get("chain_id", 31337)
    rpc_url = config.get("rpc_url", "http://127.0.0.1:8545")
    raw_docs = []
    decoded_docs = []
    derived_docs = []
    normalized_txs = []

    block_count = to_block - from_block + 1

    # --- A. Collect -----------------------------------------------------------
    collector_docs = await collect_block_range(w3, from_block, to_block, include_traces=True, rpc_url=rpc_url)
    raw_docs.extend(collector_docs)

    tx_count = len(collector_docs)
    yield _sse(
        "collector",
        f"Blocks {from_block}–{to_block} fetched · {tx_count} txs",
        "gray",
        "forensics-raw-transactions-*",
    )

    # --- B. Normalize ---------------------------------------------------------
    for doc in collector_docs:
        raw_tx, raw_receipt, block_timestamp = _split_collector_doc(doc)
        normalized = normalize_transaction(raw_tx, raw_receipt, block_timestamp, chain_id)
        normalized_txs.append(normalized)

    yield _sse(
        "normalizer",
        f"{tx_count} txs normalised · hex→int · wei→ETH",
        "ok",
        "forensics-raw-transactions-*",
    )

    # --- C. Decode ------------------------------------------------------------
    decoder = load_decoder(investigation_id)
    decoded_count = 0
    unknown_count = 0
    all_decoded_events = []

    for normalized_tx in normalized_txs:
        for log in normalized_tx.get("logs", []):
            result = decoder.decode_log(log)
            merged = {**log, **result}
            all_decoded_events.append(merged)
            decoded_docs.append(merged)

            if result.get("decode_status") == "decoded":
                decoded_count += 1
            else:
                unknown_count += 1

        # Decode function input
        func_result = decoder.decode_function_input(normalized_tx.get("input", "0x"))
        normalized_tx["function_name"] = func_result.get("function_name")
        normalized_tx["function_args"] = func_result.get("function_args", {})
        normalized_tx["decode_status"] = func_result.get("decode_status", "unknown")

    yield _sse(
        "decoder",
        f"{decoded_count} events decoded · {unknown_count} unknown selectors",
        "info",
        "forensics-decoded-events-*",
    )

    # --- D. Derive security events --------------------------------------------
    # Legacy derived builders (backward compatible)
    events_from_logs = derive_events(all_decoded_events, investigation_id)
    derived_docs.extend(events_from_logs)

    for idx, normalized_tx in enumerate(normalized_txs):
        events_from_tx = derive_events_from_tx(normalized_tx, investigation_id)
        derived_docs.extend(events_from_tx)

        collector_doc = collector_docs[idx]
        logger.debug("Tx %s trace present: %s", normalized_tx.get("tx_hash", "")[:12], bool(collector_doc.get("trace")))
        if collector_doc.get("trace"):
            events_from_trace = derive_events_from_trace(
                collector_doc["trace"],
                normalized_tx["tx_hash"],
                normalized_tx["block_number"],
                normalized_tx["block_datetime"],
                investigation_id,
            )
            derived_docs.extend(events_from_trace)

        # New-style derived builders from derived/ package
        decoded_for_tx = [e for e in all_decoded_events if e.get("tx_hash") == normalized_tx.get("tx_hash")]
        new_derived = await _run_new_derived_builders(
            normalized_tx, decoded_for_tx, collector_doc,
            investigation_id, config,
        )
        derived_docs.extend(new_derived)

    # Count derived event types
    type_counts = Counter(d.get("derived_type", "unknown") for d in derived_docs)
    type_summary = " · ".join(f"{count} {dtype}" for dtype, count in type_counts.items())

    yield _sse(
        "derived",
        type_summary or "No derived events",
        "ok",
        "forensics-derived-*",
    )

    # --- Complete -------------------------------------------------------------
    stats = {
        "blocks": block_count,
        "txs": tx_count,
        "signals": 0,
        "indexed": len(raw_docs) + len(decoded_docs) + len(derived_docs),
    }

    yield {
        "phase": "complete",
        "investigationId": investigation_id,
        "stats": stats,
        "ts": _now(),
        "raw_docs": raw_docs,
        "normalized_docs": normalized_txs,
        "decoded_docs": decoded_docs,
        "derived_docs": derived_docs,
    }
