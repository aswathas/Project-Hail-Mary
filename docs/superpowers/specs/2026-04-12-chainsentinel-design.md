# ChainSentinel — Design Specification

**Date:** 2026-04-12
**Status:** Approved
**Author:** Aswath + Claude

---

## 1. What Is ChainSentinel

A standalone EVM blockchain forensics tool. Given a transaction hash, wallet address, or block range, it runs a full forensic pipeline — collecting raw chain data, decoding it, deriving security events, running signal detection via ES queries, tracing funds, and surfacing findings in a React investigation workspace with an Ollama-powered copilot.

**Real-world workflow:** A client comes to SISA saying "we got exploited." They provide their RPC endpoint, contract ABIs, deployed addresses, and approximate time window. The analyst loads this into ChainSentinel and runs analysis. The tool detects the exploit purely from on-chain data + client ABIs.

**For development/testing:** Foundry simulations on Anvil simulate real client engagements — victim protocol + normal activity + attack. ChainSentinel analyzes using only the client handover (ABIs + manifest), never the attacker source code.

---

## 2. Core Principles

- **Python is plumbing.** Moves data from chain to ES. Does not contain detection logic.
- **ES is the brain.** Signal detection and pattern matching run as ES|QL and EQL queries. Anyone at SISA who knows ES can read, modify, and contribute detection rules.
- **Evidence integrity.** Raw chain data is never mixed with pipeline interpretations. Separate index.
- **Modular growth.** Adding a signal = drop a `.esql` file. Adding a pattern = drop a `.eql` file. Adding a derived type = add a function. Adding a simulation = add a folder.
- **Graceful degradation.** Full traces when available (Anvil, archive nodes). Tool still works with just receipts + logs when connecting to basic RPC.
- **Client-driven intake.** The tool doesn't assume what contracts exist. The client provides ABIs + addresses via a manifest.

---

## 3. Technology Stack

| Component | Technology |
|-----------|-----------|
| Simulation node | Foundry + Anvil |
| Pipeline | Python 3.11+ |
| Backend API | FastAPI 0.110+ |
| Progress streaming | Server-Sent Events (SSE) |
| Storage + detection | Elasticsearch 8.x |
| Dashboards | Kibana 8.x |
| Local LLM | Ollama + Gemma 3 1B |
| Frontend | React 18 + Vite |
| Frontend styling | Plain CSS with CSS variables (Wise design system) |
| Graph visualization | D3.js force-directed |
| Configuration | config.json (single source of truth) |

---

## 4. Repository Structure

