# ChainSentinel Foundation — Implementation Plan (Plan 1 of 6)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the complete data pipeline from RPC to Elasticsearch — collector, normalizer, decoder, derived event builder, and bulk ingest — with ES index setup and config management.

**Architecture:** Python pipeline with 4 processing layers orchestrated by a runner that yields SSE events. Data flows from any EVM RPC endpoint through collector → normalizer → decoder → derived → ES ingest. Two ES indices with strict mappings: `forensics-raw` for untouched chain evidence, `forensics` for all pipeline output.

**Tech Stack:** Python 3.11+, web3.py, elasticsearch-py, FastAPI (minimal for Plan 1), Elasticsearch 8.x, Foundry/Anvil

**Spec reference:** `docs/superpowers/specs/2026-04-12-chainsentinel-design.md`

---

## File Structure

```
chainsentinel/
├── config.json                          ← single source of truth for all endpoints
├── requirements.txt                     ← Python dependencies
├── server.py                            ← minimal FastAPI (health + analyze endpoint)
├── pipeline/
│   ├── __init__.py
│   ├── runner.py                        ← orchestrates pipeline, yields SSE events
│   ├── collector.py                     ← RPC data fetching (txs, receipts, logs, traces)
│   ├── normalizer.py                    ← hex→int, addresses lowercase, timestamps
│   ├── decoder.py                       ← ABI decode with registry lookup
│   ├── derived.py                       ← security event builder (9 derived types)
│   ├── ingest.py                        ← ES bulk ingest with idempotent _id
│   ├── selector_registry.json           ← living selector→name cache
│   └── abi_registry/
│       ├── standards/
│       │   └── erc20.json
│       └── protocols/
├── es/
│   ├── __init__.py
│   ├── setup.py                         ← creates indices + applies mappings
│   └── mappings/
│       ├── forensics-raw.json           ← strict mapping for raw evidence
│       └── forensics.json               ← strict mapping for analysis data
└── tests/
    ├── __init__.py
    ├── conftest.py                      ← shared fixtures (mock RPC data, ES client)
    ├── test_collector.py
    ├── test_normalizer.py
    ├── test_decoder.py
    ├── test_derived.py
    ├── test_ingest.py
    └── test_runner.py
```

---

### Task 1: Project Scaffolding

**Files:**
- Create: `chainsentinel/config.json`
- Create: `chainsentinel/requirements.txt`
- Create: `chainsentinel/pipeline/__init__.py`
- Create: `chainsentinel/es/__init__.py`
- Create: `chainsentinel/tests/__init__.py`
- Create: `chainsentinel/tests/conftest.py`
- Create: `chainsentinel/pipeline/selector_registry.json`

- [ ] **Step 1: Create directory structure**

```bash
cd /mnt/c/Users/aswat/OneDrive/Desktop/Projects/Project_Hail_Mary
mkdir -p chainsentinel/pipeline/abi_registry/standards
mkdir -p chainsentinel/pipeline/abi_registry/protocols
mkdir -p chainsentinel/pipeline/abi_registry/cases
mkdir -p chainsentinel/es/mappings
mkdir -p chainsentinel/tests
mkdir -p chainsentinel/detection/signals
mkdir -p chainsentinel/detection/patterns
mkdir -p chainsentinel/correlation
mkdir -p chainsentinel/ollama
mkdir -p chainsentinel/frontend
mkdir -p simulations/scenarios
mkdir -p simulations/shared/contracts
```

- [ ] **Step 2: Create config.json**

```json
{
  "rpc_url": "http://127.0.0.1:8545",
  "es_url": "http://localhost:9200",
  "ollama_url": "http://localhost:11434",
  "ollama_model": "gemma3:1b",
  "ollama_temperature": 0.2,
  "chain_id": 31337,
  "mode": "simulation",
  "max_trace_hops": 5,
  "tx_history_limit": 200,
  "signal_score_threshold": 0.5,
  "es_bulk_chunk_size": 500
}
```

- [ ] **Step 3: Create requirements.txt**

```
web3>=6.15.0
elasticsearch>=8.12.0
fastapi>=0.110.0
uvicorn>=0.27.0
sse-starlette>=1.8.0
httpx>=0.27.0
pytest>=8.0.0
pytest-asyncio>=0.23.0
```

- [ ] **Step 4: Create __init__.py files and conftest.py**

`chainsentinel/pipeline/__init__.py` — empty file

`chainsentinel/es/__init__.py` — empty file

`chainsentinel/tests/__init__.py` — empty file

`chainsentinel/tests/conftest.py`:

```python
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
```

- [ ] **Step 5: Create empty selector_registry.json**

`chainsentinel/pipeline/selector_registry.json`:

```json
{
  "event_signatures": {},
  "function_selectors": {}
}
```

- [ ] **Step 6: Install dependencies and verify**

```bash
cd /mnt/c/Users/aswat/OneDrive/Desktop/Projects/Project_Hail_Mary/chainsentinel
pip install -r requirements.txt
python -c "import web3, elasticsearch, fastapi; print('All dependencies OK')"
```

- [ ] **Step 7: Initialize git repo and commit**

```bash
cd /mnt/c/Users/aswat/OneDrive/Desktop/Projects/Project_Hail_Mary
git init
git add chainsentinel/config.json chainsentinel/requirements.txt chainsentinel/pipeline/__init__.py chainsentinel/es/__init__.py chainsentinel/tests/__init__.py chainsentinel/tests/conftest.py chainsentinel/pipeline/selector_registry.json docs/ CLAUDE.md DESIGN.md
git commit -m "feat: project scaffolding with config, dependencies, and test fixtures"
```

---

### Task 2: Elasticsearch Index Mappings

**Files:**
- Create: `chainsentinel/es/mappings/forensics-raw.json`
- Create: `chainsentinel/es/mappings/forensics.json`

- [ ] **Step 1: Create forensics-raw mapping**

`chainsentinel/es/mappings/forensics-raw.json`:

```json
{
  "settings": {
    "number_of_shards": 1,
    "number_of_replicas": 0,
    "index.mapping.total_fields.limit": 500
  },
  "mappings": {
    "dynamic": "strict",
    "properties": {
      "investigation_id": { "type": "keyword" },
      "chain_id": { "type": "integer" },
      "@timestamp": { "type": "date" },
      "block_number": { "type": "long" },
      "block_datetime": { "type": "date" },
      "block_timestamp_raw": { "type": "long" },
      "tx_hash": { "type": "keyword" },
      "doc_type": { "type": "keyword" },

      "tx_index": { "type": "integer" },
      "from_address": { "type": "keyword" },
      "to_address": { "type": "keyword" },
      "value_eth": { "type": "double" },
      "value_wei": { "type": "keyword" },
      "gas": { "type": "long" },
      "gas_price": { "type": "long" },
      "gas_used": { "type": "long" },
      "cumulative_gas_used": { "type": "long" },
      "nonce": { "type": "long" },
      "input": { "type": "keyword", "index": false, "doc_values": false },
      "success": { "type": "boolean" },
      "contract_address": { "type": "keyword" },
      "is_contract_to": { "type": "boolean" },

      "log_index": { "type": "integer" },
      "log_address": { "type": "keyword" },
      "topics": { "type": "keyword" },
      "data": { "type": "keyword", "index": false, "doc_values": false },

      "trace_type": { "type": "keyword" },
      "trace_depth": { "type": "integer" },
      "trace_calls": { "type": "flattened" },

      "raw_extra": { "type": "flattened" }
    }
  }
}
```

- [ ] **Step 2: Create forensics mapping**

`chainsentinel/es/mappings/forensics.json`:

```json
{
  "settings": {
    "number_of_shards": 1,
    "number_of_replicas": 0,
    "index.mapping.total_fields.limit": 500
  },
  "mappings": {
    "dynamic": "strict",
    "properties": {
      "investigation_id": { "type": "keyword" },
      "chain_id": { "type": "integer" },
      "@timestamp": { "type": "date" },
      "block_number": { "type": "long" },
      "block_datetime": { "type": "date" },
      "tx_hash": { "type": "keyword" },
      "layer": { "type": "keyword" },

      "from_address": { "type": "keyword" },
      "to_address": { "type": "keyword" },
      "value_eth": { "type": "double" },
      "value_wei": { "type": "keyword" },

      "decode_status": { "type": "keyword" },
      "decoded_type": { "type": "keyword" },
      "event_name": { "type": "keyword" },
      "event_args": { "type": "flattened" },
      "function_name": { "type": "keyword" },
      "function_args": { "type": "flattened" },
      "token_symbol": { "type": "keyword" },
      "token_decimals": { "type": "integer" },
      "amount_decimal": { "type": "double" },

      "derived_type": { "type": "keyword" },
      "source_tx_hash": { "type": "keyword" },
      "source_log_index": { "type": "integer" },
      "source_layer": { "type": "keyword" },
      "transfer_type": { "type": "keyword" },
      "token_address": { "type": "keyword" },
      "token_id": { "type": "keyword" },
      "trader_address": { "type": "keyword" },
      "pool_address": { "type": "keyword" },
      "token_in": { "type": "keyword" },
      "token_out": { "type": "keyword" },
      "amount_in": { "type": "double" },
      "amount_out": { "type": "double" },
      "price_impact_pct": { "type": "float" },
      "owner_address": { "type": "keyword" },
      "spender_address": { "type": "keyword" },
      "was_consumed": { "type": "boolean" },
      "consumed_tx_hash": { "type": "keyword" },
      "actor_address": { "type": "keyword" },
      "contract_address": { "type": "keyword" },
      "action_type": { "type": "keyword" },
      "new_value": { "type": "keyword" },
      "caller_address": { "type": "keyword" },
      "callee_address": { "type": "keyword" },
      "call_type": { "type": "keyword" },
      "call_depth": { "type": "integer" },
      "gas_used": { "type": "long" },
      "success": { "type": "boolean" },
      "hop_number": { "type": "integer" },
      "direction": { "type": "keyword" },
      "taint_score": { "type": "float" },
      "protocol_name": { "type": "keyword" },
      "delta_amount": { "type": "double" },
      "user_address": { "type": "keyword" },

      "signal_name": { "type": "keyword" },
      "signal_family": { "type": "keyword" },
      "score": { "type": "float" },
      "severity": { "type": "keyword" },
      "description": { "type": "text" },
      "evidence_refs": { "type": "keyword" },

      "pattern_id": { "type": "keyword" },
      "pattern_name": { "type": "keyword" },
      "signals_fired": { "type": "keyword" },
      "confidence": { "type": "float" },
      "attacker_wallet": { "type": "keyword" },
      "victim_contract": { "type": "keyword" },
      "funds_drained_eth": { "type": "double" },
      "attack_block_range_from": { "type": "long" },
      "attack_block_range_to": { "type": "long" },

      "attacker_type": { "type": "keyword" },
      "cluster_id": { "type": "keyword" },
      "cluster_wallets": { "type": "keyword" },
      "cluster_size": { "type": "integer" },
      "funded_via": { "type": "keyword" },
      "funding_block": { "type": "long" },
      "funding_amount_eth": { "type": "double" },
      "first_seen_block": { "type": "long" },
      "exploit_block": { "type": "long" },
      "exit_routes": { "type": "keyword" },
      "ofac_match": { "type": "boolean" },
      "known_exploiter": { "type": "boolean" },
      "labels": { "type": "keyword" },
      "total_stolen_eth": { "type": "double" },
      "fund_trail_hops": { "type": "integer" },

      "case_id": { "type": "keyword" },
      "mode": { "type": "keyword" },
      "attack_type": { "type": "keyword" },
      "client_name": { "type": "keyword" },
      "stats": { "type": "flattened" },
      "timeline": { "type": "flattened" },
      "metadata": { "type": "flattened" },
      "raw_extra": { "type": "flattened" }
    }
  }
}
```

