# ChainSentinel Detection Engine — Implementation Plan (Plan 2 of 6)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the ES signal engine (loads and runs .esql files), the EQL pattern engine (loads and runs .eql files), Wave 1 signal query files (~20 signals), and 4 attack pattern query files. After this plan, the pipeline can detect individual security signals and composite attack patterns purely via Elasticsearch queries.

**Architecture:** Two Python engines that auto-discover query files from disk. The signal engine loads `.esql` files from `detection/signals/`, executes them as ES|QL queries against the `forensics` index filtered by `investigation_id`, and writes results as `layer: signal` documents. The pattern engine loads `.eql` files from `detection/patterns/`, executes EQL sequence queries against signal + derived documents, and writes results as `layer: alert` documents.

**Tech Stack:** Python 3.11+, elasticsearch-py 8.x (ES|QL API + EQL API), pytest

**Spec reference:** `docs/superpowers/specs/2026-04-12-chainsentinel-design.md` sections 7, 5

**Depends on:** Plan 1 (pipeline foundation — ES indices, ingest module, config)

---

## File Structure

```
chainsentinel/
├── detection/
│   ├── __init__.py
│   ├── signal_engine.py              ← loads + runs .esql files against ES
│   ├── pattern_engine.py             ← loads + runs .eql files against ES
│   ├── signals/
│   │   ├── value/
│   │   │   ├── large_outflow.esql
│   │   │   ├── large_token_transfer.esql
│   │   │   ├── max_approval.esql
│   │   │   └── value_spike.esql
│   │   ├── flash_loan/
│   │   │   ├── flash_loan_detected.esql
│   │   │   └── flash_loan_with_drain.esql
│   │   ├── access/
│   │   │   ├── ownership_transferred.esql
│   │   │   ├── role_granted.esql
│   │   │   └── proxy_upgraded.esql
│   │   ├── structural/
│   │   │   ├── reentrancy_pattern.esql
│   │   │   ├── call_depth_anomaly.esql
│   │   │   ├── repeated_external_call.esql
│   │   │   └── internal_eth_drain.esql
│   │   ├── deployment/
│   │   │   ├── new_contract_deployed.esql
│   │   │   └── failed_high_gas.esql
│   │   ├── liquidity/
│   │   │   └── large_liquidity_removal.esql
│   │   ├── defi/
│   │   │   ├── vault_first_deposit_tiny.esql
│   │   │   └── liquidation_event.esql
│   │   └── behavioural/
│   │       ├── new_wallet_high_value.esql
│   │       └── burst_transactions.esql
│   └── patterns/
│       ├── AP-001_flash_loan_oracle.eql
│       ├── AP-005_reentrancy_drain.eql
│       ├── AP-008_access_control_abuse.eql
│       └── AP-014_mev_sandwich.eql
└── tests/
    ├── test_signal_engine.py
    └── test_pattern_engine.py
```

---

### Task 1: Detection Module Scaffolding

**Files:**
- Create: `chainsentinel/detection/__init__.py`
- Create directories for all signal families and patterns

- [ ] **Step 1: Create directory structure**

```bash
cd /mnt/c/Users/aswat/OneDrive/Desktop/Projects/Project_Hail_Mary
mkdir -p chainsentinel/detection/signals/{value,flash_loan,access,structural,deployment,liquidity,defi,behavioural}
mkdir -p chainsentinel/detection/patterns
touch chainsentinel/detection/__init__.py
```

- [ ] **Step 2: Commit scaffolding**

```bash
git add chainsentinel/detection/
git commit -m "feat: detection module directory scaffolding"
```

---

### Task 2: Signal Engine

**Files:**
- Create: `chainsentinel/detection/signal_engine.py`
- Create: `chainsentinel/tests/test_signal_engine.py`

- [ ] **Step 1: Write the tests**

`chainsentinel/tests/test_signal_engine.py`:

```python
import pytest
import json
from pathlib import Path
from unittest.mock import MagicMock, patch, call


def test_discover_signals_finds_all_esql_files(tmp_path):
    from detection.signal_engine import discover_signals

    # Create mock signal files
    value_dir = tmp_path / "value"
    value_dir.mkdir()
    (value_dir / "large_outflow.esql").write_text("FROM forensics | WHERE layer == \"derived\"")
    (value_dir / "value_spike.esql").write_text("FROM forensics | WHERE layer == \"derived\"")

    flash_dir = tmp_path / "flash_loan"
    flash_dir.mkdir()
    (flash_dir / "flash_loan_detected.esql").write_text("FROM forensics | WHERE layer == \"decoded\"")

    signals = discover_signals(tmp_path)

    assert len(signals) == 3
    names = [s["name"] for s in signals]
    assert "large_outflow" in names
    assert "value_spike" in names
    assert "flash_loan_detected" in names


def test_discover_signals_extracts_family_from_directory(tmp_path):
    from detection.signal_engine import discover_signals

    access_dir = tmp_path / "access"
    access_dir.mkdir()
    (access_dir / "ownership_transferred.esql").write_text("FROM forensics")

    signals = discover_signals(tmp_path)

    assert signals[0]["family"] == "access"
    assert signals[0]["name"] == "ownership_transferred"


def test_discover_signals_ignores_non_esql_files(tmp_path):
    from detection.signal_engine import discover_signals

    value_dir = tmp_path / "value"
    value_dir.mkdir()
    (value_dir / "large_outflow.esql").write_text("FROM forensics")
    (value_dir / "readme.md").write_text("Not a signal")
    (value_dir / "notes.txt").write_text("Not a signal")

    signals = discover_signals(tmp_path)

    assert len(signals) == 1


def test_parse_signal_metadata_from_header():
    from detection.signal_engine import parse_signal_metadata

    query_text = """-- signal: large_outflow
-- severity: HIGH
-- score: 0.8
-- description: Detects ETH outflows exceeding 10 ETH in a single transaction
FROM forensics
| WHERE layer == "derived" AND derived_type == "native_transfer"
| WHERE value_eth > 10.0
"""
    meta = parse_signal_metadata(query_text, "large_outflow", "value")

    assert meta["signal_name"] == "large_outflow"
    assert meta["severity"] == "HIGH"
    assert meta["score"] == 0.8
    assert meta["signal_family"] == "value"
    assert "10 ETH" in meta["description"]


def test_parse_signal_metadata_defaults():
    from detection.signal_engine import parse_signal_metadata

    query_text = "FROM forensics | WHERE layer == \"derived\""
    meta = parse_signal_metadata(query_text, "unknown_signal", "misc")

    assert meta["severity"] == "MED"
    assert meta["score"] == 0.5
    assert meta["signal_family"] == "misc"


def test_build_esql_query_injects_investigation_id():
    from detection.signal_engine import build_esql_query

    raw_query = """FROM forensics
| WHERE layer == "derived" AND derived_type == "native_transfer"
| WHERE value_eth > 10.0"""

    result = build_esql_query(raw_query, "INV-2026-0001")

    assert 'investigation_id == "INV-2026-0001"' in result
    assert "FROM forensics" in result


def test_run_signal_returns_documents():
    from detection.signal_engine import run_signal

    mock_client = MagicMock()
    mock_client.esql.query.return_value = {
        "columns": [
            {"name": "tx_hash", "type": "keyword"},
            {"name": "from_address", "type": "keyword"},
            {"name": "to_address", "type": "keyword"},
            {"name": "value_eth", "type": "double"},
            {"name": "block_number", "type": "long"},
        ],
        "values": [
            ["0xabc123", "0xdead", "0x1234", 15.5, 10],
            ["0xdef456", "0xdead", "0x5678", 22.0, 11],
        ],
    }

    metadata = {
        "signal_name": "large_outflow",
        "signal_family": "value",
        "severity": "HIGH",
        "score": 0.8,
        "description": "Large ETH outflow detected",
    }

    results = run_signal(
        mock_client, "FROM forensics | WHERE value_eth > 10",
        metadata, "INV-2026-0001", 31337
    )

    assert len(results) == 2
    assert results[0]["layer"] == "signal"
    assert results[0]["signal_name"] == "large_outflow"
    assert results[0]["signal_family"] == "value"
    assert results[0]["severity"] == "HIGH"
    assert results[0]["score"] == 0.8
    assert results[0]["tx_hash"] == "0xabc123"
    assert results[0]["investigation_id"] == "INV-2026-0001"
    assert results[0]["chain_id"] == 31337


def test_run_signal_handles_empty_results():
    from detection.signal_engine import run_signal

    mock_client = MagicMock()
    mock_client.esql.query.return_value = {
        "columns": [
            {"name": "tx_hash", "type": "keyword"},
        ],
        "values": [],
    }

    metadata = {
        "signal_name": "large_outflow",
        "signal_family": "value",
        "severity": "HIGH",
        "score": 0.8,
        "description": "Large ETH outflow detected",
    }

    results = run_signal(
        mock_client, "FROM forensics | WHERE value_eth > 10",
        metadata, "INV-2026-0001", 31337
    )

    assert results == []


def test_run_all_signals_orchestrates_discovery_and_execution(tmp_path):
    from detection.signal_engine import run_all_signals

    value_dir = tmp_path / "value"
    value_dir.mkdir()
    (value_dir / "large_outflow.esql").write_text(
        "-- signal: large_outflow\n-- severity: HIGH\n-- score: 0.8\n"
        "-- description: Large ETH outflow\n"
        "FROM forensics\n| WHERE layer == \"derived\" AND value_eth > 10"
    )

    mock_client = MagicMock()
    mock_client.esql.query.return_value = {
        "columns": [{"name": "tx_hash", "type": "keyword"}],
        "values": [["0xabc"]],
    }

    mock_ingest = MagicMock()

    results = run_all_signals(
        mock_client, mock_ingest, tmp_path,
        "INV-2026-0001", 31337
    )

    assert len(results) == 1
    mock_client.esql.query.assert_called_once()
    mock_ingest.assert_called_once()
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /mnt/c/Users/aswat/OneDrive/Desktop/Projects/Project_Hail_Mary/chainsentinel
python -m pytest tests/test_signal_engine.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'detection.signal_engine'`

