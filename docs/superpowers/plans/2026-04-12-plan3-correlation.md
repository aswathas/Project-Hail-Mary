# ChainSentinel Correlation Engine — Implementation Plan (Plan 3 of 6)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the Python correlation engine — fund tracing (BFS 5 hops with haircut taint), wallet clustering, mixer/bridge/CEX detection, and known address label database. After this plan, the pipeline can trace stolen funds across hops, cluster attacker wallets, and tag known entities.

**Architecture:** Four Python modules in `chainsentinel/correlation/`. Fund tracing uses BFS from a seed wallet querying ES `fund_flow_edge` documents, applying haircut taint scoring (mixer: 0.7, bridge: 0.8). Clustering groups wallets by shared funding, timing, and interaction patterns. Mixer detection matches addresses against known contract sets. Label DB provides OFAC/exploiter/CEX lookups. All outputs are written to ES as `layer: attacker` documents.

**Tech Stack:** Python 3.11+, elasticsearch-py 8.x, pytest

**Spec reference:** `docs/superpowers/specs/2026-04-12-chainsentinel-design.md` section 8

**Depends on:** Plan 1 (ES indices, ingest, derived events)

---

## File Structure

```
chainsentinel/
├── correlation/
│   ├── __init__.py
│   ├── fund_trace.py               ← BFS fund tracing, 5 hops, haircut taint
│   ├── clustering.py               ← wallet clustering by shared patterns
│   ├── mixer_detect.py             ← Tornado Cash, bridges, CEX matching
│   └── label_db.py                 ← OFAC, known exploiters, CEX wallets
└── tests/
    ├── test_fund_trace.py
    ├── test_clustering.py
    ├── test_mixer_detect.py
    └── test_label_db.py
```

---

### Task 1: Correlation Module Scaffolding

**Files:**
- Create: `chainsentinel/correlation/__init__.py`

- [ ] **Step 1: Create directory and init**

```bash
cd /mnt/c/Users/aswat/OneDrive/Desktop/Projects/Project_Hail_Mary
mkdir -p chainsentinel/correlation
touch chainsentinel/correlation/__init__.py
```

- [ ] **Step 2: Commit**

```bash
git add chainsentinel/correlation/__init__.py
git commit -m "feat: correlation module scaffolding"
```

---

### Task 2: Label Database — Known Address Lookups

**Files:**
- Create: `chainsentinel/correlation/label_db.py`
- Create: `chainsentinel/tests/test_label_db.py`

- [ ] **Step 1: Write the tests**

`chainsentinel/tests/test_label_db.py`:

```python
import pytest


def test_label_known_tornado_cash_address():
    from correlation.label_db import get_label

    label = get_label("0xd90e2f925da726b50c4ed8d0fb90ad053324f31b")
    assert label["type"] == "mixer_contract"
    assert "tornado" in label["name"].lower()


def test_label_known_cex_address():
    from correlation.label_db import get_label

    # Binance hot wallet
    label = get_label("0x28c6c06298d514db089934071355e5743bf21d60")
    assert label["type"] == "cex_deposit"
    assert "binance" in label["name"].lower()


def test_label_unknown_address():
    from correlation.label_db import get_label

    label = get_label("0x0000000000000000000000000000000000000001")
    assert label["type"] == "unknown"
    assert label["name"] == "Unknown"


def test_label_case_insensitive():
    from correlation.label_db import get_label

    label_lower = get_label("0xd90e2f925da726b50c4ed8d0fb90ad053324f31b")
    label_upper = get_label("0xD90e2f925DA726b50C4Ed8D0Fb90AD053324f31b")
    assert label_lower["type"] == label_upper["type"]


def test_is_ofac_sanctioned_true():
    from correlation.label_db import is_ofac_sanctioned

    # Tornado Cash Router
    assert is_ofac_sanctioned("0xd90e2f925da726b50c4ed8d0fb90ad053324f31b") is True


def test_is_ofac_sanctioned_false():
    from correlation.label_db import is_ofac_sanctioned

    assert is_ofac_sanctioned("0x0000000000000000000000000000000000000001") is False


def test_is_mixer_true():
    from correlation.label_db import is_mixer

    assert is_mixer("0xd90e2f925da726b50c4ed8d0fb90ad053324f31b") is True


def test_is_mixer_false():
    from correlation.label_db import is_mixer

    assert is_mixer("0x28c6c06298d514db089934071355e5743bf21d60") is False


def test_is_bridge_true():
    from correlation.label_db import is_bridge

    # Hop Protocol bridge
    assert is_bridge("0xb8901acb165ed027e32754e0ffe830802919727f") is True


def test_is_cex_true():
    from correlation.label_db import is_cex

    assert is_cex("0x28c6c06298d514db089934071355e5743bf21d60") is True


def test_get_all_labels_for_address():
    from correlation.label_db import get_all_labels

    labels = get_all_labels("0xd90e2f925da726b50c4ed8d0fb90ad053324f31b")
    assert "mixer_contract" in labels
    assert "ofac_sanctioned" in labels


def test_get_all_labels_unknown():
    from correlation.label_db import get_all_labels

    labels = get_all_labels("0x0000000000000000000000000000000000000001")
    assert labels == ["unknown"]


def test_batch_label_multiple_addresses():
    from correlation.label_db import batch_label

    addresses = [
        "0xd90e2f925da726b50c4ed8d0fb90ad053324f31b",
        "0x28c6c06298d514db089934071355e5743bf21d60",
        "0x0000000000000000000000000000000000000001",
    ]
    results = batch_label(addresses)

    assert len(results) == 3
    assert results["0xd90e2f925da726b50c4ed8d0fb90ad053324f31b"]["type"] == "mixer_contract"
    assert results["0x28c6c06298d514db089934071355e5743bf21d60"]["type"] == "cex_deposit"
    assert results["0x0000000000000000000000000000000000000001"]["type"] == "unknown"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /mnt/c/Users/aswat/OneDrive/Desktop/Projects/Project_Hail_Mary/chainsentinel
python -m pytest tests/test_label_db.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'correlation.label_db'`

- [ ] **Step 3: Implement label_db.py**

`chainsentinel/correlation/label_db.py`:

```python
"""
Label Database — known address classification.

Provides labels for known addresses: OFAC sanctioned entities,
known exploiter wallets, CEX hot wallets, mixer contracts,
bridge contracts, and protocol treasuries.

All addresses are stored and compared in lowercase.
"""


# ── Tornado Cash contracts (OFAC sanctioned) ────────────────────────────────
TORNADO_CASH = {
    "0xd90e2f925da726b50c4ed8d0fb90ad053324f31b": "Tornado Cash Router",
    "0x12d66f87a04a9e220743712ce6d9bb1b5616b8fc": "Tornado Cash 0.1 ETH",
    "0x47ce0c6ed5b0ce3d3a51fdb1c52dc66a7c3c2936": "Tornado Cash 1 ETH",
    "0x910cbd523d972eb0a6f4cae4618ad62622b39dbf": "Tornado Cash 10 ETH",
    "0xa160cdab225685da1d56aa342ad8841c3b53f291": "Tornado Cash 100 ETH",
    "0xd4b88df4d29f5cedd6857912842cff3b20c8cfa3": "Tornado Cash 100 DAI",
    "0xfd8610d20aa15b7b2e3be39b396a1bc3516c7144": "Tornado Cash 1000 DAI",
    "0x07687e702b410fa43f4cb4af7fa097918ffd2730": "Tornado Cash 10000 DAI",
    "0x94a1b5cdb22c43faab4abeb5c74999895464bdaf": "Tornado Cash Governance",
    "0x722122df12d4e14e13ac3b6895a86e84145b6967": "Tornado Cash Proxy",
}

# ── Bridge contracts ────────────────────────────────────────────────────────
BRIDGES = {
    "0xb8901acb165ed027e32754e0ffe830802919727f": "Hop Protocol Bridge",
    "0x3ee18b2214aff97000d974cf647e7c347e8fa585": "Wormhole Token Bridge",
    "0x3014ca10b91cb3d0ad85fef7a3cb95bcac9c0f79": "LayerZero Endpoint",
    "0x4d73adb72bc3dd368966edd0f0b2148401a178e2": "Across Protocol Bridge",
    "0x8731d54e9d02c286767d56ac03e8037c07e01e98": "Stargate Finance Router",
    "0x99c9fc46f92e8a1c0dec1b1747d010903e884be1": "Optimism Gateway",
    "0x3307d64cf6deab3b02e1f36fd0bfce6cba76f11c": "Arbitrum Gateway",
    "0xa0c68c638235ee32657e8f720a23cec1bfc6c4d4": "Polygon Bridge",
}

# ── CEX hot wallets ─────────────────────────────────────────────────────────
CEX_WALLETS = {
    "0x28c6c06298d514db089934071355e5743bf21d60": "Binance Hot Wallet 14",
    "0x21a31ee1afc51d94c2efccaa2092ad1028285549": "Binance Hot Wallet 15",
    "0xdfd5293d8e347dfe59e90efd55b2956a1343963d": "Binance Hot Wallet 16",
    "0x56eddb7aa87536c09ccc2793473599fd21a8b17f": "Binance Hot Wallet 17",
    "0xa9d1e08c7793af67e9d92fe308d5697fb81d3e43": "Coinbase Hot Wallet 10",
    "0x71660c4005ba85c37ccec55d0c4493e66fe775d3": "Coinbase Hot Wallet 11",
    "0x503828976d22510aad0201ac7ec88293211d23da": "Coinbase Hot Wallet 12",
    "0x6cc5f688a315f3dc28a7781717a9a798a59fda7b": "OKX Hot Wallet",
    "0x98ec059dc3adfbdd63429227d09cb52bc0a7586d": "Kraken Hot Wallet 13",
    "0x267be1c1d684f78cb4f6a176c4911b741e4ffdc0": "Kraken Hot Wallet 14",
    "0xf89d7b9c864f589bbf53a82105107622b35eaa40": "Bybit Hot Wallet",
}

# ── Known exploiter wallets ─────────────────────────────────────────────────
KNOWN_EXPLOITERS = {
    "0xb624c4aecfad7eb036c29f22cc3c7e5400b4470e": "Ronin Bridge Exploiter",
    "0x098b716b8aaf21512996dc57eb0615e2383e2f96": "Wormhole Exploiter",
    "0x0248f752802b2cfb4373cc0c3bc3964429385c26": "Nomad Bridge Exploiter",
}

# ── Protocol treasuries / known safe ────────────────────────────────────────
PROTOCOL_TREASURIES = {
    "0x40ec5b33f54e0e8a33a975908c5ba1c14e5bbbdf": "Polygon Treasury",
    "0xbe8e3e3618f7474f8cb1d074a26affef007e98fb": "Lido DAO Treasury",
}


# ── Build unified lookup (all lowercase) ────────────────────────────────────
_LABEL_DB: dict[str, dict] = {}


def _init_db():
    global _LABEL_DB
    if _LABEL_DB:
        return

    for addr, name in TORNADO_CASH.items():
        _LABEL_DB[addr.lower()] = {
            "type": "mixer_contract",
            "name": name,
            "ofac": True,
            "tags": ["mixer_contract", "ofac_sanctioned"],
        }

    for addr, name in BRIDGES.items():
        _LABEL_DB[addr.lower()] = {
            "type": "bridge_contract",
            "name": name,
            "ofac": False,
            "tags": ["bridge_contract"],
        }

    for addr, name in CEX_WALLETS.items():
        _LABEL_DB[addr.lower()] = {
            "type": "cex_deposit",
            "name": name,
            "ofac": False,
            "tags": ["cex_deposit"],
        }

    for addr, name in KNOWN_EXPLOITERS.items():
        _LABEL_DB[addr.lower()] = {
            "type": "known_exploiter",
            "name": name,
            "ofac": True,
            "tags": ["known_exploiter", "ofac_sanctioned"],
        }

    for addr, name in PROTOCOL_TREASURIES.items():
        _LABEL_DB[addr.lower()] = {
            "type": "protocol_treasury",
            "name": name,
            "ofac": False,
            "tags": ["protocol_treasury"],
        }


def get_label(address: str) -> dict:
    """Get the primary label for an address."""
    _init_db()
    entry = _LABEL_DB.get(address.lower())
    if entry:
        return {"type": entry["type"], "name": entry["name"]}
    return {"type": "unknown", "name": "Unknown"}


def is_ofac_sanctioned(address: str) -> bool:
    """Check if address is on OFAC sanctions list."""
    _init_db()
    entry = _LABEL_DB.get(address.lower())
    return entry.get("ofac", False) if entry else False


def is_mixer(address: str) -> bool:
    """Check if address is a known mixer contract."""
    _init_db()
    entry = _LABEL_DB.get(address.lower())
    return entry.get("type") == "mixer_contract" if entry else False


def is_bridge(address: str) -> bool:
    """Check if address is a known bridge contract."""
    _init_db()
    entry = _LABEL_DB.get(address.lower())
    return entry.get("type") == "bridge_contract" if entry else False


def is_cex(address: str) -> bool:
    """Check if address is a known CEX hot wallet."""
    _init_db()
    entry = _LABEL_DB.get(address.lower())
    return entry.get("type") == "cex_deposit" if entry else False


def get_all_labels(address: str) -> list[str]:
    """Get all tags for an address."""
    _init_db()
    entry = _LABEL_DB.get(address.lower())
    if entry:
        return entry["tags"]
    return ["unknown"]


def batch_label(addresses: list[str]) -> dict[str, dict]:
    """Label multiple addresses at once."""
    return {addr: get_label(addr) for addr in addresses}
```

