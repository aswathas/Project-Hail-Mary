# 5. Cookbook: add a new signal

Suppose you want a signal that fires when a contract receives an
unusually large native ETH transfer (over 1000 ETH in one tx).

## 5.1 Pick a family

Look at the seven families (**D4 §2**) and pick the closest fit. For our
example, **value** is the right home.

## 5.2 Write the `.esql`

Create `chainsentinel/detection/signals/value/native_value_spike.esql`:

```esql
FROM forensics
| WHERE investigation_id == "{investigation_id}"
    AND chain_id == {chain_id}
    AND layer == "derived"
    AND derived_type == "eth_transfers"
    AND `metadata.value_eth` >= 1000.0
| EVAL signal_name = "native_value_spike"
| EVAL score = LEAST(1.0, `metadata.value_eth` / 5000.0)
| EVAL severity = CASE(
      score >= 0.8, "CRIT",
      score >= 0.5, "WARN",
      "INFO"
    )
| KEEP investigation_id, chain_id, tx_hash, block_number,
       block_datetime, signal_name, score, severity,
       metadata.value_eth
```

Notes:

- The `{investigation_id}` and `{chain_id}` placeholders are replaced
  by `signal_engine.py` before execution.
- The query must return a `score` column.
- File stem becomes `signal_name`.

## 5.3 Run

The signal engine discovers the file on next pipeline run — no
registration required.

```bash
./chainsentinel/start.sh
# kick off a new investigation; check Sidebar for the new signal badge
```

Or, run only the signal engine against an existing investigation:

```python
from elasticsearch import Elasticsearch
from chainsentinel.detection.signal_engine import run_all_signals

es = Elasticsearch(hosts=["http://localhost:9200"])
docs = run_all_signals(es, lambda *a: None,
                       investigation_id="inv_2026-05-12_abc123",
                       chain_id=31337)
print(f"{len(docs)} signal docs produced")
```

## 5.4 Write a test

In `chainsentinel/tests/test_native_value_spike.py`:

```python
def test_native_value_spike_fires(es_with_fixture, investigation_id):
    docs = run_all_signals(es_with_fixture, lambda *a: None,
                           investigation_id=investigation_id,
                           chain_id=31337)
    fired = [d for d in docs if d["signal_name"] == "native_value_spike"]
    assert len(fired) >= 1
    assert all(d["score"] > 0 for d in fired)
```

`es_with_fixture` would be a pytest fixture loading a known
investigation snapshot — see existing tests under `chainsentinel/tests/`.

## 5.5 Document it

Add a row to `docs/manual/src/d4-detection-reference/32-signals-value.md`
under §5 (value family) with the **stem**, **file**, **inputs**,
**score weight**, and **false-positive notes**. Run `make catalogs` to
refresh the auto-generated tables; the new row will appear in
`signals_by_family.md` automatically.