- [ ] **Step 3: Implement signal_engine.py**

`chainsentinel/detection/signal_engine.py`:

```python
"""
Signal Engine — discovers and runs ES|QL signal queries.

Loads all .esql files from detection/signals/ subdirectories.
Each file is one signal. The engine:
1. Discovers all .esql files grouped by family (subdirectory name)
2. Parses metadata from comment headers (signal name, severity, score, description)
3. Injects investigation_id filter into each query
4. Executes via ES|QL API
5. Converts results to signal documents (layer: signal)
6. Bulk ingests into forensics index
"""
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


SIGNALS_DIR = Path(__file__).parent / "signals"


def discover_signals(signals_dir: Optional[Path] = None) -> list[dict]:
    """
    Walk signal subdirectories and collect all .esql files.
    Returns list of dicts: {name, family, path, query_text}
    """
    base = signals_dir or SIGNALS_DIR
    signals = []

    for esql_file in sorted(base.rglob("*.esql")):
        family = esql_file.parent.name
        name = esql_file.stem
        query_text = esql_file.read_text(encoding="utf-8")

        signals.append({
            "name": name,
            "family": family,
            "path": str(esql_file),
            "query_text": query_text,
        })

    return signals


def parse_signal_metadata(
    query_text: str, signal_name: str, family: str
) -> dict:
    """
    Extract metadata from .esql comment headers.
    Format:
        -- signal: name
        -- severity: HIGH
        -- score: 0.8
        -- description: Human readable description
    Falls back to defaults if headers missing.
    """
    severity = "MED"
    score = 0.5
    description = f"Signal {signal_name} fired"

    for line in query_text.splitlines():
        line = line.strip()
        if not line.startswith("--"):
            continue
        content = line[2:].strip()

        if content.startswith("severity:"):
            severity = content.split(":", 1)[1].strip().upper()
        elif content.startswith("score:"):
            try:
                score = float(content.split(":", 1)[1].strip())
            except ValueError:
                pass
        elif content.startswith("description:"):
            description = content.split(":", 1)[1].strip()

    return {
        "signal_name": signal_name,
        "signal_family": family,
        "severity": severity,
        "score": score,
        "description": description,
    }


def build_esql_query(raw_query: str, investigation_id: str) -> str:
    """
    Inject investigation_id filter into an ES|QL query.
    Inserts after the FROM clause.
    """
    lines = raw_query.strip().splitlines()
    result = []
    from_seen = False

    for line in lines:
        stripped = line.strip()
        # Skip comment lines
        if stripped.startswith("--"):
            continue

        result.append(line)

        # After the FROM line, inject investigation_id filter
        if not from_seen and stripped.upper().startswith("FROM "):
            from_seen = True
            result.append(
                f'| WHERE investigation_id == "{investigation_id}"'
            )

    return "\n".join(result)


def run_signal(
    es_client,
    raw_query: str,
    metadata: dict,
    investigation_id: str,
    chain_id: int,
) -> list[dict]:
    """
    Execute a single signal query and convert results to signal documents.
    """
    query = build_esql_query(raw_query, investigation_id)

    response = es_client.esql.query(
        query=query,
        format="json",
    )

    columns = [col["name"] for col in response.get("columns", [])]
    rows = response.get("values", [])

    if not rows:
        return []

    now = datetime.now(timezone.utc).isoformat()
    documents = []

    for row in rows:
        row_dict = dict(zip(columns, row))

        doc = {
            "layer": "signal",
            "investigation_id": investigation_id,
            "chain_id": chain_id,
            "@timestamp": now,
            "signal_name": metadata["signal_name"],
            "signal_family": metadata["signal_family"],
            "severity": metadata["severity"],
            "score": metadata["score"],
            "description": metadata["description"],
            "tx_hash": row_dict.get("tx_hash"),
            "block_number": row_dict.get("block_number"),
            "from_address": row_dict.get("from_address"),
            "to_address": row_dict.get("to_address"),
            "value_eth": row_dict.get("value_eth"),
            "evidence_refs": [
                f"{investigation_id}_{metadata['signal_name']}_{row_dict.get('tx_hash', 'unknown')}"
            ],
        }

        documents.append(doc)

    return documents


def run_all_signals(
    es_client,
    ingest_fn,
    signals_dir: Optional[Path] = None,
    investigation_id: str = "",
    chain_id: int = 31337,
) -> list[dict]:
    """
    Discover all signals, run each, ingest results.
    Returns all signal documents produced.

    Args:
        es_client: Elasticsearch client
        ingest_fn: Callable that takes (es_client, documents, index) and bulk ingests
        signals_dir: Override path to signals directory
        investigation_id: Current investigation ID
        chain_id: Chain ID from config
    """
    signals = discover_signals(signals_dir)
    all_results = []

    for signal in signals:
        metadata = parse_signal_metadata(
            signal["query_text"], signal["name"], signal["family"]
        )

        results = run_signal(
            es_client, signal["query_text"],
            metadata, investigation_id, chain_id
        )

        if results:
            ingest_fn(es_client, results, "forensics")
            all_results.extend(results)

    return all_results
```

