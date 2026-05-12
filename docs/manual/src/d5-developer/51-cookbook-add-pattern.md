# 6. Cookbook: add a new attack pattern

Pattern engines run EQL sequences over `layer: signal` and
`layer: derived` documents.

## 6.1 Pick an AP number

Next free number after `AP-038` is `AP-039`.

## 6.2 Write the `.eql`

Suppose we want to alert when a `native_value_spike` is immediately
followed by a `fund_dispersion_post_attack`.

Create `chainsentinel/detection/patterns/AP-039_drain_then_disperse.eql`:

```eql
sequence by investigation_id with maxspan=30m
  [ signal where signal_name == "native_value_spike" and score >= 0.5 ]
  [ signal where signal_name == "fund_dispersion_post_attack" ]
```

## 6.3 Confidence and severity

The pattern engine computes confidence from the contributing signals (see
**D4 §1.3**). To override the default severity, return a `severity` field
from the EQL query:

```eql
sequence by investigation_id with maxspan=30m
  [ signal where signal_name == "native_value_spike" and score >= 0.5 ]
  [ signal where signal_name == "fund_dispersion_post_attack" ]
| eval severity = "CRIT"
```

## 6.4 Test

Existing tests under `chainsentinel/tests/test_pattern_engine.py` show
the pattern-engine fixture pattern. Add an analogous case for AP-039.

## 6.5 Document it

Add a row to
`docs/manual/src/d4-detection-reference/40-patterns-catalog.md` under the
appropriate family table (or §10.9 for cross-cutting). The
auto-generated table refreshes on `make catalogs`.