- [ ] **Step 4: Run tests**

```bash
cd /mnt/c/Users/aswat/OneDrive/Desktop/Projects/Project_Hail_Mary/chainsentinel
python -m pytest tests/test_label_db.py -v
```

Expected: All 13 PASS

- [ ] **Step 5: Commit**

```bash
git add chainsentinel/correlation/label_db.py chainsentinel/tests/test_label_db.py
git commit -m "feat: label database with OFAC, CEX, mixer, bridge, exploiter address lookups"
```

---

### Task 3: Mixer Detection

**Files:**
- Create: `chainsentinel/correlation/mixer_detect.py`
- Create: `chainsentinel/tests/test_mixer_detect.py`

- [ ] **Step 1: Write the tests**

`chainsentinel/tests/test_mixer_detect.py`:

```python
import pytest
from unittest.mock import MagicMock


def test_classify_address_tornado_cash():
    from correlation.mixer_detect import classify_address

    result = classify_address("0xd90e2f925da726b50c4ed8d0fb90ad053324f31b")
    assert result["category"] == "mixer"
    assert result["protocol"] == "Tornado Cash"
    assert result["risk_level"] == "critical"


def test_classify_address_bridge():
    from correlation.mixer_detect import classify_address

    result = classify_address("0xb8901acb165ed027e32754e0ffe830802919727f")
    assert result["category"] == "bridge"
    assert result["risk_level"] == "high"


def test_classify_address_cex():
    from correlation.mixer_detect import classify_address

    result = classify_address("0x28c6c06298d514db089934071355e5743bf21d60")
    assert result["category"] == "cex"
    assert result["risk_level"] == "medium"


def test_classify_address_unknown():
    from correlation.mixer_detect import classify_address

    result = classify_address("0x0000000000000000000000000000000000000001")
    assert result["category"] == "unknown"
    assert result["risk_level"] == "low"


def test_detect_exit_routes_finds_mixer_deposits():
    from correlation.mixer_detect import detect_exit_routes

    mock_client = MagicMock()
    mock_client.search.return_value = {
        "hits": {
            "hits": [
                {
                    "_source": {
                        "to_address": "0xd90e2f925da726b50c4ed8d0fb90ad053324f31b",
                        "from_address": "0xattacker",
                        "value_eth": 50.0,
                        "tx_hash": "0xexit1",
                        "block_number": 100,
                    }
                },
                {
                    "_source": {
                        "to_address": "0x28c6c06298d514db089934071355e5743bf21d60",
                        "from_address": "0xattacker",
                        "value_eth": 30.0,
                        "tx_hash": "0xexit2",
                        "block_number": 101,
                    }
                },
            ]
        }
    }

    exits = detect_exit_routes(mock_client, "0xattacker", "INV-001")

    assert len(exits) == 2
    mixer_exit = [e for e in exits if e["category"] == "mixer"][0]
    assert mixer_exit["value_eth"] == 50.0
    cex_exit = [e for e in exits if e["category"] == "cex"][0]
    assert cex_exit["value_eth"] == 30.0


def test_detect_exit_routes_no_results():
    from correlation.mixer_detect import detect_exit_routes

    mock_client = MagicMock()
    mock_client.search.return_value = {"hits": {"hits": []}}

    exits = detect_exit_routes(mock_client, "0xclean", "INV-001")
    assert exits == []


def test_compute_taint_haircut_mixer():
    from correlation.mixer_detect import compute_taint_haircut

    result = compute_taint_haircut(1.0, "mixer")
    assert result == pytest.approx(0.7)


def test_compute_taint_haircut_bridge():
    from correlation.mixer_detect import compute_taint_haircut

    result = compute_taint_haircut(1.0, "bridge")
    assert result == pytest.approx(0.8)


def test_compute_taint_haircut_cex():
    from correlation.mixer_detect import compute_taint_haircut

    result = compute_taint_haircut(1.0, "cex")
    assert result == pytest.approx(0.9)


def test_compute_taint_haircut_unknown():
    from correlation.mixer_detect import compute_taint_haircut

    result = compute_taint_haircut(1.0, "unknown")
    assert result == pytest.approx(1.0)


def test_taint_never_reaches_zero():
    from correlation.mixer_detect import compute_taint_haircut

    taint = 1.0
    for _ in range(100):
        taint = compute_taint_haircut(taint, "mixer")
    assert taint > 0.0
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /mnt/c/Users/aswat/OneDrive/Desktop/Projects/Project_Hail_Mary/chainsentinel
python -m pytest tests/test_mixer_detect.py -v
```

Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Implement mixer_detect.py**

`chainsentinel/correlation/mixer_detect.py`:

```python
"""
Mixer Detection — identifies interactions with mixers, bridges, and CEX deposits.

Classifies destination addresses and computes taint haircut scores
for fund tracing through obfuscation layers.

Haircut values (from spec):
  - Mixer (Tornado Cash): taint * 0.7
  - Bridge: taint * 0.8
  - CEX: taint * 0.9
  - Unknown/direct: taint * 1.0 (no reduction)
  - Taint never reaches zero (minimum 0.01)
"""
from correlation.label_db import (
    get_label, is_mixer, is_bridge, is_cex, is_ofac_sanctioned,
)


# Haircut multipliers per category
TAINT_HAIRCUTS = {
    "mixer": 0.7,
    "bridge": 0.8,
    "cex": 0.9,
    "unknown": 1.0,
    "known_exploiter": 1.0,
    "protocol_treasury": 1.0,
}

RISK_LEVELS = {
    "mixer": "critical",
    "bridge": "high",
    "cex": "medium",
    "known_exploiter": "critical",
    "protocol_treasury": "low",
    "unknown": "low",
}

# Category mapping from label_db types
CATEGORY_MAP = {
    "mixer_contract": "mixer",
    "bridge_contract": "bridge",
    "cex_deposit": "cex",
    "known_exploiter": "known_exploiter",
    "protocol_treasury": "protocol_treasury",
    "unknown": "unknown",
}


def classify_address(address: str) -> dict:
    """
    Classify an address by its role in fund obfuscation.
    Returns: {category, protocol, risk_level, ofac}
    """
    label = get_label(address)
    label_type = label["type"]
    category = CATEGORY_MAP.get(label_type, "unknown")

    return {
        "address": address.lower(),
        "category": category,
        "protocol": label["name"],
        "risk_level": RISK_LEVELS.get(category, "low"),
        "ofac": is_ofac_sanctioned(address),
    }


def detect_exit_routes(
    es_client,
    wallet_address: str,
    investigation_id: str,
) -> list[dict]:
    """
    Query ES for all outgoing transfers from a wallet to known exit routes
    (mixers, bridges, CEX deposits).
    """
    query = {
        "bool": {
            "must": [
                {"term": {"investigation_id": investigation_id}},
                {"term": {"from_address": wallet_address.lower()}},
                {"term": {"layer": "derived"}},
                {"terms": {"derived_type": ["native_transfer", "asset_transfer"]}},
            ]
        }
    }

    response = es_client.search(
        index="forensics",
        query=query,
        size=1000,
        sort=[{"block_number": "asc"}],
    )

    exits = []
    for hit in response.get("hits", {}).get("hits", []):
        src = hit["_source"]
        to_addr = src.get("to_address", "")
        classification = classify_address(to_addr)

        if classification["category"] in ("mixer", "bridge", "cex"):
            exits.append({
                "to_address": to_addr,
                "category": classification["category"],
                "protocol": classification["protocol"],
                "risk_level": classification["risk_level"],
                "ofac": classification["ofac"],
                "value_eth": src.get("value_eth", 0.0),
                "tx_hash": src.get("tx_hash"),
                "block_number": src.get("block_number"),
            })

    return exits


def compute_taint_haircut(
    current_taint: float,
    category: str,
    min_taint: float = 0.01,
) -> float:
    """
    Apply haircut to taint score based on the category of address
    the funds passed through. Taint never reaches zero.
    """
    multiplier = TAINT_HAIRCUTS.get(category, 1.0)
    new_taint = current_taint * multiplier
    return max(new_taint, min_taint)
```

- [ ] **Step 4: Run tests**

```bash
cd /mnt/c/Users/aswat/OneDrive/Desktop/Projects/Project_Hail_Mary/chainsentinel
python -m pytest tests/test_mixer_detect.py -v
```

Expected: All 11 PASS

- [ ] **Step 5: Commit**

```bash
git add chainsentinel/correlation/mixer_detect.py chainsentinel/tests/test_mixer_detect.py
git commit -m "feat: mixer detection with address classification and taint haircut scoring"
```

---

### Task 4: Fund Tracing — BFS with Taint

**Files:**
- Create: `chainsentinel/correlation/fund_trace.py`
- Create: `chainsentinel/tests/test_fund_trace.py`

- [ ] **Step 1: Write the tests**

`chainsentinel/tests/test_fund_trace.py`:

```python
import pytest
from unittest.mock import MagicMock, patch
from collections import deque


def _mock_es_transfer_response(transfers):
    """Helper to build mock ES search response from transfer tuples."""
    hits = []
    for (from_addr, to_addr, value_eth, tx_hash, block_num) in transfers:
        hits.append({
            "_source": {
                "from_address": from_addr,
                "to_address": to_addr,
                "value_eth": value_eth,
                "tx_hash": tx_hash,
                "block_number": block_num,
                "token_address": None,
                "derived_type": "native_transfer",
            }
        })
    return {"hits": {"hits": hits}}


def test_trace_forward_single_hop():
    from correlation.fund_trace import trace_funds

    mock_client = MagicMock()
    # Hop 1: attacker sends to intermediary
    mock_client.search.side_effect = [
        _mock_es_transfer_response([
            ("0xattacker", "0xintermediary", 10.0, "0xtx1", 100),
        ]),
        # Hop 2 from intermediary: no further transfers
        _mock_es_transfer_response([]),
    ]

    trail = trace_funds(
        mock_client, "0xattacker", "INV-001",
        direction="forward", max_hops=2
    )

    assert len(trail) == 1
    assert trail[0]["from_address"] == "0xattacker"
    assert trail[0]["to_address"] == "0xintermediary"
    assert trail[0]["hop_number"] == 1
    assert trail[0]["taint_score"] == pytest.approx(1.0)


def test_trace_forward_multi_hop():
    from correlation.fund_trace import trace_funds

    mock_client = MagicMock()
    mock_client.search.side_effect = [
        # Hop 1
        _mock_es_transfer_response([
            ("0xattacker", "0xhop1", 10.0, "0xtx1", 100),
        ]),
        # Hop 2
        _mock_es_transfer_response([
            ("0xhop1", "0xhop2", 8.0, "0xtx2", 101),
        ]),
        # Hop 3
        _mock_es_transfer_response([
            ("0xhop2", "0xhop3", 6.0, "0xtx3", 102),
        ]),
        # Hop 4: no more
        _mock_es_transfer_response([]),
    ]

    trail = trace_funds(
        mock_client, "0xattacker", "INV-001",
        direction="forward", max_hops=5
    )

    assert len(trail) == 3
    assert trail[0]["hop_number"] == 1
    assert trail[1]["hop_number"] == 2
    assert trail[2]["hop_number"] == 3


def test_trace_backward():
    from correlation.fund_trace import trace_funds

    mock_client = MagicMock()
    mock_client.search.side_effect = [
        # Hop 1 backward: who funded attacker?
        _mock_es_transfer_response([
            ("0xfunder", "0xattacker", 15.0, "0xtx0", 95),
        ]),
        # Hop 2: who funded funder?
        _mock_es_transfer_response([]),
    ]

    trail = trace_funds(
        mock_client, "0xattacker", "INV-001",
        direction="backward", max_hops=5
    )

    assert len(trail) == 1
    assert trail[0]["from_address"] == "0xfunder"
    assert trail[0]["to_address"] == "0xattacker"
    assert trail[0]["direction"] == "backward"


def test_trace_respects_max_hops():
    from correlation.fund_trace import trace_funds

    mock_client = MagicMock()
    # Create infinite chain of hops
    def make_response(call_count=[0]):
        call_count[0] += 1
        hop = call_count[0]
        return _mock_es_transfer_response([
            (f"0xhop{hop}", f"0xhop{hop+1}", 10.0, f"0xtx{hop}", 100 + hop),
        ])

    mock_client.search.side_effect = [make_response() for _ in range(6)]

    trail = trace_funds(
        mock_client, "0xhop1", "INV-001",
        direction="forward", max_hops=3
    )

    # Should stop at 3 hops
    assert len(trail) <= 3


def test_trace_applies_taint_haircut_through_mixer():
    from correlation.fund_trace import trace_funds

    mock_client = MagicMock()
    # Tornado Cash address
    tornado = "0xd90e2f925da726b50c4ed8d0fb90ad053324f31b"
    mock_client.search.side_effect = [
        # Hop 1: attacker -> tornado cash
        _mock_es_transfer_response([
            ("0xattacker", tornado, 10.0, "0xtx1", 100),
        ]),
        # Hop 2: tornado -> destination
        _mock_es_transfer_response([
            (tornado, "0xdest", 10.0, "0xtx2", 200),
        ]),
        # No more hops
        _mock_es_transfer_response([]),
    ]

    trail = trace_funds(
        mock_client, "0xattacker", "INV-001",
        direction="forward", max_hops=5
    )

    assert len(trail) == 2
    # First hop: full taint
    assert trail[0]["taint_score"] == pytest.approx(1.0)
    # Second hop: after mixer haircut (0.7)
    assert trail[1]["taint_score"] == pytest.approx(0.7)


def test_trace_avoids_cycles():
    from correlation.fund_trace import trace_funds

    mock_client = MagicMock()
    mock_client.search.side_effect = [
        # Hop 1: A -> B
        _mock_es_transfer_response([
            ("0xa", "0xb", 10.0, "0xtx1", 100),
        ]),
        # Hop 2: B -> A (cycle!)
        _mock_es_transfer_response([
            ("0xb", "0xa", 5.0, "0xtx2", 101),
        ]),
        # Should not re-process A
        _mock_es_transfer_response([]),
    ]

    trail = trace_funds(
        mock_client, "0xa", "INV-001",
        direction="forward", max_hops=5
    )

    # Should trace A->B and B->A but not revisit A
    visited_froms = [t["from_address"] for t in trail]
    assert visited_froms.count("0xa") <= 1


def test_trace_produces_fund_flow_edge_documents():
    from correlation.fund_trace import trace_funds

    mock_client = MagicMock()
    mock_client.search.side_effect = [
        _mock_es_transfer_response([
            ("0xattacker", "0xdest", 10.0, "0xtx1", 100),
        ]),
        _mock_es_transfer_response([]),
    ]

    trail = trace_funds(
        mock_client, "0xattacker", "INV-001",
        direction="forward", max_hops=5
    )

    doc = trail[0]
    assert doc["layer"] == "derived"
    assert doc["derived_type"] == "fund_flow_edge"
    assert "investigation_id" in doc
    assert "taint_score" in doc
    assert "hop_number" in doc
    assert "direction" in doc
    assert "tx_hash" in doc


def test_build_fund_trail_document():
    from correlation.fund_trace import build_fund_trail_document

    trail = [
        {"from_address": "0xa", "to_address": "0xb", "value_eth": 10.0, "hop_number": 1},
        {"from_address": "0xb", "to_address": "0xc", "value_eth": 8.0, "hop_number": 2},
    ]

    doc = build_fund_trail_document(
        "0xa", trail, "INV-001", 31337
    )

    assert doc["layer"] == "attacker"
    assert doc["attacker_type"] == "fund_trail"
    assert doc["fund_trail_hops"] == 2
    assert doc["investigation_id"] == "INV-001"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /mnt/c/Users/aswat/OneDrive/Desktop/Projects/Project_Hail_Mary/chainsentinel
python -m pytest tests/test_fund_trace.py -v
```

Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Implement fund_trace.py**