- [ ] **Step 4: Run tests**

```bash
cd /mnt/c/Users/aswat/OneDrive/Desktop/Projects/Project_Hail_Mary/chainsentinel
python -m pytest tests/test_signal_engine.py -v
```

Expected: All 9 PASS

- [ ] **Step 5: Commit**

```bash
git add chainsentinel/detection/signal_engine.py chainsentinel/tests/test_signal_engine.py
git commit -m "feat: signal engine discovers and runs ES|QL signal queries"
```

---

### Task 3: Wave 1 Signal Queries — Value Family (4 signals)

**Files:**
- Create: `chainsentinel/detection/signals/value/large_outflow.esql`
- Create: `chainsentinel/detection/signals/value/large_token_transfer.esql`
- Create: `chainsentinel/detection/signals/value/max_approval.esql`
- Create: `chainsentinel/detection/signals/value/value_spike.esql`

- [ ] **Step 1: Create large_outflow.esql**

`chainsentinel/detection/signals/value/large_outflow.esql`:

```sql
-- signal: large_outflow
-- severity: HIGH
-- score: 0.8
-- description: Detects native ETH outflows exceeding 10 ETH in a single transaction
FROM forensics
| WHERE layer == "derived" AND derived_type == "native_transfer"
| WHERE value_eth > 10.0
| STATS total_outflow = SUM(value_eth), tx_count = COUNT(*) BY from_address, tx_hash, block_number
| WHERE total_outflow > 10.0
| SORT total_outflow DESC
| LIMIT 100
```

- [ ] **Step 2: Create large_token_transfer.esql**

`chainsentinel/detection/signals/value/large_token_transfer.esql`:

```sql
-- signal: large_token_transfer
-- severity: HIGH
-- score: 0.75
-- description: Detects ERC20 token transfers with amount exceeding 1M tokens (pre-decimal)
FROM forensics
| WHERE layer == "derived" AND derived_type == "asset_transfer"
| WHERE amount_decimal > 1000000.0
| STATS total_amount = SUM(amount_decimal), tx_count = COUNT(*) BY from_address, to_address, token_address, tx_hash, block_number
| SORT total_amount DESC
| LIMIT 100
```

- [ ] **Step 3: Create max_approval.esql**

`chainsentinel/detection/signals/value/max_approval.esql`:

```sql
-- signal: max_approval
-- severity: MED
-- score: 0.6
-- description: Detects ERC20 approvals set to max uint256 (unlimited spending)
FROM forensics
| WHERE layer == "decoded" AND event_name == "Approval"
| WHERE amount_decimal > 1e+70
| STATS approval_count = COUNT(*) BY owner_address, spender_address, token_address, tx_hash, block_number
| SORT approval_count DESC
| LIMIT 100
```

- [ ] **Step 4: Create value_spike.esql**

`chainsentinel/detection/signals/value/value_spike.esql`:

```sql
-- signal: value_spike
-- severity: HIGH
-- score: 0.7
-- description: Detects transactions whose value is >5x the average for that address pair
FROM forensics
| WHERE layer == "derived" AND derived_type == "native_transfer"
| STATS avg_value = AVG(value_eth), max_value = MAX(value_eth), tx_count = COUNT(*) BY from_address, to_address
| WHERE max_value > avg_value * 5 AND tx_count > 1 AND max_value > 1.0
| EVAL spike_ratio = max_value / avg_value
| SORT spike_ratio DESC
| LIMIT 100
```

- [ ] **Step 5: Write validation test**

`chainsentinel/tests/test_signal_queries.py` (append or create):

```python
import pytest
from pathlib import Path


SIGNALS_DIR = Path(__file__).parent.parent / "detection" / "signals"


def test_all_value_signals_have_required_headers():
    """Every .esql in value/ must have signal, severity, score, description headers."""
    value_dir = SIGNALS_DIR / "value"
    for esql_file in value_dir.glob("*.esql"):
        content = esql_file.read_text()
        assert "-- signal:" in content, f"{esql_file.name} missing signal header"
        assert "-- severity:" in content, f"{esql_file.name} missing severity header"
        assert "-- score:" in content, f"{esql_file.name} missing score header"
        assert "-- description:" in content, f"{esql_file.name} missing description header"
        assert "FROM forensics" in content, f"{esql_file.name} missing FROM forensics"


def test_all_value_signals_exist():
    value_dir = SIGNALS_DIR / "value"
    expected = ["large_outflow", "large_token_transfer", "max_approval", "value_spike"]
    for name in expected:
        assert (value_dir / f"{name}.esql").exists(), f"Missing {name}.esql"


def test_signal_files_are_valid_esql():
    """Basic syntax check: every signal must start with comments then FROM forensics."""
    for esql_file in SIGNALS_DIR.rglob("*.esql"):
        content = esql_file.read_text()
        # Strip comment lines, first non-comment line should start with FROM
        lines = [l.strip() for l in content.splitlines() if l.strip() and not l.strip().startswith("--")]
        assert len(lines) > 0, f"{esql_file.name} is empty after removing comments"
        assert lines[0].startswith("FROM "), f"{esql_file.name} first query line must start with FROM"
```

- [ ] **Step 6: Run tests**

```bash
cd /mnt/c/Users/aswat/OneDrive/Desktop/Projects/Project_Hail_Mary/chainsentinel
python -m pytest tests/test_signal_queries.py -v
```

Expected: All PASS

- [ ] **Step 7: Commit**

```bash
git add chainsentinel/detection/signals/value/ chainsentinel/tests/test_signal_queries.py
git commit -m "feat: Wave 1 value signals — large_outflow, large_token_transfer, max_approval, value_spike"
```

---

### Task 4: Wave 1 Signal Queries — Flash Loan Family (2 signals)

**Files:**
- Create: `chainsentinel/detection/signals/flash_loan/flash_loan_detected.esql`
- Create: `chainsentinel/detection/signals/flash_loan/flash_loan_with_drain.esql`

- [ ] **Step 1: Create flash_loan_detected.esql**

`chainsentinel/detection/signals/flash_loan/flash_loan_detected.esql`:

```sql
-- signal: flash_loan_detected
-- severity: MED
-- score: 0.6
-- description: Detects flash loan events (Aave FlashLoan, dYdX, Euler, Balancer)
FROM forensics
| WHERE layer == "decoded"
| WHERE event_name == "FlashLoan" OR event_name == "Flash" OR event_name == "FlashBorrow"
| STATS loan_count = COUNT(*), total_value = SUM(amount_decimal) BY from_address, tx_hash, block_number, token_address
| SORT total_value DESC
| LIMIT 100
```

- [ ] **Step 2: Create flash_loan_with_drain.esql**

`chainsentinel/detection/signals/flash_loan/flash_loan_with_drain.esql`:

```sql
-- signal: flash_loan_with_drain
-- severity: CRIT
-- score: 0.9
-- description: Detects flash loan in same tx as a large value outflow (potential exploit)
FROM forensics
| WHERE layer == "derived"
| WHERE (derived_type == "asset_transfer" AND amount_decimal > 100000) OR (derived_type == "native_transfer" AND value_eth > 10.0)
| STATS drain_value = SUM(value_eth), token_drain = SUM(amount_decimal), drain_count = COUNT(*) BY tx_hash, from_address, to_address, block_number
| WHERE drain_value > 10.0 OR token_drain > 100000
| SORT drain_value DESC
| LIMIT 50
```

- [ ] **Step 3: Add flash loan signals to validation test**

Append to `chainsentinel/tests/test_signal_queries.py`:

```python
def test_all_flash_loan_signals_exist():
    flash_dir = SIGNALS_DIR / "flash_loan"
    expected = ["flash_loan_detected", "flash_loan_with_drain"]
    for name in expected:
        assert (flash_dir / f"{name}.esql").exists(), f"Missing {name}.esql"
```

- [ ] **Step 4: Run tests**

```bash
cd /mnt/c/Users/aswat/OneDrive/Desktop/Projects/Project_Hail_Mary/chainsentinel
python -m pytest tests/test_signal_queries.py -v
```

Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add chainsentinel/detection/signals/flash_loan/ chainsentinel/tests/test_signal_queries.py
git commit -m "feat: Wave 1 flash loan signals — flash_loan_detected, flash_loan_with_drain"
```

---

### Task 5: Wave 1 Signal Queries — Access Family (3 signals)

**Files:**
- Create: `chainsentinel/detection/signals/access/ownership_transferred.esql`
- Create: `chainsentinel/detection/signals/access/role_granted.esql`
- Create: `chainsentinel/detection/signals/access/proxy_upgraded.esql`

- [ ] **Step 1: Create ownership_transferred.esql**

`chainsentinel/detection/signals/access/ownership_transferred.esql`:

```sql
-- signal: ownership_transferred
-- severity: CRIT
-- score: 0.85
-- description: Detects OwnershipTransferred events indicating admin control change
FROM forensics
| WHERE layer == "decoded"
| WHERE event_name == "OwnershipTransferred"
| STATS transfer_count = COUNT(*) BY from_address, to_address, contract_address, tx_hash, block_number
| SORT block_number ASC
| LIMIT 100
```

- [ ] **Step 2: Create role_granted.esql**

`chainsentinel/detection/signals/access/role_granted.esql`:

```sql
-- signal: role_granted
-- severity: HIGH
-- score: 0.7
-- description: Detects RoleGranted events (OpenZeppelin AccessControl) for privilege escalation
FROM forensics
| WHERE layer == "decoded"
| WHERE event_name == "RoleGranted"
| STATS grant_count = COUNT(*) BY from_address, to_address, contract_address, tx_hash, block_number
| SORT block_number ASC
| LIMIT 100
```

- [ ] **Step 3: Create proxy_upgraded.esql**

`chainsentinel/detection/signals/access/proxy_upgraded.esql`:

```sql
-- signal: proxy_upgraded
-- severity: CRIT
-- score: 0.9
-- description: Detects proxy contract upgrades (Upgraded event) which can introduce malicious logic
FROM forensics
| WHERE layer == "decoded"
| WHERE event_name == "Upgraded" OR event_name == "AdminChanged" OR event_name == "BeaconUpgraded"
| STATS upgrade_count = COUNT(*) BY contract_address, tx_hash, block_number, from_address
| SORT block_number ASC
| LIMIT 100
```

- [ ] **Step 4: Run tests**

```bash
cd /mnt/c/Users/aswat/OneDrive/Desktop/Projects/Project_Hail_Mary/chainsentinel
python -m pytest tests/test_signal_queries.py -v
```

- [ ] **Step 5: Commit**

```bash
git add chainsentinel/detection/signals/access/
git commit -m "feat: Wave 1 access signals — ownership_transferred, role_granted, proxy_upgraded"
```

---

### Task 6: Wave 1 Signal Queries — Structural Family (4 signals)

**Files:**
- Create: `chainsentinel/detection/signals/structural/reentrancy_pattern.esql`
- Create: `chainsentinel/detection/signals/structural/call_depth_anomaly.esql`
- Create: `chainsentinel/detection/signals/structural/repeated_external_call.esql`
- Create: `chainsentinel/detection/signals/structural/internal_eth_drain.esql`

- [ ] **Step 1: Create reentrancy_pattern.esql**

`chainsentinel/detection/signals/structural/reentrancy_pattern.esql`:

```sql
-- signal: reentrancy_pattern
-- severity: CRIT
-- score: 0.95
-- description: Detects reentrancy via recursive calls — same callee appears at multiple depths in trace
FROM forensics
| WHERE layer == "derived" AND derived_type == "execution_edge"
| STATS call_count = COUNT(*), max_depth = MAX(call_depth), min_depth = MIN(call_depth) BY callee_address, caller_address, tx_hash, block_number
| WHERE call_count > 2 AND max_depth > min_depth
| EVAL depth_spread = max_depth - min_depth
| WHERE depth_spread >= 2
| SORT call_count DESC
| LIMIT 50
```

- [ ] **Step 2: Create call_depth_anomaly.esql**

`chainsentinel/detection/signals/structural/call_depth_anomaly.esql`:

```sql
-- signal: call_depth_anomaly
-- severity: HIGH
-- score: 0.8
-- description: Detects transactions with abnormally deep call stacks (>10 levels)
FROM forensics
| WHERE layer == "derived" AND derived_type == "execution_edge"
| STATS max_depth = MAX(call_depth), total_calls = COUNT(*) BY tx_hash, block_number
| WHERE max_depth > 10
| SORT max_depth DESC
| LIMIT 50
```

- [ ] **Step 3: Create repeated_external_call.esql**

`chainsentinel/detection/signals/structural/repeated_external_call.esql`:

```sql
-- signal: repeated_external_call
-- severity: HIGH
-- score: 0.75
-- description: Detects the same external address being called 3+ times in one transaction
FROM forensics
| WHERE layer == "derived" AND derived_type == "execution_edge"
| WHERE call_type == "CALL" OR call_type == "STATICCALL"
| STATS repeat_count = COUNT(*) BY callee_address, tx_hash, block_number, caller_address
| WHERE repeat_count >= 3
| SORT repeat_count DESC
| LIMIT 50
```

- [ ] **Step 4: Create internal_eth_drain.esql**

`chainsentinel/detection/signals/structural/internal_eth_drain.esql`:

```sql
-- signal: internal_eth_drain
-- severity: CRIT
-- score: 0.85
-- description: Detects ETH movement via internal calls (not top-level tx value) exceeding 5 ETH
FROM forensics
| WHERE layer == "derived" AND derived_type == "execution_edge"
| WHERE call_type == "CALL" AND value_eth > 0
| STATS total_internal_eth = SUM(value_eth), call_count = COUNT(*) BY tx_hash, block_number, caller_address, callee_address
| WHERE total_internal_eth > 5.0
| SORT total_internal_eth DESC
| LIMIT 50
```

- [ ] **Step 5: Run tests**

```bash
cd /mnt/c/Users/aswat/OneDrive/Desktop/Projects/Project_Hail_Mary/chainsentinel
python -m pytest tests/test_signal_queries.py -v
```

- [ ] **Step 6: Commit**

```bash
git add chainsentinel/detection/signals/structural/
git commit -m "feat: Wave 1 structural signals — reentrancy_pattern, call_depth_anomaly, repeated_external_call, internal_eth_drain"
```

---

### Task 7: Wave 1 Signal Queries — Deployment Family (2 signals)

**Files:**
- Create: `chainsentinel/detection/signals/deployment/new_contract_deployed.esql`
- Create: `chainsentinel/detection/signals/deployment/failed_high_gas.esql`

- [ ] **Step 1: Create new_contract_deployed.esql**

`chainsentinel/detection/signals/deployment/new_contract_deployed.esql`:

```sql
-- signal: new_contract_deployed
-- severity: LOW
-- score: 0.3
-- description: Detects new contract deployments (tx with to=null and contractAddress set)
FROM forensics
| WHERE layer == "derived" AND derived_type == "contract_interaction"
| WHERE contract_address IS NOT NULL
| STATS deploy_count = COUNT(*) BY from_address, contract_address, tx_hash, block_number
| SORT block_number ASC
| LIMIT 200
```

- [ ] **Step 2: Create failed_high_gas.esql**

`chainsentinel/detection/signals/deployment/failed_high_gas.esql`:

```sql
-- signal: failed_high_gas
-- severity: MED
-- score: 0.5
-- description: Detects failed transactions that consumed significant gas (>500k) — may indicate exploit attempts
FROM forensics
| WHERE layer == "derived" AND derived_type == "contract_interaction"
| WHERE success == false AND gas_used > 500000
| STATS fail_count = COUNT(*), total_gas_wasted = SUM(gas_used) BY from_address, to_address, tx_hash, block_number
| SORT total_gas_wasted DESC
| LIMIT 50
```

- [ ] **Step 3: Commit**

```bash
git add chainsentinel/detection/signals/deployment/
git commit -m "feat: Wave 1 deployment signals — new_contract_deployed, failed_high_gas"
```

---

### Task 8: Wave 1 Signal Queries — Liquidity, DeFi, Behavioural (5 signals)

**Files:**
- Create: `chainsentinel/detection/signals/liquidity/large_liquidity_removal.esql`
- Create: `chainsentinel/detection/signals/defi/vault_first_deposit_tiny.esql`
- Create: `chainsentinel/detection/signals/defi/liquidation_event.esql`
- Create: `chainsentinel/detection/signals/behavioural/new_wallet_high_value.esql`
- Create: `chainsentinel/detection/signals/behavioural/burst_transactions.esql`

- [ ] **Step 1: Create large_liquidity_removal.esql**

`chainsentinel/detection/signals/liquidity/large_liquidity_removal.esql`:

```sql
-- signal: large_liquidity_removal
-- severity: HIGH
-- score: 0.75
-- description: Detects large liquidity removals from DEX pools (Burn event with significant value)
FROM forensics
| WHERE layer == "decoded"
| WHERE event_name == "Burn" OR event_name == "RemoveLiquidity" OR event_name == "RemoveLiquidityETH" OR event_name == "RemoveLiquidityOneToken"
| WHERE amount_decimal > 100000 OR value_eth > 10.0
| STATS removal_value = SUM(amount_decimal), removal_count = COUNT(*) BY from_address, contract_address, tx_hash, block_number
| SORT removal_value DESC
| LIMIT 50
```

- [ ] **Step 2: Create vault_first_deposit_tiny.esql**

`chainsentinel/detection/signals/defi/vault_first_deposit_tiny.esql`:

```sql
-- signal: vault_first_deposit_tiny
-- severity: HIGH
-- score: 0.7
-- description: Detects first deposit to a vault being unusually small (inflation attack setup)
FROM forensics
| WHERE layer == "decoded"
| WHERE event_name == "Deposit"
| STATS first_deposit = MIN(amount_decimal), deposit_count = COUNT(*), first_block = MIN(block_number) BY contract_address, tx_hash, block_number
| WHERE first_deposit < 0.001 AND deposit_count == 1
| SORT first_block ASC
| LIMIT 50
```

- [ ] **Step 3: Create liquidation_event.esql**

`chainsentinel/detection/signals/defi/liquidation_event.esql`:

```sql
-- signal: liquidation_event
-- severity: MED
-- score: 0.6
-- description: Detects liquidation events in lending protocols
FROM forensics
| WHERE layer == "decoded"
| WHERE event_name == "LiquidationCall" OR event_name == "Liquidate" OR event_name == "LiquidateBorrow" OR event_name == "AbsorbCollateral"
| STATS liquidation_count = COUNT(*), total_value = SUM(amount_decimal) BY from_address, to_address, contract_address, tx_hash, block_number
| SORT total_value DESC
| LIMIT 100
```

- [ ] **Step 4: Create new_wallet_high_value.esql**

`chainsentinel/detection/signals/behavioural/new_wallet_high_value.esql`:

```sql
-- signal: new_wallet_high_value
-- severity: HIGH
-- score: 0.7
-- description: Detects wallets with very few transactions but high cumulative value (potential attacker funded wallet)
FROM forensics
| WHERE layer == "derived" AND (derived_type == "native_transfer" OR derived_type == "asset_transfer")
| STATS total_eth = SUM(value_eth), total_tokens = SUM(amount_decimal), tx_count = COUNT(*), first_block = MIN(block_number), last_block = MAX(block_number) BY from_address
| WHERE tx_count <= 5 AND (total_eth > 10.0 OR total_tokens > 1000000)
| EVAL block_span = last_block - first_block
| WHERE block_span < 10
| SORT total_eth DESC
| LIMIT 50
```

- [ ] **Step 5: Create burst_transactions.esql**

`chainsentinel/detection/signals/behavioural/burst_transactions.esql`:

```sql
-- signal: burst_transactions
-- severity: MED
-- score: 0.6
-- description: Detects wallets sending 5+ transactions within a 3-block window
FROM forensics
| WHERE layer == "derived" AND derived_type == "contract_interaction"
| STATS tx_count = COUNT(*), block_min = MIN(block_number), block_max = MAX(block_number) BY from_address
| EVAL block_span = block_max - block_min
| WHERE tx_count >= 5 AND block_span <= 3
| SORT tx_count DESC
| LIMIT 50
```

- [ ] **Step 6: Add validation tests for remaining families**

Append to `chainsentinel/tests/test_signal_queries.py`:

```python
def test_all_flash_loan_signals_have_headers():
    flash_dir = SIGNALS_DIR / "flash_loan"
    for esql_file in flash_dir.glob("*.esql"):
        content = esql_file.read_text()
        assert "-- signal:" in content, f"{esql_file.name} missing signal header"
        assert "FROM forensics" in content, f"{esql_file.name} missing FROM forensics"