```
Project_Hail_Mary/
├── CLAUDE.md
├── DESIGN.md
│
├── chainsentinel/                      ← the forensic tool
│   ├── config.json
│   ├── server.py
│   ├── start.sh
│   ├── requirements.txt
│   │
│   ├── pipeline/
│   │   ├── runner.py                   ← orchestrates pipeline, yields SSE events
│   │   ├── collector.py                ← RPC data fetching
│   │   ├── normalizer.py               ← hex→int, addresses lowercase, timestamps
│   │   ├── decoder.py                  ← ABI decoding with registry
│   │   ├── derived.py                  ← security event builder
│   │   ├── ingest.py                   ← ES bulk ingest
│   │   ├── selector_registry.json      ← living selector→name cache
│   │   └── abi_registry/
│   │       ├── standards/              ← ERC20, ERC721, ERC1155
│   │       ├── protocols/              ← Uniswap, Aave, Compound, Curve
│   │       └── cases/                  ← per-investigation client ABIs
│   │           └── {investigation_id}/
│   │               ├── manifest.json
│   │               └── *.json (ABIs)
│   │
│   ├── detection/
│   │   ├── signal_engine.py            ← loads + runs .esql files
│   │   ├── pattern_engine.py           ← loads + runs .eql files
│   │   ├── signals/
│   │   │   ├── value/
│   │   │   │   ├── large_outflow.esql
│   │   │   │   ├── large_token_transfer.esql
│   │   │   │   ├── max_approval.esql
│   │   │   │   ├── zero_then_max_approval.esql
│   │   │   │   ├── large_mint_from_zero.esql
│   │   │   │   ├── value_spike.esql
│   │   │   │   └── large_price_impact_swap.esql
│   │   │   ├── flash_loan/
│   │   │   │   ├── flash_loan_detected.esql
│   │   │   │   ├── flash_loan_with_drain.esql
│   │   │   │   └── flash_loan_with_swap.esql
│   │   │   ├── access/
│   │   │   │   ├── ownership_transferred.esql
│   │   │   │   ├── role_granted.esql
│   │   │   │   ├── proxy_upgraded.esql
│   │   │   │   ├── paused_or_unpaused.esql
│   │   │   │   └── approval_then_transferfrom.esql
│   │   │   ├── structural/
│   │   │   │   ├── reentrancy_pattern.esql
│   │   │   │   ├── call_depth_anomaly.esql
│   │   │   │   ├── repeated_external_call.esql
│   │   │   │   ├── delegatecall_to_unknown.esql
│   │   │   │   ├── delegatecall_chain.esql
│   │   │   │   ├── internal_eth_drain.esql
│   │   │   │   ├── self_destruct.esql
│   │   │   │   ├── create2_deployment.esql
│   │   │   │   ├── oracle_read_after_large_swap.esql
│   │   │   │   └── spot_price_query.esql
│   │   │   ├── deployment/
│   │   │   │   ├── new_contract_deployed.esql
│   │   │   │   ├── contract_deployed_by_new_wallet.esql
│   │   │   │   └── failed_high_gas.esql
│   │   │   ├── liquidity/
│   │   │   │   ├── large_liquidity_removal.esql
│   │   │   │   └── deposit_withdraw_same_block.esql
│   │   │   ├── token/
│   │   │   │   ├── honeypot_sell_failure.esql
│   │   │   │   ├── fee_on_transfer_anomaly.esql
│   │   │   │   ├── token_balance_mismatch.esql
│   │   │   │   └── massive_supply_mint.esql
│   │   │   ├── governance/
│   │   │   │   ├── governance_vote_cast.esql
│   │   │   │   ├── proposal_created_executed_fast.esql
│   │   │   │   └── flash_loan_before_vote.esql
│   │   │   ├── defi/
│   │   │   │   ├── vault_first_deposit_tiny.esql
│   │   │   │   ├── vault_donation_before_deposit.esql
│   │   │   │   ├── liquidation_event.esql
│   │   │   │   ├── self_liquidation.esql
│   │   │   │   ├── borrow_at_max_ltv.esql
│   │   │   │   └── cascading_liquidations.esql
│   │   │   ├── behavioural/
│   │   │   │   ├── new_wallet_high_value.esql
│   │   │   │   ├── dormant_reactivation.esql
│   │   │   │   ├── burst_transactions.esql
│   │   │   │   ├── funding_from_mixer.esql
│   │   │   │   ├── mixer_deposit_post_exploit.esql
│   │   │   │   ├── cex_deposit_post_exploit.esql
│   │   │   │   └── bridge_exit_post_exploit.esql
│   │   │   ├── bridge/
│   │   │   │   ├── bridge_large_outflow.esql
│   │   │   │   └── bridge_called_by_new_wallet.esql
│   │   │   ├── graph/
│   │   │   │   ├── high_fanout.esql
│   │   │   │   ├── star_convergence.esql
│   │   │   │   ├── circular_flow.esql
│   │   │   │   └── multi_hop_movement.esql
│   │   │   └── evasion/
│   │   │       ├── multi_mixer_usage.esql
│   │   │       ├── rapid_chain_of_transfers.esql
│   │   │       └── dust_consolidation.esql
│   │   │
│   │   └── patterns/
│   │       ├── AP-001_flash_loan_oracle.eql
│   │       ├── AP-002_flash_loan_governance.eql
│   │       ├── AP-003_flash_loan_liquidation.eql
│   │       ├── AP-004_flash_loan_arbitrage.eql
│   │       ├── AP-005_reentrancy_drain.eql
│   │       ├── AP-006_cross_function_reentry.eql
│   │       ├── AP-007_read_only_reentry.eql
│   │       ├── AP-008_access_control_abuse.eql
│   │       ├── AP-009_proxy_upgrade_attack.eql
│   │       ├── AP-010_unauthorized_mint.eql
│   │       ├── AP-011_rug_pull.eql
│   │       ├── AP-012_mint_and_dump.eql
│   │       ├── AP-013_honeypot_token.eql
│   │       ├── AP-014_mev_sandwich.eql
│   │       ├── AP-015_wash_trading.eql
│   │       ├── AP-016_oracle_spot_manipulation.eql
│   │       ├── AP-017_vault_donation.eql
│   │       ├── AP-018_liquidation_cascade.eql
│   │       ├── AP-019_bridge_drain.eql
│   │       └── AP-020_fund_laundering.eql
│   │
│   ├── correlation/
│   │   ├── clustering.py               ← wallet clustering
│   │   ├── fund_trace.py               ← BFS fund tracing, 5 hops, haircut taint
│   │   ├── mixer_detect.py             ← Tornado Cash, bridges, CEX matching
│   │   └── label_db.py                 ← OFAC, known exploiters, CEX wallets
│   │
│   ├── es/
│   │   ├── mappings/
│   │   │   ├── forensics-raw.json      ← strict mapping for raw evidence
│   │   │   └── forensics.json          ← strict mapping for analysis data
│   │   └── setup.py                    ← creates indices + mappings on startup
│   │
│   ├── ollama/
│   │   ├── copilot.py                  ← chat with investigation context
│   │   ├── report_template.py          ← builds structured JSON context
│   │   └── report_sections.py          ← 7-section report generation
│   │
│   └── frontend/
│       ├── package.json
│       ├── vite.config.js
│       └── src/
│           ├── App.jsx
│           ├── App.css                  ← Wise design system CSS variables
│           ├── components/
│           │   ├── Sidebar.jsx          ← config, modes, run button, saved analyses
│           │   ├── PipelineFeed.jsx     ← SSE log stream with severity colors
│           │   ├── InvestigationView.jsx ← timeline + signals + meta bar
│           │   ├── EntityGraph.jsx      ← D3.js force-directed graph
│           │   ├── CopilotPanel.jsx     ← Ollama chat + report generation
│           │   └── StoredAnalyses.jsx   ← saved cases list
│           ├── hooks/
│           │   ├── useAnalysis.js       ← SSE connection + state machine
│           │   ├── useElasticsearch.js  ← direct ES queries from frontend
│           │   ├── useOllama.js         ← Ollama API interaction
│           │   └── useLocalStorage.js   ← case persistence
│           └── api/
│               ├── pipeline.js          ← POST /analyze, GET /health
│               ├── elasticsearch.js     ← ES query helpers
│               └── ollama.js            ← Ollama API helpers
│
└── simulations/                         ← separate from chainsentinel
    ├── foundry.toml
    ├── lib/
    ├── shared/
    │   └── contracts/
    │       ├── MockERC20.sol
    │       ├── MockWETH.sol
    │       └── UserActivity.sol         ← generates realistic normal traffic
    │
    └── scenarios/
        ├── reentrancy-drain/
        │   ├── client/                  ← what the client gives SISA
        │   │   ├── abis/
        │   │   │   ├── VulnerableVault.json
        │   │   │   └── MockERC20.json
        │   │   └── manifest.json
        │   ├── src/
        │   │   ├── victim/
        │   │   │   ├── VulnerableVault.sol
        │   │   │   └── MockERC20.sol
        │   │   ├── attacker/
        │   │   │   └── ReentrancyAttacker.sol
        │   │   └── activity/
        │   │       └── NormalUsers.sol
        │   ├── script/
        │   │   ├── 01_DeployProtocol.s.sol
        │   │   ├── 02_NormalActivity.s.sol
        │   │   ├── 03_ExecuteAttack.s.sol
        │   │   └── RunAll.s.sol
        │   └── README.md
        │
        ├── flash-loan-oracle/
        │   ├── client/
        │   ├── src/
        │   ├── script/
        │   └── README.md
        │
        ├── admin-key-abuse/
        │   ├── client/
        │   ├── src/
        │   ├── script/
        │   └── README.md
        │
        └── mev-sandwich/
            ├── client/
            ├── src/
            ├── script/
            └── README.md
```