`chainsentinel/correlation/fund_trace.py`:

```python
"""
Fund Tracing — BFS fund tracing with haircut taint scoring.

Starting from a seed wallet, traces funds forward (where did they go)
or backward (where did they come from) up to max_hops (default 5).

Taint scoring: funds passing through a mixer receive taint * 0.7,
through a bridge * 0.8. Taint never reaches zero (min 0.01).

Output: fund_flow_edge documents (layer: derived, derived_type: fund_flow_edge)
and a fund_trail summary document (layer: attacker, attacker_type: fund_trail).
"""
from collections import deque
from datetime import datetime, timezone
from typing import Optional

from correlation.mixer_detect import classify_address, compute_taint_haircut


def _query_transfers(
    es_client,
    address: str,
    investigation_id: str,
    direction: str,
) -> list[dict]:
    """
    Query ES for transfers to/from an address.
    direction='forward': address is the sender (from_address)
    direction='backward': address is the receiver (to_address)
    """
    if direction == "forward":
        address_field = "from_address"
    else:
        address_field = "to_address"

    query = {
        "bool": {
            "must": [
                {"term": {"investigation_id": investigation_id}},
                {"term": {address_field: address.lower()}},
                {"term": {"layer": "derived"}},
                {"terms": {"derived_type": ["native_transfer", "asset_transfer"]}},
            ]
        }
    }

    response = es_client.search(
        index="forensics",
        query=query,
        size=500,
        sort=[{"block_number": "asc"}],
    )

    transfers = []
    for hit in response.get("hits", {}).get("hits", []):
        transfers.append(hit["_source"])

    return transfers


def trace_funds(
    es_client,
    seed_address: str,
    investigation_id: str,
    direction: str = "forward",
    max_hops: int = 5,
    chain_id: int = 31337,
) -> list[dict]:
    """
    BFS fund tracing from seed address.

    Args:
        es_client: Elasticsearch client
        seed_address: Starting wallet address
        investigation_id: Current investigation ID
        direction: 'forward' (where funds went) or 'backward' (where funds came from)
        max_hops: Maximum trace depth (default 5)
        chain_id: Chain ID from config

    Returns:
        List of fund_flow_edge documents
    """
    now = datetime.now(timezone.utc).isoformat()
    trail = []
    visited = set()
    visited.add(seed_address.lower())

    # BFS queue: (address, hop_number, current_taint)
    queue = deque([(seed_address.lower(), 0, 1.0)])

    while queue:
        current_address, current_hop, current_taint = queue.popleft()

        if current_hop >= max_hops:
            continue

        transfers = _query_transfers(
            es_client, current_address, investigation_id, direction
        )

        for transfer in transfers:
            if direction == "forward":
                next_address = transfer.get("to_address", "").lower()
            else:
                next_address = transfer.get("from_address", "").lower()

            if not next_address:
                continue

            # Classify the next address for taint calculation
            classification = classify_address(next_address)
            new_taint = compute_taint_haircut(
                current_taint, classification["category"]
            )

            hop_number = current_hop + 1

            edge_doc = {
                "layer": "derived",
                "derived_type": "fund_flow_edge",
                "investigation_id": investigation_id,
                "chain_id": chain_id,
                "@timestamp": now,
                "from_address": transfer.get("from_address", ""),
                "to_address": transfer.get("to_address", ""),
                "value_eth": transfer.get("value_eth", 0.0),
                "token_address": transfer.get("token_address"),
                "tx_hash": transfer.get("tx_hash"),
                "block_number": transfer.get("block_number"),
                "hop_number": hop_number,
                "direction": direction,
                "taint_score": new_taint,
            }

            trail.append(edge_doc)

            # Only continue BFS if we haven't visited this address
            if next_address not in visited:
                visited.add(next_address)
                queue.append((next_address, hop_number, new_taint))

    return trail


def build_fund_trail_document(
    seed_address: str,
    trail: list[dict],
    investigation_id: str,
    chain_id: int,
) -> dict:
    """
    Build a summary fund_trail document from the traced edges.
    Stored as layer: attacker, attacker_type: fund_trail.
    """
    now = datetime.now(timezone.utc).isoformat()

    # Collect all unique addresses in trail
    all_addresses = set()
    exit_routes = []
    total_value = 0.0

    for edge in trail:
        all_addresses.add(edge.get("from_address", ""))
        all_addresses.add(edge.get("to_address", ""))
        total_value += edge.get("value_eth", 0.0)

        to_class = classify_address(edge.get("to_address", ""))
        if to_class["category"] in ("mixer", "bridge", "cex"):
            exit_routes.append(
                f"{to_class['category']}:{to_class['protocol']}"
            )

    max_hop = max((e.get("hop_number", 0) for e in trail), default=0)
    min_block = min((e.get("block_number", 0) for e in trail if e.get("block_number")), default=0)
    max_block = max((e.get("block_number", 0) for e in trail if e.get("block_number")), default=0)

    return {
        "layer": "attacker",
        "attacker_type": "fund_trail",
        "investigation_id": investigation_id,
        "chain_id": chain_id,
        "@timestamp": now,
        "from_address": seed_address.lower(),
        "fund_trail_hops": max_hop,
        "total_stolen_eth": total_value,
        "exit_routes": list(set(exit_routes)),
        "cluster_wallets": list(all_addresses),
        "cluster_size": len(all_addresses),
        "attack_block_range_from": min_block,
        "attack_block_range_to": max_block,
    }
```

