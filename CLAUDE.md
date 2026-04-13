ChainSentinel — CLAUDE.md

---

DESIGN SPEC AND IMPLEMENTATION PLANS

The authoritative design and implementation plans live at:
- Spec: docs/superpowers/specs/2026-04-12-chainsentinel-design.md
- Plan 1 (Foundation): docs/superpowers/plans/2026-04-12-plan1-foundation.md [COMPLETE]
- Plan 2 (Detection): docs/superpowers/plans/2026-04-12-plan2-detection.md [COMPLETE]
- Plan 3 (Correlation): docs/superpowers/plans/2026-04-12-plan3-correlation.md [COMPLETE]
- Plan 4 (Frontend): docs/superpowers/plans/2026-04-12-plan4-frontend.md [COMPLETE]
- Plan 5 (Simulations): docs/superpowers/plans/2026-04-12-plan5-simulations.md [COMPLETE]
- Plan 6 (Copilot): docs/superpowers/plans/2026-04-12-plan6-copilot.md [COMPLETE]

When building, follow the plans exactly. They contain file structure, task-by-task steps with code, tests, and commit instructions. Use superpowers:subagent-driven-development or superpowers:executing-plans to implement them.

---

PROJECT OVERVIEW

ChainSentinel is a standalone EVM blockchain forensics tool. Given a transaction hash, wallet address, or block range, it runs a full forensic pipeline — collecting raw chain data, decoding it, deriving security events, running signal detection via ES queries, tracing funds, and surfacing findings in a React investigation workspace with an Ollama-powered copilot.

Real-world workflow: A client comes to SISA saying "we got exploited." They provide their RPC endpoint, contract ABIs, deployed addresses, and approximate time window. The analyst loads this into ChainSentinel and runs analysis. The tool detects the exploit purely from on-chain data + client ABIs.

For development/testing: Foundry simulations on Anvil simulate real client engagements — victim protocol + normal activity + attack. ChainSentinel analyzes using only the client handover (ABIs + manifest), never the attacker source code.

---

CORE PRINCIPLES

- Python is plumbing. Moves data from chain to ES. Does not contain detection logic.
- ES is the brain. Signal detection and pattern matching run as ES|QL and EQL queries. Anyone at SISA who knows ES can read, modify, and contribute detection rules.
- Evidence integrity. Raw chain data is never mixed with pipeline interpretations. Separate index.
- Modular growth. Adding a signal = drop a .esql file. Adding a pattern = drop a .eql file. Adding a derived type = add a function. Adding a simulation = add a folder.
- Graceful degradation. Full traces when available (Anvil, archive nodes). Tool still works with just receipts + logs when connecting to basic RPC.
- Client-driven intake. The tool doesn't assume what contracts exist. The client provides ABIs + addresses via a manifest.

---

TECHNOLOGY STACK

Simulation: Foundry + Anvil
Pipeline: Python 3.11+
Backend: FastAPI 0.110+
Streaming: Server-Sent Events (SSE)
Storage + Detection: Elasticsearch 8.x
Dashboards: Kibana 8.x
Local LLM: Ollama + Gemma 3 1B
Frontend: React 18 + Vite
Frontend styling: Plain CSS with CSS variables (Wise design system)
Graph visualization: D3.js force-directed
Config: config.json (single source of truth)

---

CONFIG.JSON

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

Three configurations differ only by rpc_url and chain_id:
- Simulation: rpc_url http://127.0.0.1:8545, chain_id 31337
- Sepolia: Alchemy/Infura Sepolia endpoint, chain_id 11155111
- Mainnet: Alchemy/Infura mainnet endpoint, chain_id 1

---

REPOSITORY STRUCTURE