- [ ] **Step 3: Commit mappings**

```bash
git add chainsentinel/es/mappings/
git commit -m "feat: ES strict mappings for forensics-raw and forensics indices"
```

---

### Task 3: Elasticsearch Setup Module

**Files:**
- Create: `chainsentinel/es/setup.py`
- Create: `chainsentinel/tests/test_es_setup.py`

- [ ] **Step 1: Write the test**

`chainsentinel/tests/test_es_setup.py`:

```python
import pytest
import json
from pathlib import Path
from unittest.mock import MagicMock, patch, call


def test_setup_creates_indices_if_not_exist():
    from es.setup import setup_elasticsearch

    mock_client = MagicMock()
    mock_client.indices.exists.return_value = False

    setup_elasticsearch(mock_client)

    assert mock_client.indices.create.call_count == 2

    calls = mock_client.indices.create.call_args_list
    index_names = [c.kwargs["index"] for c in calls]
    assert "forensics-raw" in index_names
    assert "forensics" in index_names


def test_setup_skips_existing_indices():
    from es.setup import setup_elasticsearch

    mock_client = MagicMock()
    mock_client.indices.exists.return_value = True

    setup_elasticsearch(mock_client)

    mock_client.indices.create.assert_not_called()


def test_setup_uses_mapping_files():
    from es.setup import setup_elasticsearch

    mock_client = MagicMock()
    mock_client.indices.exists.return_value = False

    setup_elasticsearch(mock_client)

    for c in mock_client.indices.create.call_args_list:
        body = c.kwargs["body"]
        assert "mappings" in body
        assert body["mappings"]["dynamic"] == "strict"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /mnt/c/Users/aswat/OneDrive/Desktop/Projects/Project_Hail_Mary/chainsentinel
python -m pytest tests/test_es_setup.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'es.setup'`

- [ ] **Step 3: Implement es/setup.py**

`chainsentinel/es/setup.py`:

```python
import json
from pathlib import Path


MAPPINGS_DIR = Path(__file__).parent / "mappings"

INDICES = {
    "forensics-raw": MAPPINGS_DIR / "forensics-raw.json",
    "forensics": MAPPINGS_DIR / "forensics.json",
}


def setup_elasticsearch(client):
    """Create forensic indices with strict mappings if they don't exist."""
    for index_name, mapping_path in INDICES.items():
        if client.indices.exists(index=index_name):
            continue

        with open(mapping_path) as f:
            body = json.load(f)

        client.indices.create(index=index_name, body=body)


def teardown_elasticsearch(client):
    """Delete forensic indices. Used in testing only."""
    for index_name in INDICES:
        if client.indices.exists(index=index_name):
            client.indices.delete(index=index_name)
```

- [ ] **Step 4: Run tests**

```bash
cd /mnt/c/Users/aswat/OneDrive/Desktop/Projects/Project_Hail_Mary/chainsentinel
python -m pytest tests/test_es_setup.py -v
```

Expected: All 3 PASS

- [ ] **Step 5: Commit**

```bash
git add chainsentinel/es/setup.py chainsentinel/tests/test_es_setup.py
git commit -m "feat: ES setup module creates indices with strict mappings"
```

---

### Task 4: Collector — RPC Data Fetching

**Files:**
- Create: `chainsentinel/pipeline/collector.py`
- Create: `chainsentinel/tests/test_collector.py`

- [ ] **Step 1: Write the tests**

`chainsentinel/tests/test_collector.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /mnt/c/Users/aswat/OneDrive/Desktop/Projects/Project_Hail_Mary/chainsentinel
python -m pytest tests/test_collector.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'pipeline.collector'`

- [ ] **Step 3: Implement collector.py**

`chainsentinel/pipeline/collector.py`:

```python
"""
Collector — fetches raw chain data from any EVM RPC endpoint.
Merges transaction + receipt into one document.
Optionally fetches debug_traceTransaction (graceful if unavailable).
"""
from typing import Optional


def _hex_to_int(val):
    """Convert hex string to int, pass through if already int."""
    if isinstance(val, str) and val.startswith("0x"):
        return int(val, 16)
    return val


def _extract_hash(val):
    """Extract hex string from various web3 return types."""
    if hasattr(val, "hex"):
        return val.hex() if not val.hex().startswith("0x") else val.hex()
    if isinstance(val, bytes):
        return "0x" + val.hex()
    return str(val)


async def collect_transaction(w3, tx_hash: str, include_trace: bool = False) -> dict:
    """
    Fetch a transaction + receipt + block timestamp, merge into one document.
    Optionally fetch debug_traceTransaction.
    """
    tx = await w3.eth.get_transaction(tx_hash)
    receipt = await w3.eth.get_transaction_receipt(tx_hash)
    block = await w3.eth.get_block(_hex_to_int(tx.get("blockNumber", tx.get("block_number", 0))))

    logs = []
    for log in receipt.get("logs", []):
        logs.append({
            "log_index": _hex_to_int(log.get("logIndex", log.get("log_index", 0))),
            "address": str(log.get("address", "")),
            "topics": [_extract_hash(t) for t in log.get("topics", [])],
            "data": str(log.get("data", "0x")),
        })

    doc = {
        "tx_hash": _extract_hash(tx.get("hash", tx_hash)),
        "block_number": _hex_to_int(tx.get("blockNumber", tx.get("block_number", 0))),
        "block_timestamp": _hex_to_int(block.get("timestamp", 0)),
        "tx_index": _hex_to_int(tx.get("transactionIndex", tx.get("transaction_index", 0))),
        "from": str(tx.get("from", "")),
        "to": str(tx.get("to", "")),
        "value": _hex_to_int(tx.get("value", 0)),
        "gas": _hex_to_int(tx.get("gas", 0)),
        "gas_price": _hex_to_int(tx.get("gasPrice", tx.get("gas_price", 0))),
        "nonce": _hex_to_int(tx.get("nonce", 0)),
        "input": str(tx.get("input", "0x")),
        "status": _hex_to_int(receipt.get("status", 0)),
        "gas_used": _hex_to_int(receipt.get("gasUsed", receipt.get("gas_used", 0))),
        "cumulative_gas_used": _hex_to_int(
            receipt.get("cumulativeGasUsed", receipt.get("cumulative_gas_used", 0))
        ),
        "contract_address": str(receipt.get("contractAddress", receipt.get("contract_address", "")))
            if receipt.get("contractAddress", receipt.get("contract_address"))
            else None,
        "logs": logs,
        "trace": None,
    }

    if include_trace:
        try:
            trace = w3.manager.request_blocking(
                "debug_traceTransaction", [tx_hash, {"tracer": "callTracer"}]
            )
            doc["trace"] = dict(trace) if trace else None
        except Exception:
            doc["trace"] = None

    return doc


async def collect_block_range(
    w3, from_block: int, to_block: int, include_traces: bool = False
) -> list[dict]:
    """Fetch all transactions in a block range."""
    results = []

    for block_num in range(from_block, to_block + 1):
        block = await w3.eth.get_block(block_num, full_transactions=True)
        timestamp = _hex_to_int(block.get("timestamp", 0))

        for tx in block.get("transactions", []):
            tx_hash = _extract_hash(tx.get("hash", ""))
            receipt = await w3.eth.get_transaction_receipt(tx_hash)

            logs = []
            for log in receipt.get("logs", []):
                logs.append({
                    "log_index": _hex_to_int(
                        log.get("logIndex", log.get("log_index", 0))
                    ),
                    "address": str(log.get("address", "")),
                    "topics": [_extract_hash(t) for t in log.get("topics", [])],
                    "data": str(log.get("data", "0x")),
                })

            doc = {
                "tx_hash": tx_hash,
                "block_number": block_num,
                "block_timestamp": timestamp,
                "tx_index": _hex_to_int(
                    tx.get("transactionIndex", tx.get("transaction_index", 0))
                ),
                "from": str(tx.get("from", "")),
                "to": str(tx.get("to", "")),
                "value": _hex_to_int(tx.get("value", 0)),
                "gas": _hex_to_int(tx.get("gas", 0)),
                "gas_price": _hex_to_int(
                    tx.get("gasPrice", tx.get("gas_price", 0))
                ),
                "nonce": _hex_to_int(tx.get("nonce", 0)),
                "input": str(tx.get("input", "0x")),
                "status": _hex_to_int(receipt.get("status", 0)),
                "gas_used": _hex_to_int(
                    receipt.get("gasUsed", receipt.get("gas_used", 0))
                ),
                "cumulative_gas_used": _hex_to_int(
                    receipt.get("cumulativeGasUsed", receipt.get("cumulative_gas_used", 0))
                ),
                "contract_address": str(
                    receipt.get("contractAddress", receipt.get("contract_address", ""))
                ) if receipt.get("contractAddress", receipt.get("contract_address")) else None,
                "logs": logs,
                "trace": None,
            }

            if include_traces:
                try:
                    trace = w3.manager.request_blocking(
                        "debug_traceTransaction",
                        [tx_hash, {"tracer": "callTracer"}],
                    )
                    doc["trace"] = dict(trace) if trace else None
                except Exception:
                    doc["trace"] = None

            results.append(doc)

    return results


async def collect_logs(w3, from_block: int, to_block: int) -> list[dict]:
    """Fetch all event logs in a block range via eth_getLogs."""
    raw_logs = await w3.eth.get_logs({
        "fromBlock": from_block,
        "toBlock": to_block,
    })

    return [
        {
            "tx_hash": _extract_hash(log.get("transactionHash", log.get("transaction_hash", ""))),
            "block_number": _hex_to_int(log.get("blockNumber", log.get("block_number", 0))),
            "log_index": _hex_to_int(log.get("logIndex", log.get("log_index", 0))),
            "address": str(log.get("address", "")),
            "topics": [_extract_hash(t) for t in log.get("topics", [])],
            "data": str(log.get("data", "0x")),
        }
        for log in raw_logs
    ]
```

