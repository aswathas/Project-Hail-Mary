# ChainSentinel

**EVM Blockchain Forensics Tool** — Investigate on-chain exploits end-to-end.

Given a transaction hash, wallet address, or block range, ChainSentinel runs a full forensic pipeline: collects raw chain data, decodes it, derives security events, runs 20 heuristic signal detections via ES|QL, matches 4 composite attack patterns via EQL, traces funds across 5 hops, clusters attacker wallets, and surfaces findings in a React investigation workspace with an Ollama-powered copilot that generates 7-section forensic reports.

Built for SISA. Runs fully offline — no cloud dependencies.

---

## Quick Start

### Prerequisites

| Tool | Install |
|------|---------|
| Docker | [docker.com](https://docs.docker.com/get-docker/) |
| Python 3.11+ | `sudo apt install python3.11 python3.11-venv` |
| Node 18+ | `curl -fsSL https://deb.nodesource.com/setup_18.x \| sudo -E bash - && sudo apt install -y nodejs` |
| Foundry (Anvil) | `curl -L https://foundry.paradigm.xyz \| bash && foundryup` |
| Ollama | `curl -fsSL https://ollama.com/install.sh \| sh` |

### One-Command Startup

```bash
cd chainsentinel
chmod +x start.sh
./start.sh
```

Open **http://localhost:5173** in your browser.

### Manual Startup (5 terminals)

**Terminal 1 — Elasticsearch:**
```bash
docker run -d --name chainsentinel-es -p 9200:9200 \
  -e "discovery.type=single-node" \
  -e "xpack.security.enabled=false" \
  -e "ES_JAVA_OPTS=-Xms512m -Xmx512m" \
  elasticsearch:8.12.0
```

**Terminal 2 — Ollama:**
```bash
ollama serve
# In another tab or after serve starts:
ollama pull gemma3:1b
```

**Terminal 3 — Anvil (local EVM node):**
```bash
anvil --chain-id 31337
```

**Terminal 4 — Backend (FastAPI):**
```bash
cd chainsentinel
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn server:app --host 0.0.0.0 --port 8000 --reload
```

**Terminal 5 — Frontend (React):**
```bash
cd chainsentinel/frontend
npm install
npm run dev
```

Open **http://localhost:5173**

---

## Running a Demo

### Step 1: Deploy a simulation

With Anvil running, deploy one of the 4 attack scenarios:

```bash
cd simulations

# Reentrancy drain (tests AP-005)
forge script scenarios/reentrancy-drain/script/RunAll.s.sol \
  --rpc-url http://127.0.0.1:8545 --broadcast

# Flash loan oracle manipulation (tests AP-001)
forge script scenarios/flash-loan-oracle/script/RunAll.s.sol \
  --rpc-url http://127.0.0.1:8545 --broadcast

# Admin key abuse (tests AP-008)
forge script scenarios/admin-key-abuse/script/RunAll.s.sol \
  --rpc-url http://127.0.0.1:8545 --broadcast

# MEV sandwich (tests AP-014)
forge script scenarios/mev-sandwich/script/RunAll.s.sol \
  --rpc-url http://127.0.0.1:8545 --broadcast
```

Each script prints transaction hashes — copy one of the attack tx hashes.

### Step 2: Analyze in the UI

1. Open http://localhost:5173
2. Verify all 3 connection dots are green (RPC, Elasticsearch, Ollama)
3. Select **Tx Analysis** mode
4. Paste the attack transaction hash
5. Click **Run Analysis**
6. Watch the pipeline stream:
   - Collector fetches raw tx data
   - Normalizer standardizes types
   - Decoder matches ABI signatures
   - Derived builder produces security events
   - Signal engine fires ES|QL heuristics
   - Pattern engine matches attack sequences
7. Auto-transitions to **Investigation View** showing:
   - Attack timeline with severity-colored events
   - Fired signals with scores
   - Entity graph (attackers in red, protocols in blue)
   - Meta bar with attacker address, victim contract, funds drained

### Step 3: Use the Copilot

After analysis completes, use the right panel:
- Click **"What signals fired"** for signal explanations
- Click **"Generate Report"** for a 7-section forensic report
- Ask free-form questions about the investigation

### Step 4: Try Range Analysis

```bash
# After running simulations, scan all blocks:
# In the UI: select Range mode, from_block: 0, to_block: 20
# Click Run Analysis
```

---

## Architecture

```
RPC (Anvil/Testnet/Mainnet)
  |
  v
Collector --> raw txs, receipts, logs, traces
  |
  v --> ES: forensics-raw
Normalizer --> hex->int, addresses lowercase, timestamps ISO 8601
  |
  v
Decoder --> ABI decode (case ABIs -> standards -> protocols -> selector cache)
  |
  v --> ES: forensics (layer: decoded)
Derived Event Builder --> 9 security event types
  |
  v --> ES: forensics (layer: derived)
Signal Engine --> runs 20 .esql queries
  |
  v --> ES: forensics (layer: signal)
Pattern Engine --> runs 4 .eql sequence queries
  |
  v --> ES: forensics (layer: alert)
Correlation --> fund tracing + wallet clustering
  |
  v --> ES: forensics (layer: attacker)
```

### Key Design Principles

- **Python is plumbing** — moves data from chain to ES
- **ES is the brain** — signal detection and pattern matching are ES|QL and EQL queries
- **Adding a signal** = drop a `.esql` file in `detection/signals/`
- **Adding a pattern** = drop a `.eql` file in `detection/patterns/`
- **Evidence integrity** — raw chain data never modified, separate index
- **Idempotent** — rerunning analysis creates no duplicates

---

## Project Structure

```
Project_Hail_Mary/
├── chainsentinel/                  # The forensic tool
│   ├── config.json                 # Single source of truth
│   ├── server.py                   # FastAPI + SSE streaming
│   ├── start.sh                    # One-command startup
│   ├── requirements.txt
│   │
│   ├── pipeline/                   # Data pipeline (Plan 1)
│   │   ├── collector.py            # RPC data fetching
│   │   ├── normalizer.py           # Type normalization
│   │   ├── decoder.py              # ABI decoding
│   │   ├── derived.py              # Security event builder
│   │   ├── ingest.py               # ES bulk ingest
│   │   ├── runner.py               # Pipeline orchestrator
│   │   └── abi_registry/           # ERC20, protocols, case ABIs
│   │
│   ├── detection/                  # Detection engine (Plan 2)
│   │   ├── signal_engine.py        # Runs .esql files
│   │   ├── pattern_engine.py       # Runs .eql files
│   │   ├── signals/                # 20 ES|QL signal queries
│   │   └── patterns/               # 4 EQL attack patterns
│   │
│   ├── correlation/                # Correlation engine (Plan 3)
│   │   ├── fund_trace.py           # BFS 5-hop fund tracing
│   │   ├── clustering.py           # Wallet clustering
│   │   ├── mixer_detect.py         # Tornado Cash/bridge/CEX
│   │   └── label_db.py             # OFAC/known exploiter labels
│   │
│   ├── ollama/                     # LLM integration (Plan 6)
│   │   ├── copilot.py              # Context-aware chat
│   │   ├── report_template.py      # Builds JSON context
│   │   └── report_sections.py      # 7-section report
│   │
│   ├── es/                         # Elasticsearch
│   │   ├── setup.py                # Index creation
│   │   └── mappings/               # Strict JSON mappings
│   │
│   ├── frontend/                   # React UI (Plan 4)
│   │   └── src/
│   │       ├── components/         # 6 components
│   │       ├── hooks/              # 4 custom hooks
│   │       └── api/                # 3 API modules
│   │
│   └── tests/                      # 130 Python tests
│
└── simulations/                    # Foundry simulations (Plan 5)
    ├── shared/contracts/            # MockERC20, MockWETH
    └── scenarios/                   # 4 attack scenarios
        ├── reentrancy-drain/
        ├── flash-loan-oracle/
        ├── admin-key-abuse/
        └── mev-sandwich/
```

---

## Running Tests

```bash
# Python tests (130 tests)
cd chainsentinel
source .venv/bin/activate
python -m pytest tests/ -v

# Frontend tests (28 tests)
cd chainsentinel/frontend
npx vitest run

# Solidity compilation
cd simulations
forge build
```

---

## Analysis Modes

| Mode | Input | Use Case |
|------|-------|----------|
| **Tx Analysis** | Transaction hash | Deep-dive a single suspicious tx |
| **Range Analysis** | From/to block numbers | Scan a known exploit window |
| **Wallet Hunt** | Wallet address | Trace an attacker's fund flow |
| **Watch Mode** | None (continuous) | Real-time monitoring |

---

## Detection Coverage

### 20 Signals (Wave 1)

| Family | Signals |
|--------|---------|
| Value | large_outflow, large_token_transfer, max_approval, value_spike |
| Flash Loan | flash_loan_detected, flash_loan_with_drain |
| Access | ownership_transferred, role_granted, proxy_upgraded |
| Structural | reentrancy_pattern, call_depth_anomaly, repeated_external_call, internal_eth_drain |
| Deployment | new_contract_deployed, failed_high_gas |
| Liquidity | large_liquidity_removal |
| DeFi | vault_first_deposit_tiny, liquidation_event |
| Behavioural | new_wallet_high_value, burst_transactions |

### 4 Attack Patterns

| ID | Pattern | Confidence |
|----|---------|------------|
| AP-001 | Flash Loan Oracle Manipulation | 0.90 |
| AP-005 | Reentrancy Drain | 0.90 |
| AP-008 | Access Control Abuse | 0.85 |
| AP-014 | MEV Sandwich | 0.80 |

---

## Configuration

Edit `chainsentinel/config.json`:

```json
{
  "rpc_url": "http://127.0.0.1:8545",
  "es_url": "http://localhost:9200",
  "ollama_url": "http://localhost:11434",
  "ollama_model": "gemma3:1b",
  "chain_id": 31337,
  "mode": "simulation"
}
```

Switch to mainnet: change `rpc_url` to your Alchemy/Infura endpoint and `chain_id` to `1`. No code changes needed.

---

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Pipeline | Python 3.11+, web3.py |
| Backend | FastAPI, SSE |
| Detection | Elasticsearch 8.x (ES|QL + EQL) |
| Frontend | React 18, Vite, D3.js |
| Styling | Plain CSS (Wise design system) |
| LLM | Ollama + Gemma 3 1B |
| Simulations | Foundry, Solidity 0.8.24+ |

---

## Setting Up on a New Machine

```bash
# 1. Clone the repo
git clone https://github.com/aswathas/Project-Hail-Mary.git
cd Project-Hail-Mary

# 2. Install Python dependencies
cd chainsentinel
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 3. Install frontend dependencies
cd frontend
npm install
cd ..

# 4. Install Foundry (for simulations)
curl -L https://foundry.paradigm.xyz | bash
foundryup
cd ../simulations
forge install
cd ..

# 5. Pull Ollama model
ollama pull gemma3:1b

# 6. Start everything
cd chainsentinel
./start.sh
```

---

Built by Aswath for SISA.
