# 5. Family: value (9 signals)

Value signals measure **token and ETH movement** — drain ratios,
concentration, share-price spikes. They sit at the heart of every
exploit detection.

| Stem | File | Inputs |
|------|------|--------|
| `drain_ratio_exceeded` | `detection/signals/value/drain_ratio_exceeded.esql` | `derived/value_flow_intra_tx`, `derived/multi_token_balance_snapshot` |
| `large_value_inflow_spike` | `detection/signals/value/large_value_inflow_spike.esql` | `derived/eth_transfers`, `derived/token_transfer_graph` |
| `liquidity_removal_spike` | `detection/signals/value/liquidity_removal_spike.esql` | `decoded` Burn / RemoveLiquidity events |
| `mint_to_dump_ratio` | `detection/signals/value/mint_to_dump_ratio.esql` | `decoded` Mint + Transfer events |
| `multiple_asset_drain_same_tx` | `detection/signals/value/multiple_asset_drain_same_tx.esql` | `derived/value_flow_intra_tx` |
| `net_negative_contract_balance` | `detection/signals/value/net_negative_contract_balance.esql` | `derived/balance_spike_registry` |
| `value_concentration` | `detection/signals/value/value_concentration.esql` | `derived/value_flow_graph` |
| `value_dispersion` | `detection/signals/value/value_dispersion.esql` | `derived/value_flow_graph` |
| `vault_share_price_spike` | `detection/signals/value/vault_share_price_spike.esql` | `derived/share_price_history` |

## 5.1 Per-signal notes (selected)

### `drain_ratio_exceeded`
- **Score weight:** `min(1.0, drained / pre_balance × 1.2)`
- **Detection:** Within one transaction, the victim contract's balance
  for any monitored asset drops by more than 30 % of its pre-tx balance.
- **FP notes:** Legitimate vault withdrawals; pair with
  `flashloan_bracket_detected` or `value_concentration` to confirm.

### `multiple_asset_drain_same_tx`
- **Score weight:** `0.9`
- **Detection:** ≥ 2 distinct ERC-20 token contracts show a net negative
  delta for the same victim in the same tx.
- **FP notes:** Multi-asset zap-out transactions match.

### `vault_share_price_spike`
- **Score weight:** Scales with magnitude; ≥ 0.7 at +5%.
- **Detection:** ERC-4626 `pricePerShare()` drifts by more than 5 % from
  the trailing average.
- **FP notes:** Legitimate yield accrual is gradual; sudden steps almost
  always indicate share inflation (`AP-024`) or donation (`AP-023`).

### `liquidity_removal_spike`
- **Score weight:** `0.7`
- **Detection:** > 50 % of total LP supply burned in one transaction by a
  single address.
- **FP notes:** Treasury withdrawals; pair with `mint_to_dump_ratio` for
  `AP-019` (liquidity rug).

### `value_concentration`
- **Score weight:** Scales with Gini coefficient of the value-flow graph.
- **Detection:** Post-exploit, ≥ 70 % of flowed value lands in fewer than
  three addresses.
- **FP notes:** CEX deposits look concentrated; combine with
  `cex_deposit` label from the label DB.

### `value_dispersion`
- **Score weight:** Scales with branching factor.
- **Detection:** Funds split into ≥ 8 outflows from a single attacker EOA
  within 50 blocks.
- **FP notes:** Airdrop distribution and payroll match.

### `large_value_inflow_spike`
- **Score weight:** `0.6`
- **Detection:** Single inbound transfer > 90th percentile of the
  victim's monthly inflow.
- **FP notes:** Treasury deposits.

### `net_negative_contract_balance`
- **Score weight:** `0.7`
- **Detection:** Sum of value-out minus value-in for the victim is
  negative across the investigation window.
- **FP notes:** Yield contracts intentionally net-out; filter on the
  victim address being a vault by checking the manifest.

### `mint_to_dump_ratio`
- **Score weight:** `0.8`
- **Detection:** Within `K` blocks of a token mint, more than 50 % of
  the minted supply is sold into the primary pool.
- **FP notes:** Initial liquidity events for new tokens match by design.