```
Project_Hail_Mary/
├── CLAUDE.md
├── docs/superpowers/specs/          ← design spec
├── docs/superpowers/plans/          ← 6 implementation plans
│
├── chainsentinel/                   ← the forensic tool
│   ├── config.json
│   ├── server.py
│   ├── start.sh
│   ├── requirements.txt
│   │
│   ├── pipeline/
│   │   ├── runner.py                ← orchestrates pipeline, yields SSE events
│   │   ├── collector.py             ← RPC data fetching
│   │   ├── normalizer.py            ← hex→int, addresses lowercase, timestamps
│   │   ├── decoder.py               ← ABI decoding with registry
│   │   ├── derived.py               ← security event builder (9 derived types)
│   │   ├── ingest.py                ← ES bulk ingest with idempotent _id
│   │   ├── selector_registry.json   ← living selector→name cache
│   │   └── abi_registry/
│   │       ├── standards/           ← ERC20, ERC721, ERC1155
│   │       ├── protocols/           ← Uniswap, Aave, Compound, Curve
│   │       └── cases/               ← per-investigation client ABIs
│   │
│   ├── detection/
│   │   ├── signal_engine.py         ← loads + runs .esql files against ES
│   │   ├── pattern_engine.py        ← loads + runs .eql files against ES
│   │   ├── signals/                 ← 61 .esql query files in 12 family folders
│   │   └── patterns/                ← 20 .eql attack pattern files
│   │
│   ├── correlation/
│   │   ├── fund_trace.py            ← BFS fund tracing, 5 hops, haircut taint
│   │   ├── clustering.py            ← wallet clustering
│   │   ├── mixer_detect.py          ← Tornado Cash, bridges, CEX matching
│   │   └── label_db.py              ← OFAC, known exploiters, CEX wallets
│   │
│   ├── es/
│   │   ├── setup.py                 ← creates indices + mappings
│   │   └── mappings/
│   │       ├── forensics-raw.json   ← strict mapping for raw evidence
│   │       └── forensics.json       ← strict mapping for analysis data
│   │
│   ├── ollama/
│   │   ├── copilot.py               ← chat with investigation context
│   │   ├── report_template.py       ← builds structured JSON context from ES
│   │   └── report_sections.py       ← 7-section report generation
│   │
│   └── frontend/
│       ├── package.json
│       ├── vite.config.js
│       └── src/
│           ├── App.jsx / App.css    ← Wise design system CSS variables + layout
│           ├── components/          ← Sidebar, PipelineFeed, InvestigationView,
│           │                           EntityGraph, CopilotPanel, StoredAnalyses
│           ├── hooks/               ← useAnalysis, useElasticsearch, useOllama,
│           │                           useLocalStorage
│           └── api/                 ← pipeline.js, elasticsearch.js, ollama.js
│
└── simulations/                     ← separate from chainsentinel
    ├── foundry.toml
    ├── shared/contracts/            ← MockERC20, MockWETH, UserActivity
    └── scenarios/                   ← 4 attack scenarios
        ├── reentrancy-drain/
        ├── flash-loan-oracle/
        ├── admin-key-abuse/
        └── mev-sandwich/
```

---

ELASTICSEARCH ARCHITECTURE

2 Indices with strict mappings:

forensics-raw — Untouched chain evidence. Never modified after ingest.
- doc_type: transaction (per tx_hash), log (per tx_hash+log_index), trace (per tx_hash)

forensics — Everything the pipeline and detection engine produce.
- layer: decoded, derived, signal, alert, attacker, case

Shared fields on every document: investigation_id, chain_id, @timestamp, block_number, block_datetime, tx_hash.

Key mapping rules:
- All addresses: keyword (exact match, lowercased)
- event_args, function_args, metadata, raw_extra: flattened (prevents mapping explosion)
- value_eth: double. value_wei: keyword (exceeds long range)
- score: float. severity: keyword. decode_status: keyword
- dynamic: strict on both indices

Document ID strategy (idempotent):
- forensics-raw transaction: {chain_id}_{tx_hash}
- forensics-raw log: {chain_id}_{tx_hash}_{log_index}
- forensics-raw trace: {chain_id}_{tx_hash}_trace
- forensics decoded: {investigation_id}_{tx_hash}_{log_index}_decoded
- forensics derived: {investigation_id}_{derived_type}_{tx_hash}_{log_index}
- forensics signal: {investigation_id}_{signal_name}_{tx_hash}
- forensics alert: {investigation_id}_{pattern_id}
- forensics attacker: {investigation_id}_{cluster_id}
- forensics case: {investigation_id}

---

PIPELINE DATA FLOW

```
RPC Endpoint (Anvil / testnet / mainnet)
    ↓
Collector → raw blocks, txs+receipts, logs, traces
    ↓ → ES: forensics-raw (doc_type: transaction, log, trace)
Normalizer → hex to int, addresses lowercase, timestamps ISO 8601
    ↓
Decoder → ABI decode using registry (case ABIs → standards → protocols → selector cache)
    ↓ → ES: forensics (layer: decoded)
Derived Event Builder → security events (9 derived types)
    ↓ → ES: forensics (layer: derived)
ES Signal Engine → runs all .esql files against forensics index
    ↓ → ES: forensics (layer: signal)
ES Pattern Engine → runs all .eql files combining signals
    ↓ → ES: forensics (layer: alert)
Python Correlation → fund tracing BFS + wallet clustering
    └─→ ES: forensics (layer: attacker, case)
```

---

DETECTION ENGINE — ES QUERIES

Signal Engine (signal_engine.py): Loads all .esql files from detection/signals/. Runs each as ES|QL query against forensics index filtered by investigation_id. Stores results as layer: signal documents.

61 Signals across 12 families:
- Value (7), Flash Loan (3), Access (5), Deployment (3), Liquidity (2), Token (4), Governance (3), DeFi (6), Structural (10), Behavioural (7), Bridge (2), Graph (4), Evasion (3)

Pattern Engine (pattern_engine.py): Loads all .eql files from detection/patterns/. Runs EQL sequence queries against signal + derived documents. Stores results as layer: alert documents.

20 Attack Patterns: AP-001 through AP-020. Each has required signals and confidence threshold.

Wave delivery:
- Wave 1: ~20 signals + 4 patterns (testable with 4 Foundry simulations)
- Wave 2: Remaining signals + patterns as data sources expand
- Adding new: Drop file in correct folder. Engine auto-discovers.