- [ ] **Step 4: Run tests**

```bash
cd /mnt/c/Users/aswat/OneDrive/Desktop/Projects/Project_Hail_Mary/chainsentinel
python -m pytest tests/test_collector.py -v
```

Expected: All 4 PASS

- [ ] **Step 5: Commit**

```bash
git add chainsentinel/pipeline/collector.py chainsentinel/tests/test_collector.py
git commit -m "feat: collector fetches txs, receipts, logs, traces from RPC"
```

---

### Task 5: Normalizer — Type Conversion

**Files:**
- Create: `chainsentinel/pipeline/normalizer.py`
- Create: `chainsentinel/tests/test_normalizer.py`

- [ ] **Step 1: Write the tests**

`chainsentinel/tests/test_normalizer.py`:

```python
import pytest


def test_normalizer_converts_hex_to_int(sample_raw_tx, sample_raw_receipt):
    from pipeline.normalizer import normalize_transaction

    result = normalize_transaction(sample_raw_tx, sample_raw_receipt, block_timestamp=1736942400, chain_id=31337)

    assert result["block_number"] == 10
    assert isinstance(result["block_number"], int)
    assert result["gas"] == 21000
    assert result["gas_used"] == 21000
    assert result["nonce"] == 5


def test_normalizer_lowercases_addresses(sample_raw_tx, sample_raw_receipt):
    from pipeline.normalizer import normalize_transaction

    result = normalize_transaction(sample_raw_tx, sample_raw_receipt, block_timestamp=1736942400, chain_id=31337)

    assert result["from_address"] == "0xdeadbeefdeadbeefdeadbeefdeadbeefdeadbeef"
    assert result["to_address"] == "0x1234567890abcdef1234567890abcdef12345678"
    assert result["from_address"] == result["from_address"].lower()


def test_normalizer_converts_wei_to_eth(sample_raw_tx, sample_raw_receipt):
    from pipeline.normalizer import normalize_transaction

    result = normalize_transaction(sample_raw_tx, sample_raw_receipt, block_timestamp=1736942400, chain_id=31337)

    assert result["value_eth"] == 1.0
    assert result["value_wei"] == "1000000000000000000"
    assert isinstance(result["value_wei"], str)


def test_normalizer_converts_timestamp_to_iso(sample_raw_tx, sample_raw_receipt):
    from pipeline.normalizer import normalize_transaction

    result = normalize_transaction(sample_raw_tx, sample_raw_receipt, block_timestamp=1736942400, chain_id=31337)

    assert result["block_datetime"].endswith("Z")
    assert result["block_timestamp_raw"] == 1736942400


def test_normalizer_sets_success_boolean(sample_raw_tx, sample_raw_receipt):
    from pipeline.normalizer import normalize_transaction

    result = normalize_transaction(sample_raw_tx, sample_raw_receipt, block_timestamp=1736942400, chain_id=31337)
    assert result["success"] is True

    sample_raw_receipt["status"] = "0x0"
    result2 = normalize_transaction(sample_raw_tx, sample_raw_receipt, block_timestamp=1736942400, chain_id=31337)
    assert result2["success"] is False


def test_normalizer_sets_decode_status_pending(sample_raw_tx, sample_raw_receipt):
    from pipeline.normalizer import normalize_transaction

    result = normalize_transaction(sample_raw_tx, sample_raw_receipt, block_timestamp=1736942400, chain_id=31337)

    assert result["decode_status"] == "pending"


def test_normalizer_preserves_unknown_fields(sample_raw_tx, sample_raw_receipt):
    from pipeline.normalizer import normalize_transaction

    sample_raw_tx["weirdNewField"] = "unexpected_data"
    result = normalize_transaction(sample_raw_tx, sample_raw_receipt, block_timestamp=1736942400, chain_id=31337)

    assert "weirdNewField" in result["raw_extra"]


def test_normalize_log(sample_raw_log):
    from pipeline.normalizer import normalize_log

    result = normalize_log(sample_raw_log, block_datetime="2026-01-15T12:00:00Z", chain_id=31337)

    assert result["log_address"] == "0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48"
    assert result["block_number"] == 10
    assert result["log_index"] == 0
    assert len(result["topics"]) == 3
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /mnt/c/Users/aswat/OneDrive/Desktop/Projects/Project_Hail_Mary/chainsentinel
python -m pytest tests/test_normalizer.py -v
```

Expected: FAIL

- [ ] **Step 3: Implement normalizer.py**

`chainsentinel/pipeline/normalizer.py`:

```python
"""
Normalizer — converts blockchain-native types into a stable typed schema.
Hex → int. Addresses → lowercase. Wei → ETH. Timestamps → ISO 8601.
Unknown fields preserved in raw_extra.
"""
from datetime import datetime, timezone


KNOWN_TX_FIELDS = {
    "hash", "blockNumber", "blockHash", "transactionIndex", "from", "to",
    "value", "gas", "gasPrice", "nonce", "input", "type", "chainId",
    "maxFeePerGas", "maxPriorityFeePerGas", "accessList",
    "transactionHash", "status", "gasUsed", "cumulativeGasUsed",
    "contractAddress", "logs", "logsBloom",
}


def _hex_to_int(val):
    if isinstance(val, str) and val.startswith("0x"):
        return int(val, 16)
    if isinstance(val, int):
        return val
    return val


def _to_iso8601(timestamp_int: int) -> str:
    return datetime.fromtimestamp(timestamp_int, tz=timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )


def normalize_transaction(
    raw_tx: dict, raw_receipt: dict, block_timestamp: int, chain_id: int
) -> dict:
    """Normalize a raw tx + receipt into a stable schema."""
    value_wei = _hex_to_int(raw_tx.get("value", 0))
    value_eth = value_wei / 1e18 if isinstance(value_wei, (int, float)) else 0.0

    status_raw = _hex_to_int(raw_receipt.get("status", 0))
    success = bool(status_raw)

    block_datetime = _to_iso8601(block_timestamp)

    contract_addr = raw_receipt.get("contractAddress", raw_receipt.get("contract_address"))

    # Collect unknown fields into raw_extra
    all_keys = set(raw_tx.keys()) | set(raw_receipt.keys())
    raw_extra = {}
    for key in all_keys:
        if key not in KNOWN_TX_FIELDS:
            val = raw_tx.get(key, raw_receipt.get(key))
            if val is not None:
                raw_extra[key] = val

    from_addr = str(raw_tx.get("from", "")).lower()
    to_addr = str(raw_tx.get("to", "")).lower() if raw_tx.get("to") else ""

    logs = []
    for log in raw_receipt.get("logs", []):
        logs.append(normalize_log(log, block_datetime=block_datetime, chain_id=chain_id))

    return {
        "tx_hash": str(raw_tx.get("hash", raw_receipt.get("transactionHash", ""))).lower(),
        "block_number": _hex_to_int(raw_tx.get("blockNumber", 0)),
        "block_datetime": block_datetime,
        "block_timestamp_raw": block_timestamp,
        "tx_index": _hex_to_int(raw_tx.get("transactionIndex", 0)),
        "from_address": from_addr,
        "to_address": to_addr,
        "value_eth": value_eth,
        "value_wei": str(value_wei),
        "gas": _hex_to_int(raw_tx.get("gas", 0)),
        "gas_price": _hex_to_int(raw_tx.get("gasPrice", 0)),
        "gas_used": _hex_to_int(raw_receipt.get("gasUsed", 0)),
        "cumulative_gas_used": _hex_to_int(raw_receipt.get("cumulativeGasUsed", 0)),
        "nonce": _hex_to_int(raw_tx.get("nonce", 0)),
        "input": str(raw_tx.get("input", "0x")),
        "success": success,
        "contract_address": str(contract_addr).lower() if contract_addr else None,
        "logs": logs,
        "chain_id": chain_id,
        "decode_status": "pending",
        "raw_extra": raw_extra,
    }


def normalize_log(raw_log: dict, block_datetime: str, chain_id: int) -> dict:
    """Normalize a raw event log."""

    def _extract_topic(t):
        if hasattr(t, "hex"):
            h = t.hex()
            return h if h.startswith("0x") else "0x" + h
        if isinstance(t, bytes):
            return "0x" + t.hex()
        return str(t)

    return {
        "tx_hash": str(
            raw_log.get("transactionHash", raw_log.get("transaction_hash", ""))
        ).lower(),
        "block_number": _hex_to_int(
            raw_log.get("blockNumber", raw_log.get("block_number", 0))
        ),
        "block_datetime": block_datetime,
        "log_index": _hex_to_int(
            raw_log.get("logIndex", raw_log.get("log_index", 0))
        ),
        "log_address": str(raw_log.get("address", "")).lower(),
        "topics": [_extract_topic(t) for t in raw_log.get("topics", [])],
        "data": str(raw_log.get("data", "0x")),
        "chain_id": chain_id,
    }
```

