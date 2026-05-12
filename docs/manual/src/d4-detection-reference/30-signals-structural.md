# 3. Family: structural (11 signals)

Structural signals fire on properties of the **execution trace itself** —
call depth, opcodes, delegatecall write paths, selfdestruct. They are
the strongest signals available because the evidence is unambiguous.

| Stem | File | Inputs |
|------|------|--------|
| `create2_redeployment` | `detection/signals/structural/create2_redeployment.esql` | `derived/contract_deployments` |
| `cross_function_reentry` | `detection/signals/structural/cross_function_reentry.esql` | `derived/reentrancy_patterns`, `derived/execution_structure` |
| `delegatecall_storage_write` | `detection/signals/structural/delegatecall_storage_write.esql` | `derived/storage_mutations`, raw traces |
| `flashloan_bracket_detected` | `detection/signals/structural/flashloan_bracket_detected.esql` | `derived/value_flow_intra_tx`, `decoded` Transfer events |
| `hook_callback_detected` | `detection/signals/structural/hook_callback_detected.esql` | `derived/execution_structure` |
| `initialize_on_live_contract` | `detection/signals/structural/initialize_on_live_contract.esql` | `decoded` function calls |
| `proxy_implementation_change` | `detection/signals/structural/proxy_implementation_change.esql` | `decoded` Upgraded events |
| `recursive_depth_pattern` | `detection/signals/structural/recursive_depth_pattern.esql` | `derived/execution_structure` |
| `selfdestruct_detected` | `detection/signals/structural/selfdestruct_detected.esql` | raw traces |
| `storage_update_delay` | `detection/signals/structural/storage_update_delay.esql` | `derived/storage_mutations` |
| `value_drain_per_depth` | `detection/signals/structural/value_drain_per_depth.esql` | `derived/value_flow_intra_tx`, `derived/execution_structure` |

## 3.1 Per-signal notes

### `flashloan_bracket_detected`
- **Score weight:** `0.9`
- **What it detects:** A flash-loan opening transfer (e.g. Aave / Balancer
  / dYdX `flashLoan` call) and a closing repayment in the same
  transaction.
- **False-positive notes:** Some legitimate yield-strategies use
  flash loans; this signal alone is *not* a verdict — it is the entry
  condition for `AP-005..AP-008`.

### `cross_function_reentry`
- **Score weight:** `0.95`
- **What it detects:** The same callee appears at two different call
  depths within a tx, where the second call writes state visible to the
  first.
- **False-positive notes:** Multicall patterns can trigger this; the
  pattern engine filters by combining with `derived/reentrancy_patterns`.

### `delegatecall_storage_write`
- **Score weight:** `1.0`
- **What it detects:** A `DELEGATECALL` opcode where the callee's
  execution writes to the *caller's* storage at a slot that subsequently
  changes admin / owner / implementation.
- **False-positive notes:** Proxy upgrades intentionally do this; combine
  with `proxy_implementation_change` to disambiguate legitimate upgrades.

### `selfdestruct_detected`
- **Score weight:** `1.0`
- **What it detects:** A `SELFDESTRUCT` opcode in the trace.
- **False-positive notes:** Disposable factory contracts may
  self-destruct as part of normal CREATE2 patterns; pair with
  `contract_size_zero_after_selfdestruct` from the `additional` family.

### `recursive_depth_pattern`
- **Score weight:** `0.7`
- **What it detects:** Call depth exceeds a configured threshold (default
  `3`) for the same target contract.
- **False-positive notes:** Deep DEX aggregator routes can match; filter
  by combining with value-flow signals.

### `proxy_implementation_change`
- **Score weight:** `0.6`
- **What it detects:** An `Upgraded(address)` event from any contract.
- **False-positive notes:** Legitimate upgrades fire this constantly;
  the pattern engine uses it in `AP-013` (uninitialized proxy) alongside
  `initialize_on_live_contract`.

### `initialize_on_live_contract`
- **Score weight:** `0.8`
- **What it detects:** An `initialize()` call on a contract whose nonce
  is `> 0` or whose code was deployed in a previous block.
- **False-positive notes:** Beacon-proxy patterns occasionally re-call
  initialize during legitimate upgrades.

### `hook_callback_detected`
- **Score weight:** `0.6`
- **What it detects:** ERC777 / ERC1155 hook re-enters the caller in the
  same trace.
- **False-positive notes:** Legitimate token bridges use hooks; combine
  with reentrancy depth.

### `storage_update_delay`
- **Score weight:** `0.5`
- **What it detects:** A storage write happens at a higher call depth
  than the read that should have prevented it (classic reentrancy
  symptom).
- **False-positive notes:** Compound interest accrual occasionally
  triggers this; combine with `drain_ratio_exceeded`.

### `value_drain_per_depth`
- **Score weight:** `0.85`
- **What it detects:** Aggregate value transferred from a single
  contract increases monotonically with call depth.
- **False-positive notes:** Multi-leg arb routes can trigger; filter by
  source = victim contract address from the manifest.

### `create2_redeployment`
- **Score weight:** `0.8`
- **What it detects:** A CREATE2 deployment to an address that previously
  hosted different code (i.e. metamorphic contract).
- **False-positive notes:** Some governance systems intentionally redeploy
  beacon implementations to the same address.
