import pytest
from unittest.mock import MagicMock, AsyncMock, patch


@pytest.mark.asyncio
async def test_collect_transaction_returns_merged_tx_receipt():
    from pipeline.collector import collect_transaction

    mock_w3 = MagicMock()
    mock_w3.eth.get_transaction = AsyncMock(return_value={
        "hash": "0xabc",
        "blockNumber": 10,
        "from": "0xdead",
        "to": "0x1234",
        "value": 1000000000000000000,
        "gas": 21000,
        "gasPrice": 1000000000,
        "nonce": 5,
        "input": "0x",
        "transactionIndex": 0,
    })
    mock_w3.eth.get_transaction_receipt = AsyncMock(return_value={
        "transactionHash": "0xabc",
        "blockNumber": 10,
        "status": 1,
        "gasUsed": 21000,
        "cumulativeGasUsed": 21000,
        "contractAddress": None,
        "logs": [],
    })
    mock_w3.eth.get_block = AsyncMock(return_value={
        "number": 10,
        "timestamp": 1736942400,
    })

    result = await collect_transaction(mock_w3, "0xabc")

    assert result["tx_hash"] == "0xabc"
    assert result["block_number"] == 10
    assert result["status"] == 1
    assert result["gas_used"] == 21000
    assert result["logs"] == []
    assert result["block_timestamp"] == 1736942400


@pytest.mark.asyncio
async def test_collect_transaction_includes_trace_when_available():
    from pipeline.collector import collect_transaction

    mock_w3 = MagicMock()
    mock_w3.eth.get_transaction = AsyncMock(return_value={
        "hash": "0xabc", "blockNumber": 10, "from": "0xdead",
        "to": "0x1234", "value": 0, "gas": 100000,
        "gasPrice": 1000000000, "nonce": 0, "input": "0x",
        "transactionIndex": 0,
    })
    mock_w3.eth.get_transaction_receipt = AsyncMock(return_value={
        "transactionHash": "0xabc", "blockNumber": 10, "status": 1,
        "gasUsed": 50000, "cumulativeGasUsed": 50000,
        "contractAddress": None, "logs": [],
    })
    mock_w3.eth.get_block = AsyncMock(return_value={
        "number": 10, "timestamp": 1736942400,
    })
    mock_w3.manager = MagicMock()
    mock_w3.manager.request_blocking = MagicMock(return_value={
        "type": "CALL", "from": "0xdead", "to": "0x1234",
        "value": "0x0", "calls": [],
    })

    result = await collect_transaction(mock_w3, "0xabc", include_trace=True)

    assert result["trace"] is not None
    assert result["trace"]["type"] == "CALL"


@pytest.mark.asyncio
async def test_collect_transaction_graceful_without_trace():
    from pipeline.collector import collect_transaction

    mock_w3 = MagicMock()
    mock_w3.eth.get_transaction = AsyncMock(return_value={
        "hash": "0xabc", "blockNumber": 10, "from": "0xdead",
        "to": "0x1234", "value": 0, "gas": 21000,
        "gasPrice": 1000000000, "nonce": 0, "input": "0x",
        "transactionIndex": 0,
    })
    mock_w3.eth.get_transaction_receipt = AsyncMock(return_value={
        "transactionHash": "0xabc", "blockNumber": 10, "status": 1,
        "gasUsed": 21000, "cumulativeGasUsed": 21000,
        "contractAddress": None, "logs": [],
    })
    mock_w3.eth.get_block = AsyncMock(return_value={
        "number": 10, "timestamp": 1736942400,
    })
    mock_w3.manager = MagicMock()
    mock_w3.manager.request_blocking = MagicMock(
        side_effect=Exception("debug_traceTransaction not supported")
    )

    result = await collect_transaction(mock_w3, "0xabc", include_trace=True)

    assert result["trace"] is None
    assert result["tx_hash"] == "0xabc"


@pytest.mark.asyncio
async def test_collect_block_range_returns_all_txs():
    from pipeline.collector import collect_block_range

    mock_w3 = MagicMock()
    mock_w3.eth.get_block = AsyncMock(return_value={
        "number": 10,
        "timestamp": 1736942400,
        "transactions": [
            {"hash": "0xabc", "blockNumber": 10, "from": "0xdead",
             "to": "0x1234", "value": 0, "gas": 21000,
             "gasPrice": 1000000000, "nonce": 0, "input": "0x",
             "transactionIndex": 0},
        ],
    })
    mock_w3.eth.get_transaction_receipt = AsyncMock(return_value={
        "transactionHash": "0xabc", "blockNumber": 10, "status": 1,
        "gasUsed": 21000, "cumulativeGasUsed": 21000,
        "contractAddress": None, "logs": [],
    })

    results = await collect_block_range(mock_w3, 10, 10)

    assert len(results) == 1
    assert results[0]["tx_hash"] == "0xabc"