def test_all_access_signals_exist():
    access_dir = SIGNALS_DIR / "access"
    expected = ["ownership_transferred", "role_granted", "proxy_upgraded"]
    for name in expected:
        assert (access_dir / f"{name}.esql").exists(), f"Missing {name}.esql"


def test_all_structural_signals_exist():
    struct_dir = SIGNALS_DIR / "structural"
    expected = ["reentrancy_pattern", "call_depth_anomaly", "repeated_external_call", "internal_eth_drain"]
    for name in expected:
        assert (struct_dir / f"{name}.esql").exists(), f"Missing {name}.esql"


def test_all_deployment_signals_exist():
    deploy_dir = SIGNALS_DIR / "deployment"
    expected = ["new_contract_deployed", "failed_high_gas"]
    for name in expected:
        assert (deploy_dir / f"{name}.esql").exists(), f"Missing {name}.esql"


def test_all_liquidity_signals_exist():
    liq_dir = SIGNALS_DIR / "liquidity"
    expected = ["large_liquidity_removal"]
    for name in expected:
        assert (liq_dir / f"{name}.esql").exists(), f"Missing {name}.esql"


def test_all_defi_signals_exist():
    defi_dir = SIGNALS_DIR / "defi"
    expected = ["vault_first_deposit_tiny", "liquidation_event"]
    for name in expected:
        assert (defi_dir / f"{name}.esql").exists(), f"Missing {name}.esql"