- [ ] **Step 4: Run tests**

```bash
cd /mnt/c/Users/aswat/OneDrive/Desktop/Projects/Project_Hail_Mary/chainsentinel
python -m pytest tests/test_fund_trace.py -v
```

Expected: All 8 PASS

- [ ] **Step 5: Commit**

```bash
git add chainsentinel/correlation/fund_trace.py chainsentinel/tests/test_fund_trace.py
git commit -m "feat: BFS fund tracing with 5-hop limit and haircut taint scoring"
```

---

### Task 5: Wallet Clustering

**Files:**
- Create: `chainsentinel/correlation/clustering.py`
- Create: `chainsentinel/tests/test_clustering.py`

- [ ] **Step 1: Write the tests**

`chainsentinel/tests/test_clustering.py`:

```python
import pytest
from unittest.mock import MagicMock


def test_cluster_by_funding_source():
    from correlation.clustering import cluster_by_funding_source

    mock_client = MagicMock()
    # Two wallets funded by the same source
    mock_client.search.return_value = {
        "aggregations": {
            "funding_sources": {
                "buckets": [
                    {
                        "key": "0xfunder",
                        "doc_count": 2,
                        "funded_wallets": {
                            "buckets": [
                                {"key": "0xwallet_a", "doc_count": 1},
                                {"key": "0xwallet_b", "doc_count": 1},
                            ]
                        },
                    }
                ]
            }
        }
    }

    clusters = cluster_by_funding_source(mock_client, "INV-001")

    assert len(clusters) == 1
    assert "0xwallet_a" in clusters[0]["wallets"]
    assert "0xwallet_b" in clusters[0]["wallets"]
    assert clusters[0]["funded_via"] == "0xfunder"


def test_cluster_by_timing():
    from correlation.clustering import cluster_by_timing

    mock_client = MagicMock()
    mock_client.search.return_value = {
        "aggregations": {
            "block_windows": {
                "buckets": [
                    {
                        "key": 100,
                        "doc_count": 3,
                        "active_wallets": {
                            "buckets": [
                                {"key": "0xwallet_a", "doc_count": 2},
                                {"key": "0xwallet_b", "doc_count": 1},
                                {"key": "0xwallet_c", "doc_count": 1},
                            ]
                        },
                    }
                ]
            }
        }
    }

    clusters = cluster_by_timing(mock_client, "INV-001", window_blocks=5)

    assert len(clusters) >= 1
    cluster_wallets = clusters[0]["wallets"]
    assert len(cluster_wallets) >= 2


def test_merge_clusters_deduplicates():
    from correlation.clustering import merge_clusters

    clusters = [
        {"wallets": {"0xa", "0xb"}, "method": "funding"},
        {"wallets": {"0xb", "0xc"}, "method": "timing"},
        {"wallets": {"0xd"}, "method": "funding"},
    ]

    merged = merge_clusters(clusters)

    # 0xa, 0xb, 0xc should be in same cluster (connected via 0xb)
    found = False
    for cluster in merged:
        if "0xa" in cluster["wallets"] and "0xc" in cluster["wallets"]:
            found = True
            assert "0xb" in cluster["wallets"]
    assert found


def test_merge_clusters_preserves_isolated():
    from correlation.clustering import merge_clusters

    clusters = [
        {"wallets": {"0xa", "0xb"}, "method": "funding"},
        {"wallets": {"0xd", "0xe"}, "method": "timing"},
    ]

    merged = merge_clusters(clusters)
    assert len(merged) == 2


def test_build_cluster_document():
    from correlation.clustering import build_cluster_document

    doc = build_cluster_document(
        cluster_id="CLUSTER-001",
        wallets=["0xa", "0xb", "0xc"],
        funded_via="0xfunder",
        investigation_id="INV-001",
        chain_id=31337,
        method="funding_source",
    )

    assert doc["layer"] == "attacker"
    assert doc["attacker_type"] == "cluster"
    assert doc["cluster_id"] == "CLUSTER-001"
    assert doc["cluster_size"] == 3
    assert "0xa" in doc["cluster_wallets"]
    assert doc["investigation_id"] == "INV-001"


def test_build_attacker_profile():
    from correlation.clustering import build_attacker_profile

    profile = build_attacker_profile(
        cluster_id="CLUSTER-001",
        wallets=["0xa", "0xb"],
        fund_trail_hops=3,
        exit_routes=["mixer:Tornado Cash", "cex:Binance"],
        total_stolen_eth=150.0,
        investigation_id="INV-001",
        chain_id=31337,
        first_seen_block=95,
        exploit_block=100,
    )

    assert profile["layer"] == "attacker"
    assert profile["attacker_type"] == "profile"
    assert profile["total_stolen_eth"] == 150.0
    assert profile["fund_trail_hops"] == 3
    assert "mixer:Tornado Cash" in profile["exit_routes"]
    assert profile["first_seen_block"] == 95
    assert profile["exploit_block"] == 100


def test_run_clustering_full_pipeline():
    from correlation.clustering import run_clustering

    mock_client = MagicMock()
    # Funding source query
    mock_client.search.side_effect = [
        {
            "aggregations": {
                "funding_sources": {
                    "buckets": [
                        {
                            "key": "0xfunder",
                            "doc_count": 2,
                            "funded_wallets": {
                                "buckets": [
                                    {"key": "0xwallet_a", "doc_count": 1},
                                    {"key": "0xwallet_b", "doc_count": 1},
                                ]
                            },
                        }
                    ]
                }
            }
        },
        # Timing query
        {
            "aggregations": {
                "block_windows": {
                    "buckets": []
                }
            }
        },
    ]

    mock_ingest = MagicMock()

    docs = run_clustering(mock_client, mock_ingest, "INV-001", 31337)

    assert len(docs) >= 1
    assert docs[0]["attacker_type"] == "cluster"
    mock_ingest.assert_called_once()
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /mnt/c/Users/aswat/OneDrive/Desktop/Projects/Project_Hail_Mary/chainsentinel
python -m pytest tests/test_clustering.py -v
```

Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Implement clustering.py**

