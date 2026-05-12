# 9. Family: additional (12 signals)

The catch-all family. Each of these targets a specific exploit
mechanic that does not fit cleanly into the six core families.

| Stem | File | Inputs |
|------|------|--------|
| `contract_size_zero_after_selfdestruct` | `detection/signals/additional/contract_size_zero_after_selfdestruct.esql` | raw traces |
| `cross_contract_state_dependency` | `detection/signals/additional/cross_contract_state_dependency.esql` | `derived/storage_mutations`, `derived/internal_calls` |
| `eip712_replay_detected` | `detection/signals/additional/eip712_replay_detected.esql` | `derived/permit_usage_log` |
| `fee_on_transfer_discrepancy` | `detection/signals/additional/fee_on_transfer_discrepancy.esql` | `decoded` Transfer events, balance deltas |
| `governance_instant_execution` | `detection/signals/additional/governance_instant_execution.esql` | `decoded` Propose / Execute events |
| `integer_overflow_detected` | `detection/signals/additional/integer_overflow_detected.esql` | `derived/storage_mutations`, value deltas |
| `liquidation_cascade_trigger` | `detection/signals/additional/liquidation_cascade_trigger.esql` | `derived/liquidation_events` |
| `permit_used_before_owner_approval` | `detection/signals/additional/permit_used_before_owner_approval.esql` | `derived/permit_usage_log`, `derived/approval_registry` |
| `rapid_token_dump` | `detection/signals/additional/rapid_token_dump.esql` | `derived/token_transfer_graph` |
| `rebasing_balance_manipulation` | `detection/signals/additional/rebasing_balance_manipulation.esql` | balance snapshots |
| `reentrancy_guard_bypass` | `detection/signals/additional/reentrancy_guard_bypass.esql` | `derived/reentrancy_patterns`, `decoded` |
| `token_balance_drain` | `detection/signals/additional/token_balance_drain.esql` | `derived/multi_token_balance_snapshot` |

## 9.1 Per-signal notes (selected)

### `governance_instant_execution`
- **Score weight:** `0.85`
- **Detection:** `Propose` and `Execute` events on the same proposal in
  consecutive blocks — bypasses any minimum voting period.
- **FP notes:** Emergency timelock-skip paths intentionally do this.

### `eip712_replay_detected`
- **Score weight:** `0.9`
- **Detection:** Same EIP-712 typed-data signature used in two distinct
  transactions.
- **FP notes:** None expected — replay protection is fundamental.

### `integer_overflow_detected`
- **Score weight:** `0.95`
- **Detection:** A `uint256` storage write where the new value is
  numerically less than the old + delta would suggest (modular wrap).
- **FP notes:** Negligible since Solidity 0.8.

### `fee_on_transfer_discrepancy`
- **Score weight:** `0.5`
- **Detection:** Transfer event amount ≠ recipient balance delta.
- **FP notes:** Fee-on-transfer tokens (`AP-027`) match by design.

### `reentrancy_guard_bypass`
- **Score weight:** `1.0`
- **Detection:** Reentrant call succeeds despite a guard mutex being set
  (e.g. via delegatecall or proxy upgrade).
- **FP notes:** None.

### `cross_contract_state_dependency`
- **Score weight:** `0.6`
- **Detection:** Contract A reads state from B that B itself modifies
  inside the same tx — classic read-only reentrancy condition.
- **FP notes:** Composable DeFi protocols.

### `liquidation_cascade_trigger`
- **Score weight:** `0.7`
- **Detection:** ≥ 3 liquidations within 5 blocks affecting the same
  asset pair.
- **FP notes:** Sharp price drops can liquidate many positions
  legitimately.

### `permit_used_before_owner_approval`
- **Score weight:** `0.85`
- **Detection:** A `permit()` call's nonce was consumed by an attacker
  before the legitimate owner observed it on-chain.
- **FP notes:** None — front-running mempool permits.

### `token_balance_drain`
- **Score weight:** `0.8`
- **Detection:** A contract's token balance drops to (or below) the
  reentrancy-guard-zero floor.
- **FP notes:** Intentional sweep functions.

### `rebasing_balance_manipulation`
- **Score weight:** `0.55`
- **Detection:** Rebase index changed mid-tx, mid-loop.
- **FP notes:** Legitimate rebases happen daily.

### `rapid_token_dump`
- **Score weight:** `0.7`
- **Detection:** Single address moves > 30 % of a token's supply through
  swaps within `< K` blocks.
- **FP notes:** Treasury rebalancing.

### `contract_size_zero_after_selfdestruct`
- **Score weight:** `0.9`
- **Detection:** Code length at an address transitioned to 0 after a
  `SELFDESTRUCT`, then the trace shows further calls to it (succeed in
  EVM ≤ Shanghai but return 0).
- **FP notes:** Disposable proxies.