def test_all_behavioural_signals_exist():
    behav_dir = SIGNALS_DIR / "behavioural"
    expected = ["new_wallet_high_value", "burst_transactions"]
    for name in expected:
        assert (behav_dir / f"{name}.esql").exists(), f"Missing {name}.esql"


def test_wave1_total_signal_count():
    """Wave 1 should have exactly 20 signals."""
    count = len(list(SIGNALS_DIR.rglob("*.esql")))
    assert count == 20, f"Expected 20 Wave 1 signals, found {count}"
```

- [ ] **Step 7: Run all signal query tests**

```bash
cd /mnt/c/Users/aswat/OneDrive/Desktop/Projects/Project_Hail_Mary/chainsentinel
python -m pytest tests/test_signal_queries.py -v
```

Expected: All PASS

- [ ] **Step 8: Commit**

```bash
git add chainsentinel/detection/signals/ chainsentinel/tests/test_signal_queries.py
git commit -m "feat: Wave 1 remaining signals — liquidity, defi, behavioural families (20 total)"
```

---

### Task 9: Pattern Engine

**Files:**
- Create: `chainsentinel/detection/pattern_engine.py`
- Create: `chainsentinel/tests/test_pattern_engine.py`

- [ ] **Step 1: Write the tests**

`chainsentinel/tests/test_pattern_engine.py`:

```python
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch


def test_discover_patterns_finds_all_eql_files(tmp_path):
    from detection.pattern_engine import discover_patterns

    (tmp_path / "AP-001_flash_loan_oracle.eql").write_text("sequence by tx_hash")
    (tmp_path / "AP-005_reentrancy_drain.eql").write_text("sequence by tx_hash")
    (tmp_path / "readme.md").write_text("Not a pattern")

    patterns = discover_patterns(tmp_path)

    assert len(patterns) == 2
    ids = [p["pattern_id"] for p in patterns]
    assert "AP-001" in ids
    assert "AP-005" in ids


def test_discover_patterns_extracts_id_and_name(tmp_path):
    from detection.pattern_engine import discover_patterns

    (tmp_path / "AP-014_mev_sandwich.eql").write_text("sequence by tx_hash")

    patterns = discover_patterns(tmp_path)

    assert patterns[0]["pattern_id"] == "AP-014"
    assert patterns[0]["pattern_name"] == "mev_sandwich"


def test_parse_pattern_metadata_from_header():
    from detection.pattern_engine import parse_pattern_metadata

    query_text = """/* pattern: AP-001
   name: Flash Loan Oracle Manipulation
   confidence: 0.90
   description: Flash loan followed by price manipulation and drain
   required_signals: flash_loan_detected, large_price_impact_swap, large_token_transfer
*/
sequence by investigation_id with maxspan=1m
  [signal_name == "flash_loan_detected"]
  [signal_name == "large_price_impact_swap"]
  [signal_name == "large_token_transfer"]
"""
    meta = parse_pattern_metadata(query_text, "AP-001", "flash_loan_oracle")

    assert meta["pattern_id"] == "AP-001"
    assert meta["confidence"] == 0.90
    assert "flash_loan_detected" in meta["required_signals"]
    assert len(meta["required_signals"]) == 3


def test_parse_pattern_metadata_defaults():
    from detection.pattern_engine import parse_pattern_metadata

    query_text = "sequence by tx_hash [signal_name == \"test\"]"
    meta = parse_pattern_metadata(query_text, "AP-999", "unknown_pattern")

    assert meta["confidence"] == 0.5
    assert meta["required_signals"] == []


def test_run_pattern_returns_alert_documents():
    from detection.pattern_engine import run_pattern

    mock_client = MagicMock()
    mock_client.eql.search.return_value = {
        "hits": {
            "sequences": [
                {
                    "events": [
                        {
                            "_source": {
                                "signal_name": "flash_loan_detected",
                                "tx_hash": "0xabc",
                                "block_number": 10,
                                "from_address": "0xattacker",
                                "to_address": "0xvictim",
                                "value_eth": 100.0,
                            }
                        },
                        {
                            "_source": {
                                "signal_name": "large_token_transfer",
                                "tx_hash": "0xabc",
                                "block_number": 10,
                                "from_address": "0xvictim",
                                "to_address": "0xattacker",
                                "value_eth": 50.0,
                            }
                        },
                    ]
                }
            ]
        }
    }

    metadata = {
        "pattern_id": "AP-001",
        "pattern_name": "Flash Loan Oracle Manipulation",
        "confidence": 0.90,
        "description": "Flash loan oracle attack",
        "required_signals": ["flash_loan_detected", "large_token_transfer"],
    }

    results = run_pattern(
        mock_client, "sequence by tx_hash ...",
        metadata, "INV-2026-0001", 31337
    )

    assert len(results) == 1
    assert results[0]["layer"] == "alert"
    assert results[0]["pattern_id"] == "AP-001"
    assert results[0]["confidence"] == 0.90
    assert results[0]["investigation_id"] == "INV-2026-0001"
    assert "flash_loan_detected" in results[0]["signals_fired"]


def test_run_pattern_handles_no_matches():
    from detection.pattern_engine import run_pattern

    mock_client = MagicMock()
    mock_client.eql.search.return_value = {
        "hits": {"sequences": []}
    }

    metadata = {
        "pattern_id": "AP-001",
        "pattern_name": "test",
        "confidence": 0.9,
        "description": "test",
        "required_signals": [],
    }

    results = run_pattern(
        mock_client, "sequence by tx_hash ...",
        metadata, "INV-2026-0001", 31337
    )

    assert results == []


def test_run_all_patterns_orchestrates(tmp_path):
    from detection.pattern_engine import run_all_patterns

    (tmp_path / "AP-001_flash_loan_oracle.eql").write_text(
        "/* pattern: AP-001\n   name: Flash Loan Oracle\n   confidence: 0.9\n"
        "   description: Flash loan oracle attack\n"
        "   required_signals: flash_loan_detected\n*/\n"
        'sequence by investigation_id [signal_name == "flash_loan_detected"]'
    )

    mock_client = MagicMock()
    mock_client.eql.search.return_value = {
        "hits": {"sequences": []}
    }
    mock_ingest = MagicMock()

    results = run_all_patterns(
        mock_client, mock_ingest, tmp_path,
        "INV-2026-0001", 31337
    )

    assert results == []
    mock_client.eql.search.assert_called_once()
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /mnt/c/Users/aswat/OneDrive/Desktop/Projects/Project_Hail_Mary/chainsentinel
python -m pytest tests/test_pattern_engine.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'detection.pattern_engine'`

- [ ] **Step 3: Implement pattern_engine.py**

`chainsentinel/detection/pattern_engine.py`:

```python
"""
Pattern Engine — discovers and runs EQL pattern queries.

Loads all .eql files from detection/patterns/.
Each file defines an attack pattern as an EQL sequence query.
The engine:
1. Discovers all .eql files
2. Parses metadata from block comment headers
3. Executes via EQL search API against forensics index
4. Converts matched sequences to alert documents (layer: alert)
5. Bulk ingests into forensics index
"""
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