`chainsentinel/correlation/clustering.py`:

```python
"""
Wallet Clustering — groups related wallets by shared patterns.

Clustering methods:
1. Same funding source — wallets funded by the same address
2. Timing correlation — wallets active in the same block window relative to exploit
3. Shared contract interaction — wallets interacting with the same unusual contracts
4. Common trace address — wallets appearing in each other's call traces

Output: cluster documents (layer: attacker, attacker_type: cluster)
and attacker profile documents (layer: attacker, attacker_type: profile).
"""
import hashlib
from datetime import datetime, timezone
from typing import Optional


def cluster_by_funding_source(
    es_client,
    investigation_id: str,
) -> list[dict]:
    """
    Find wallets that share a common funding source.
    Uses ES aggregation on from_address → to_address pairs.
    """
    query = {
        "bool": {
            "must": [
                {"term": {"investigation_id": investigation_id}},
                {"term": {"layer": "derived"}},
                {"terms": {"derived_type": ["native_transfer", "asset_transfer"]}},
            ]
        }
    }

    aggs = {
        "funding_sources": {
            "terms": {"field": "from_address", "size": 100},
            "aggs": {
                "funded_wallets": {
                    "terms": {"field": "to_address", "size": 100}
                }
            },
        }
    }

    response = es_client.search(
        index="forensics",
        query=query,
        aggs=aggs,
        size=0,
    )

    clusters = []
    buckets = response.get("aggregations", {}).get("funding_sources", {}).get("buckets", [])

    for bucket in buckets:
        funder = bucket["key"]
        funded = bucket.get("funded_wallets", {}).get("buckets", [])

        if len(funded) >= 2:
            wallets = [w["key"] for w in funded]
            clusters.append({
                "wallets": set(wallets),
                "funded_via": funder,
                "method": "funding_source",
            })

    return clusters


def cluster_by_timing(
    es_client,
    investigation_id: str,
    window_blocks: int = 5,
) -> list[dict]:
    """
    Find wallets active in the same narrow block window.
    Uses histogram aggregation on block_number.
    """
    query = {
        "bool": {
            "must": [
                {"term": {"investigation_id": investigation_id}},
                {"term": {"layer": "derived"}},
            ]
        }
    }

    aggs = {
        "block_windows": {
            "histogram": {"field": "block_number", "interval": window_blocks},
            "aggs": {
                "active_wallets": {
                    "terms": {"field": "from_address", "size": 50}
                }
            },
        }
    }

    response = es_client.search(
        index="forensics",
        query=query,
        aggs=aggs,
        size=0,
    )

    clusters = []
    buckets = response.get("aggregations", {}).get("block_windows", {}).get("buckets", [])

    for bucket in buckets:
        wallets_in_window = bucket.get("active_wallets", {}).get("buckets", [])
        if len(wallets_in_window) >= 2:
            wallet_set = set(w["key"] for w in wallets_in_window)
            clusters.append({
                "wallets": wallet_set,
                "method": "timing",
                "block_window": bucket["key"],
            })

    return clusters


def merge_clusters(clusters: list[dict]) -> list[dict]:
    """
    Merge overlapping clusters using union-find.
    Two clusters merge if they share at least one wallet.
    """
    if not clusters:
        return []

    # Union-Find
    parent = {}

    def find(x):
        if x not in parent:
            parent[x] = x
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb

    # Build union-find from cluster wallet sets
    for cluster in clusters:
        wallets = list(cluster["wallets"])
        for i in range(1, len(wallets)):
            union(wallets[0], wallets[i])

    # Group wallets by their root
    groups = {}
    all_wallets = set()
    for cluster in clusters:
        all_wallets.update(cluster["wallets"])

    for wallet in all_wallets:
        root = find(wallet)
        if root not in groups:
            groups[root] = set()
        groups[root].add(wallet)

    # Collect methods used per group
    methods_per_group = {root: set() for root in groups}
    for cluster in clusters:
        wallets = list(cluster["wallets"])
        if wallets:
            root = find(wallets[0])
            methods_per_group[root].add(cluster.get("method", "unknown"))

    merged = []
    for root, wallet_set in groups.items():
        merged.append({
            "wallets": wallet_set,
            "methods": list(methods_per_group.get(root, set())),
        })

    return merged


def _generate_cluster_id(wallets: set[str]) -> str:
    """Generate a deterministic cluster ID from sorted wallet addresses."""
    sorted_wallets = sorted(wallets)
    hash_input = ",".join(sorted_wallets).encode()
    return "CLUSTER-" + hashlib.sha256(hash_input).hexdigest()[:12].upper()


def build_cluster_document(
    cluster_id: str,
    wallets: list[str],
    funded_via: str,
    investigation_id: str,
    chain_id: int,
    method: str = "unknown",
) -> dict:
    """Build an attacker cluster document for ES."""
    now = datetime.now(timezone.utc).isoformat()

    return {
        "layer": "attacker",
        "attacker_type": "cluster",
        "investigation_id": investigation_id,
        "chain_id": chain_id,
        "@timestamp": now,
        "cluster_id": cluster_id,
        "cluster_wallets": wallets,
        "cluster_size": len(wallets),
        "funded_via": funded_via,
        "labels": [method],
    }


def build_attacker_profile(
    cluster_id: str,
    wallets: list[str],
    fund_trail_hops: int,
    exit_routes: list[str],
    total_stolen_eth: float,
    investigation_id: str,
    chain_id: int,
    first_seen_block: Optional[int] = None,
    exploit_block: Optional[int] = None,
) -> dict:
    """Build an attacker profile document summarizing attribution data."""
    now = datetime.now(timezone.utc).isoformat()

    return {
        "layer": "attacker",
        "attacker_type": "profile",
        "investigation_id": investigation_id,
        "chain_id": chain_id,
        "@timestamp": now,
        "cluster_id": cluster_id,
        "cluster_wallets": wallets,
        "cluster_size": len(wallets),
        "fund_trail_hops": fund_trail_hops,
        "exit_routes": exit_routes,
        "total_stolen_eth": total_stolen_eth,
        "first_seen_block": first_seen_block,
        "exploit_block": exploit_block,
    }


def run_clustering(
    es_client,
    ingest_fn,
    investigation_id: str,
    chain_id: int,
) -> list[dict]:
    """
    Run all clustering methods, merge results, build cluster documents.
    """
    # Gather clusters from different methods
    funding_clusters = cluster_by_funding_source(es_client, investigation_id)
    timing_clusters = cluster_by_timing(es_client, investigation_id)

    all_clusters = funding_clusters + timing_clusters

    if not all_clusters:
        return []

    merged = merge_clusters(all_clusters)

    documents = []
    for cluster in merged:
        wallets = list(cluster["wallets"])
        cluster_id = _generate_cluster_id(cluster["wallets"])

        # Find funding source if available
        funded_via = ""
        for fc in funding_clusters:
            if fc["wallets"] & cluster["wallets"]:
                funded_via = fc.get("funded_via", "")
                break

        doc = build_cluster_document(
            cluster_id=cluster_id,
            wallets=wallets,
            funded_via=funded_via,
            investigation_id=investigation_id,
            chain_id=chain_id,
            method=", ".join(cluster.get("methods", ["unknown"])),
        )
        documents.append(doc)

    if documents:
        ingest_fn(es_client, documents, "forensics")

    return documents
```

