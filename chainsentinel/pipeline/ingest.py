"""
Elasticsearch Bulk Ingest — indexes pipeline output into forensic indices.

All ingest is idempotent: document _id is derived deterministically from
tx_hash + log_index (or tx_hash + derived_type / tx_hash + doc_type),
so rerunning an analysis against the same data produces no duplicates.
"""
import hashlib
import json
import logging
from datetime import datetime, timezone

from elasticsearch.helpers import async_bulk

logger = logging.getLogger(__name__)


def _hash_unique_fields(doc: dict) -> str:
    """Hash non-core fields to produce a short unique suffix for IDs."""
    exclude = {
        "investigation_id", "layer", "derived_type", "tx_hash",
        "block_number", "block_datetime", "@timestamp",
        "source_tx_hash", "source_log_index", "source_layer",
    }
    unique_data = {k: v for k, v in sorted(doc.items()) if k not in exclude and v is not None}
    raw = json.dumps(unique_data, sort_keys=True, default=str)
    return hashlib.sha256(raw.encode()).hexdigest()[:12]


def make_doc_id(doc: dict) -> str:
    """Generate a deterministic _id from document fields.

    Priority:
      1. Signal docs: {investigation_id}_{signal_name}_{tx_hash}
      2. Alert docs:  {investigation_id}_{pattern_id}
      3. tx_hash + log_index  (event-level records — decoded logs)
      4. Derived with source_log_index: {tx_hash}_{source_log_index}_{derived_type}
      5. Derived without source_log_index: {tx_hash}_{derived_type}_{hash}
      6. tx_hash + doc_type   (raw records typed by collector)
      7. tx_hash + "_tx"      (bare transactions)
    """
    inv_id = doc.get("investigation_id", "")
    tx_hash = doc.get("tx_hash", doc.get("source_tx_hash", "unknown"))

    # Signal documents
    if doc.get("layer") == "signal" and doc.get("signal_name"):
        return f"{inv_id}_{doc['signal_name']}_{tx_hash}"

    # Alert documents
    if doc.get("layer") == "alert" and doc.get("pattern_id"):
        return f"{inv_id}_{doc['pattern_id']}"

    # Decoded event logs (have log_index but no derived_type)
    if doc.get("log_index") is not None and not doc.get("derived_type"):
        return f"{tx_hash}_{doc['log_index']}"

    # Derived docs with source_log_index (trace-based, event-based)
    if doc.get("derived_type") and doc.get("source_log_index") is not None:
        return f"{tx_hash}_{doc['source_log_index']}_{doc['derived_type']}"

    # Derived docs without source_log_index (tx-based derived types)
    if doc.get("derived_type"):
        suffix = _hash_unique_fields(doc)
        return f"{tx_hash}_{doc['derived_type']}_{suffix}"

    if doc.get("doc_type"):
        return f"{tx_hash}_{doc['doc_type']}"

    return f"{tx_hash}_tx"


def _actions(documents: list[dict], index_name: str):
    """Yield bulk action dicts for async_bulk."""
    for doc in documents:
        yield {
            "_index": index_name,
            "_id": make_doc_id(doc),
            "_source": doc,
        }


async def bulk_index(
    es_client,
    documents: list[dict],
    index_name: str,
    chunk_size: int = 500,
) -> dict:
    """Bulk-index documents into *index_name* in chunks.

    Returns ``{"indexed": N, "errors": N, "error_details": [...]}``.
    """
    stats = {"indexed": 0, "errors": 0, "error_details": []}

    if not documents:
        return stats

    for start in range(0, len(documents), chunk_size):
        chunk = documents[start : start + chunk_size]
        try:
            success, errors = await async_bulk(
                es_client,
                _actions(chunk, index_name),
                raise_on_error=False,
                raise_on_exception=False,
                chunk_size=chunk_size,
            )
            stats["indexed"] += success
            if isinstance(errors, list):
                stats["errors"] += len(errors)
                stats["error_details"].extend(errors)
        except Exception as exc:
            logger.error("Bulk ingest failed for chunk %d-%d: %s",
                         start, start + len(chunk), exc)
            stats["errors"] += len(chunk)
            stats["error_details"].append(str(exc))

    if stats["errors"]:
        logger.warning(
            "Bulk ingest to %s finished with %d errors out of %d docs",
            index_name, stats["errors"], len(documents),
        )
    else:
        logger.info(
            "Bulk ingest to %s complete: %d docs indexed",
            index_name, stats["indexed"],
        )

    return stats


async def index_raw(
    es_client,
    raw_docs: list[dict],
    investigation_id: str,
) -> dict:
    """Index raw collector output into the ``forensics-raw`` index.

    Adds ``investigation_id``, ``@timestamp``, and infers ``doc_type``
    (transaction / log / trace) before indexing.
    """
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    enriched = []
    for doc in raw_docs:
        enriched_doc = dict(doc)
        enriched_doc["investigation_id"] = investigation_id
        enriched_doc.setdefault("@timestamp", now)

        # Infer doc_type if not already set
        if "doc_type" not in enriched_doc:
            if "trace_type" in enriched_doc or "trace_calls" in enriched_doc:
                enriched_doc["doc_type"] = "trace"
            elif "log_index" in enriched_doc or "log_address" in enriched_doc:
                enriched_doc["doc_type"] = "log"
            else:
                enriched_doc["doc_type"] = "transaction"

        enriched.append(enriched_doc)

    return await bulk_index(es_client, enriched, "forensics-raw")


async def index_derived(
    es_client,
    derived_docs: list[dict],
) -> dict:
    """Index decoded events, derived security events, signals, patterns,
    and attacker profiles into the ``forensics`` index.

    Documents are expected to already carry ``investigation_id``, ``layer``,
    ``derived_type``, etc. as set by the derived.py / signals / patterns
    modules.
    """
    return await bulk_index(es_client, derived_docs, "forensics")