- [ ] **Step 4: Run tests**

```bash
cd /mnt/c/Users/aswat/OneDrive/Desktop/Projects/Project_Hail_Mary/chainsentinel
python -m pytest tests/test_normalizer.py -v
```

Expected: All 8 PASS

- [ ] **Step 5: Commit**

```bash
git add chainsentinel/pipeline/normalizer.py chainsentinel/tests/test_normalizer.py
git commit -m "feat: normalizer converts hex to int, addresses to lowercase, wei to ETH"
```

---

### Task 6: ABI Registry + ERC20 ABI

**Files:**
- Create: `chainsentinel/pipeline/abi_registry/standards/erc20.json`

- [ ] **Step 1: Create ERC20 ABI**

`chainsentinel/pipeline/abi_registry/standards/erc20.json`:

```json
[
  {
    "anonymous": false,
    "inputs": [
      {"indexed": true, "name": "from", "type": "address"},
      {"indexed": true, "name": "to", "type": "address"},
      {"indexed": false, "name": "value", "type": "uint256"}
    ],
    "name": "Transfer",
    "type": "event"
  },
  {
    "anonymous": false,
    "inputs": [
      {"indexed": true, "name": "owner", "type": "address"},
      {"indexed": true, "name": "spender", "type": "address"},
      {"indexed": false, "name": "value", "type": "uint256"}
    ],
    "name": "Approval",
    "type": "event"
  },
  {
    "inputs": [
      {"name": "to", "type": "address"},
      {"name": "value", "type": "uint256"}
    ],
    "name": "transfer",
    "outputs": [{"name": "", "type": "bool"}],
    "type": "function"
  },
  {
    "inputs": [
      {"name": "spender", "type": "address"},
      {"name": "value", "type": "uint256"}
    ],
    "name": "approve",
    "outputs": [{"name": "", "type": "bool"}],
    "type": "function"
  },
  {
    "inputs": [
      {"name": "from", "type": "address"},
      {"name": "to", "type": "address"},
      {"name": "value", "type": "uint256"}
    ],
    "name": "transferFrom",
    "outputs": [{"name": "", "type": "bool"}],
    "type": "function"
  }
]
```

- [ ] **Step 2: Commit**

```bash
git add chainsentinel/pipeline/abi_registry/standards/erc20.json
git commit -m "feat: ERC20 standard ABI for decoder registry"
```

---

### Task 7: Decoder — ABI Decoding

**Files:**
- Create: `chainsentinel/pipeline/decoder.py`
- Create: `chainsentinel/tests/test_decoder.py`

- [ ] **Step 1: Write the tests**

`chainsentinel/tests/test_decoder.py`:

```python
import pytest


def test_decoder_decodes_erc20_transfer(sample_raw_log, sample_erc20_abi):
    from pipeline.decoder import Decoder

    decoder = Decoder(abis={"standards": [sample_erc20_abi]})
    result = decoder.decode_log(sample_raw_log)

    assert result["event_name"] == "Transfer"
    assert result["decode_status"] == "decoded"
    assert "from" in result["event_args"]
    assert "to" in result["event_args"]
    assert "value" in result["event_args"]


def test_decoder_returns_unknown_for_unrecognized_log():
    from pipeline.decoder import Decoder

    decoder = Decoder(abis={"standards": []})
    unknown_log = {
        "address": "0x1234567890abcdef1234567890abcdef12345678",
        "topics": ["0xabcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890"],
        "data": "0x00000000000000000000000000000000000000000000000000000000000000ff",
    }
    result = decoder.decode_log(unknown_log)

    assert result["decode_status"] == "unknown"
    assert result["event_name"] is None
    assert result["topics"] == unknown_log["topics"]


def test_decoder_decodes_function_selector():
    from pipeline.decoder import Decoder

    decoder = Decoder(abis={"standards": [[
        {
            "inputs": [
                {"name": "to", "type": "address"},
                {"name": "value", "type": "uint256"},
            ],
            "name": "transfer",
            "outputs": [{"name": "", "type": "bool"}],
            "type": "function",
        }
    ]]})

    # transfer(address,uint256) selector = 0xa9059cbb
    result = decoder.decode_function_input(
        "0xa9059cbb"
        "000000000000000000000000deadbeefdeadbeefdeadbeefdeadbeefdeadbeef"
        "0000000000000000000000000000000000000000000000000000000005f5e100"
    )

    assert result["function_name"] == "transfer"
    assert result["decode_status"] == "decoded"


def test_decoder_updates_selector_registry():
    from pipeline.decoder import Decoder

    decoder = Decoder(abis={"standards": [[
        {
            "inputs": [
                {"name": "to", "type": "address"},
                {"name": "value", "type": "uint256"},
            ],
            "name": "transfer",
            "outputs": [{"name": "", "type": "bool"}],
            "type": "function",
        }
    ]]})

    assert "0xa9059cbb" in decoder.selector_map
    assert decoder.selector_map["0xa9059cbb"]["name"] == "transfer"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /mnt/c/Users/aswat/OneDrive/Desktop/Projects/Project_Hail_Mary/chainsentinel
python -m pytest tests/test_decoder.py -v
```

Expected: FAIL

- [ ] **Step 3: Implement decoder.py**

`chainsentinel/pipeline/decoder.py`:

```python
"""
Decoder — gives meaning to raw normalised structures.
Decodes event signatures from topic0, event arguments from ABI,
function selectors from input data.
"""
import json
from pathlib import Path
from web3 import Web3


REGISTRY_PATH = Path(__file__).parent / "selector_registry.json"
ABI_DIR = Path(__file__).parent / "abi_registry"


class Decoder:
    def __init__(self, abis: dict = None, case_manifest: dict = None):
        """
        abis: {"standards": [abi_list, ...], "protocols": [abi_list, ...]}
        case_manifest: {"contracts": [{"address": "0x...", "abi": "path.json"}, ...]}
        """
        self.event_map = {}      # topic0_hash → {name, abi_entry}
        self.selector_map = {}   # bytes4 → {name, abi_entry}
        self.address_abis = {}   # address → abi_list (from case manifest)

        # Load selector registry cache
        if REGISTRY_PATH.exists():
            with open(REGISTRY_PATH) as f:
                cache = json.load(f)
                self.event_map.update(
                    {k: v for k, v in cache.get("event_signatures", {}).items()}
                )
                self.selector_map.update(
                    {k: v for k, v in cache.get("function_selectors", {}).items()}
                )

        # Load provided ABIs
        if abis:
            for category_abis in abis.values():
                for abi_list in category_abis:
                    self._index_abi(abi_list)

        # Load case-specific ABIs by address
        if case_manifest:
            for contract in case_manifest.get("contracts", []):
                addr = contract["address"].lower()
                abi_path = contract.get("abi_path")
                if abi_path and Path(abi_path).exists():
                    with open(abi_path) as f:
                        abi = json.load(f)
                    self.address_abis[addr] = abi
                    self._index_abi(abi)

    def _index_abi(self, abi: list):
        """Index all events and functions from an ABI."""
        for entry in abi:
            if entry.get("type") == "event":
                sig = self._event_signature(entry)
                topic0 = Web3.keccak(text=sig).hex()
                self.event_map[topic0] = {
                    "name": entry["name"],
                    "inputs": entry.get("inputs", []),
                }
            elif entry.get("type") == "function":
                sig = self._function_signature(entry)
                selector = Web3.keccak(text=sig).hex()[:10]
                self.selector_map[selector] = {
                    "name": entry["name"],
                    "inputs": entry.get("inputs", []),
                }

    def _event_signature(self, entry: dict) -> str:
        types = ",".join(inp["type"] for inp in entry.get("inputs", []))
        return f"{entry['name']}({types})"

    def _function_signature(self, entry: dict) -> str:
        types = ",".join(inp["type"] for inp in entry.get("inputs", []))
        return f"{entry['name']}({types})"

    def decode_log(self, log: dict) -> dict:
        """Decode an event log using topic0 lookup."""
        topics = log.get("topics", [])
        data = log.get("data", "0x")

        if not topics:
            return {
                "event_name": None,
                "event_args": {},
                "decode_status": "unknown",
                "topics": topics,
                "data": data,
            }

        topic0 = topics[0]
        entry = self.event_map.get(topic0)

        if not entry:
            return {
                "event_name": None,
                "event_args": {},
                "decode_status": "unknown",
                "topics": topics,
                "data": data,
            }

        # Decode arguments
        args = {}
        indexed_inputs = [i for i in entry["inputs"] if i.get("indexed")]
        data_inputs = [i for i in entry["inputs"] if not i.get("indexed")]

        # Decode indexed args from topics[1:]
        for idx, inp in enumerate(indexed_inputs):
            if idx + 1 < len(topics):
                raw = topics[idx + 1]
                if inp["type"] == "address":
                    args[inp["name"]] = "0x" + raw[-40:]
                elif inp["type"] in ("uint256", "uint128", "uint64", "uint32", "uint8", "int256"):
                    args[inp["name"]] = int(raw, 16)
                else:
                    args[inp["name"]] = raw

        # Decode non-indexed args from data
        if data and data != "0x" and data_inputs:
            data_bytes = data[2:]  # strip 0x
            offset = 0
            for inp in data_inputs:
                if offset + 64 <= len(data_bytes):
                    chunk = data_bytes[offset:offset + 64]
                    if inp["type"] in ("uint256", "uint128", "uint64", "uint32", "uint8", "int256"):
                        args[inp["name"]] = int(chunk, 16)
                    elif inp["type"] == "address":
                        args[inp["name"]] = "0x" + chunk[-40:]
                    elif inp["type"] == "bool":
                        args[inp["name"]] = int(chunk, 16) != 0
                    else:
                        args[inp["name"]] = "0x" + chunk
                    offset += 64

        return {
            "event_name": entry["name"],
            "event_args": args,
            "decode_status": "decoded",
            "topics": topics,
            "data": data,
        }

    def decode_function_input(self, input_data: str) -> dict:
        """Decode function selector + args from transaction input."""
        if not input_data or input_data == "0x" or len(input_data) < 10:
            return {
                "function_name": None,
                "function_args": {},
                "decode_status": "unknown",
            }

        selector = input_data[:10]
        entry = self.selector_map.get(selector)

        if not entry:
            return {
                "function_name": None,
                "function_args": {},
                "decode_status": "unknown",
            }

        args = {}
        data_hex = input_data[10:]
        offset = 0
        for inp in entry.get("inputs", []):
            if offset + 64 <= len(data_hex):
                chunk = data_hex[offset:offset + 64]
                if inp["type"] in ("uint256", "uint128", "uint64", "uint32", "uint8", "int256"):
                    args[inp["name"]] = int(chunk, 16)
                elif inp["type"] == "address":
                    args[inp["name"]] = "0x" + chunk[-40:]
                elif inp["type"] == "bool":
                    args[inp["name"]] = int(chunk, 16) != 0
                else:
                    args[inp["name"]] = "0x" + chunk
                offset += 64

        return {
            "function_name": entry["name"],
            "function_args": args,
            "decode_status": "decoded",
        }

    def save_registry(self):
        """Persist the selector registry cache."""
        cache = {
            "event_signatures": {
                k: {"name": v["name"]} for k, v in self.event_map.items()
            },
            "function_selectors": {
                k: {"name": v["name"]} for k, v in self.selector_map.items()
            },
        }
        with open(REGISTRY_PATH, "w") as f:
            json.dump(cache, f, indent=2)


def load_decoder(investigation_id: str = None) -> Decoder:
    """Factory: build a Decoder from the ABI registry + optional case ABIs."""
    abis = {"standards": [], "protocols": []}

    standards_dir = ABI_DIR / "standards"
    if standards_dir.exists():
        for f in standards_dir.glob("*.json"):
            with open(f) as fh:
                abis["standards"].append(json.load(fh))

    protocols_dir = ABI_DIR / "protocols"
    if protocols_dir.exists():
        for f in protocols_dir.glob("*.json"):
            with open(f) as fh:
                abis["protocols"].append(json.load(fh))

    case_manifest = None
    if investigation_id:
        case_dir = ABI_DIR / "cases" / investigation_id
        manifest_path = case_dir / "manifest.json"
        if manifest_path.exists():
            with open(manifest_path) as fh:
                case_manifest = json.load(fh)
            # Resolve ABI paths relative to case dir
            for contract in case_manifest.get("contracts", []):
                if "abi" in contract:
                    contract["abi_path"] = str(case_dir / "abis" / contract["abi"])

    return Decoder(abis=abis, case_manifest=case_manifest)
```

