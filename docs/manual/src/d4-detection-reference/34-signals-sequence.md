# 7. Family: sequence (6 signals)

Sequence signals look at **event ordering and presence** in
transactions. They detect protocol-level inconsistencies (missing
expected events, repeats, ownership-then-drain patterns).

| Stem | File | Inputs |
|------|------|--------|
| `deposit_withdraw_same_tx` | `detection/signals/sequence/deposit_withdraw_same_tx.esql` | `decoded` Deposit / Withdraw events |
| `duplicate_event_emission` | `detection/signals/sequence/duplicate_event_emission.esql` | `decoded` (any) |
| `event_order_violation` | `detection/signals/sequence/event_order_violation.esql` | `decoded` |
| `event_parameter_mismatch` | `detection/signals/sequence/event_parameter_mismatch.esql` | `decoded` |
| `missing_expected_event` | `detection/signals/sequence/missing_expected_event.esql` | `decoded` |
| `ownership_transfer_then_drain` | `detection/signals/sequence/ownership_transfer_then_drain.esql` | `decoded` OwnershipTransferred, value flows |

## 7.1 Per-signal notes

### `deposit_withdraw_same_tx`
- **Score weight:** `0.7`
- **Detection:** A `Deposit(user, amount)` and a `Withdraw(user,
  amount')` event from the same vault, same user, same transaction,
  where `amount' > amount × 1.1`.
- **FP notes:** Legitimate router contracts may do round-trips; filter
  on user balance delta being positive.

### `ownership_transfer_then_drain`
- **Score weight:** `0.95`
- **Detection:** `OwnershipTransferred(prev, new)` followed within `N`
  blocks by `new` calling privileged functions that drain the contract.
- **FP notes:** Multisig migrations; tighten with manifest annotation of
  expected admins.

### `missing_expected_event`
- **Score weight:** `0.5`
- **Detection:** A function called per the ABI did not emit its expected
  event. Often indicates a reentrant call that bypassed an emit, or
  failed inner logic.
- **FP notes:** Legitimate revert paths.

### `duplicate_event_emission`
- **Score weight:** `0.4`
- **Detection:** Same indexed event with identical args emitted twice
  in a single trace at different call depths.
- **FP notes:** Some hook-using tokens legitimately emit twice.

### `event_order_violation`
- **Score weight:** `0.55`
- **Detection:** Events emitted in an order that contradicts the
  ABI-declared sequence (e.g. Transfer before Approval in a permit
  flow).
- **FP notes:** Custom protocols may legitimately reorder events.

### `event_parameter_mismatch`
- **Score weight:** `0.45`
- **Detection:** Decoded event arg value contradicts a derived expectation
  (e.g. `Transfer(from=X, to=Y, value=V)` but the balance delta is not
  `V`).
- **FP notes:** Rebasing tokens (`AP-028`) cause this by design.
