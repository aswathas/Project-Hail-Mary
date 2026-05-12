# 5. `config.json` reference

The complete, authoritative configuration. Every key, its default, its
effect, and any cross-cutting consequences.

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

## 5.1 Connectivity

| Key | Default | Effect |
|-----|---------|--------|
| `rpc_url` | `http://127.0.0.1:8545` | Where `collector.py` fetches blockchain data. The FastAPI server validates this is reachable before opening an SSE stream — failure produces HTTP 503. |
| `es_url`  | `http://localhost:9200` | Elasticsearch endpoint. Used by the pipeline, the detection engines, and the copilot's context builder. |
| `ollama_url` | `http://localhost:11434` | Ollama server. The copilot streams completions from `<ollama_url>/api/generate`. |

All three are URL-overridable per `POST /analyze` request (see **D5 §3.1**).

## 5.2 LLM

| Key | Default | Effect |
|-----|---------|--------|
| `ollama_model` | `gemma3:1b` | Model name passed to Ollama. `start.sh` `ollama pull`s this on first run. |
| `ollama_temperature` | `0.2` | Lower = more deterministic. Pinned low so different runs of the same investigation produce similar reports. |

## 5.3 Chain identity

| Key | Default | Effect |
|-----|---------|--------|
| `chain_id` | `31337` | Anvil's default chain ID. Becomes part of every ES `_id` for raw documents; **change this when switching chains.** |
| `mode` | `simulation` | Drives `start.sh`'s behaviour — `simulation` boots Anvil, `testnet` / `mainnet` skip it. Pipeline behaviour is unaffected. |

Three example configurations differing only in `rpc_url` + `chain_id`:

```json
// Simulation
{ "rpc_url": "http://127.0.0.1:8545", "chain_id": 31337, "mode": "simulation" }
// Sepolia
{ "rpc_url": "https://eth-sepolia.g.alchemy.com/v2/<key>", "chain_id": 11155111, "mode": "testnet" }
// Mainnet
{ "rpc_url": "https://eth-mainnet.g.alchemy.com/v2/<key>", "chain_id": 1, "mode": "mainnet" }
```

## 5.4 Pipeline limits

| Key | Default | Effect |
|-----|---------|--------|
| `max_trace_hops` | `5` | BFS hop limit for `correlation/fund_trace.py`. Higher values produce richer graphs but slow down post-pipeline correlation linearly. |
| `tx_history_limit` | `200` | Cap on backfill tx count in range / wallet modes. Protects the operator from a runaway investigation. |
| `signal_score_threshold` | `0.5` | Below this, a signal still ingests but is not counted in roll-up stats and the UI badges. |
| `es_bulk_chunk_size` | `500` | Number of docs per ES bulk request. Increase to 1000+ on a fat box; decrease to 100 on a small ES. |

## 5.5 Per-request overrides

`POST /analyze` accepts `rpc_url`, `es_url`, `ollama_url` overrides
in the request body, letting an analyst run a one-off investigation
against a different endpoint without touching `config.json`. The
override applies only to that request.