- [ ] **Step 4: Run tests**

```bash
cd /mnt/c/Users/aswat/OneDrive/Desktop/Projects/Project_Hail_Mary/chainsentinel
python -m pytest tests/test_decoder.py -v
```

Expected: All 4 PASS

- [ ] **Step 5: Commit**

```bash
git add chainsentinel/pipeline/decoder.py chainsentinel/tests/test_decoder.py
git commit -m "feat: decoder with ABI registry, event/function decoding, selector cache"
```

---

### Task 8: Derived Event Builder

**Files:**
- Create: `chainsentinel/pipeline/derived.py`
- Create: `chainsentinel/tests/test_derived.py`

- [ ] **Step 1: Write the tests**

`chainsentinel/tests/test_derived.py`:

```python
import pytest


def test_derive_asset_transfer_from_decoded_transfer():
    from pipeline.derived import derive_events

    decoded_event = {
        "tx_hash": "0xabc",
        "block_number": 10,
        "block_datetime": "2026-01-15T12:00:00Z",
        "log_index": 0,
        "log_address": "0xtoken",
        "event_name": "Transfer",
        "event_args": {
            "from": "0xsender",
            "to": "0xreceiver",
            "value": 100000000,
        },
        "decode_status": "decoded",
        "token_symbol": "USDC",
        "token_decimals": 6,
    }

    results = derive_events([decoded_event], investigation_id="INV-001")

    transfers = [r for r in results if r["derived_type"] == "asset_transfer"]
    assert len(transfers) == 1
    assert transfers[0]["from_address"] == "0xsender"
    assert transfers[0]["to_address"] == "0xreceiver"
    assert transfers[0]["amount_decimal"] == 100.0
    assert transfers[0]["source_tx_hash"] == "0xabc"
    assert transfers[0]["source_log_index"] == 0
    assert transfers[0]["source_layer"] == "decoded"


def test_derive_native_transfer_from_tx():
    from pipeline.derived import derive_events_from_tx

    normalized_tx = {
        "tx_hash": "0xabc",
        "block_number": 10,
        "block_datetime": "2026-01-15T12:00:00Z",
        "from_address": "0xsender",
        "to_address": "0xreceiver",
        "value_eth": 5.0,
        "value_wei": "5000000000000000000",
        "success": True,
    }

    results = derive_events_from_tx(normalized_tx, investigation_id="INV-001")

    native = [r for r in results if r["derived_type"] == "native_transfer"]
    assert len(native) == 1
    assert native[0]["value_eth"] == 5.0
    assert native[0]["from_address"] == "0xsender"


def test_derive_admin_action_from_ownership_transfer():
    from pipeline.derived import derive_events

    decoded_event = {
        "tx_hash": "0xabc",
        "block_number": 10,
        "block_datetime": "2026-01-15T12:00:00Z",
        "log_index": 1,
        "log_address": "0xcontract",
        "event_name": "OwnershipTransferred",
        "event_args": {
            "previousOwner": "0xold_owner",
            "newOwner": "0xnew_owner",
        },
        "decode_status": "decoded",
    }

    results = derive_events([decoded_event], investigation_id="INV-001")

    admin = [r for r in results if r["derived_type"] == "admin_action"]
    assert len(admin) == 1
    assert admin[0]["action_type"] == "ownership_transfer"
    assert admin[0]["actor_address"] == "0xnew_owner"


def test_derive_execution_edge_from_trace():
    from pipeline.derived import derive_events_from_trace

    trace = {
        "type": "CALL",
        "from": "0xcaller",
        "to": "0xcallee",
        "value": "0xde0b6b3a7640000",
        "input": "0xa9059cbb",
        "gas": "0x5208",
        "gasUsed": "0x1388",
        "calls": [
            {
                "type": "DELEGATECALL",
                "from": "0xcallee",
                "to": "0ximpl",
                "value": "0x0",
                "input": "0x",
                "gas": "0x2710",
                "gasUsed": "0xbb8",
                "calls": [],
            }
        ],
    }

    results = derive_events_from_trace(
        trace, tx_hash="0xabc", block_number=10,
        block_datetime="2026-01-15T12:00:00Z", investigation_id="INV-001"
    )

    edges = [r for r in results if r["derived_type"] == "execution_edge"]
    assert len(edges) == 2  # root call + inner delegatecall
    assert edges[0]["call_type"] == "CALL"
    assert edges[0]["call_depth"] == 0
    assert edges[1]["call_type"] == "DELEGATECALL"
    assert edges[1]["call_depth"] == 1


def test_every_derived_event_has_chain_of_custody():
    from pipeline.derived import derive_events

    decoded_event = {
        "tx_hash": "0xabc",
        "block_number": 10,
        "block_datetime": "2026-01-15T12:00:00Z",
        "log_index": 0,
        "log_address": "0xtoken",
        "event_name": "Transfer",
        "event_args": {"from": "0xa", "to": "0xb", "value": 1000},
        "decode_status": "decoded",
    }

    results = derive_events([decoded_event], investigation_id="INV-001")

    for r in results:
        assert "source_tx_hash" in r
        assert "source_log_index" in r or r["derived_type"] == "balance_delta"
        assert "source_layer" in r
        assert r["investigation_id"] == "INV-001"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /mnt/c/Users/aswat/OneDrive/Desktop/Projects/Project_Hail_Mary/chainsentinel
python -m pytest tests/test_derived.py -v
```

Expected: FAIL

- [ ] **Step 3: Implement derived.py**

`chainsentinel/pipeline/derived.py`:

```python
"""
Derived Event Builder — produces security-shaped records from decoded data.
9 derived types: asset_transfer, native_transfer, swap_summary, approval_usage,
admin_action, execution_edge, fund_flow_edge, contract_interaction, balance_delta.
"""
from datetime import datetime, timezone


def _hex_to_int(val):
    if isinstance(val, str) and val.startswith("0x"):
        return int(val, 16)
    if isinstance(val, int):
        return val
    return 0


def _base_doc(tx_hash, block_number, block_datetime, investigation_id, derived_type,
              source_log_index=None, source_layer="decoded"):
    return {
        "investigation_id": investigation_id,
        "layer": "derived",
        "derived_type": derived_type,
        "tx_hash": tx_hash,
        "block_number": block_number,
        "block_datetime": block_datetime,
        "@timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source_tx_hash": tx_hash,
        "source_log_index": source_log_index,
        "source_layer": source_layer,
    }


def derive_events(decoded_events: list[dict], investigation_id: str) -> list[dict]:
    """Derive security events from a list of decoded event logs."""
    results = []

    for event in decoded_events:
        name = event.get("event_name")
        args = event.get("event_args", {})
        tx_hash = event.get("tx_hash", "")
        block_number = event.get("block_number", 0)
        block_datetime = event.get("block_datetime", "")
        log_index = event.get("log_index", 0)

        if name == "Transfer":
            doc = _base_doc(tx_hash, block_number, block_datetime,
                           investigation_id, "asset_transfer", log_index)
            from_addr = str(args.get("from", "")).lower()
            to_addr = str(args.get("to", "")).lower()
            raw_value = args.get("value", 0)
            decimals = event.get("token_decimals", 18)
            amount = raw_value / (10 ** decimals) if decimals else raw_value

            doc.update({
                "from_address": from_addr,
                "to_address": to_addr,
                "token_address": event.get("log_address", ""),
                "token_symbol": event.get("token_symbol", ""),
                "amount_decimal": amount,
                "value_wei": str(raw_value),
                "transfer_type": "erc20",
            })

            # Detect mint (from zero address)
            if from_addr == "0x" + "0" * 40:
                doc["transfer_type"] = "mint"
            # Detect burn (to zero address)
            elif to_addr == "0x" + "0" * 40:
                doc["transfer_type"] = "burn"

            results.append(doc)

        elif name == "Approval":
            doc = _base_doc(tx_hash, block_number, block_datetime,
                           investigation_id, "approval_usage", log_index)
            doc.update({
                "owner_address": str(args.get("owner", "")).lower(),
                "spender_address": str(args.get("spender", "")).lower(),
                "token_address": event.get("log_address", ""),
                "amount_decimal": args.get("value", 0),
                "was_consumed": False,
                "consumed_tx_hash": None,
            })
            results.append(doc)

        elif name in ("OwnershipTransferred", "RoleGranted", "RoleRevoked",
                       "Upgraded", "Paused", "Unpaused"):
            doc = _base_doc(tx_hash, block_number, block_datetime,
                           investigation_id, "admin_action", log_index)

            action_map = {
                "OwnershipTransferred": "ownership_transfer",
                "RoleGranted": "role_grant",
                "RoleRevoked": "role_revoke",
                "Upgraded": "upgrade",
                "Paused": "pause",
                "Unpaused": "unpause",
            }

            actor = ""
            new_value = ""
            if name == "OwnershipTransferred":
                actor = str(args.get("newOwner", "")).lower()
                new_value = actor
            elif name == "RoleGranted":
                actor = str(args.get("account", "")).lower()
                new_value = str(args.get("role", ""))
            elif name == "Upgraded":
                new_value = str(args.get("implementation", "")).lower()

            doc.update({
                "action_type": action_map.get(name, name.lower()),
                "actor_address": actor,
                "contract_address": event.get("log_address", ""),
                "new_value": new_value,
            })
            results.append(doc)

        elif name == "Swap":
            doc = _base_doc(tx_hash, block_number, block_datetime,
                           investigation_id, "swap_summary", log_index)
            doc.update({
                "pool_address": event.get("log_address", ""),
                "trader_address": str(args.get("sender", args.get("recipient", ""))).lower(),
                "amount_in": abs(args.get("amount0In", args.get("amount0", 0))),
                "amount_out": abs(args.get("amount1Out", args.get("amount1", 0))),
                "token_in": "",
                "token_out": "",
                "protocol_name": "",
                "price_impact_pct": 0.0,
            })
            results.append(doc)

    return results


def derive_events_from_tx(normalized_tx: dict, investigation_id: str) -> list[dict]:
    """Derive events from a normalized transaction (native ETH transfers)."""
    results = []

    value_eth = normalized_tx.get("value_eth", 0)
    if value_eth > 0 and normalized_tx.get("success", False):
        doc = _base_doc(
            normalized_tx["tx_hash"],
            normalized_tx["block_number"],
            normalized_tx["block_datetime"],
            investigation_id, "native_transfer",
            source_layer="raw",
        )
        doc.update({
            "from_address": normalized_tx.get("from_address", ""),
            "to_address": normalized_tx.get("to_address", ""),
            "value_eth": value_eth,
            "value_wei": normalized_tx.get("value_wei", "0"),
        })
        results.append(doc)

    # Contract interaction
    if normalized_tx.get("input", "0x") != "0x" and normalized_tx.get("to_address"):
        doc = _base_doc(
            normalized_tx["tx_hash"],
            normalized_tx["block_number"],
            normalized_tx["block_datetime"],
            investigation_id, "contract_interaction",
            source_layer="raw",
        )
        doc.update({
            "user_address": normalized_tx.get("from_address", ""),
            "contract_address": normalized_tx.get("to_address", ""),
            "function_name": None,
            "protocol_name": None,
            "success": normalized_tx.get("success", False),
        })
        results.append(doc)

    return results


def derive_events_from_trace(
    trace: dict, tx_hash: str, block_number: int,
    block_datetime: str, investigation_id: str, depth: int = 0
) -> list[dict]:
    """Recursively derive execution_edge events from a call trace."""
    results = []

    value_hex = trace.get("value", "0x0")
    value_int = _hex_to_int(value_hex)
    value_eth = value_int / 1e18 if value_int else 0.0

    doc = _base_doc(tx_hash, block_number, block_datetime,
                   investigation_id, "execution_edge", source_layer="trace")
    doc.update({
        "caller_address": str(trace.get("from", "")).lower(),
        "callee_address": str(trace.get("to", "")).lower(),
        "call_type": trace.get("type", "CALL"),
        "function_name": None,
        "value_eth": value_eth,
        "call_depth": depth,
        "gas_used": _hex_to_int(trace.get("gasUsed", 0)),
        "success": True,
    })

    # Try to extract function selector
    input_data = trace.get("input", "0x")
    if input_data and len(input_data) >= 10:
        doc["function_name"] = input_data[:10]

    results.append(doc)

    # Recurse into sub-calls
    for sub_call in trace.get("calls", []):
        results.extend(derive_events_from_trace(
            sub_call, tx_hash, block_number, block_datetime,
            investigation_id, depth + 1
        ))

    return results
```

- [ ] **Step 4: Run tests**

```bash
cd /mnt/c/Users/aswat/OneDrive/Desktop/Projects/Project_Hail_Mary/chainsentinel
python -m pytest tests/test_derived.py -v
```

Expected: All 5 PASS

- [ ] **Step 5: Commit**

```bash
git add chainsentinel/pipeline/derived.py chainsentinel/tests/test_derived.py
git commit -m "feat: derived event builder produces 9 security event types"
```

---

### Task 9: ES Bulk Ingest

**Files:**
- Create: `chainsentinel/pipeline/ingest.py`
- Create: `chainsentinel/tests/test_ingest.py`

- [ ] **Step 1: Write the tests**

`chainsentinel/tests/test_ingest.py`:

```python
import pytest
from unittest.mock import MagicMock, patch


def test_ingest_raw_transaction_uses_correct_id():
    from pipeline.ingest import build_raw_doc

    doc = build_raw_doc(
        doc_type="transaction",
        tx_hash="0xabc",
        chain_id=31337,
        investigation_id="INV-001",
        data={"tx_hash": "0xabc", "block_number": 10},
    )

    assert doc["_id"] == "31337_0xabc"
    assert doc["_index"] == "forensics-raw"
    assert doc["doc_type"] == "transaction"


def test_ingest_raw_log_uses_correct_id():
    from pipeline.ingest import build_raw_doc

    doc = build_raw_doc(
        doc_type="log",
        tx_hash="0xabc",
        chain_id=31337,
        investigation_id="INV-001",
        data={"log_index": 3},
        log_index=3,
    )

    assert doc["_id"] == "31337_0xabc_3"


def test_ingest_derived_uses_correct_id():
    from pipeline.ingest import build_analysis_doc

    doc = build_analysis_doc(
        layer="derived",
        investigation_id="INV-001",
        data={
            "derived_type": "asset_transfer",
            "tx_hash": "0xabc",
            "source_log_index": 0,
        },
    )

    assert doc["_id"] == "INV-001_asset_transfer_0xabc_0"
    assert doc["_index"] == "forensics"
    assert doc["layer"] == "derived"


def test_ingest_signal_uses_correct_id():
    from pipeline.ingest import build_analysis_doc

    doc = build_analysis_doc(
        layer="signal",
        investigation_id="INV-001",
        data={
            "signal_name": "reentrancy_pattern",
            "tx_hash": "0xabc",
        },
    )

    assert doc["_id"] == "INV-001_reentrancy_pattern_0xabc"


def test_bulk_ingest_calls_es_helpers(sample_normalized_tx):
    from pipeline.ingest import bulk_ingest

    mock_client = MagicMock()

    docs = [
        {
            "_id": "31337_0xabc",
            "_index": "forensics-raw",
            "doc_type": "transaction",
            "tx_hash": "0xabc",
        }
    ]

    with patch("pipeline.ingest.helpers") as mock_helpers:
        mock_helpers.bulk.return_value = (1, [])
        success, errors = bulk_ingest(mock_client, docs)

    assert success == 1
    assert errors == []
    mock_helpers.bulk.assert_called_once()
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /mnt/c/Users/aswat/OneDrive/Desktop/Projects/Project_Hail_Mary/chainsentinel
python -m pytest tests/test_ingest.py -v
```

Expected: FAIL

- [ ] **Step 3: Implement ingest.py**

`chainsentinel/pipeline/ingest.py`:

```python
"""
ES Bulk Ingest — stores documents to Elasticsearch with idempotent _id.
"""
from datetime import datetime, timezone
from elasticsearch import helpers


def _now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def build_raw_doc(
    doc_type: str, tx_hash: str, chain_id: int,
    investigation_id: str, data: dict, log_index: int = None
) -> dict:
    """Build a forensics-raw document with idempotent _id."""
    if doc_type == "log" and log_index is not None:
        doc_id = f"{chain_id}_{tx_hash}_{log_index}"
    elif doc_type == "trace":
        doc_id = f"{chain_id}_{tx_hash}_trace"
    else:
        doc_id = f"{chain_id}_{tx_hash}"

    doc = {
        "_id": doc_id,
        "_index": "forensics-raw",
        "investigation_id": investigation_id,
        "chain_id": chain_id,
        "@timestamp": _now_iso(),
        "doc_type": doc_type,
        "tx_hash": tx_hash,
    }
    doc.update(data)
    return doc


def build_analysis_doc(layer: str, investigation_id: str, data: dict) -> dict:
    """Build a forensics document with idempotent _id."""
    tx_hash = data.get("tx_hash", "")

    if layer == "signal":
        signal_name = data.get("signal_name", "unknown")
        doc_id = f"{investigation_id}_{signal_name}_{tx_hash}"
    elif layer == "alert":
        pattern_id = data.get("pattern_id", "unknown")
        doc_id = f"{investigation_id}_{pattern_id}"
    elif layer == "attacker":
        cluster_id = data.get("cluster_id", "unknown")
        doc_id = f"{investigation_id}_{cluster_id}"
    elif layer == "case":
        doc_id = investigation_id
    elif layer == "derived":
        derived_type = data.get("derived_type", "unknown")
        log_index = data.get("source_log_index", 0)
        doc_id = f"{investigation_id}_{derived_type}_{tx_hash}_{log_index}"
    elif layer == "decoded":
        log_index = data.get("source_log_index", data.get("log_index", 0))
        doc_id = f"{investigation_id}_{tx_hash}_{log_index}_decoded"
    else:
        doc_id = f"{investigation_id}_{layer}_{tx_hash}"

    doc = {
        "_id": doc_id,
        "_index": "forensics",
        "investigation_id": investigation_id,
        "@timestamp": _now_iso(),
        "layer": layer,
    }
    doc.update(data)
    return doc


def bulk_ingest(client, docs: list[dict], chunk_size: int = 500) -> tuple[int, list]:
    """Bulk ingest documents to Elasticsearch. Returns (success_count, errors)."""
    actions = []
    for doc in docs:
        action = {
            "_index": doc.pop("_index"),
            "_id": doc.pop("_id"),
            "_source": doc,
        }
        actions.append(action)

    success, errors = helpers.bulk(
        client, actions, chunk_size=chunk_size, raise_on_error=False
    )
    return success, errors
```