---

## 5. Elasticsearch Architecture

### 2 Indices

**`forensics-raw`** — Untouched chain evidence. Never modified after ingest.

| `doc_type` | Contents | One document per |
|-----------|----------|-----------------|
| `transaction` | Tx object + receipt merged | tx_hash |
| `log` | Event log (address, topics[], data) | tx_hash + log_index |
| `trace` | debug_traceTransaction call tree | tx_hash |

**`forensics`** — Everything the pipeline and detection engine produce.

| `layer` | Contents | Sub-type field |
|---------|----------|---------------|
| `decoded` | ABI-decoded events and calls | `decoded_type`: event, call |
| `derived` | Security events | `derived_type`: asset_transfer, native_transfer, swap_summary, approval_usage, admin_action, execution_edge, fund_flow_edge, contract_interaction, balance_delta |
| `signal` | Heuristic signal firings | `signal_name` |
| `alert` | Composite attack pattern matches | `pattern_id` |
| `attacker` | Wallet clusters, profiles, fund trails | `attacker_type`: cluster, fund_trail, profile |
| `case` | Investigation documents | — |

### Shared fields on every document

```
investigation_id    → keyword
chain_id            → integer
@timestamp          → date (ingest time)
block_number        → long
block_datetime      → date (on-chain time)
tx_hash             → keyword
```

