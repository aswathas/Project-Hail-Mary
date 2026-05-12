# 2. Local development setup

## 2.1 Prerequisites

| Component | Version | Install |
|-----------|---------|---------|
| Python    | 3.11+   | `pyenv install 3.11.8` |
| Node.js   | 20+     | `nvm install 20` |
| Docker    | 24+     | Docker Desktop / Engine |
| Foundry   | nightly | `curl -L https://foundry.paradigm.xyz \| bash; foundryup` |
| Ollama    | 0.1.30+ | https://ollama.com |
| pandoc    | 3.1+    | for documentation builds (optional) |
| mmdc      | latest  | `npm i -g @mermaid-js/mermaid-cli` (optional) |

## 2.2 Python environment

```bash
cd chainsentinel
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

`requirements.txt` is currently:

```
web3>=6.15.0
elasticsearch>=8.12.0
fastapi>=0.110.0
uvicorn>=0.27.0
sse-starlette>=1.8.0
httpx>=0.27.0
pytest>=8.0.0
```

## 2.3 Frontend

```bash
cd chainsentinel/frontend
npm install
npm run dev    # Vite on :5173
```

## 2.4 One-shot stack

From the project root:

```bash
./chainsentinel/start.sh
```

Which performs:

1. `docker compose up -d elasticsearch kibana` (if not already up)
2. Starts Ollama and pulls `gemma3:1b`
3. In `simulation` mode, starts Anvil on `:8545`
4. Starts FastAPI on `:8000` with hot reload
5. Starts Vite on `:5173`

Stop with `Ctrl-C`; `start.sh` traps the signal and stops every child.

## 2.5 Running tests

```bash
cd chainsentinel
pytest                       # all tests
pytest tests/test_decoder.py # one file
pytest -k "reentrancy"       # by keyword
```

The frontend's vitest suite:

```bash
cd chainsentinel/frontend
npm test
```

## 2.6 Configuration

`chainsentinel/config.json` is the single source of truth:

| Key | Default | Effect |
|-----|---------|--------|
| `rpc_url` | `http://127.0.0.1:8545` | Where the collector fetches from |
| `es_url` | `http://localhost:9200` | Elasticsearch endpoint |
| `ollama_url` | `http://localhost:11434` | Ollama server |
| `ollama_model` | `gemma3:1b` | LLM model name |
| `ollama_temperature` | `0.2` | Generation temperature |
| `chain_id` | `31337` | EVM chain ID for `_id` strings |
| `mode` | `simulation` | `simulation` \| `testnet` \| `mainnet` |
| `max_trace_hops` | `5` | BFS depth limit |
| `tx_history_limit` | `200` | Backfill window |
| `signal_score_threshold` | `0.5` | Severity cut-off |
| `es_bulk_chunk_size` | `500` | Ingest batch size |