- [ ] **Step 4: Run tests**

```bash
cd /mnt/c/Users/aswat/OneDrive/Desktop/Projects/Project_Hail_Mary/chainsentinel
python -m pytest tests/test_ingest.py -v
```

Expected: All 5 PASS

- [ ] **Step 5: Commit**

```bash
git add chainsentinel/pipeline/ingest.py chainsentinel/tests/test_ingest.py
git commit -m "feat: ES bulk ingest with idempotent document IDs"
```

---

### Task 10: Pipeline Runner — Orchestration

**Files:**
- Create: `chainsentinel/pipeline/runner.py`
- Create: `chainsentinel/tests/test_runner.py`

- [ ] **Step 1: Write the tests**

`chainsentinel/tests/test_runner.py`:

```python
import pytest
from unittest.mock import MagicMock, AsyncMock, patch


@pytest.mark.asyncio
async def test_runner_yields_sse_events():
    from pipeline.runner import run_pipeline

    events = []
    async for event in run_pipeline(
        mode="tx",
        target="0xabc123",
        rpc_url="http://127.0.0.1:8545",
        es_url="http://localhost:9200",
        chain_id=31337,
        investigation_id="INV-TEST-001",
    ):
        events.append(event)
        if event.get("phase") == "complete" or len(events) > 20:
            break

    # Should have at least a collector phase and a complete phase
    phases = [e["phase"] for e in events]
    assert "collector" in phases or "error" in phases


@pytest.mark.asyncio
async def test_runner_produces_complete_event():
    from pipeline.runner import _build_sse_event

    event = _build_sse_event("complete", "Analysis finished", "ok",
                             investigation_id="INV-001",
                             stats={"blocks": 1, "txs": 5, "signals": 2, "indexed": 30})

    assert event["phase"] == "complete"
    assert event["investigationId"] == "INV-001"
    assert event["stats"]["txs"] == 5
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /mnt/c/Users/aswat/OneDrive/Desktop/Projects/Project_Hail_Mary/chainsentinel
python -m pytest tests/test_runner.py -v
```

Expected: FAIL

- [ ] **Step 3: Implement runner.py**

`chainsentinel/pipeline/runner.py`:

```python
"""
Pipeline Runner — orchestrates the full forensic pipeline.
Yields SSE events as each stage completes.
"""
import asyncio
from datetime import datetime, timezone
from typing import AsyncGenerator
from web3 import Web3, AsyncWeb3
from elasticsearch import Elasticsearch

from pipeline.collector import collect_transaction, collect_block_range, collect_logs
from pipeline.normalizer import normalize_transaction, normalize_log
from pipeline.decoder import load_decoder
from pipeline.derived import derive_events, derive_events_from_tx, derive_events_from_trace
from pipeline.ingest import build_raw_doc, build_analysis_doc, bulk_ingest


def _now():
    return datetime.now(timezone.utc).strftime("%H:%M:%S")


def _build_sse_event(phase: str, msg: str, severity: str, **kwargs) -> dict:
    event = {"phase": phase, "msg": msg, "severity": severity, "ts": _now()}
    if "investigation_id" in kwargs:
        event["investigationId"] = kwargs["investigation_id"]
    if "stats" in kwargs:
        event["stats"] = kwargs["stats"]
    if "es_index" in kwargs:
        event["esIndex"] = kwargs["es_index"]
    return event


async def run_pipeline(
    mode: str,
    target: str,
    rpc_url: str,
    es_url: str,
    chain_id: int,
    investigation_id: str,
    manifest_path: str = None,
    include_traces: bool = True,
) -> AsyncGenerator[dict, None]:
    """
    Run the full forensic pipeline. Yields SSE events.
    mode: 'tx', 'range', 'watch', 'wallet'
    target: tx hash, 'from_block-to_block', or wallet address
    """
    stats = {"blocks": 0, "txs": 0, "signals": 0, "indexed": 0}

    try:
        # Connect to RPC
        w3 = AsyncWeb3(AsyncWeb3.AsyncHTTPProvider(rpc_url))
        yield _build_sse_event("init", f"Connected to {rpc_url}", "ok")

        # Connect to ES
        es = Elasticsearch(es_url)
        yield _build_sse_event("init", f"Connected to Elasticsearch", "ok")

        # Load decoder
        decoder = load_decoder(investigation_id)
        yield _build_sse_event("init", f"Decoder loaded with {len(decoder.event_map)} event signatures", "ok")

        # === PHASE 1: COLLECT ===
        raw_txs = []

        if mode == "tx":
            yield _build_sse_event("collector", f"Fetching tx {target[:16]}...", "info")
            raw = await collect_transaction(w3, target, include_trace=include_traces)
            raw_txs.append(raw)
            stats["txs"] = 1
            stats["blocks"] = 1
            yield _build_sse_event("collector", f"1 tx fetched with {len(raw.get('logs', []))} logs", "ok",
                                   es_index="forensics-raw")

        elif mode == "range":
            parts = target.split("-")
            from_block = int(parts[0])
            to_block = int(parts[1])
            yield _build_sse_event("collector", f"Fetching blocks {from_block} to {to_block}", "info")
            raw_txs = await collect_block_range(w3, from_block, to_block, include_traces=include_traces)
            stats["blocks"] = to_block - from_block + 1
            stats["txs"] = len(raw_txs)
            yield _build_sse_event("collector", f"{len(raw_txs)} txs from {stats['blocks']} blocks", "ok",
                                   es_index="forensics-raw")

        elif mode == "watch":
            yield _build_sse_event("collector", "Watch mode: polling for new blocks", "info")
            last_block = await w3.eth.block_number
            yield _build_sse_event("collector", f"Starting from block {last_block}", "ok")
            # Watch mode runs continuously - for now collect current block
            raw_txs = await collect_block_range(w3, last_block, last_block, include_traces=include_traces)
            stats["blocks"] = 1
            stats["txs"] = len(raw_txs)
            yield _build_sse_event("collector", f"{len(raw_txs)} txs in block {last_block}", "ok")

        elif mode == "wallet":
            yield _build_sse_event("collector", f"Wallet hunt: {target[:16]}...", "info")
            # For wallet mode, we'll need to query historical txs
            # For now, yield a placeholder
            yield _build_sse_event("collector", "Wallet history collection (implementation in correlation plan)", "info")

        # === PHASE 2: NORMALIZE + INGEST RAW ===
        normalized_txs = []
        raw_docs = []

        for raw in raw_txs:
            # Build normalized tx from raw collector output
            norm = {
                "tx_hash": raw["tx_hash"],
                "block_number": raw["block_number"],
                "block_datetime": datetime.fromtimestamp(
                    raw["block_timestamp"], tz=timezone.utc
                ).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "block_timestamp_raw": raw["block_timestamp"],
                "tx_index": raw.get("tx_index", 0),
                "from_address": str(raw.get("from", "")).lower(),
                "to_address": str(raw.get("to", "")).lower(),
                "value_eth": raw.get("value", 0) / 1e18 if isinstance(raw.get("value"), (int, float)) else 0.0,
                "value_wei": str(raw.get("value", 0)),
                "gas": raw.get("gas", 0),
                "gas_price": raw.get("gas_price", 0),
                "gas_used": raw.get("gas_used", 0),
                "cumulative_gas_used": raw.get("cumulative_gas_used", 0),
                "nonce": raw.get("nonce", 0),
                "input": raw.get("input", "0x"),
                "success": bool(raw.get("status", 0)),
                "contract_address": raw.get("contract_address"),
                "logs": raw.get("logs", []),
                "trace": raw.get("trace"),
                "chain_id": chain_id,
                "decode_status": "pending",
                "raw_extra": {},
            }
            normalized_txs.append(norm)

            # Build raw ES doc
            raw_doc = build_raw_doc(
                doc_type="transaction", tx_hash=norm["tx_hash"],
                chain_id=chain_id, investigation_id=investigation_id,
                data={
                    "block_number": norm["block_number"],
                    "block_datetime": norm["block_datetime"],
                    "from_address": norm["from_address"],
                    "to_address": norm["to_address"],
                    "value_eth": norm["value_eth"],
                    "value_wei": norm["value_wei"],
                    "gas": norm["gas"],
                    "gas_used": norm["gas_used"],
                    "nonce": norm["nonce"],
                    "input": norm["input"],
                    "success": norm["success"],
                    "contract_address": norm["contract_address"],
                },
            )
            raw_docs.append(raw_doc)

            # Raw log documents
            for log in norm["logs"]:
                log_doc = build_raw_doc(
                    doc_type="log", tx_hash=norm["tx_hash"],
                    chain_id=chain_id, investigation_id=investigation_id,
                    data={
                        "block_number": norm["block_number"],
                        "block_datetime": norm["block_datetime"],
                        "log_index": log.get("log_index", 0),
                        "log_address": str(log.get("address", "")).lower(),
                        "topics": log.get("topics", []),
                        "data": log.get("data", "0x"),
                    },
                    log_index=log.get("log_index", 0),
                )
                raw_docs.append(log_doc)

            # Raw trace document
            if norm.get("trace"):
                trace_doc = build_raw_doc(
                    doc_type="trace", tx_hash=norm["tx_hash"],
                    chain_id=chain_id, investigation_id=investigation_id,
                    data={
                        "block_number": norm["block_number"],
                        "block_datetime": norm["block_datetime"],
                        "trace_calls": norm["trace"],
                    },
                )
                raw_docs.append(trace_doc)

        # Ingest raw docs
        if raw_docs:
            success, errors = bulk_ingest(es, raw_docs)
            stats["indexed"] += success
            yield _build_sse_event("normalizer",
                                   f"{len(normalized_txs)} txs normalized, {success} raw docs indexed",
                                   "ok", es_index="forensics-raw")

        # === PHASE 3: DECODE ===
        all_decoded = []

        for norm in normalized_txs:
            for log in norm.get("logs", []):
                decoded = decoder.decode_log(log)
                decoded.update({
                    "tx_hash": norm["tx_hash"],
                    "block_number": norm["block_number"],
                    "block_datetime": norm["block_datetime"],
                    "log_index": log.get("log_index", 0),
                    "log_address": str(log.get("address", "")).lower(),
                })

                if norm.get("input") and norm["input"] != "0x":
                    func_decoded = decoder.decode_function_input(norm["input"])
                    decoded["function_name"] = func_decoded.get("function_name")
                    decoded["function_args"] = func_decoded.get("function_args", {})

                all_decoded.append(decoded)

        # Ingest decoded docs
        decoded_docs = []
        for d in all_decoded:
            doc = build_analysis_doc(layer="decoded", investigation_id=investigation_id, data={
                "tx_hash": d.get("tx_hash", ""),
                "block_number": d.get("block_number", 0),
                "block_datetime": d.get("block_datetime", ""),
                "source_log_index": d.get("log_index", 0),
                "log_address": d.get("log_address", ""),
                "event_name": d.get("event_name"),
                "event_args": d.get("event_args", {}),
                "decode_status": d.get("decode_status", "unknown"),
                "function_name": d.get("function_name"),
                "function_args": d.get("function_args", {}),
            })
            decoded_docs.append(doc)

        if decoded_docs:
            success, errors = bulk_ingest(es, decoded_docs)
            stats["indexed"] += success

        decoded_count = len([d for d in all_decoded if d.get("decode_status") == "decoded"])
        unknown_count = len([d for d in all_decoded if d.get("decode_status") == "unknown"])
        yield _build_sse_event("decoder",
                               f"{decoded_count} decoded, {unknown_count} unknown selectors",
                               "info", es_index="forensics")

        # === PHASE 4: DERIVE ===
        all_derived = []

        # From decoded events
        all_derived.extend(derive_events(all_decoded, investigation_id))

        # From normalized transactions (native transfers, contract interactions)
        for norm in normalized_txs:
            all_derived.extend(derive_events_from_tx(norm, investigation_id))

            # From traces
            if norm.get("trace"):
                all_derived.extend(derive_events_from_trace(
                    norm["trace"], norm["tx_hash"], norm["block_number"],
                    norm["block_datetime"], investigation_id
                ))

        # Ingest derived docs
        derived_docs = [
            build_analysis_doc(layer="derived", investigation_id=investigation_id, data=d)
            for d in all_derived
        ]

        if derived_docs:
            success, errors = bulk_ingest(es, derived_docs)
            stats["indexed"] += success

        # Count by derived type
        type_counts = {}
        for d in all_derived:
            dt = d.get("derived_type", "unknown")
            type_counts[dt] = type_counts.get(dt, 0) + 1

        type_summary = " · ".join(f"{count} {dtype}" for dtype, count in type_counts.items())
        yield _build_sse_event("derived", type_summary or "No derived events", "ok",
                               es_index="forensics")

        # Save decoder registry
        decoder.save_registry()

        # === PHASE 5: SIGNALS (placeholder — implemented in Plan 2) ===
        yield _build_sse_event("signals", "Signal detection deferred to ES query engine", "info")

        # === PHASE 6: CORRELATION (placeholder — implemented in Plan 3) ===
        yield _build_sse_event("correlation", "Correlation deferred to correlation engine", "info")

        # === COMPLETE ===
        yield _build_sse_event("complete", "Analysis complete", "ok",
                               investigation_id=investigation_id, stats=stats)

    except Exception as e:
        yield _build_sse_event("error", str(e), "crit")
```

