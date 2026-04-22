# ChainSentinel — Technical Deep Dive
## EVM Blockchain Forensics: From Raw Chain Data to Confirmed Alerts

**Prepared by:** SISA Information Security  
**Classification:** Internal Technical Reference  
**Version:** 1.0 | April 2026

---

## Table of Contents

1. [System Overview](#1-system-overview)
2. [Architecture: The 7-Layer Pipeline](#2-architecture-the-7-layer-pipeline)
3. [Layer 1 — Collection (RPC Interface)](#3-layer-1--collection-rpc-interface)
4. [Layer 2 — Normalization](#4-layer-2--normalization)
5. [Layer 3 — Decoding (ABI Engine)](#5-layer-3--decoding-abi-engine)
6. [Layer 4 — Derived Event Builder (9 Security Primitives)](#6-layer-4--derived-event-builder)
7. [Layer 5 — Signal Engine (ES|QL)](#7-layer-5--signal-engine-esql)
8. [Layer 6 — Pattern Engine (EQL)](#8-layer-6--pattern-engine-eql)
9. [Layer 7 — Correlation & Attribution](#9-layer-7--correlation--attribution)
10. [Elasticsearch Index Architecture](#10-elasticsearch-index-architecture)
11. [Attack Detection Walkthrough: Reentrancy](#11-attack-detection-walkthrough-reentrancy)
12. [Attack Detection Walkthrough: Flash Loan Oracle Manipulation](#12-attack-detection-walkthrough-flash-loan)
13. [Signal Library — All 61 Signals](#13-signal-library)
14. [Pattern Library — All 20 Attack Patterns](#14-pattern-library)
15. [Deployment Configurations](#15-deployment-configurations)
16. [Design Principles & Why They Matter](#16-design-principles)

---

## 1. System Overview

ChainSentinel is a standalone EVM blockchain forensics tool. Given any of the following inputs:

```
Input A: Transaction Hash    → 0x76d28f281e0f64e5ff9559a015fcc40d615a83b0fc2395e65b94e950bf74c0e8
Input B: Block Range         → from_block: 1, to_block: 1238
Input C: Wallet Address      → 0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266
```

ChainSentinel runs a **full forensic pipeline** that:

1. Pulls all raw on-chain data (blocks, transactions, receipts, logs, call traces)
2. Decodes every function call and event using client-provided ABIs + known protocol ABIs
3. Builds 9 derived security event types from the decoded data
4. Runs 61 ES|QL signal queries against Elasticsearch
5. Runs 20 EQL sequential pattern queries to correlate signals into attack alerts
6. Traces fund flows using BFS from attacker wallets
7. Surfaces findings in a React investigation workspace with an Ollama-powered AI copilot

**Real-world use case:** A client (DeFi protocol, exchange, DAO) was exploited. They provide their RPC endpoint, contract ABIs, deployed addresses, and approximate time window. ChainSentinel analyzes purely from on-chain data. No attacker source code needed.

---

## 2. Architecture: The 7-Layer Pipeline

```
╔══════════════════════════════════════════════════════════════════════════════╗
║                        CHAINSENTINEL ARCHITECTURE                           ║
╚══════════════════════════════════════════════════════════════════════════════╝

  CLIENT INPUT                     ANALYSIS PIPELINE                  OUTPUTS
  ─────────────                    ─────────────────                  ───────

  ┌─────────────┐
  │  RPC URL    │◄── Anvil (local)
  │  Chain ID   │◄── Alchemy/Infura (testnet)
  │  ABI Files  │◄── Mainnet Archive Node
  │  Manifest   │
  └──────┬──────┘
         │
         ▼
  ┌──────────────────────────────────────────────────────────────────────────┐
  │  LAYER 1: COLLECTOR                                                      │
  │  collector.py                                                            │
  │                                                                          │
  │  eth_getBlockByNumber ──► block headers                                  │
  │  eth_getTransactionReceipt ──► status, gas, logs                        │
  │  eth_getLogs ──► event log entries                                       │
  │  debug_traceTransaction ──► internal call tree (Anvil/archive)           │
  └───────────────────────────────┬──────────────────────────────────────────┘
                                  │  raw JSON docs
                                  ▼
                         [forensics-raw index]
                      doc_type: transaction | log | trace
                                  │
  ┌───────────────────────────────▼──────────────────────────────────────────┐
  │  LAYER 2: NORMALIZER                                                     │
  │  normalizer.py                                                           │
  │                                                                          │
  │  hex → int (block numbers, gas, values)                                  │
  │  addresses → lowercase checksummed                                       │
  │  timestamps → ISO 8601 UTC                                               │
  │  value_wei (keyword) + value_eth (double)                                │
  └───────────────────────────────┬──────────────────────────────────────────┘
                                  │
  ┌───────────────────────────────▼──────────────────────────────────────────┐
  │  LAYER 3: DECODER (ABI Engine)                                           │
  │  decoder.py + abi_registry/                                              │
  │                                                                          │
  │  Priority 1: cases/    ← Client ABI files (VulnerableVault.json etc)    │
  │  Priority 2: standards/ ← ERC20, ERC721, ERC1155                        │
  │  Priority 3: protocols/ ← Uniswap V2/V3, Aave, Compound, Curve         │
  │  Priority 4: selector_registry.json ← living 4-byte selector cache      │
  │                                                                          │
  │  Output: function_name, function_args, event_name, event_args           │
  │          decode_status: decoded | partial | unknown                      │
  └───────────────────────────────┬──────────────────────────────────────────┘
                                  │  decoded docs
                                  ▼
                         [forensics index, layer: decoded]
                                  │
  ┌───────────────────────────────▼──────────────────────────────────────────┐
  │  LAYER 4: DERIVED EVENT BUILDER (9 Security Primitives)                  │
  │  derived.py                                                              │
  │                                                                          │
  │  value_flow_intra_tx  ← ETH/token flow within single tx call tree       │
  │  price_reads          ← oracle/price function calls at depth > 0         │
  │  access_control       ← ownership transfer, role grants                  │
  │  deployment           ← new contract deployment events                   │
  │  liquidity_change     ← add/remove liquidity events                      │
  │  token_transfer       ← ERC20/721 transfers with value                   │
  │  governance_action    ← proposal, vote, execution events                 │
  │  call_depth           ← internal call depth measurement                  │
  │  storage_pattern      ← storage write timing relative to external calls  │
  └───────────────────────────────┬──────────────────────────────────────────┘
                                  │  derived docs
                                  ▼
                         [forensics index, layer: derived]
                                  │
  ┌───────────────────────────────▼──────────────────────────────────────────┐
  │  LAYER 5: SIGNAL ENGINE (ES|QL)                                          │
  │  signal_engine.py + detection/signals/                                   │
  │                                                                          │
  │  61 .esql files → Elasticsearch ES|QL queries                            │
  │  Each query: filtered by investigation_id, produces signal documents      │
  │                                                                          │
  │  12 Signal Families:                                                     │
  │  Value(7) Flash(3) Access(5) Deploy(3) Liquidity(2) Token(4)            │
  │  Governance(3) DeFi(6) Structural(10) Behavioural(7) Bridge(2) Graph(4) │
  │  Evasion(3)                                                              │
  └───────────────────────────────┬──────────────────────────────────────────┘
                                  │  signal docs
                                  ▼
                         [forensics index, layer: signal]
                                  │
  ┌───────────────────────────────▼──────────────────────────────────────────┐
  │  LAYER 6: PATTERN ENGINE (EQL)                                           │
  │  pattern_engine.py + detection/patterns/                                 │
  │                                                                          │
  │  20 .eql files → Elasticsearch EQL sequence queries                      │
  │  Correlates signals across time + same tx_hash                           │
  │  Produces alerts when signal sequence matches with confidence threshold  │
  └───────────────────────────────┬──────────────────────────────────────────┘
                                  │  alert docs
                                  ▼
                         [forensics index, layer: alert]
                                  │
  ┌───────────────────────────────▼──────────────────────────────────────────┐
  │  LAYER 7: CORRELATION (Python BFS)                                       │
  │  fund_trace.py + clustering.py + mixer_detect.py + label_db.py          │
  │                                                                          │
  │  BFS fund trace: 5 hops forward + backward from attacker                │
  │  Taint scoring: mixer ×0.7, bridge ×0.8, direct ×1.0                   │
  │  Wallet clustering: shared funding, timing, deployment patterns          │
  │  Labels: OFAC SDN, known exploiters, CEX hot wallets, bridges           │
  └───────────────────────────────┬──────────────────────────────────────────┘
                                  │  attacker + case docs
                                  ▼
                    [forensics index, layer: attacker | case]
                                  │
                          ┌───────▼───────┐
                          │  FastAPI SSE  │  ← streams live progress events
                          │   server.py   │
                          └───────┬───────┘
                                  │
               ┌──────────────────┼──────────────────┐
               ▼                  ▼                   ▼
        [React Frontend]   [Kibana Dashboards]  [Ollama Copilot]
        Investigation UI   Visual analytics     AI forensic report
```

---

## 3. Layer 1 — Collection (RPC Interface)

**File:** `chainsentinel/pipeline/collector.py`

The collector is the only component that talks directly to the blockchain RPC endpoint. It supports three modes:

### 3.1 TX Analysis Mode
```
eth_getTransactionByHash(tx_hash)
eth_getTransactionReceipt(tx_hash)
debug_traceTransaction(tx_hash, {tracer: "callTracer"})
eth_getLogs(fromBlock=block, toBlock=block)
```

### 3.2 Range Analysis Mode
```
For each block in [from_block, to_block]:
  eth_getBlockByNumber(block, True)     ← gets full tx list
  For each tx in block:
    eth_getTransactionReceipt(tx_hash)
    debug_traceTransaction(tx_hash)     ← only if supported
  eth_getLogs(fromBlock, toBlock)       ← batch log fetch
```

### 3.3 Graceful Degradation

```
RPC Capability Matrix:
┌─────────────────────────────┬────────┬────────┬────────┐
│ Method                      │ Anvil  │Sepolia │Mainnet │
│                             │ (local)│ (basic)│(archive│
├─────────────────────────────┼────────┼────────┼────────┤
│ eth_getBlock                │  YES   │  YES   │  YES   │
│ eth_getTransactionReceipt   │  YES   │  YES   │  YES   │
│ eth_getLogs                 │  YES   │  YES   │  YES   │
│ debug_traceTransaction      │  YES   │   NO   │YES(arc)│
└─────────────────────────────┴────────┴────────┴────────┘

If debug_traceTransaction fails:
  → Skip trace collection
  → Derived types that need traces: value_flow_intra_tx, price_reads, call_depth
  → These derived types produce 0 documents
  → Signals depending on those derived types score 0
  → Tool still works, just with reduced signal coverage
```

### 3.4 Document Produced (forensics-raw)

```json
{
  "_id": "31337_0x76d28f281e0f64e5ff9...",
  "doc_type": "transaction",
  "tx_hash": "0x76d28f...",
  "block_number": 33,
  "block_datetime": "2026-04-22T07:31:10Z",
  "from_address": "0xf39fd6e51aad88f6...",
  "to_address": "0x5fbdb2315678afecb3...",
  "value_wei": "100000000000000000",
  "value_eth": 0.1,
  "gas": 120000,
  "gas_used": 89432,
  "success": true,
  "input": "0x3ccfd60b",
  "chain_id": 31337,
  "investigation_id": "INV-REEN-0001"
}
```

---

## 4. Layer 2 — Normalization

**File:** `chainsentinel/pipeline/normalizer.py`

All hex values from the RPC become typed values. All addresses become lowercase. Timestamps become ISO 8601. This ensures consistent field types for ES|QL arithmetic queries.

```
hex "0x1f" → int 31
hex address "0xF39FD6E51aad88F6F4ce6aB..." → "0xf39fd6e51aad88f6f4ce6ab..."
hex timestamp "0x67f7d6e1" → "2026-04-22T07:31:10Z"
value "0x16345785D8A0000" → value_wei: "100000000000000000"
                          → value_eth: 0.1
```

`value_wei` is stored as **keyword** (not long) because uint256 values exceed JavaScript's MAX_SAFE_INTEGER and Elasticsearch's long range. `value_eth` is **double** for arithmetic in queries.

---

## 5. Layer 3 — Decoding (ABI Engine)

**File:** `chainsentinel/pipeline/decoder.py`  
**Registry:** `chainsentinel/pipeline/abi_registry/`

### 5.1 ABI Resolution Priority

```
For each transaction input / event log:

  STEP 1: Extract 4-byte selector (first 4 bytes of input data)
           0x3ccfd60b → "withdraw(uint256)"

  STEP 2: Try case ABIs (client-provided)
           abi_registry/cases/VulnerableVault.json
           abi_registry/cases/ReentrancyAttacker.json

  STEP 3: Try standard ABIs (ERC20, ERC721, ERC1155)
           abi_registry/standards/erc20.json
           → matches "transfer(address,uint256)"

  STEP 4: Try protocol ABIs (Uniswap V2/V3, Aave, Compound, Curve)
           abi_registry/protocols/uniswap_v2.json

  STEP 5: Try selector_registry.json (4-byte cache, grows at runtime)
           { "0x3ccfd60b": "withdraw(uint256)" }

  STEP 6: If all fail → decode_status: "unknown", function_name: null
```

### 5.2 Document Produced (forensics, layer: decoded)

```json
{
  "_id": "INV-REEN-0001_0x76d28f..._0_decoded",
  "layer": "decoded",
  "tx_hash": "0x76d28f...",
  "block_number": 33,
  "event_name": "Withdraw",
  "event_args": {
    "user": "0xf39fd6e51aad88f6f4ce6ab8827279cfffb92266",
    "amount": 100000000000000000
  },
  "decode_status": "decoded",
  "investigation_id": "INV-REEN-0001"
}
```

---

## 6. Layer 4 — Derived Event Builder

**File:** `chainsentinel/pipeline/derived.py`

This is where Python "understands" security. Nine derived types are computed from decoded transactions and traces. Each produces documents that become the input to signal queries.

### 6.1 The 9 Derived Types

```
┌─────────────────────────┬──────────────────────────────────────────────────┐
│ Derived Type            │ What It Captures                                 │
├─────────────────────────┼──────────────────────────────────────────────────┤
│ value_flow_intra_tx     │ ETH movement at each call depth within a single  │
│                         │ transaction. Detects flash loan brackets          │
│                         │ (large in + large out same tx), drain patterns   │
│                         │ Requires: debug_traceTransaction                  │
├─────────────────────────┼──────────────────────────────────────────────────┤
│ price_reads             │ Any call to getPrice(), getSpotPrice(),           │
│                         │ latestRoundData() made at call depth > 0 (i.e., │
│                         │ inside a callback or nested call)                │
│                         │ Requires: debug_traceTransaction                  │
├─────────────────────────┼──────────────────────────────────────────────────┤
│ access_control          │ Owner transfer, role grant/revoke, minter add     │
│                         │ Detected from Ownership/Role event signatures    │
├─────────────────────────┼──────────────────────────────────────────────────┤
│ deployment              │ Contract creation with bytecode size, deployer   │
│                         │ address, creation salt (for CREATE2)             │
├─────────────────────────┼──────────────────────────────────────────────────┤
│ liquidity_change        │ addLiquidity / removeLiquidity events            │
│                         │ Tracks reserve deltas per pool                  │
├─────────────────────────┼──────────────────────────────────────────────────┤
│ token_transfer          │ ERC20 Transfer events with token address,        │
│                         │ from, to, value. Normalized to ETH equivalent   │
├─────────────────────────┼──────────────────────────────────────────────────┤
│ governance_action       │ Proposal creation, votes cast, proposal executed │
│                         │ Tracks quorum, timelock delays, direct execution │
├─────────────────────────┼──────────────────────────────────────────────────┤
│ call_depth              │ Maximum call depth reached in a transaction      │
│                         │ and depth at which each external call occurs    │
│                         │ Requires: debug_traceTransaction                  │
├─────────────────────────┼──────────────────────────────────────────────────┤
│ storage_pattern         │ Timing of storage writes relative to external   │
│                         │ calls. Pre-call write = safe, post-call = risky │
│                         │ Requires: debug_traceTransaction                  │
└─────────────────────────┴──────────────────────────────────────────────────┘
```

### 6.2 Reentrancy Detection via Derived Types

```
Transaction: 0x76d28f... (the reentrancy attack)

TRACE (debug_traceTransaction output, simplified):
  depth=1  call: vault.withdraw(0.1 ETH)
    depth=2  call: reAttacker.receive() [ETH transfer triggers fallback]
      depth=3  call: vault.withdraw(0.1 ETH)   ← RE-ENTRY!
        depth=4  call: reAttacker.receive()
          depth=5  call: vault.withdraw(0.1 ETH) ← second re-entry
            ...
          ETH sent: 0.1
          STORAGE write: balances[attacker] -= 0.1  ← AFTER ETH send
        ETH sent: 0.1
        STORAGE write: balances[attacker] -= 0.1
      ETH sent: 0.1
      STORAGE write: balances[attacker] -= 0.1

derived_type: call_depth
  → max_depth: 5
  → has_recursive_pattern: true

derived_type: storage_pattern
  → external_call_before_storage_write: true    ← THE VULNERABILITY
  → depth_of_storage_write: 5

derived_type: value_flow_intra_tx
  → inflow_depth_1: 0.1 ETH (user's deposit entry)
  → outflow_depth_2: 0.3 ETH (drained at depth 2)
  → drain_ratio: 3.0x (drained 3× inflow)
```

---

## 7. Layer 5 — Signal Engine (ES|QL)

**File:** `chainsentinel/detection/signal_engine.py`  
**Queries:** `chainsentinel/detection/signals/**/*.esql`

### 7.1 How Signals Work

```python
# signal_engine.py (simplified)
def run_all_signals(investigation_id):
    for esql_file in glob("signals/**/*.esql"):
        signal_name = esql_file.stem
        query = load_query(esql_file)
        
        # Inject investigation filter
        query = query.replace("{{investigation_id}}", investigation_id)
        
        # Run against Elasticsearch
        results = es.esql.query(query=query)
        
        # Store each hit as a signal document
        for row in results.rows:
            ingest_signal(signal_name, row, investigation_id)
```

### 7.2 Example: recursive_depth_pattern.esql

```sql
FROM forensics
| WHERE investigation_id == "{{investigation_id}}"
| WHERE layer == "derived"
| WHERE derived_type == "call_depth"
| WHERE max_call_depth >= 3
| WHERE has_recursive_pattern == true
| STATS
    tx_count = COUNT(tx_hash),
    max_depth_seen = MAX(max_call_depth)
  BY tx_hash, block_number
| WHERE tx_count >= 1
```

**What it detects:** Any transaction where a contract calls itself recursively 3+ levels deep.

### 7.3 Example: drain_ratio_exceeded.esql

```sql
FROM forensics
| WHERE investigation_id == "{{investigation_id}}"
| WHERE layer == "derived"
| WHERE derived_type == "value_flow_intra_tx"
| WHERE inflow_eth > 0
| EVAL drain_ratio = outflow_eth / inflow_eth
| WHERE drain_ratio >= 1.5
| KEEP tx_hash, block_number, contract_address, drain_ratio, inflow_eth, outflow_eth
```

**What it detects:** Any contract that outputs 150%+ of what it received in the same tx — indicating extraction of pre-existing funds.

### 7.4 Example: flashloan_bracket_detected.esql

```sql
FROM forensics
| WHERE investigation_id == "{{investigation_id}}"
| WHERE layer == "derived"
| WHERE derived_type == "value_flow_intra_tx"
| WHERE large_inflow == true AND large_outflow == true
| WHERE same_tx_repay == true
| WHERE inflow_eth >= 1000
| KEEP tx_hash, block_number, inflow_eth, outflow_eth, flash_loan_contract
```

**What it detects:** Large token inflow + repayment in same tx (ERC3156 flash loan pattern).

### 7.5 Signal Coverage Map

```
SIGNAL FAMILY          SIGNALS                              REQUIRED DATA
──────────────────────────────────────────────────────────────────────────────
Value (7)              large_value_inflow_spike             logs + traces
                       drain_ratio_exceeded                 traces
                       net_negative_contract_balance        traces
                       value_concentration                  logs
                       value_dispersion                     logs
                       multiple_asset_drain_same_tx         logs + traces
                       vault_share_price_spike              logs

Flash Loan (3)         flashloan_bracket_detected           traces (critical)
                       price_read_during_callback           traces (critical)
                       hook_callback_detected               traces

Access Control (5)     ownership_transfer_then_drain        logs
                       approval_for_max_amount              logs
                       cross_function_reentry               traces
                       delegatecall_storage_write           traces
                       initialize_on_live_contract          logs

Deployment (3)         contract_deployed_before_attack      logs
                       same_block_deploy_and_attack         logs
                       create2_redeployment                 logs

Structural (10)        recursive_depth_pattern              traces
                       storage_update_delay                 traces
                       value_drain_per_depth                traces
                       cross_contract_state_dependency      traces
                       event_order_violation                logs
                       duplicate_event_emission             logs
                       missing_expected_event               logs
                       event_parameter_mismatch             logs
                       proxy_implementation_change          logs
                       selfdestruct_detected                traces

Behavioural (7)        address_funded_before_attack         logs
                       new_address_first_interaction        logs
                       failed_attempts_before_success       receipts
                       nonce_gap_detected                   receipts
                       high_gas_anomaly                     receipts
                       same_block_deploy_and_attack         logs
                       rapid_token_dump                     logs

... (61 total signals)
```

---

## 8. Layer 6 — Pattern Engine (EQL)

**File:** `chainsentinel/detection/pattern_engine.py`  
**Queries:** `chainsentinel/detection/patterns/*.eql`

### 8.1 Why EQL (Event Query Language)?

ES|QL works on individual documents (signals). EQL works on **sequences of events**. An attack isn't one signal — it's a **choreography** of signals across time and transactions.

EQL lets us write:
> "Find a transaction where: first a flash loan bracket appears, then a price oracle is read during the callback, then a drain ratio is exceeded — all within the same tx_hash"

### 8.2 How Pattern Engine Works

```python
# pattern_engine.py (simplified)
def run_all_patterns(investigation_id):
    for eql_file in glob("patterns/*.eql"):
        pattern_id = extract_pattern_id(eql_file)  # "AP-001"
        pattern_name = extract_metadata(eql_file)    # "classic_reentrancy"
        confidence = extract_confidence(eql_file)    # 0.95
        
        query = load_query(eql_file).replace("{{id}}", investigation_id)
        
        # Run EQL sequence query
        results = es.eql.search(
            index="forensics",
            query=query,
            size=10
        )
        
        for sequence in results.sequences:
            # Each sequence = one confirmed attack instance
            ingest_alert(pattern_id, sequence, confidence, investigation_id)
```

### 8.3 Example: AP-001 classic_reentrancy.eql

```javascript
// AP-001: Classic Single-Function Reentrancy
// confidence: 0.95
// required_signals: recursive_depth_pattern, storage_update_delay, value_drain_per_depth

sequence by tx_hash
  [signal where investigation_id == "{{id}}"
             and signal_name == "recursive_depth_pattern"]
  [signal where investigation_id == "{{id}}"
             and signal_name == "storage_update_delay"]
  [signal where investigation_id == "{{id}}"
             and signal_name == "value_drain_per_depth"]
```

**What this means:** In the same transaction, we must see:
1. A recursive call pattern (depth 3+)
2. A storage write happening AFTER an external call (the bug)
3. Value being drained at each depth level (the extraction)

If all 3 appear in sequence on the same `tx_hash` → **AP-001 alert fires at 95% confidence**.

### 8.4 Example: AP-006 flash_loan_oracle_manipulation.eql

```javascript
// AP-006: Flash Loan Oracle Manipulation
// confidence: 0.90
// required_signals: flashloan_bracket_detected, price_read_during_callback,
//                   spot_price_manipulation, drain_ratio_exceeded

sequence by tx_hash
  [signal where investigation_id == "{{id}}"
             and signal_name == "flashloan_bracket_detected"]
  [signal where investigation_id == "{{id}}"
             and signal_name == "price_read_during_callback"]
  [signal where investigation_id == "{{id}}"
             and signal_name == "spot_price_manipulation"]
  [signal where investigation_id == "{{id}}"
             and signal_name == "drain_ratio_exceeded"]
```

### 8.5 Full Pattern Catalog

```
AP-001  classic_reentrancy               95%  ← reentrancy-drain scenario
AP-002  cross_function_reentrancy        90%
AP-003  read_only_reentrancy             85%
AP-004  cross_contract_reentrancy        88%
AP-005  reentrancy_with_flashloan        92%
AP-006  flash_loan_oracle_manipulation   90%  ← flash-loan-oracle scenario
AP-007  flash_loan_governance_attack     85%
AP-008  admin_key_compromise             88%  ← admin-key-abuse scenario
AP-009  price_oracle_manipulation        87%
AP-010  token_mint_and_dump              85%  ← admin-key-abuse scenario
AP-011  governance_instant_execution     83%
AP-012  liquidity_pool_drain             88%
AP-013  donation_attack                  80%
AP-014  mev_sandwich                     85%  ← mev-sandwich scenario
AP-015  bridge_fund_relay                78%
AP-016  mixer_fund_obfuscation           82%
AP-017  create2_redeploy_attack          87%
AP-018  permit_frontrun                  80%
AP-019  integer_overflow_chain           83%
AP-020  liquidation_cascade              86%
```

---

## 9. Layer 7 — Correlation & Attribution

### 9.1 Fund Trace BFS

```
ATTACKER WALLET: 0x70997970c51812dc3a010c7d01b50e0d17dc79c8

                              ┌─────────────────┐
                              │ ATTACKER WALLET  │ taint=1.0
                              │ 0x70997970...   │
                              └────────┬────────┘
                  ┌───────────────┬────┘
                  ▼               ▼
          ┌──────────┐    ┌──────────────┐
          │ fresh1   │    │ Tornado Cash │ taint×0.7
          │ 0xabc... │    │  0x910c...  │
          │taint=1.0 │    │ taint=0.70  │
          └─────┬────┘    └──────────────┘
                ▼
          ┌──────────┐
          │ fresh2   │
          │ 0xdef... │
          │taint=1.0 │
          └──────────┘

hop=0: seed wallet (taint=1.0)
hop=1: direct recipients (taint=1.0)
hop=2: mixer interaction (taint×0.7=0.70)
hop=3: mixer exit wallets (taint×0.7×0.8=0.56)
hop=4: CEX deposit (labeled, taint=0.56)
hop=5: CEX hot wallet (labeled, taint=0.56)
```

### 9.2 Wallet Clustering

```python
# Wallets are grouped into clusters when they share:
# 1. Same funding source (funded from same address)
# 2. Same time window of first activity (within 1 hour)
# 3. Same contract deployer
# 4. Common nonce patterns (sequential, batch creation)

Cluster AP-001-CLUSTER-001:
  - attacker EOA:       0x70997970... (funded attacker)
  - fresh1:             0xabc...      (funded by attacker)
  - fresh2:             0xdef...      (funded by attacker)
  - reAttacker contract: 0x5fbdb2...  (deployed by attacker)
```

---

## 10. Elasticsearch Index Architecture

### 10.1 Two Indices, Strict Separation

```
┌─────────────────────────────────────────────────────────────────────┐
│  forensics-raw                                                       │
│  PURPOSE: Untouched chain evidence (never modified after ingest)    │
├─────────────────────────────────────────────────────────────────────┤
│  doc_type: "transaction"  │  doc_type: "log"  │  doc_type: "trace" │
│  One doc per tx           │  One doc per log  │  One doc per tx    │
│  ID: {chain}_{tx_hash}    │  ID: {chain}_     │  ID: {chain}_      │
│                           │  {tx}_{log_idx}   │  {tx}_trace        │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│  forensics                                                           │
│  PURPOSE: Pipeline analysis outputs (decoded → derived → signal → alert)
├─────────────────────────────────────────────────────────────────────┤
│  layer: "decoded"    │  layer: "derived"    │  layer: "signal"     │
│  layer: "alert"      │  layer: "attacker"   │  layer: "case"       │
└─────────────────────────────────────────────────────────────────────┘
```

### 10.2 Deterministic Document IDs (Idempotency)

Re-running the pipeline never creates duplicates. Every document ID is deterministic:

```
forensics-raw transaction:  {chain_id}_{tx_hash}
forensics-raw log:          {chain_id}_{tx_hash}_{log_index}
forensics-raw trace:        {chain_id}_{tx_hash}_trace
forensics decoded:          {investigation_id}_{tx_hash}_{log_index}_decoded
forensics derived:          {investigation_id}_{derived_type}_{tx_hash}_{log_index}
forensics signal:           {investigation_id}_{signal_name}_{tx_hash}
forensics alert:            {investigation_id}_{pattern_id}
forensics attacker:         {investigation_id}_{cluster_id}
forensics case:             {investigation_id}
```

### 10.3 Field Type Strategy

```
Field          Type       Why
─────────────────────────────────────────────────────────────────
address        keyword    Exact match only, lowercase enforced
tx_hash        keyword    Exact match, EQL sequence join key
event_args     flattened  Prevents mapping explosion (dynamic keys)
function_args  flattened  Same — arbitrary function parameters
value_eth      double     Arithmetic in ES|QL (comparisons, EVAL)
value_wei      keyword    Too large for long (uint256 > MAX_SAFE_INT)
score          float      Signal confidence scoring
block_number   long       Range queries, ordering
@timestamp     date       Time-based filtering in Kibana
layer          keyword    Partition queries by pipeline stage
derived_type   keyword    Filter within derived layer
signal_name    keyword    EQL signal correlation key
dynamic        strict     Prevents unknown fields (both indices)
```

---

## 11. Attack Detection Walkthrough: Reentrancy

### Real transaction from simulation: 0x76d28f281e0f64e5ff9559a015fcc40d615a83b0fc2395e65b94e950bf74c0e8

```
STEP-BY-STEP DETECTION

Block 33 — The Attack Transaction

┌─ COLLECTOR ──────────────────────────────────────────────────────────────┐
│ debug_traceTransaction("0x76d28f...")                                     │
│                                                                           │
│ Returns call tree:                                                        │
│   ReentrancyAttacker.attack()                                            │
│     → VulnerableVault.withdraw(0.1 ETH)         [depth 1]               │
│       → ReentrancyAttacker.receive()             [depth 2, ETH received] │
│         → VulnerableVault.withdraw(0.1 ETH)     [depth 3, RE-ENTRY]     │
│           → ReentrancyAttacker.receive()         [depth 4]               │
│             → VulnerableVault.withdraw(0.1 ETH) [depth 5, RE-ENTRY]    │
│               [balances not yet updated at any depth]                    │
│               → Transfer 0.1 ETH                                         │
│               → STORAGE WRITE: balances[attacker] -= 0.1               │
│             → Transfer 0.1 ETH                                           │
│             → STORAGE WRITE: balances[attacker] -= 0.1                 │
│           → Transfer 0.1 ETH                                             │
│           → STORAGE WRITE: balances[attacker] -= 0.1                   │
└──────────────────────────────────────────────────────────────────────────┘
                                 │
                                 ▼
┌─ NORMALIZER ─────────────────────────────────────────────────────────────┐
│ hex block → int 33                                                        │
│ "0x76d28f..." → lowercase preserved                                       │
│ 0x16345785D8A0000 → value_wei: "100000000000000000", value_eth: 0.1     │
└──────────────────────────────────────────────────────────────────────────┘
                                 │
                                 ▼
┌─ DECODER ────────────────────────────────────────────────────────────────┐
│ 0xd0e30db0 → "attack()" from cases/ReentrancyAttacker.json              │
│ 0x3ccfd60b → "withdraw(uint256)" from cases/VulnerableVault.json        │
│ Withdraw event → decoded with event_args: {user: ..., amount: 0.1 ETH}  │
└──────────────────────────────────────────────────────────────────────────┘
                                 │
                                 ▼
┌─ DERIVED EVENT BUILDER ──────────────────────────────────────────────────┐
│                                                                           │
│ call_depth doc:                                                           │
│   { max_call_depth: 5, has_recursive_pattern: true, tx_hash: "0x76d28f"}│
│                                                                           │
│ storage_pattern doc:                                                      │
│   { external_call_before_storage_write: true,                            │
│     storage_write_depth: 5, tx_hash: "0x76d28f" }                       │
│                                                                           │
│ value_flow_intra_tx doc:                                                  │
│   { inflow_eth: 0.1, outflow_eth: 0.3, drain_ratio: 3.0,               │
│     contract: "0x5fbdb2...(VulnerableVault)", tx_hash: "0x76d28f" }     │
└──────────────────────────────────────────────────────────────────────────┘
                                 │
                                 ▼
┌─ SIGNAL ENGINE (ES|QL) ──────────────────────────────────────────────────┐
│                                                                           │
│ recursive_depth_pattern.esql fires:                                      │
│   → Signal doc: { signal_name: "recursive_depth_pattern",               │
│                   tx_hash: "0x76d28f", block_number: 33 }               │
│                                                                           │
│ storage_update_delay.esql fires:                                         │
│   → Signal doc: { signal_name: "storage_update_delay",                  │
│                   tx_hash: "0x76d28f", block_number: 33 }               │
│                                                                           │
│ value_drain_per_depth.esql fires:                                        │
│   → Signal doc: { signal_name: "value_drain_per_depth",                 │
│                   tx_hash: "0x76d28f", block_number: 33 }               │
└──────────────────────────────────────────────────────────────────────────┘
                                 │
                                 ▼
┌─ PATTERN ENGINE (EQL) ───────────────────────────────────────────────────┐
│                                                                           │
│ AP-001 sequence query runs:                                               │
│   sequence by tx_hash                                                    │
│     [signal: recursive_depth_pattern] ← MATCHED (block 33)             │
│     [signal: storage_update_delay]    ← MATCHED (block 33)             │
│     [signal: value_drain_per_depth]   ← MATCHED (block 33)             │
│                                                                           │
│ ALL 3 SIGNALS MATCH ON SAME TX_HASH → ALERT FIRES                        │
│                                                                           │
│ Alert doc:                                                                │
│   { pattern_id: "AP-001",                                                │
│     pattern_name: "classic_reentrancy",                                  │
│     confidence: 0.95,                                                    │
│     tx_hash: "0x76d28f...",                                             │
│     block_number: 33,                                                    │
│     signals_fired: ["recursive_depth_pattern",                          │
│                     "storage_update_delay",                              │
│                     "value_drain_per_depth"] }                           │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## 12. Attack Detection Walkthrough: Flash Loan Oracle Manipulation

### How AP-006 would fire on the flash-loan-oracle simulation

```
FLASH LOAN ATTACK TRANSACTION (single tx, multiple contract interactions)

Block N — The Attack

  Attacker → FlashLoanPool.flashLoan(400,000 tokenA)
    ↓ Pool transfers 400k tokenA to attacker
    ↓ Pool calls attacker.onFlashLoan() [CALLBACK STARTS]
      
      [Inside callback, depth=2]
      Attacker → VulnerableLending.depositCollateral(200k tokenA)
      Attacker → FlashLoanPool.getSpotPrice()   ← ORACLE READ AT DEPTH 2
      Attacker → VulnerableLending.borrow(X tokenB)
      
      [Pool manipulation via swap]
      Attacker → FlashLoanPool.swap(200k tokenA → tokenB)
        ← reserves shift: tokenA↑, tokenB↓ → price drops for tokenA
    
    ↓ Pool checks balance: received 400k back? YES.
    [CALLBACK ENDS]

DERIVED EVENTS BUILT:
  value_flow_intra_tx:
    inflow: 400k tokenA (flash loan)
    outflow: 400k tokenA (repayment)
    large_inflow: true, large_outflow: true, same_tx_repay: true

  price_reads:
    call_depth: 2
    function_called: "getSpotPrice()"
    called_during_callback: true

SIGNALS FIRED:
  flashloan_bracket_detected    (large in + out same tx)
  price_read_during_callback    (oracle at depth > 0)
  spot_price_manipulation       (reserves shifted >10%)
  drain_ratio_exceeded          (lending pool lost funds relative to inflow)

EQL PATTERN AP-006:
  sequence by tx_hash
    [flashloan_bracket_detected] ✓
    [price_read_during_callback] ✓
    [spot_price_manipulation]    ✓
    [drain_ratio_exceeded]       ✓
  → AP-006 ALERT FIRES at 90% confidence
```

---

## 13. Signal Library

### Complete list of all 61 signals with trigger conditions

```
FAMILY: VALUE (7 signals)
  large_value_inflow_spike         ETH/token inflow > 10× address 30-day avg
  drain_ratio_exceeded             outflow > 1.5× inflow same tx
  net_negative_contract_balance    contract ETH balance drops to zero
  value_concentration              >50% of tokens moved to single address
  value_dispersion                 funds split to >10 new addresses
  multiple_asset_drain_same_tx     3+ different tokens drained in one tx
  vault_share_price_spike          share price increases >20% intra-block

FAMILY: FLASH LOAN (3 signals)
  flashloan_bracket_detected       large in+out same tx, ERC3156 pattern
  price_read_during_callback       oracle call at trace depth > 0
  hook_callback_detected           unexpected callback to caller during tx

FAMILY: ACCESS CONTROL (5 signals)
  ownership_transfer_then_drain    owner change followed by drain within 10 blocks
  approval_for_max_amount          approve(type(uint256).max) to unverified addr
  cross_function_reentry           re-entry via different function selector
  delegatecall_storage_write       delegatecall modifies caller storage
  initialize_on_live_contract      initialize() called on deployed contract

FAMILY: DEPLOYMENT (3 signals)
  contract_deployed_before_attack  contract deployed <10 blocks before exploit
  same_block_deploy_and_attack     deploy + exploit in identical block
  create2_redeployment             same CREATE2 salt used to re-deploy

FAMILY: LIQUIDITY (2 signals)
  liquidity_removal_spike          >80% of pool liquidity removed in one tx
  donation_balance_inflation       direct ETH/token send to vault (ERC4626 attack)

FAMILY: TOKEN (4 signals)
  mint_to_dump_ratio               token minted then sold >80% within 5 blocks
  rapid_token_dump                 >50% of holder's balance sold within 1 block
  token_balance_drain              token balance drops to 0 from >1000 tokens
  fee_on_transfer_discrepancy      received amount ≠ sent amount (hidden fee)

FAMILY: GOVERNANCE (3 signals)
  governance_instant_execution     proposal executed without timelock delay
  integer_overflow_detected        arithmetic producing unexpected large output
  permit_used_before_owner_approval permit signature used before EIP-2612 approval

FAMILY: DEFI (6 signals)
  spot_price_manipulation          spot price changes >10% within single tx
  twap_drift_detected              TWAP deviates >5% from recent window
  reserve_ratio_spike              pool reserves shift >30% in one block
  multi_oracle_divergence          two oracle sources disagree >5%
  price_before_after_mismatch      price at tx start ≠ price at tx end
  liquidation_cascade_trigger      mass liquidations triggered by price move

FAMILY: STRUCTURAL (10 signals)
  recursive_depth_pattern          max call depth >= 3 with recursion
  storage_update_delay             storage write after external call
  value_drain_per_depth            ETH extracted at each recursive depth
  cross_contract_state_dependency  state read from contract A used in contract B
  event_order_violation            events emitted out of expected sequence
  duplicate_event_emission         same event emitted twice per tx
  missing_expected_event           function called but expected event absent
  event_parameter_mismatch         event args don't match function args
  proxy_implementation_change      implementation slot updated
  selfdestruct_detected            SELFDESTRUCT opcode executed

FAMILY: BEHAVIOURAL (7 signals)
  address_funded_before_attack     attacker funded <24h before exploit
  new_address_first_interaction    first-ever tx from this address
  failed_attempts_before_success   3+ failed txs before success
  nonce_gap_detected               nonce jump > 1 (suggests cancelled txs)
  high_gas_anomaly                 gas_used > 2× block average
  address_funded_before_attack     fresh wallet pattern
  contract_size_zero_after_selfdestruct contract code = 0 bytes post tx

FAMILY: BRIDGE (2 signals)
  bridge_interaction_detected      known bridge contract interaction
  multi_hop_fund_trail             funds through 3+ intermediary addresses

FAMILY: GRAPH (4 signals)
  address_cluster_identified       wallet grouped with known attacker cluster
  contract_creator_linked          deployer address linked to known exploit
  fund_dispersion_post_attack      funds scatter to >5 fresh addresses post-exploit
  mixer_interaction_detected       interaction with Tornado Cash or equivalent

FAMILY: EVASION (3 signals)
  create2_redeployment             same CREATE2 address reused
  contract_size_anomaly            bytecode size < 10 or exactly target size
  reentrancy_guard_bypass          ReentrancyGuard event absent despite deep call
```

---

## 14. Pattern Library

### All 20 attack patterns with signal sequences

| Pattern | Name | Confidence | Key Signals |
|---------|------|-----------|-------------|
| AP-001 | classic_reentrancy | 95% | recursive_depth + storage_delay + value_drain |
| AP-002 | cross_function_reentrancy | 90% | cross_function_reentry + storage_delay |
| AP-003 | read_only_reentrancy | 85% | hook_callback + price_read_during_callback |
| AP-004 | cross_contract_reentrancy | 88% | recursive_depth + cross_contract_state |
| AP-005 | reentrancy_with_flashloan | 92% | flashloan_bracket + recursive_depth + drain |
| AP-006 | flash_loan_oracle_manipulation | 90% | flashloan_bracket + price_read + spot_manip + drain |
| AP-007 | flash_loan_governance_attack | 85% | flashloan_bracket + governance_instant |
| AP-008 | admin_key_compromise | 88% | ownership_transfer + approval_max + drain |
| AP-009 | price_oracle_manipulation | 87% | spot_price_manip + borrow_spike + drain |
| AP-010 | token_mint_and_dump | 85% | ownership_transfer + mint_to_dump |
| AP-011 | governance_instant_execution | 83% | governance_instant + drain |
| AP-012 | liquidity_pool_drain | 88% | liquidity_removal + drain_ratio |
| AP-013 | donation_attack | 80% | donation_balance_inflation + vault_share_spike |
| AP-014 | mev_sandwich | 85% | high_gas_anomaly + swap_sequence + profit |
| AP-015 | bridge_fund_relay | 78% | bridge_interaction + multi_hop_trail |
| AP-016 | mixer_fund_obfuscation | 82% | mixer_interaction + fund_dispersion |
| AP-017 | create2_redeploy_attack | 87% | create2_redeploy + selfdestruct |
| AP-018 | permit_frontrun | 80% | permit_before_approval + rapid_dump |
| AP-019 | integer_overflow_chain | 83% | integer_overflow + drain |
| AP-020 | liquidation_cascade | 86% | price_manip + liquidation_cascade_trigger |

---

## 15. Deployment Configurations

```
CONFIGURATION A — Local Simulation (Development)
┌────────────────────────────────────────────────────────┐
│  Anvil          → http://127.0.0.1:8545, chain_id 31337│
│  Elasticsearch  → http://localhost:9200               │
│  Kibana         → http://localhost:5601               │
│  Ollama         → http://localhost:11434              │
│  Full traces    → YES (debug_traceTransaction)        │
│  Archive node   → NOT NEEDED                          │
│  Cost           → FREE                                │
└────────────────────────────────────────────────────────┘

CONFIGURATION B — Sepolia Testnet
┌────────────────────────────────────────────────────────┐
│  RPC URL        → Alchemy/Infura Sepolia endpoint     │
│  chain_id       → 11155111                            │
│  Traces         → Only on Alchemy Archive tier        │
│  Cost           → ~$50/month Alchemy Growth plan      │
└────────────────────────────────────────────────────────┘

CONFIGURATION C — Ethereum Mainnet (Production)
┌────────────────────────────────────────────────────────┐
│  RPC URL        → Alchemy/Infura Mainnet endpoint     │
│  chain_id       → 1                                   │
│  Traces         → Alchemy Archive node REQUIRED       │
│                   (debug_traceTransaction = archive)  │
│  Cost           → ~$200-500/month depending on volume │
│  Data volume    → ~2000-5000 txs per block            │
└────────────────────────────────────────────────────────┘

ONE-LINE CONFIG SWITCH:
  # config.json — only 2 fields change between all 3 modes:
  { "rpc_url": "http://127.0.0.1:8545", "chain_id": 31337 }
  { "rpc_url": "https://eth-sepolia.g.alchemy.com/v2/KEY", "chain_id": 11155111 }
  { "rpc_url": "https://eth-mainnet.g.alchemy.com/v2/KEY", "chain_id": 1 }
```

---

## 16. Design Principles

### Why Python is Only Plumbing

Python moves data from the chain to Elasticsearch. It does not contain detection logic. This matters because:

1. **Accessibility** — Any SISA analyst who knows Elasticsearch (not Python) can read, write, and modify signals
2. **Auditability** — ES|QL query files are simple text. They can be reviewed, versioned, and understood independently
3. **Speed** — Elasticsearch pushes computation to where the data lives. Signal queries run in parallel across all documents
4. **Modifiability** — Adding a signal means dropping one .esql file. Modifying a threshold means editing one line

### Why EQL for Patterns (Not Python Logic)

Python `if signal_A and signal_B and signal_C` would work but:
- Ordering would require complex timestamp comparisons
- Cross-tx correlation would require in-memory state
- No tooling for debugging or explaining matches

EQL `sequence by tx_hash [A] [B] [C]` is:
- Executed entirely in Elasticsearch
- Self-documenting (pattern file = exact match criteria)
- Extensible without touching Python code

### Why Two ES Indices

`forensics-raw` = evidence integrity. Never modified. Can be used as ground truth in legal or compliance contexts.

`forensics` = analysis outputs. Can be re-derived from raw if an algorithm changes. Separation means running a new signal version doesn't corrupt the underlying evidence.

### Why Strict Dynamic Mapping

Both indices use `"dynamic": "strict"`. This means any unknown field causes an ingest error. This is intentional: it forces all fields to be explicitly mapped, prevents accidental data type confusion (a string field silently ingested where a number was expected), and keeps the schema controlled and auditable.

---

*ChainSentinel — SISA Information Security Pvt. Ltd.*  
*This document is technical reference material. Not for external distribution.*
