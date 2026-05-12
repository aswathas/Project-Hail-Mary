# 8. Security and performance

## 8.1 Network surface

By default, every service binds to `localhost`:

| Service | Port | Bind | Notes |
|---------|------|------|-------|
| FastAPI | 8000 | 0.0.0.0 (dev) | CORS allows `http://localhost:5173` only |
| Vite | 5173 | 127.0.0.1 | Frontend dev server |
| Anvil | 8545 | 127.0.0.1 | Local sim only |
| Elasticsearch | 9200 | 127.0.0.1 | No auth in dev — see §8.3 |
| Ollama | 11434 | 127.0.0.1 | Local LLM |

For production deployment, bind ES + Ollama to a private VLAN, terminate
TLS at the FastAPI server, and set CORS to the analyst origin only.

## 8.2 Input handling

- The `AnalyzeRequest` model uses Pydantic validation. `mode` is checked
  against the allowed set; mismatched payload shapes (e.g. `tx` mode
  given a dict target) produce SSE error events, not crashes.
- ABIs in the manifest are loaded but never executed. Malformed JSON is
  caught in the decoder and downgrades affected logs to
  `decode_status: unknown`.
- The copilot does not accept free-form SQL or ES queries from the chat
  input — only natural language. All ES access is mediated by
  `report_template.py`.

## 8.3 What is *not* secured

- Elasticsearch ships without authentication in the default
  `docker-compose.yml` (single-node, ES_SETTING `xpack.security.enabled=false`).
  This is acceptable for an analyst's local machine; it is **not** acceptable
  for a shared cluster.
- The FastAPI server has no auth. Anyone with HTTP access to port 8000 can
  start an investigation. Run behind an authenticated reverse proxy if
  exposed beyond localhost.
- The `kibana_setup.py` script writes Kibana saved objects without auth
  — same caveat.

## 8.4 Performance characteristics

Observed on a 16-core, 32 GB-RAM developer machine:

| Workload | Time | Bottleneck |
|----------|------|------------|
| `start.sh` cold start | 60–90 s | Ollama model pull (one-time) |
| ES boot | 15–25 s | Heap allocation, mapping creation |
| Single tx forensic run (small contract, ~30 logs) | 4–8 s | RPC trace fetch dominates |
| `demo-500` scenario (500 txs) | 60–120 s | Bulk ingest + signal queries |
| 60 ES&#124;QL signals against ~5k derived docs | 1–3 s | ES per-query latency |
| 38 EQL patterns over 200 signals | 0.5–1.5 s | ES `sequence` evaluation |
| Fund trace 5 hops, ~50-edge graph | < 1 s | Pure Python BFS |
| Copilot section generation (gemma3:1b) | 2–4 s per section | LLM token rate |

Tuning knobs:

- `es_bulk_chunk_size` (default 500) — increase to 1000+ on a fat box;
  decrease on low-RAM hosts.
- `max_trace_hops` (default 5) — drop to 3 for very dispersed graphs.
- `tx_history_limit` (default 200) — caps backfill in range/wallet mode.
- Ollama model — swap to `llama3:8b` for higher-quality reports at
  ~5× the latency.
