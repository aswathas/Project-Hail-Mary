import pytest
from unittest.mock import AsyncMock, patch, call

from pipeline.ingest import make_doc_id, bulk_index, index_raw, index_derived


# ---------------------------------------------------------------------------
# make_doc_id tests
# ---------------------------------------------------------------------------

def test_make_doc_id_with_log_index():
    doc = {"tx_hash": "0xabc", "log_index": 3}
    assert make_doc_id(doc) == "0xabc_3"


def test_make_doc_id_with_log_index_zero():
    """log_index of 0 is valid and must not be treated as falsy."""
    doc = {"tx_hash": "0xabc", "log_index": 0}
    assert make_doc_id(doc) == "0xabc_0"


def test_make_doc_id_with_derived_type():
    doc = {"tx_hash": "0xabc", "derived_type": "asset_transfer",
           "source_log_index": 2}
    assert make_doc_id(doc) == "0xabc_2_asset_transfer"


def test_make_doc_id_with_derived_type_no_source_log():
    doc = {"tx_hash": "0xabc", "derived_type": "native_transfer"}
    result = make_doc_id(doc)
    # New format: {tx_hash}_{derived_type}_{hash_of_unique_fields}
    assert result.startswith("0xabc_native_transfer_")
    assert len(result) > len("0xabc_native_transfer_")


def test_make_doc_id_transaction():
    doc = {"tx_hash": "0xabc"}
    assert make_doc_id(doc) == "0xabc_tx"


def test_make_doc_id_with_doc_type():
    doc = {"tx_hash": "0xabc", "doc_type": "trace"}
    assert make_doc_id(doc) == "0xabc_trace"


# ---------------------------------------------------------------------------
# bulk_index tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_bulk_index_chunks_correctly():
    """Verify that bulk_index splits documents into correct chunk sizes."""
    es_client = AsyncMock()
    docs = [{"tx_hash": f"0x{i:04x}", "log_index": 0} for i in range(7)]

    with patch("pipeline.ingest.async_bulk", new_callable=AsyncMock) as mock_bulk:
        # Each call returns (success_count, errors_list)
        mock_bulk.return_value = (3, [])

        stats = await bulk_index(es_client, docs, "forensics-raw", chunk_size=3)

    # 7 docs / chunk_size 3 => 3 calls (3 + 3 + 1)
    assert mock_bulk.call_count == 3
    assert stats["indexed"] == 9  # 3 calls x 3 reported successes
    assert stats["errors"] == 0


@pytest.mark.asyncio
async def test_bulk_index_empty_list():
    es_client = AsyncMock()
    stats = await bulk_index(es_client, [], "forensics-raw")
    assert stats == {"indexed": 0, "errors": 0, "error_details": []}


@pytest.mark.asyncio
async def test_bulk_index_handles_errors():
    es_client = AsyncMock()
    docs = [{"tx_hash": "0x01", "log_index": 0}]

    error_detail = {"index": {"_id": "0x01_0", "error": "mapping issue"}}
    with patch("pipeline.ingest.async_bulk", new_callable=AsyncMock) as mock_bulk:
        mock_bulk.return_value = (0, [error_detail])

        stats = await bulk_index(es_client, docs, "forensics")

    assert stats["indexed"] == 0
    assert stats["errors"] == 1
    assert stats["error_details"] == [error_detail]


# ---------------------------------------------------------------------------
# index_raw tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_index_raw_sets_investigation_id_and_doc_type():
    es_client = AsyncMock()
    raw_docs = [
        {"tx_hash": "0xabc", "block_number": 10, "from_address": "0x1"},
        {"tx_hash": "0xdef", "log_index": 0, "log_address": "0xtoken"},
        {"tx_hash": "0xghi", "trace_type": "CALL"},
    ]

    with patch("pipeline.ingest.bulk_index", new_callable=AsyncMock) as mock_bi:
        mock_bi.return_value = {"indexed": 3, "errors": 0, "error_details": []}
        await index_raw(es_client, raw_docs, "INV-001")

    call_args = mock_bi.call_args
    enriched = call_args[0][1]  # second positional arg: documents

    assert all(d["investigation_id"] == "INV-001" for d in enriched)
    assert all("@timestamp" in d for d in enriched)

    assert enriched[0]["doc_type"] == "transaction"
    assert enriched[1]["doc_type"] == "log"
    assert enriched[2]["doc_type"] == "trace"

    # Index name must be forensics-raw
    assert call_args[0][2] == "forensics-raw"


# ---------------------------------------------------------------------------
# index_derived tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_index_derived_delegates_to_bulk_index():
    es_client = AsyncMock()
    derived_docs = [
        {
            "tx_hash": "0xabc",
            "investigation_id": "INV-001",
            "layer": "derived",
            "derived_type": "asset_transfer",
            "source_log_index": 0,
        }
    ]

    with patch("pipeline.ingest.bulk_index", new_callable=AsyncMock) as mock_bi:
        mock_bi.return_value = {"indexed": 1, "errors": 0, "error_details": []}
        await index_derived(es_client, derived_docs)

    call_args = mock_bi.call_args
    assert call_args[0][2] == "forensics"
    assert call_args[0][1] == derived_docs
