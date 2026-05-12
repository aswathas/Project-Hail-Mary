# 6. Family: oracle (7 signals)

Oracle signals identify **price-feed manipulation**, which is the leading
class of DeFi exploit by total value lost.

| Stem | File | Inputs |
|------|------|--------|
| `donation_balance_inflation` | `detection/signals/oracle/donation_balance_inflation.esql` | `derived/donation_tracker`, `decoded` Transfer events |
| `multi_oracle_divergence` | `detection/signals/oracle/multi_oracle_divergence.esql` | `derived/price_reads` |
| `price_before_after_mismatch` | `detection/signals/oracle/price_before_after_mismatch.esql` | `derived/price_reads`, `derived/value_flow_intra_tx` |
| `price_read_during_callback` | `detection/signals/oracle/price_read_during_callback.esql` | `derived/price_reads`, `derived/execution_structure` |
| `reserve_ratio_spike` | `detection/signals/oracle/reserve_ratio_spike.esql` | `derived/multi_token_balance_snapshot` |
| `spot_price_manipulation` | `detection/signals/oracle/spot_price_manipulation.esql` | `derived/price_reads` |
| `twap_drift_detected` | `detection/signals/oracle/twap_drift_detected.esql` | `derived/price_reads` |

## 6.1 Per-signal notes

### `spot_price_manipulation`
- **Score weight:** Scales with deviation; ≥ 0.8 at 10 % drift.
- **Detection:** Spot price reads on the same AMM pool diverge by more
  than 5 % within a single transaction.
- **FP notes:** Legitimate arbitrage transactions move price; filter by
  combining with `flashloan_bracket_detected` for `AP-009`.

### `twap_drift_detected`
- **Score weight:** Scales with drift magnitude.
- **Detection:** Reported TWAP drifts > N standard deviations from its
  trailing baseline.
- **FP notes:** Low-liquidity pools have noisy TWAPs; this is the entry
  condition for `AP-010` (TWAP manipulation).

### `multi_oracle_divergence`
- **Score weight:** `0.85`
- **Detection:** Two distinct oracle reads (e.g. Chainlink and the
  protocol's local spot) for the same asset diverge by > 3 % in the same
  block.
- **FP notes:** Stale Chainlink rounds occasionally diverge; combine
  with `price_before_after_mismatch` for `AP-011`.

### `donation_balance_inflation`
- **Score weight:** `0.9`
- **Detection:** Direct ETH/token transfer (not via `deposit()`) to a
  vault that subsequently mints abnormally few shares relative to the
  inflated balance — classic vault-inflation pattern.
- **FP notes:** Legitimate fee donations to a treasury vault.

### `price_read_during_callback`
- **Score weight:** `0.85`
- **Detection:** A price read occurs inside a hook callback (ERC777,
  ERC1155, flash-loan callback). Strong indicator of pre-state oracle
  read used in oracle manipulation.
- **FP notes:** None in practice — well-built oracles cache values before
  external calls.

### `reserve_ratio_spike`
- **Score weight:** `0.7`
- **Detection:** AMM reserve ratio changes by > 20 % in a single trace.
- **FP notes:** Large legitimate swaps; pair with
  `flashloan_bracket_detected` for `AP-009`.

### `price_before_after_mismatch`
- **Score weight:** `0.8`
- **Detection:** Two reads of the same price oracle in the same trace
  return values that differ by > N %, and the trace executed a swap or
  liquidation in between.
- **FP notes:** Multi-leg routes legitimately observe price changes;
  pair with value-drain signals.
