# 3. Module reference

This section documents every Python module under `chainsentinel/`. Each
subsection: **path**, **purpose**, **public API**, **invariants**, and
**common changes**.

## 3.1 `server.py` — FastAPI + SSE

**Path:** `chainsentinel/server.py`

**Purpose.** Thin HTTP wrapper around the pipeline. Four endpoints; no
business logic. Loads `config.json` on import.

### 3.1.1 Endpoint contracts

The auto-generated table is in **D4 §14.1**. Full schemas:

#### POST `/analyze`

Request (`AnalyzeRequest`):

```json
{
  "mode": "tx" | "range" | "wallet" | "watch",
  "target": "<tx hash>" | { "from_block": 12, "to_block": 100 } | "<wallet address>",
  "rpc_url": null | "https://...",
  "es_url": null | "http://...",
  "ollama_url": null | "http://..."
}
```

Response: `text/event-stream` (SSE).

SSE event shape:

```json
{
  "event": "pipeline",
  "data": "{\"phase\":\"...\",\"msg\":\"...\",\"severity\":\"ok|warn|crit|gray\",\"esIndex\":\"...\",\"ts\":\"HH:MM:SS\"}"
}
```

Final event (`phase: complete`) carries:

```json
{
  "phase": "complete",
  "investigationId": "inv_2026-05-12_<uuid>",
  "stats": { "decoded": N, "derived": N, "signals": N, "indexed": N }
}
```

Error event: `phase: error`, `severity: crit`, `msg: <message>`.

HTTP status codes:

| Code | Cause |
|------|-------|
| `200` | Stream opened (events may still contain errors) |
| `422` | Pydantic validation failed |
| `503` | RPC unreachable before stream opens |

#### GET `/health`

Returns `{ "rpc": "ok|error", "elasticsearch": "ok|error", "ollama": "ok|error" }`.
Independent checks — one failure does not short-circuit the others.

#### GET `/analysis/{investigation_id}`

Returns the `layer: case` document for a completed investigation, or `404`.

#### POST `/simulate`

Currently a placeholder returning `{ "status": "not_implemented", ... }`.
Reserved for future Foundry-via-server integration.

### 3.1.2 Invariants

- The `_resolve(request_val, config_key)` helper makes request-level
  overrides win over config defaults. Always use it for any new
  endpoint that accepts URL overrides.
- ES index setup (`setup_elasticsearch`) is called inside `/analyze` —
  it is idempotent and non-fatal on failure.
- The SSE generator must `await es_client.close()` in a `finally` block.

### 3.1.3 Common changes

- **Adding a new endpoint**: define a Pydantic model for input, add a
  decorated handler, and update `scripts/generate_catalog_tables.py`
  output by re-running `make catalogs`.
- **Adding a new SSE phase**: pick a string for `phase`, emit it from
  the runner, and add a CSS rule in the frontend if you need new styling.
