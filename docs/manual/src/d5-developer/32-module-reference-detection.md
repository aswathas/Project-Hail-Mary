# 3.8–3.9 Detection engines

## 3.8 `detection/signal_engine.py`

**Purpose.** Discover and execute every `.esql` signal against ES.

**Public function:**

- `run_all_signals(es, ingest_fn, *, investigation_id, chain_id) -> list[dict]`
  - **`es`**: synchronous `elasticsearch.Elasticsearch` client.
  - **`ingest_fn`**: callable `(es, docs, index)` — the engine calls it
    after running each batch. Pass a no-op if `server.py` is going to
    bulk-index the returned list itself.
  - **Returns**: list of signal documents.

**Algorithm.**

```
discover detection/signals/**/*.esql
for each file:
    text = file.read_text()
    sub  = text.format(investigation_id=…, chain_id=…)
    rows = es.esql.query(query=sub)
    for row in rows:
        doc = {
            "investigation_id": investigation_id,
            "chain_id": chain_id,
            "layer": "signal",
            "signal_name": file.stem,
            "score": row.get("score", 0.0),
            "severity": severity_from_score(row["score"]),
            ... rest of row ...
        }
        out.append(doc)
return out
```

**Invariants.**

- `signal_name` is the file stem.
- The `.esql` must return a `score` column or a literal.
- The engine is **side-effect-free** apart from passing docs to
  `ingest_fn`.

## 3.9 `detection/pattern_engine.py`

**Purpose.** Discover and execute every `.eql` attack pattern.

**Public function:**

- `run_all_patterns(es, ingest_fn, *, investigation_id, chain_id) -> list[dict]`

Identical signature to `run_all_signals`. Uses ES's
`POST /_eql/search` against the `forensics` index, filtered by
`investigation_id` and `layer ∈ {signal, derived}`.

**Returned doc shape:**

```json
{
  "investigation_id": "...",
  "chain_id": 31337,
  "layer": "alert",
  "pattern_id": "AP-006",
  "pattern_name": "flash_loan_oracle",
  "confidence": 0.92,
  "severity": "CRIT",
  "required_signals": [
    "flashloan_bracket_detected",
    "spot_price_manipulation",
    "drain_ratio_exceeded"
  ],
  "matched_signals": [ ... full signal docs in match order ... ]
}
```

**Adding a pattern.** Drop a `.eql` file named `AP-NNN_short_slug.eql`
under `detection/patterns/`. The engine discovers it on next run. See
**D5 §5–6** for the cookbook.
