# 1. Scoring model

## 1.1 Signal score

A signal score is a function in `[0,1]` defined by the signal's `.esql`
query. The query returns a `score` column either as a literal weight or
as a computed expression. Weighting conventions:

| Signal class | Typical weight | Reasoning |
|--------------|----------------|-----------|
| Structural ground-truth (`selfdestruct_detected`, `delegatecall_storage_write`) | `1.0` | The behaviour is unambiguous in the trace. |
| Strong heuristic (`flashloan_bracket_detected`, `drain_ratio_exceeded`) | `0.7..0.9` | Almost always indicative; rare benign false positives. |
| Soft heuristic (`high_gas_anomaly`, `new_address_first_interaction`) | `0.3..0.6` | Context-dependent — useful when combined. |
| Statistical signal (`twap_drift_detected`, `vault_share_price_spike`) | `0.5..0.8` × magnitude factor | Scales with the size of the deviation. |

The per-signal score in the `.esql` file is the authoritative value;
this table lists conventions, not rules.

## 1.2 Severity buckets

The signal engine compares the score to thresholds:

| Severity | Score | UI styling |
|----------|-------|------------|
| `INFO`   | `0.0 ≤ s < 0.5` | Grey badge, no toast |
| `WARN`   | `0.5 ≤ s < 0.8` | Yellow badge, no toast |
| `CRIT`   | `0.8 ≤ s ≤ 1.0` | Red badge, toast on fire |

`signal_score_threshold` in `config.json` (default `0.5`) gates whether a
signal is *counted* in roll-up stats; below threshold it is still
ingested for analyst review.

## 1.3 Pattern confidence

A pattern's confidence is a weighted geometric mean of its required
signal scores, multiplied by a sequence-quality factor:

```
confidence(P) = ( ∏ score(s_i)^w_i )^(1/Σw_i) × seq_quality(P)
```

`seq_quality(P)` is `1.0` if all signals appeared in the order expected
by the `.eql` sequence, and `0.8` if they appeared out of order but
within the `maxspan` window. Patterns inherit the highest severity of
their contributing signals.

## 1.4 Severity in the UI

The frontend `PipelineFeed` and `Sidebar` derive colour from the
`severity` field:

| `severity` value | Colour token |
|------------------|--------------|
| `ok`             | `--wise-green` |
| `gray`           | `--gray` |
| `warn`           | `--warning-yellow` |
| `crit`           | `--danger-red` |

This is the colour pipeline used end-to-end: from `.esql` row →
ingest → SSE event → React badge.