---

CORRELATION ENGINE

Fund Tracing (fund_trace.py): BFS from seed wallet. 5 hops forward + backward. Haircut taint scoring: mixer = *0.7, bridge = *0.8. Output: fund_flow_edge documents.

Wallet Clustering (clustering.py): Groups wallets by shared funding, timing, deployment patterns. Each cluster gets a cluster_id.

Known Addresses (mixer_detect.py + label_db.py): Tornado Cash, bridges, CEX hot wallets, OFAC SDN, known exploiters. Labels: ofac_sanctioned, known_exploiter, cex_deposit, mixer_contract, bridge_contract, protocol_treasury, unknown.

---

FRONTEND — WISE DESIGN SYSTEM

Three-column layout: Sidebar (252px) | Workspace (center) | CopilotPanel (280px)

Workspace state machine: Running (SSE log) → Complete (investigation view, auto-transition)

Wise colors: Near Black #0e0f0c, Wise Green #9fe870, Dark Green #163300, Light Mint #e2f6d5, Danger Red #d03238, Warning Yellow #ffd11a, Gray #868685.

Typography: Inter weight 600 body, weight 900 headings, monospace for addresses/hashes/amounts.

Components: Pill buttons (border-radius: 9999px), Cards (border-radius: 30px), ring shadows.

---

FOUNDRY SIMULATIONS — 4 SCENARIOS

Each has 3 phases: deploy victim → generate normal activity → execute attack. Each outputs a client/ folder (ABIs + manifest.json).

- reentrancy-drain: VulnerableVault → recursive withdraw → tests AP-005
- flash-loan-oracle: LendingPool + Oracle + Pool → flash loan oracle manipulation → tests AP-001
- admin-key-abuse: GovernanceToken → ownership transfer + mint + dump → tests AP-008, AP-010
- mev-sandwich: SimpleDEX → frontrun + victim swap + backrun → tests AP-014

---

ANALYSIS MODES

TX ANALYSIS — single tx hash, deepest detail with full trace
RANGE ANALYSIS — from_block to to_block, batch processing
WALLET HUNT — address + 5-hop BFS fund tracing + attacker profiling
WATCH MODE — continuous new block polling, runs until stopped

---

FASTAPI SERVER — server.py

POST /analyze — accepts mode, rpc_url, target, investigation_id, manifest path. Streams SSE events.
GET /analysis/{id} — fetches investigation from ES
GET /health — checks RPC, ES, Ollama connectivity
POST /simulate — runs forge script against Anvil, returns block range + tx hashes

---

OLLAMA REPORT GENERATION

7-section forensic report from structured JSON context:
1. Executive Summary
2. Attack Timeline
3. Technical Mechanism
4. Attacker Attribution
5. Fund Trail
6. Signal Evidence
7. Remediation Actions

Copilot never invents addresses, amounts, tx hashes, or block numbers. Only summarizes and explains what analysis found.

---

BUILD STATUS

PLAN 1 — FOUNDATION [COMPLETE]:
- pipeline/collector.py, normalizer.py, decoder.py, derived.py, ingest.py, runner.py
- server.py (FastAPI with SSE), es/setup.py, es/mappings/
- abi_registry/standards/erc20.json, selector_registry.json
- 130 Python tests + 28 frontend tests, all passing

PLAN 2 — DETECTION ENGINE [COMPLETE]
- signal_engine.py, pattern_engine.py, 20 .esql signals, 4 .eql patterns

PLAN 3 — CORRELATION ENGINE [COMPLETE]
- fund_trace.py, clustering.py, mixer_detect.py, label_db.py

PLAN 4 — FRONTEND [COMPLETE]
- React 18 + Vite, 6 components, 4 hooks, 3 API modules, Wise design system

PLAN 5 — SIMULATIONS [COMPLETE]
- Foundry project, 4 scenarios (reentrancy, flash-loan, admin-key, mev-sandwich)

PLAN 6 — COPILOT [COMPLETE]
- copilot.py, report_template.py, report_sections.py

INTEGRATION [COMPLETE]
- server.py: pipeline → ingest → signals → patterns → complete
- start.sh: one-command startup

---

RULES FOR CLAUDE

Follow the implementation plans exactly. They are the source of truth for what to build and how.

Python is plumbing — detection logic lives in .esql and .eql files, not Python code.

decode_status is mandatory on every decoded record. Values: decoded, partial, unknown. Never omit.

All ES index mappings live as JSON in es/mappings/. Never define mappings inline.

selector_registry.json is a living document that grows at runtime.

Every derived event includes source_tx_hash, source_log_index, source_layer.

ES bulk ingest uses deterministic _id for idempotency.

The tool must be fully demonstrable offline using Anvil + simulation scenarios.

start.sh must bring up the entire stack with one command.

Switching between Anvil, testnet, and mainnet is one URL change. No node-specific conditional logic.

Ollama receives structured JSON context, never raw ES documents. Copilot never invents data.

Fund trace BFS uses haircut taint scoring: mixer *0.7, bridge *0.8.