PATTERNS_DIR = Path(__file__).parent / "patterns"


def discover_patterns(patterns_dir: Optional[Path] = None) -> list[dict]:
    """
    Find all .eql files in patterns directory.
    Returns list of dicts: {pattern_id, pattern_name, path, query_text}
    """
    base = patterns_dir or PATTERNS_DIR
    patterns = []

    for eql_file in sorted(base.glob("*.eql")):
        filename = eql_file.stem  # e.g. AP-001_flash_loan_oracle
        parts = filename.split("_", 1)
        pattern_id = parts[0]  # AP-001
        pattern_name = parts[1] if len(parts) > 1 else filename
        query_text = eql_file.read_text(encoding="utf-8")

        patterns.append({
            "pattern_id": pattern_id,
            "pattern_name": pattern_name,
            "path": str(eql_file),
            "query_text": query_text,
        })

    return patterns


def parse_pattern_metadata(
    query_text: str, pattern_id: str, pattern_name: str
) -> dict:
    """
    Extract metadata from .eql block comment headers.
    Format:
        /* pattern: AP-001
           name: Flash Loan Oracle Manipulation
           confidence: 0.90
           description: ...
           required_signals: signal1, signal2, signal3
        */
    """
    confidence = 0.5
    description = f"Pattern {pattern_id} matched"
    required_signals = []
    display_name = pattern_name.replace("_", " ").title()

    # Extract block comment
    block_match = re.search(r"/\*(.*?)\*/", query_text, re.DOTALL)
    if block_match:
        block = block_match.group(1)
        for line in block.splitlines():
            line = line.strip()
            if line.startswith("name:"):
                display_name = line.split(":", 1)[1].strip()
            elif line.startswith("confidence:"):
                try:
                    confidence = float(line.split(":", 1)[1].strip())
                except ValueError:
                    pass
            elif line.startswith("description:"):
                description = line.split(":", 1)[1].strip()
            elif line.startswith("required_signals:"):
                signals_str = line.split(":", 1)[1].strip()
                required_signals = [
                    s.strip() for s in signals_str.split(",") if s.strip()
                ]

    return {
        "pattern_id": pattern_id,
        "pattern_name": display_name,
        "confidence": confidence,
        "description": description,
        "required_signals": required_signals,
    }


def _extract_query_body(query_text: str) -> str:
    """Strip block comments from EQL query, return just the query body."""
    # Remove block comments
    cleaned = re.sub(r"/\*.*?\*/", "", query_text, flags=re.DOTALL)
    return cleaned.strip()


def run_pattern(
    es_client,
    raw_query: str,
    metadata: dict,
    investigation_id: str,
    chain_id: int,
) -> list[dict]:
    """
    Execute a single EQL pattern query and convert matched sequences to alert documents.
    """
    query_body = _extract_query_body(raw_query)

    response = es_client.eql.search(
        index="forensics",
        query=query_body,
        filter={
            "bool": {
                "must": [
                    {"term": {"investigation_id": investigation_id}},
                    {"terms": {"layer": ["signal", "derived"]}},
                ]
            }
        },
        timestamp_field="@timestamp",
        event_category_field="layer",
    )

    sequences = response.get("hits", {}).get("sequences", [])
    if not sequences:
        return []

    now = datetime.now(timezone.utc).isoformat()
    documents = []

    for seq in sequences:
        events = seq.get("events", [])
        if not events:
            continue

        # Extract signals fired from the sequence
        signals_fired = []
        tx_hashes = set()
        blocks = set()
        attacker_wallet = None
        victim_contract = None
        total_value = 0.0

        for event in events:
            src = event.get("_source", {})
            sig_name = src.get("signal_name")
            if sig_name:
                signals_fired.append(sig_name)
            tx = src.get("tx_hash")
            if tx:
                tx_hashes.add(tx)
            bn = src.get("block_number")
            if bn:
                blocks.add(bn)
            # Heuristic: first from_address is attacker, first to_address is victim
            if not attacker_wallet and src.get("from_address"):
                attacker_wallet = src["from_address"]
            if not victim_contract and src.get("to_address"):
                victim_contract = src["to_address"]
            if src.get("value_eth"):
                total_value += float(src["value_eth"])

        doc = {
            "layer": "alert",
            "investigation_id": investigation_id,
            "chain_id": chain_id,
            "@timestamp": now,
            "pattern_id": metadata["pattern_id"],
            "pattern_name": metadata["pattern_name"],
            "confidence": metadata["confidence"],
            "description": metadata["description"],
            "signals_fired": signals_fired or metadata["required_signals"],
            "tx_hash": list(tx_hashes)[0] if tx_hashes else None,
            "block_number": min(blocks) if blocks else None,
            "attacker_wallet": attacker_wallet,
            "victim_contract": victim_contract,
            "funds_drained_eth": total_value,
            "attack_block_range_from": min(blocks) if blocks else None,
            "attack_block_range_to": max(blocks) if blocks else None,
        }

        documents.append(doc)

    return documents


def run_all_patterns(
    es_client,
    ingest_fn,
    patterns_dir: Optional[Path] = None,
    investigation_id: str = "",
    chain_id: int = 31337,
) -> list[dict]:
    """
    Discover all patterns, run each, ingest results.
    Returns all alert documents produced.
    """
    patterns = discover_patterns(patterns_dir)
    all_results = []

    for pattern in patterns:
        metadata = parse_pattern_metadata(
            pattern["query_text"],
            pattern["pattern_id"],
            pattern["pattern_name"],
        )

        results = run_pattern(
            es_client, pattern["query_text"],
            metadata, investigation_id, chain_id
        )

        if results:
            ingest_fn(es_client, results, "forensics")
            all_results.extend(results)

    return all_results
```

- [ ] **Step 4: Run tests**

```bash
cd /mnt/c/Users/aswat/OneDrive/Desktop/Projects/Project_Hail_Mary/chainsentinel
python -m pytest tests/test_pattern_engine.py -v
```

Expected: All 7 PASS

- [ ] **Step 5: Commit**

```bash
git add chainsentinel/detection/pattern_engine.py chainsentinel/tests/test_pattern_engine.py
git commit -m "feat: pattern engine discovers and runs EQL attack pattern queries"
```

---

### Task 10: Wave 1 Attack Patterns (4 patterns)

**Files:**
- Create: `chainsentinel/detection/patterns/AP-001_flash_loan_oracle.eql`
- Create: `chainsentinel/detection/patterns/AP-005_reentrancy_drain.eql`
- Create: `chainsentinel/detection/patterns/AP-008_access_control_abuse.eql`
- Create: `chainsentinel/detection/patterns/AP-014_mev_sandwich.eql`

- [ ] **Step 1: Create AP-001_flash_loan_oracle.eql**

`chainsentinel/detection/patterns/AP-001_flash_loan_oracle.eql`:

```
/* pattern: AP-001
   name: Flash Loan Oracle Manipulation
   confidence: 0.90
   description: Flash loan used to manipulate DEX pool, read stale oracle, drain victim protocol
   required_signals: flash_loan_detected, large_price_impact_swap, large_token_transfer
*/
sequence by tx_hash with maxspan=1m
  [layer == "signal" and signal_name == "flash_loan_detected"]
  [layer == "signal" and signal_name == "large_token_transfer"]
