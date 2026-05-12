# 3.2–3.7 Pipeline modules

## 3.2 `pipeline/collector.py`

**Purpose.** Fetch raw blockchain data from RPC.

**Public functions:**

- `async fetch_transaction(w3, tx_hash) -> dict` — returns the
  transaction + receipt + (optionally) traces.
- `async fetch_block_range(w3, from_block, to_block) -> AsyncIterable[dict]`
  — yields per-tx payloads.
- `async fetch_traces(w3, tx_hash) -> list[dict]` — `debug_traceTransaction`
  if available, empty list otherwise.

**Invariants.**

- Returns raw RPC payloads with no transformation. Hex stays hex.
- Tolerates RPC providers without `debug_traceTransaction` — the
  pipeline degrades from full trace to logs-only.
- Never raises on malformed responses; it returns sentinel values
  the normalizer recognises.

## 3.3 `pipeline/ingest.py`

**Purpose.** Bulk-index documents to ES with deterministic `_id`s.

**Public functions:**

- `async index_raw(es, docs, investigation_id)` — to `forensics-raw`.
- `async index_derived(es, docs)` — to `forensics`. Each doc must
  include `layer` and the deterministic-`_id` fields.
- `async bulk_index(es, docs, index)` — generic bulk wrapper used by
  the signal/pattern engines.

**Invariants.**

- ID formula: see **D3 §3.4**. If you change a derived event's shape,
  ensure the `_id` still uniquely identifies it.
- Chunks at `es_bulk_chunk_size`; bulk failures retry once.

## 3.4 `pipeline/decoder.py`

**Purpose.** ABI-based decoding of logs and function calldata.

**Public functions:**

- `decode_log(log: dict, registry: ABIRegistry) -> dict` — returns a
  decoded record with `event_name`, `event_args`, `decode_status`.
- `decode_function_call(tx: dict, registry: ABIRegistry) -> dict` —
  returns `function_name`, `function_args`, `decode_status`.
- `class ABIRegistry` — case → standards → protocols → selector cache
  resolution.

**Invariants.**

- `decode_status` is **mandatory** on every decoded record. Values:
  `decoded` | `partial` | `unknown`.
- Unknown selectors get written to `selector_registry.json` (the cache)
  with `null` name until a future enrichment.

## 3.5 `pipeline/normalizer.py`

**Purpose.** Lossless transformation to canonical types.

**Conventions:**

- Hex strings → integers (where the field is numeric).
- Addresses → lowercase `0x…`.
- Timestamps → ISO 8601 UTC.
- `value_wei`: `keyword` (string), `value_eth`: `double`.
- Any field the normalizer does not understand is preserved in
  `raw_extra` (a `flattened` ES field).

## 3.6 `pipeline/runner.py`

**Purpose.** Pipeline orchestration; yields SSE events.

**Public functions:**

- `async run_tx_analysis(w3, tx_hash, investigation_id, config) -> AsyncIterator[dict]`
- `async run_range_analysis(w3, from_block, to_block, investigation_id, config) -> AsyncIterator[dict]`
- `generate_investigation_id() -> str` — returns `inv_<ISO date>_<8-char uuid>`.

**Event schema:** see **D5 §3.1.1**.

**Invariants.** Yields `phase: complete` exactly once, last. The complete
event carries the bulk `raw_docs`, `decoded_docs`, `derived_docs` payloads
that `server.py` extracts and bulk-indexes.

## 3.7 `pipeline/derived/_base.py` — builder contract

```python
class Builder:
    derived_type: str          # written to forensics.derived_type
    requires: list[str]        # decoded/derived layers it consumes

    def emit(self, ctx: PipelineContext) -> Iterable[dict]:
        ...
```

`PipelineContext` carries: the investigation ID, the normalized tx
payload, the decoded events, and references to other already-built
derived layers (builders run in `requires`-order).

**Output document shape:**

```json
{
  "investigation_id": "...",
  "chain_id":         31337,
  "@timestamp":       "...",
  "block_number":     12345,
  "block_datetime":   "...",
  "tx_hash":          "0x...",
  "layer":            "derived",
  "derived_type":     "<this builder's type>",
  "source_tx_hash":   "0x...",
  "source_log_index": 7,
  "source_layer":     "decoded" | "derived",
  "metadata":         { ... arbitrary flattened ... }
}
```

The 36 builders shipped in the box are catalogued in **D4 §11**.