### Key mapping rules

- All addresses → `keyword` (exact match, lowercased)
- `event_args`, `function_args`, `metadata`, `raw_extra` → `flattened` (prevents mapping explosion)
- `value_eth` → `double`
- `value_wei` → `keyword` (exceeds long range)
- `score` → `float`
- `severity` → `keyword`
- `decode_status` → `keyword` (decoded, partial, unknown)
- `"dynamic": "strict"` on both indices

### Document ID strategy (idempotent)

| Index / layer | `_id` formula |
|--------------|---------------|
| forensics-raw transaction | `{chain_id}_{tx_hash}` |
| forensics-raw log | `{chain_id}_{tx_hash}_{log_index}` |
| forensics-raw trace | `{chain_id}_{tx_hash}_trace` |
| forensics decoded | `{investigation_id}_{tx_hash}_{log_index}_decoded` |
| forensics derived | `{investigation_id}_{derived_type}_{tx_hash}_{log_index}` |
| forensics signal | `{investigation_id}_{signal_name}_{tx_hash}` |
| forensics alert | `{investigation_id}_{pattern_id}` |
| forensics attacker | `{investigation_id}_{cluster_id}` |
| forensics case | `{investigation_id}` |

### Future index splitting

If performance requires it: filter by `layer`, create new index, change one line in `ingest.py`, run ES reindex API. Queries don't change — just point at new index.

---

## 6. Pipeline Architecture

### Data flow

```
RPC Endpoint (Anvil / testnet / mainnet)
    ↓
Collector → raw blocks, txs+receipts, logs, traces
    ↓
    ├──→ ES: forensics-raw (doc_type: transaction, log, trace)
    ↓
Normalizer → hex to int, addresses lowercase, timestamps ISO 8601
    ↓
Decoder → ABI decode using registry (case ABIs → standards → protocols → selector cache)
    ↓
    ├──→ ES: forensics (layer: decoded)
    ↓
Derived Event Builder → security events (9 derived types)
    ↓
    ├──→ ES: forensics (layer: derived)
    ↓
ES Signal Engine → runs all .esql files against forensics index
    ↓
    ├──→ ES: forensics (layer: signal)
    ↓
ES Pattern Engine → runs all .eql files combining signals
    ↓
    ├──→ ES: forensics (layer: alert)
    ↓
Python Correlation → fund tracing BFS + wallet clustering
    ↓
    └──→ ES: forensics (layer: attacker, case)
```

### Collector — collector.py

Talks to RPC. Fetches:
- `eth_getTransactionByHash` + `eth_getTransactionReceipt` → merged into one document
- `eth_getLogs` → for range/watch mode
- `debug_traceTransaction` → when available (Anvil, archive nodes). If unavailable, skips gracefully.

Block header data (timestamp, block_number, base_fee) denormalized onto transaction documents. No separate block index.

`is_contract` check: single `eth_getCode` call per unique address. Stored as boolean field, not separate document.

### Normalizer — normalizer.py

- Hex numeric strings → integers (blockNumber, value, gas, gasPrice, gasUsed, nonce)
- Block timestamp → ISO 8601 UTC (`block_datetime`). Original preserved as `block_timestamp_raw`.
- All addresses → lowercased 0x-prefixed
- Value wei → ETH (`value_eth` as double). Original preserved as `value_wei` keyword.
- Transaction status → boolean `success`
- `decode_status: pending` added to every record passing through decoder
- Unknown fields → `raw_extra` (flattened type)

### Decoder — decoder.py

Priority order:
1. **Case ABIs** — from `abi_registry/cases/{investigation_id}/`, matched by contract address via manifest
2. **Standards** — ERC20, ERC721, ERC1155 (matched by event signature)
3. **Known protocols** — Uniswap, Aave, Compound, Curve (matched by event signature)
4. **Selector registry** — `selector_registry.json` cache (matched by bytes4/bytes32)
5. **No match** → `decode_status: unknown`, raw topics + data preserved

