# 4. Family: behavioural (9 signals)

Behavioural signals look at **what an actor did across transactions** —
funding lineage, deployment timing, failed-attempt patterns. They are
weaker individually but powerful when chained.

| Stem | File | Inputs |
|------|------|--------|
| `address_funded_before_attack` | `detection/signals/behavioural/address_funded_before_attack.esql` | `derived/address_first_contact`, `derived/eth_transfers` |
| `approval_for_max_amount` | `detection/signals/behavioural/approval_for_max_amount.esql` | `derived/approval_registry` |
| `contract_deployed_before_attack` | `detection/signals/behavioural/contract_deployed_before_attack.esql` | `derived/contract_deployments` |
| `contract_size_anomaly` | `detection/signals/behavioural/contract_size_anomaly.esql` | `derived/contract_deployments` |
| `failed_attempts_before_success` | `detection/signals/behavioural/failed_attempts_before_success.esql` | `derived/failed_attempt_history` |
| `high_gas_anomaly` | `detection/signals/behavioural/high_gas_anomaly.esql` | `derived/gas_analysis` |
| `new_address_first_interaction` | `detection/signals/behavioural/new_address_first_interaction.esql` | `derived/address_first_contact` |
| `nonce_gap_detected` | `detection/signals/behavioural/nonce_gap_detected.esql` | `derived/nonce_tracking` |
| `same_block_deploy_and_attack` | `detection/signals/behavioural/same_block_deploy_and_attack.esql` | `derived/deployment_to_attack` |

## 4.1 Per-signal notes (selected)

### `same_block_deploy_and_attack`
- **Score weight:** `0.9`
- **Detection:** Attacker EOA deploys a contract and executes the
  exploit transaction within the *same block*.
- **FP notes:** Rare in legitimate use; bot operators occasionally do
  this for MEV. Combine with `drain_ratio_exceeded` to confirm.

### `address_funded_before_attack`
- **Score weight:** `0.7`
- **Detection:** The attacker EOA received its first inbound ETH /
  stablecoin within the last `N` blocks (default `7200` ≈ one day),
  exclusively from a mixer or bridge.
- **FP notes:** New users do this all the time; the *mixer/bridge only*
  predicate is what tightens the signal.

### `failed_attempts_before_success`
- **Score weight:** `0.6`
- **Detection:** The attacker tried the same call signature ≥ 2 times
  with `status: 0` before the successful exploit.
- **FP notes:** Bots probing arbitrage can match; filter on the target
  contract being the victim from the manifest.

### `approval_for_max_amount`
- **Score weight:** `0.4` (alone), `0.8` (in `AP-021`)
- **Detection:** An `Approval(spender, value=MAX_UINT)` event toward a
  contract that subsequently drains the approver.
- **FP notes:** Common in DEX aggregators; signal is only useful as a
  prerequisite for `AP-021 infinite_approval_drain`.

### `new_address_first_interaction`
- **Score weight:** `0.3`
- **Detection:** Caller's first ever interaction with the victim
  contract; nonce-derived.
- **FP notes:** True of every legitimate user too. Used as a *condition*
  in patterns, not a standalone alert.

### `contract_size_anomaly`
- **Score weight:** `0.5`
- **Detection:** Deployed bytecode is < 200 bytes (minimal proxy) or
  > 24 kB (near EIP-170 limit).
- **FP notes:** Minimal proxies are extremely common in production; this
  is purely a context signal.

### `high_gas_anomaly`
- **Score weight:** `0.3`
- **Detection:** Tx gas used > 90th percentile for the victim contract
  in the recent window.
- **FP notes:** Bridges and multi-hop swaps routinely use lots of gas.

### `nonce_gap_detected`
- **Score weight:** `0.4`
- **Detection:** Nonce monotonicity broken; e.g. a deployment from an
  address whose previous nonce-N transaction had `status: 0`.
- **FP notes:** Routine RPC desync.

### `contract_deployed_before_attack`
- **Score weight:** `0.6`
- **Detection:** Attacker EOA's deployment occurred within `M` blocks
  prior to the exploit (default `M = 100`).
- **FP notes:** Bot infrastructure does this constantly; signal acts as a
  predicate.
