# 3.10–3.13 Correlation modules

## 3.10 `correlation/fund_trace.py`

**Purpose.** BFS over value-transfer edges with haircut taint scoring.

**Public functions:**

- `trace_funds(es, *, investigation_id, seed_addresses, max_hops=5,
  direction="both") -> list[FundFlowEdge]`

**Algorithm.**

1. Query `forensics` for `value_flow_intra_tx` and `eth_transfers`
   derived events filtered by `investigation_id`.
2. BFS from each seed in both directions, stopping at `max_hops`.
3. At each hop, multiply the carried taint by the destination
   classification's haircut (see **D3 §5.2**).

**Output edge:**

```json
{
  "src": "0x...",
  "dst": "0x...",
  "tx_hash": "0x...",
  "value_eth": 12.3,
  "hop_index": 2,
  "taint": 0.7,
  "label_src": "attacker",
  "label_dst": "mixer_contract"
}
```

## 3.11 `correlation/clustering.py`

**Purpose.** Group wallets by shared funding / timing / creator.

**Public function:**

- `cluster_addresses(es, *, investigation_id) -> list[Cluster]`

**Cluster shape:**

```json
{
  "cluster_id": "blake2b8_<hash>",
  "addresses": ["0x...", "0x..."],
  "evidence": {
    "shared_funding": ["0x..."],
    "timing_overlap": [block_a, block_b],
    "creator": "0x...",
    "co_traces": ["0x<tx>", ...]
  },
  "label": "unknown" | "known_exploiter" | ...
}
```

## 3.12 `correlation/mixer_detect.py`

**Purpose.** Classify addresses into mixer / bridge / CEX / OFAC /
known_exploiter / unknown by querying `label_db`.

**Public function:**

- `classify(address: str) -> str` — returns the label keyword.
- `haircut(label: str) -> float` — returns the taint multiplier
  (mixer `0.7`, bridge `0.8`, CEX `0.9`, otherwise `1.0`).

## 3.13 `correlation/label_db.py`

**Purpose.** In-memory address corpus.

**Public functions:**

- `lookup(address: str) -> str | None` — returns the label or `None`.
- `register(address: str, label: str)` — used by future intel imports.

Corpus categories:

- 10 Tornado Cash contracts
- Hop, Stargate, Multichain, Across bridges
- Binance, Coinbase, Kraken hot wallets
- OFAC SDN seed list
- Notable past exploiter EOAs

To swap in a remote intel feed, reimplement `lookup` against your
provider's API — no other call site needs to change.