Decoded fields: `event_name`, `event_args` (flattened), `function_name`, `function_args` (flattened), `token_symbol`, `token_decimals`, `amount_decimal`, `decode_status`.

`selector_registry.json` is a living document — grows as new ABIs are processed.

### Derived Event Builder — derived.py

| `derived_type` | Source | Key fields |
|---------------|--------|-----------|
| `asset_transfer` | Transfer event | from, to, token_address, token_symbol, amount_decimal, transfer_type (erc20/erc721) |
| `native_transfer` | tx.value or internal call | from, to, value_eth |
| `swap_summary` | Swap event | trader, pool, token_in, token_out, amount_in, amount_out, price_impact_pct |
| `approval_usage` | Approval event | owner, spender, token, amount, was_consumed |
| `admin_action` | OwnershipTransferred, RoleGranted, Upgraded, Paused | actor, contract, action_type, new_value |
| `execution_edge` | Trace call tree | caller, callee, call_type, function_name, value_eth, call_depth, success |
| `fund_flow_edge` | Aggregated transfers | from, to, value_eth, token_address, hop_number |
| `contract_interaction` | Tx + decoded input | user, contract, function_name, protocol_name |
| `balance_delta` | Aggregated transfers | address, token, delta_amount, direction |

Every derived event includes: `source_tx_hash`, `source_log_index`, `source_layer` for chain of custody.

---

## 7. Detection Engine — ES Queries

### Signal Engine — signal_engine.py

Loads all `.esql` files from `detection/signals/`. Runs each query against the `forensics` index filtered by `investigation_id`. Stores results as `layer: signal` documents.

### 61 Signals across 12 families

**Tier 1 — Basic (tx + receipt + logs, no trace needed):**

Value (7): large_outflow, large_token_transfer, max_approval, zero_then_max_approval, large_mint_from_zero, value_spike, large_price_impact_swap

Flash Loan (3): flash_loan_detected, flash_loan_with_drain, flash_loan_with_swap

Access (5): ownership_transferred, role_granted, proxy_upgraded, paused_or_unpaused, approval_then_transferfrom

Deployment (3): new_contract_deployed, contract_deployed_by_new_wallet, failed_high_gas

Liquidity (2): large_liquidity_removal, deposit_withdraw_same_block

Token (4): honeypot_sell_failure, fee_on_transfer_anomaly, token_balance_mismatch, massive_supply_mint

Governance (3): governance_vote_cast, proposal_created_executed_fast, flash_loan_before_vote

DeFi (6): vault_first_deposit_tiny, vault_donation_before_deposit, liquidation_event, self_liquidation, borrow_at_max_ltv, cascading_liquidations

**Tier 2 — Deep (require debug_traceTransaction):**

Structural (10): reentrancy_pattern, call_depth_anomaly, repeated_external_call, delegatecall_to_unknown, delegatecall_chain, internal_eth_drain, self_destruct, create2_deployment, oracle_read_after_large_swap, spot_price_query

**Tier 3 — Correlation (cross-transaction ES queries):**

Behavioural (7): new_wallet_high_value, dormant_reactivation, burst_transactions, funding_from_mixer, mixer_deposit_post_exploit, cex_deposit_post_exploit, bridge_exit_post_exploit

Bridge (2): bridge_large_outflow, bridge_called_by_new_wallet

Graph (4): high_fanout, star_convergence, circular_flow, multi_hop_movement

Evasion (3): multi_mixer_usage, rapid_chain_of_transfers, dust_consolidation

Each signal document: `signal_name`, `score` (0.0-1.0), `severity` (CRIT/HIGH/MED/LOW), `tx_hash`, `block_number`, `evidence` (source doc references), `description`.

### Pattern Engine — pattern_engine.py

Loads all `.eql` files from `detection/patterns/`. Runs EQL sequence queries against signal + derived documents. Stores results as `layer: alert` documents.

### 20 Attack Patterns across 8 categories