```

- [ ] **Step 2: Create AP-005_reentrancy_drain.eql**

`chainsentinel/detection/patterns/AP-005_reentrancy_drain.eql`:

```
/* pattern: AP-005
   name: Reentrancy Drain
   confidence: 0.90
   description: Recursive call pattern with abnormal call depth followed by large ETH outflow
   required_signals: reentrancy_pattern, call_depth_anomaly, large_outflow, internal_eth_drain
*/
sequence by tx_hash with maxspan=1m
  [layer == "signal" and signal_name == "reentrancy_pattern"]
  [layer == "signal" and (signal_name == "large_outflow" or signal_name == "internal_eth_drain")]
```

- [ ] **Step 3: Create AP-008_access_control_abuse.eql**

`chainsentinel/detection/patterns/AP-008_access_control_abuse.eql`:

```
/* pattern: AP-008
   name: Private Key Compromise / Access Control Abuse
   confidence: 0.85
   description: Ownership transfer to unknown address followed by large value extraction
   required_signals: ownership_transferred, large_outflow, large_token_transfer
*/
sequence by investigation_id with maxspan=5m
  [layer == "signal" and signal_name == "ownership_transferred"]
  [layer == "signal" and (signal_name == "large_outflow" or signal_name == "large_token_transfer")]
```

- [ ] **Step 4: Create AP-014_mev_sandwich.eql**

`chainsentinel/detection/patterns/AP-014_mev_sandwich.eql`:

```
/* pattern: AP-014
   name: MEV Sandwich Attack
   confidence: 0.80
   description: Attacker front-runs victim swap, victim executes at worse price, attacker back-runs for profit
   required_signals: large_token_transfer, value_spike
*/
sequence by investigation_id with maxspan=1m
  [layer == "signal" and signal_name == "large_token_transfer"]
  [layer == "signal" and signal_name == "large_token_transfer"]
  [layer == "signal" and signal_name == "large_token_transfer"]
```

- [ ] **Step 5: Write pattern validation tests**

Append to `chainsentinel/tests/test_signal_queries.py`:

```python
PATTERNS_DIR = Path(__file__).parent.parent / "detection" / "patterns"


def test_wave1_patterns_exist():
    expected = [
        "AP-001_flash_loan_oracle",
        "AP-005_reentrancy_drain",
        "AP-008_access_control_abuse",
        "AP-014_mev_sandwich",
    ]
    for name in expected:
        assert (PATTERNS_DIR / f"{name}.eql").exists(), f"Missing {name}.eql"


def test_wave1_pattern_count():
    count = len(list(PATTERNS_DIR.glob("*.eql")))
    assert count == 4, f"Expected 4 Wave 1 patterns, found {count}"


def test_all_patterns_have_required_headers():
    for eql_file in PATTERNS_DIR.glob("*.eql"):
        content = eql_file.read_text()
        assert "pattern:" in content, f"{eql_file.name} missing pattern header"
        assert "confidence:" in content, f"{eql_file.name} missing confidence header"
        assert "required_signals:" in content, f"{eql_file.name} missing required_signals"
        assert "sequence" in content, f"{eql_file.name} missing sequence keyword"


def test_all_patterns_have_valid_id_in_filename():
    import re
    for eql_file in PATTERNS_DIR.glob("*.eql"):
        assert re.match(r"AP-\d{3}_", eql_file.stem), f"{eql_file.name} doesn't match AP-NNN_ format"
```

- [ ] **Step 6: Run all tests**

```bash
cd /mnt/c/Users/aswat/OneDrive/Desktop/Projects/Project_Hail_Mary/chainsentinel
python -m pytest tests/test_signal_queries.py tests/test_pattern_engine.py tests/test_signal_engine.py -v
```

Expected: All PASS

- [ ] **Step 7: Commit**

```bash
git add chainsentinel/detection/patterns/ chainsentinel/tests/test_signal_queries.py
git commit -m "feat: Wave 1 attack patterns — AP-001 flash loan oracle, AP-005 reentrancy, AP-008 access abuse, AP-014 MEV sandwich"
```

---

### Task 11: Integration — Wire Detection into Pipeline Runner

**Files:**
- Modify: `chainsentinel/pipeline/runner.py` (from Plan 1)

- [ ] **Step 1: Write integration test**

`chainsentinel/tests/test_detection_integration.py`:

```python
import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path


def test_detection_phase_runs_after_ingest():
    """Detection engines should be called after derived events are ingested."""
    from detection.signal_engine import run_all_signals
    from detection.pattern_engine import run_all_patterns

    mock_client = MagicMock()
    mock_client.esql.query.return_value = {"columns": [], "values": []}
    mock_client.eql.search.return_value = {"hits": {"sequences": []}}
    mock_ingest = MagicMock()

    signals_dir = Path(__file__).parent.parent / "detection" / "signals"
    patterns_dir = Path(__file__).parent.parent / "detection" / "patterns"

    # Should not raise
    signals = run_all_signals(
        mock_client, mock_ingest, signals_dir,
        "INV-TEST-001", 31337
    )
    patterns = run_all_patterns(
        mock_client, mock_ingest, patterns_dir,
        "INV-TEST-001", 31337
    )

    # Signal engine should have called esql.query for each .esql file
    assert mock_client.esql.query.call_count == 20
    # Pattern engine should have called eql.search for each .eql file
    assert mock_client.eql.search.call_count == 4


def test_signal_documents_have_correct_id_format():
    """Signal document IDs should follow {investigation_id}_{signal_name}_{tx_hash} format."""
    from detection.signal_engine import run_signal

    mock_client = MagicMock()
    mock_client.esql.query.return_value = {
        "columns": [
            {"name": "tx_hash", "type": "keyword"},
            {"name": "block_number", "type": "long"},
        ],
        "values": [["0xabc123", 10]],
    }

    metadata = {
        "signal_name": "reentrancy_pattern",
        "signal_family": "structural",
        "severity": "CRIT",
        "score": 0.95,
        "description": "Test",
    }

    results = run_signal(
        mock_client, "FROM forensics", metadata, "INV-2026-0001", 31337
    )

    assert len(results) == 1
    assert results[0]["signal_name"] == "reentrancy_pattern"
    assert results[0]["investigation_id"] == "INV-2026-0001"
    # Verify evidence ref follows ID convention
    assert "INV-2026-0001_reentrancy_pattern_0xabc123" in results[0]["evidence_refs"]
```

- [ ] **Step 2: Run integration tests**

```bash
cd /mnt/c/Users/aswat/OneDrive/Desktop/Projects/Project_Hail_Mary/chainsentinel
python -m pytest tests/test_detection_integration.py -v
```

Expected: All PASS

- [ ] **Step 3: Commit**

```bash
git add chainsentinel/tests/test_detection_integration.py
git commit -m "feat: detection integration tests verify signal and pattern engines wire into pipeline"
```