- [ ] **Step 4: Run tests**

```bash
cd /mnt/c/Users/aswat/OneDrive/Desktop/Projects/Project_Hail_Mary/chainsentinel
python -m pytest tests/test_clustering.py -v
```

Expected: All 7 PASS

- [ ] **Step 5: Commit**

```bash
git add chainsentinel/correlation/clustering.py chainsentinel/tests/test_clustering.py
git commit -m "feat: wallet clustering by funding source and timing with union-find merge"
```

---

### Task 6: Correlation Integration Tests

**Files:**
- Create: `chainsentinel/tests/test_correlation_integration.py`

- [ ] **Step 1: Write integration test**

`chainsentinel/tests/test_correlation_integration.py`:

```python
import pytest
from unittest.mock import MagicMock


def test_full_correlation_pipeline():
    """
    Integration test: fund_trace -> clustering -> label_db -> mixer_detect
    all work together to produce attacker attribution documents.
    """
    from correlation.fund_trace import trace_funds, build_fund_trail_document
    from correlation.clustering import run_clustering
    from correlation.label_db import get_label, is_ofac_sanctioned
    from correlation.mixer_detect import detect_exit_routes, classify_address

    # Verify label_db is accessible from all modules
    label = get_label("0xd90e2f925da726b50c4ed8d0fb90ad053324f31b")
    assert label["type"] == "mixer_contract"

    # Verify classify_address uses label_db
    classification = classify_address("0xd90e2f925da726b50c4ed8d0fb90ad053324f31b")
    assert classification["category"] == "mixer"

    # Verify OFAC check works
    assert is_ofac_sanctioned("0xd90e2f925da726b50c4ed8d0fb90ad053324f31b") is True


def test_fund_trail_feeds_into_cluster():
    """Fund trail addresses should be usable as clustering input."""
    from correlation.fund_trace import build_fund_trail_document
    from correlation.clustering import build_attacker_profile

    trail = [
        {
            "from_address": "0xattacker",
            "to_address": "0xhop1",
            "value_eth": 50.0,
            "hop_number": 1,
        },
        {
            "from_address": "0xhop1",
            "to_address": "0xd90e2f925da726b50c4ed8d0fb90ad053324f31b",
            "value_eth": 50.0,
            "hop_number": 2,
        },
    ]

    trail_doc = build_fund_trail_document("0xattacker", trail, "INV-001", 31337)

    profile = build_attacker_profile(
        cluster_id="CLUSTER-001",
        wallets=trail_doc["cluster_wallets"],
        fund_trail_hops=trail_doc["fund_trail_hops"],
        exit_routes=trail_doc["exit_routes"],
        total_stolen_eth=trail_doc["total_stolen_eth"],
        investigation_id="INV-001",
        chain_id=31337,
        first_seen_block=trail_doc["attack_block_range_from"],
        exploit_block=trail_doc["attack_block_range_to"],
    )

    assert profile["attacker_type"] == "profile"
    assert profile["fund_trail_hops"] == 2
    assert profile["total_stolen_eth"] == 100.0
```

- [ ] **Step 2: Run integration tests**

```bash
cd /mnt/c/Users/aswat/OneDrive/Desktop/Projects/Project_Hail_Mary/chainsentinel
python -m pytest tests/test_correlation_integration.py -v
```

Expected: All PASS

- [ ] **Step 3: Run all correlation tests together**

```bash
cd /mnt/c/Users/aswat/OneDrive/Desktop/Projects/Project_Hail_Mary/chainsentinel
python -m pytest tests/test_label_db.py tests/test_mixer_detect.py tests/test_fund_trace.py tests/test_clustering.py tests/test_correlation_integration.py -v
```

Expected: All PASS

- [ ] **Step 4: Commit**

```bash
git add chainsentinel/tests/test_correlation_integration.py
git commit -m "feat: correlation integration tests verify fund_trace -> clustering -> label_db pipeline"
```