| ID | Pattern | Required signals | Confidence |
|----|---------|-----------------|------------|
| AP-001 | Flash Loan Oracle Manipulation | flash_loan_detected + (large_price_impact_swap OR oracle_read_after_large_swap) + large_token_transfer | 0.90 |
| AP-002 | Flash Loan Governance Takeover | flash_loan_detected + flash_loan_before_vote + proposal_created_executed_fast | 0.90 |
| AP-003 | Flash Loan Liquidation Attack | flash_loan_detected + large_price_impact_swap + liquidation_event + large_token_transfer | 0.85 |
| AP-004 | Flash Loan Arbitrage Exploit | flash_loan_detected + multi_hop_movement + profit extraction | 0.75 |
| AP-005 | Reentrancy Drain | reentrancy_pattern + call_depth_anomaly + (large_outflow OR internal_eth_drain) | 0.90 |
| AP-006 | Cross-Function Reentrancy | repeated_external_call + different selectors at alternating depths + value outflow | 0.80 |
| AP-007 | Read-Only Reentrancy | staticcall during reentrancy + action based on stale read | 0.75 |
| AP-008 | Private Key Compromise | ownership_transferred (unknown addr) + (large_outflow OR large_token_transfer) | 0.85 |
| AP-009 | Proxy Upgrade Attack | proxy_upgraded + new impl deployed same block + value outflow | 0.90 |
| AP-010 | Unauthorized Mint | (role_granted OR ownership_transferred) + massive_supply_mint + large swap sell | 0.85 |
| AP-011 | Liquidity Rug Pull | large_liquidity_removal + large_token_transfer + (mixer_deposit OR cex_deposit) | 0.85 |
| AP-012 | Mint and Dump | massive_supply_mint + large swap sell + large_price_impact_swap | 0.80 |
| AP-013 | Honeypot Token | honeypot_sell_failure + successful buys from multiple addresses | 0.85 |
| AP-014 | MEV Sandwich | 3 txs same block: attacker buy → victim swap → attacker sell | 0.80 |
| AP-015 | Wash Trading | circular_flow + multiple swaps between related addresses + burst_transactions | 0.70 |
| AP-016 | Oracle Spot Price Manipulation | spot_price_query + large_price_impact_swap + victim protocol interaction | 0.85 |
| AP-017 | Vault Donation Attack | vault_first_deposit_tiny + vault_donation_before_deposit + large withdrawal | 0.85 |
| AP-018 | Liquidation Cascade | flash_loan_detected + large_price_impact_swap + cascading_liquidations | 0.80 |
| AP-019 | Bridge Drain | bridge_large_outflow + (new_wallet_high_value OR bridge_called_by_new_wallet) | 0.80 |
| AP-020 | Fund Laundering Chain | any alert + rapid_chain_of_transfers + (mixer OR bridge OR cex deposit) | 0.85 |

Each alert document: `pattern_id`, `pattern_name`, `signals_fired[]`, `confidence`, `attacker_wallet`, `victim_contract`, `funds_drained_eth`, `attack_block_range`.

### Wave delivery

- **Wave 1:** ~20 signals + 4 patterns (testable with 4 Foundry simulations)
- **Wave 2:** Remaining signals + patterns as data sources expand
- **Adding new:** Drop file in correct folder. Engine auto-discovers.

---

## 8. Correlation Engine — Python

### Fund Tracing — fund_trace.py

BFS from seed wallet. 5 hops forward (where did funds go), 5 backward (where did funds come from). Configurable via `max_trace_hops` in config.json.

Haircut taint scoring: value passing through a mixer receives taint_score * 0.7. Through a bridge: * 0.8. Taint never reaches zero.

Output: `fund_flow_edge` documents with from, to, value_eth, token_address, tx_hash, hop_number, direction, taint_score.

### Wallet Clustering — clustering.py

Groups wallets by: same funding source, same deployment pattern, same timing relative to exploit, shared contract interaction fingerprint, common address in traces.

Each cluster gets a `cluster_id`. Output: attacker profile documents.

### Known Address Matching — mixer_detect.py + label_db.py

Tornado Cash (all pool sizes), Hop Protocol, Stargate, Across, LayerZero, Connext. Binance, Coinbase, Kraken, OKX, Bybit hot wallets. OFAC SDN list. Community exploit trackers.

Labels: `ofac_sanctioned`, `known_exploiter`, `cex_deposit`, `mixer_contract`, `bridge_contract`, `protocol_treasury`, `unknown`.

---