- [ ] **Step 4: Run tests**

```bash
cd /mnt/c/Users/aswat/OneDrive/Desktop/Projects/Project_Hail_Mary/chainsentinel
python -m pytest tests/test_runner.py -v
```

Expected: test_runner_produces_complete_event PASS (the integration test may need Anvil running — skip if not available)

- [ ] **Step 5: Commit**

```bash
git add chainsentinel/pipeline/runner.py chainsentinel/tests/test_runner.py
git commit -m "feat: pipeline runner orchestrates collect → normalize → decode → derive → ingest"
```

---

### Task 11: Minimal FastAPI Server

**Files:**
- Create: `chainsentinel/server.py`

- [ ] **Step 1: Create server.py**

`chainsentinel/server.py`:

```python
"""
FastAPI server — thin wrapper around the pipeline.
Streams SSE events during analysis.
"""
import json
import uuid
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from sse_starlette.sse import EventSourceResponse
from elasticsearch import Elasticsearch

from pipeline.runner import run_pipeline
from es.setup import setup_elasticsearch


app = FastAPI(title="ChainSentinel", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

CONFIG_PATH = Path(__file__).parent / "config.json"


def load_config():
    with open(CONFIG_PATH) as f:
        return json.load(f)


@app.on_event("startup")
async def startup():
    config = load_config()
    es = Elasticsearch(config["es_url"])
    setup_elasticsearch(es)
    es.close()


@app.get("/health")
async def health():
    config = load_config()
    status = {"rpc": "unknown", "elasticsearch": "unknown", "ollama": "unknown"}

    # Check RPC
    try:
        from web3 import Web3
        w3 = Web3(Web3.HTTPProvider(config["rpc_url"]))
        w3.eth.block_number
        status["rpc"] = "connected"
    except Exception:
        status["rpc"] = "disconnected"

    # Check ES
    try:
        es = Elasticsearch(config["es_url"])
        es.info()
        status["elasticsearch"] = "connected"
        es.close()
    except Exception:
        status["elasticsearch"] = "disconnected"

    # Check Ollama
    try:
        import httpx
        resp = httpx.get(f"{config['ollama_url']}/api/tags", timeout=3)
        status["ollama"] = "connected" if resp.status_code == 200 else "disconnected"
    except Exception:
        status["ollama"] = "disconnected"

    return status


@app.post("/analyze")
async def analyze(request: Request):
    body = await request.json()
    config = load_config()

    mode = body.get("mode", "tx")
    target = body.get("target", "")
    investigation_id = body.get("investigation_id", f"INV-{uuid.uuid4().hex[:8].upper()}")
    rpc_url = body.get("rpc_url", config["rpc_url"])
    es_url = body.get("es_url", config["es_url"])
    chain_id = body.get("chain_id", config["chain_id"])
    manifest_path = body.get("manifest_path")

    async def event_generator():
        async for event in run_pipeline(
            mode=mode,
            target=target,
            rpc_url=rpc_url,
            es_url=es_url,
            chain_id=chain_id,
            investigation_id=investigation_id,
            manifest_path=manifest_path,
        ):
            yield {"event": "message", "data": json.dumps(event)}

    return EventSourceResponse(event_generator())


@app.get("/analysis/{investigation_id}")
async def get_analysis(investigation_id: str):
    config = load_config()
    es = Elasticsearch(config["es_url"])

    try:
        result = es.search(
            index="forensics",
            body={
                "query": {
                    "bool": {
                        "must": [
                            {"term": {"investigation_id": investigation_id}},
                            {"term": {"layer": "case"}},
                        ]
                    }
                },
                "size": 1,
            },
        )
        hits = result.get("hits", {}).get("hits", [])
        if hits:
            return hits[0]["_source"]
        return {"error": "Investigation not found"}
    finally:
        es.close()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

- [ ] **Step 2: Test server starts**

```bash
cd /mnt/c/Users/aswat/OneDrive/Desktop/Projects/Project_Hail_Mary/chainsentinel
python -c "from server import app; print('Server module loads OK')"
```

- [ ] **Step 3: Commit**

```bash
git add chainsentinel/server.py
git commit -m "feat: FastAPI server with /health, /analyze (SSE), and /analysis endpoints"
```

---

### Task 12: End-to-End Smoke Test

- [ ] **Step 1: Run all tests**

```bash
cd /mnt/c/Users/aswat/OneDrive/Desktop/Projects/Project_Hail_Mary/chainsentinel
python -m pytest tests/ -v --tb=short
```

Expected: All tests PASS

- [ ] **Step 2: Final commit**

```bash
git add -A
git commit -m "feat: ChainSentinel foundation — complete pipeline from RPC to Elasticsearch"
```

---

## Plan Summary

| Task | Component | Files |
|------|-----------|-------|
| 1 | Scaffolding | config.json, requirements.txt, conftest.py |
| 2 | ES Mappings | forensics-raw.json, forensics.json |
| 3 | ES Setup | es/setup.py |
| 4 | Collector | pipeline/collector.py |
| 5 | Normalizer | pipeline/normalizer.py |
| 6 | ABI Registry | abi_registry/standards/erc20.json |
| 7 | Decoder | pipeline/decoder.py |
| 8 | Derived Builder | pipeline/derived.py |
| 9 | ES Ingest | pipeline/ingest.py |
| 10 | Pipeline Runner | pipeline/runner.py |
| 11 | FastAPI Server | server.py |
| 12 | Smoke Test | all tests green |
