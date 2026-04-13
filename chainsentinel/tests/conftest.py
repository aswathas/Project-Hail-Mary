import pytest
import json
from pathlib import Path


@pytest.fixture
def config():
    config_path = Path(__file__).parent.parent / "config.json"
    with open(config_path) as f:
        return json.load(f)


@pytest.fixture
def sample_raw_tx():
    """A realistic raw transaction as returned by eth_getTransactionByHash."""
    return {
        "hash": "0xabc123def456789012345678901234567890123456789012345678901234abcd",
        "blockNumber": "0xa",
        "blockHash": "0x1111111111111111111111111111111111111111111111111111111111111111",
        "transactionIndex": "0x0",
        "from": "0xDeaDbeefdEAdbeefdEadbEEFdeadbeEFdEaDbeeF",
        "to": "0x1234567890AbcdEF1234567890aBcDeF12345678",
        "value": "0xde0b6b3a7640000",
        "gas": "0x5208",
        "gasPrice": "0x3b9aca00",
        "nonce": "0x5",
        "input": "0x",
        "type": "0x2",
        "chainId": "0x7a69",
    }


@pytest.fixture
def sample_raw_receipt():
    """A realistic raw receipt as returned by eth_getTransactionReceipt."""
    return {
        "transactionHash": "0xabc123def456789012345678901234567890123456789012345678901234abcd",
        "blockNumber": "0xa",
        "blockHash": "0x1111111111111111111111111111111111111111111111111111111111111111",
        "transactionIndex": "0x0",
        "from": "0xDeaDbeefdEAdbeefdEadbEEFdeadbeEFdEaDbeeF",
        "to": "0x1234567890AbcdEF1234567890aBcDeF12345678",
        "status": "0x1",
        "gasUsed": "0x5208",
        "cumulativeGasUsed": "0x5208",
        "contractAddress": None,
        "logs": [],
        "logsBloom": "0x" + "0" * 512,
    }


@pytest.fixture
def sample_raw_log():
    """A realistic ERC20 Transfer event log."""
    return {
        "address": "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
        "topics": [
            "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef",
            "0x000000000000000000000000deadbeefdeadbeefdeadbeefdeadbeefdeadbeef",
            "0x0000000000000000000000001234567890abcdef1234567890abcdef12345678",
        ],
        "data": "0x0000000000000000000000000000000000000000000000000000000005f5e100",
        "blockNumber": "0xa",
        "transactionHash": "0xabc123def456789012345678901234567890123456789012345678901234abcd",
        "transactionIndex": "0x0",
        "logIndex": "0x0",
        "blockHash": "0x1111111111111111111111111111111111111111111111111111111111111111",
        "removed": False,
    }


@pytest.fixture
def sample_trace():
    """A realistic debug_traceTransaction result."""
    return {
        "type": "CALL",
        "from": "0xdeadbeefdeadbeefdeadbeefdeadbeefdeadbeef",
        "to": "0x1234567890abcdef1234567890abcdef12345678",
        "value": "0xde0b6b3a7640000",
        "gas": "0x5208",
        "gasUsed": "0x5208",
        "input": "0x",
        "output": "0x",
        "calls": [
            {
                "type": "CALL",
                "from": "0x1234567890abcdef1234567890abcdef12345678",
                "to": "0xdeadbeefdeadbeefdeadbeefdeadbeefdeadbeef",
                "value": "0xde0b6b3a7640000",
                "gas": "0x2710",
                "gasUsed": "0x1388",
                "input": "0x",
                "output": "0x",
                "calls": [],
            }
        ],
    }


@pytest.fixture
def sample_normalized_tx():
    """A normalized transaction (after normalizer)."""
    return {
        "tx_hash": "0xabc123def456789012345678901234567890123456789012345678901234abcd",
        "block_number": 10,
        "block_datetime": "2026-01-15T12:00:00Z",
        "block_timestamp_raw": 1736942400,
        "tx_index": 0,
        "from_address": "0xdeadbeefdeadbeefdeadbeefdeadbeefdeadbeef",
        "to_address": "0x1234567890abcdef1234567890abcdef12345678",
        "value_eth": 1.0,
        "value_wei": "1000000000000000000",
        "gas": 21000,
        "gas_price": 1000000000,
        "gas_used": 21000,
        "nonce": 5,
        "input": "0x",
        "success": True,
        "contract_address": None,
        "logs": [],
        "chain_id": 31337,
        "decode_status": "pending",
        "raw_extra": {},
    }


@pytest.fixture
def sample_erc20_abi():
    """Minimal ERC20 ABI for Transfer and Approval events."""
    return [
        {
            "anonymous": False,
            "inputs": [
                {"indexed": True, "name": "from", "type": "address"},
                {"indexed": True, "name": "to", "type": "address"},
                {"indexed": False, "name": "value", "type": "uint256"},
            ],
            "name": "Transfer",
            "type": "event",
        },
        {
            "anonymous": False,
            "inputs": [
                {"indexed": True, "name": "owner", "type": "address"},
                {"indexed": True, "name": "spender", "type": "address"},
                {"indexed": False, "name": "value", "type": "uint256"},
            ],
            "name": "Approval",
            "type": "event",
        },
    ]