## 9. FastAPI Server — server.py

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/analyze` | POST | Accepts investigation config (mode, rpc_url, target, investigation_id, manifest path). Runs pipeline. Streams SSE events. |
| `/analysis/{id}` | GET | Fetch completed investigation from ES |
| `/health` | GET | Check Anvil/RPC, ES, Ollama connectivity. Returns status per service. |
| `/simulate` | POST | Accepts scenario name. Runs `forge script` against Anvil. Returns block range + tx hashes. |

### SSE event format

During pipeline:
```json
{"phase": "collector", "msg": "Block 5 fetched - 12 txs", "severity": "ok", "ts": "12:04:02"}
{"phase": "signals", "msg": "reentrancy_pattern fired (0.95)", "severity": "crit", "ts": "12:04:06"}
```

On completion:
```json
{"phase": "complete", "investigationId": "INV-2026-0001", "stats": {"blocks": 8, "txs": 47, "signals": 5, "indexed": 189}}
```

---

## 10. Frontend Architecture

### Layout — Three fixed columns

| Column | Width | Component |
|--------|-------|-----------|
| Left | 252px | Sidebar.jsx |
| Center | Remaining | Workspace (state machine) |
| Right | 280px | CopilotPanel.jsx |

### Sidebar.jsx

From top to bottom:
- Connection config: RPC URL, ES URL, Ollama URL inputs. Each with green/red dot indicator (calls GET /health).
- Investigation setup: Load manifest button (or manual ABI upload + contract addresses with role dropdowns).
- Mode selector: 4 cards — Watch, Range, Tx Analysis, Wallet Hunt. Clicking selects mode and updates target inputs.
- Target inputs: Watch = no input. Range = from_block + to_block. Tx = transaction hash. Wallet = wallet address.
- Run Analysis button: Wise Green pill button. Disabled when not connected. Shows "Running..." state during analysis.
- Saved analyses: List at bottom. Each item shows case ID, attack type, severity badge, timestamp. Click to restore.

### Center Workspace — 2 states

| State | Trigger | Shows |
|-------|---------|-------|
| Running | User clicks Run | Stats bar (blocks, txs, signals, indexed) + live SSE log with severity colors + phase headers |
| Complete | `phase: complete` SSE event | Investigation view — auto-transitions. Case saved to localStorage. |

### InvestigationView.jsx

- Top bar: severity badge (CRIT/HIGH/MED), attack type label, case ID (monospace), view tabs (Timeline, Graph, Raw)
- Meta bar: 4 cells — attacker address, victim contract, funds drained (red), block range. All monospace.
- Left panel: Attack timeline. Chronological events with colored dots (red=CRIT, amber=HIGH, blue=neutral, gray=setup), bold event name, monospace detail. Vertical line connects dots.
- Right panel: Signals fired. "X of 61 signals fired" header. Cards with severity bar, signal name (bold), description, score.
- Bottom row: 4 action buttons — Explain Signals, Trace Funds, Pattern Match, Generate Report. Each sends context to copilot.

### EntityGraph.jsx

D3.js force-directed graph. Shown on Graph tab.
- Red nodes: attacker wallets, victim contracts
- Blue nodes: known protocols (Aave, Uniswap)
- Gray nodes: mixers, bridges, unknown
- Red edges: value movement (labeled with ETH amount)
- Gray edges: structural (deployments, calls)
- Interactive: click node for details, hover for labels, zoom/pan

### CopilotPanel.jsx

3 states:
- Idle: greeting + instructions
- Watching: during analysis — proactively narrates CRIT signal firings
- Ready: after analysis — answers questions using investigation context

Quick buttons: What signals fired, Trace fund flow, Is this a known pattern, Generate report, What's in ES

Chat input at bottom. History saved per case in localStorage.

### Report Generation

Generate Report button builds structured JSON context (case_id, attack_type, signals, attacker_profile, fund_trail, stats, ES evidence refs) and sends to Gemma 3 1B via Ollama.

7-section output streamed into copilot panel:
1. Executive Summary
2. Attack Timeline
3. Technical Mechanism
4. Attacker Attribution
5. Fund Trail
6. Signal Evidence
7. Remediation Actions

### StoredAnalyses.jsx

Lists all cases from localStorage. Columns: case ID, mode, attack type, severity badge, funds drained, timestamp. Click to restore full investigation view + copilot history.

---

## 11. Wise Design System Application

### Colors
- Near Black `#0e0f0c`: primary text, workspace background
- Wise Green `#9fe870`: primary CTAs, success states, connected indicators
- Dark Green `#163300`: button text on green backgrounds
- Light Mint `#e2f6d5`: soft green surface, badge backgrounds
- Danger Red `#d03238`: CRIT severity, alerts, funds drained
- Warning Yellow `#ffd11a`: HIGH severity warnings
- Gray `#868685`: secondary text, muted elements
- White/off-white: card backgrounds, sidebar

### Typography
- Inter weight 600: body default (confident)
- Inter weight 900: headings
- Monospace: all addresses, tx hashes, block numbers, amounts
- `font-feature-settings: "calt"` on all text

### Components
- Pill buttons: `border-radius: 9999px`, `padding: 5px 16px`
- Hover: `transform: scale(1.05)`, Active: `transform: scale(0.95)`
- Cards: `border-radius: 30px`, `border: 1px solid rgba(14,15,12,0.12)`
- Shadows: ring only — `rgba(14,15,12,0.12) 0px 0px 0px 1px`
- Severity bars: red (CRIT), amber (HIGH), blue (MED), gray (LOW)

---

## 12. Analysis Modes

### Watch Mode
Polls RPC for new blocks via `eth_blockNumber`. Processes each new block through the full pipeline in real time. Signals fire as blocks arrive. No predefined target. Runs until stopped.

### Range Analysis
Input: from_block, to_block. Batch fetches all blocks. Processes entire range as one investigation. Full signal + pattern detection across the complete dataset.

### Tx Analysis
Input: single transaction hash. Fetches tx + receipt + trace. Most detailed output — full call trace available. Deep-dive a specific suspicious transaction.

### Wallet Hunt
Input: wallet address. Loads transaction history up to `tx_history_limit` (default 200). Runs 5-hop BFS fund tracing. Builds wallet cluster. Identifies funding sources and exit destinations. Produces attacker profile even without known exploit.

---

## 13. Foundry Simulations

### 4 Scenarios

Each scenario has 3 phases:
1. Deploy victim protocol + supporting contracts
2. Generate normal user activity (realistic noise)
3. Execute the attack

Each scenario outputs a `client/` folder with ABIs + manifest.json — simulating what a real client would hand over.

| Scenario | Victim protocol | Attack type | Tests patterns |
|----------|----------------|-------------|---------------|
| reentrancy-drain | VulnerableVault (ETH vault with withdraw-before-update) | Recursive withdraw | AP-005 |
| flash-loan-oracle | LendingPool + SimpleOracle + MockUniswapPool | Flash loan → pool manipulation → oracle read → drain | AP-001 |
| admin-key-abuse | GovernanceToken with owner mint | Ownership transfer → mint → dump | AP-008, AP-010 |
| mev-sandwich | SimpleDEX (AMM pool) | Frontrun → victim swap → backrun | AP-014 |

---

## 14. Configuration — config.json

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

Frontend sidebar allows runtime override. Overrides don't persist — current session only.

---

## 15. Startup — start.sh

One command brings up the entire stack:
1. Start Elasticsearch via Docker
2. Start Ollama + pull gemma3:1b if not present
3. Start Anvil (if simulation mode)
4. Create ES indices + mappings
5. Start FastAPI server
6. Start Vite dev server

Manual: 5 terminals as documented in config.

---

## 16. What's NOT In Scope (honest limits)

| Attack type | Why we can't detect it | What we CAN show |
|-------------|----------------------|------------------|
| Logic bugs (rounding, precision) | Needs source code analysis | Symptoms: unexpected value outflows |
| Storage collision (proxy slots) | Needs storage slot reads | Symptoms: unexpected state changes after upgrade |
| Signature replay | Needs mempool data | Symptoms: unexpected authorized actions |
| Social engineering setup | Off-chain | We detect the on-chain drain that follows |
| Zero-day compiler bugs | Needs bytecode decompilation | Reentrancy signals still fire on exploit tx |

When signals fire but no pattern matches → "Unknown pattern — manual review required."

---

## 17. Future Upgrade Path

| Addition | How |
|----------|-----|
| New signal | Drop `.esql` file in correct family folder |
| New pattern | Drop `.eql` file in patterns/ |
| New derived type | Add builder function in derived.py, set new derived_type |
| New ABI/protocol | Drop JSON in abi_registry/protocols/ |
| New simulation | Create folder under scenarios/ |
| New chain | Change rpc_url + chain_id in config |
| Split ES index | Change one line in ingest.py, run ES reindex |
| Bytecode decompilation | New pipeline module (Phase 2) |
| Cross-chain tracing | New collector per chain (Phase 3) |
| Multi-investigator | New ES index + auth layer (Phase 4) |
