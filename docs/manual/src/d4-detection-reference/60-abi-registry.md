# 12. ABI registry

The ABI registry tells the decoder how to turn topics + calldata into
human-readable events and function calls.

## 12.1 Resolution order

The decoder walks four levels, first match wins:

1. **Case ABIs** — `pipeline/abi_registry/cases/{investigation_id}/*.json`.
   These are per-investigation client handovers; they override anything
   else.
2. **Standards** — `pipeline/abi_registry/standards/*.json`. The eight
   ABIs catalogued below.
3. **Protocols** — `pipeline/abi_registry/protocols/*.json` (Uniswap,
   Aave, Compound, Curve — additions made as needed).
4. **Selector cache** — `pipeline/selector_registry.json`. A living
   document of `selector → name` mappings discovered at runtime via
   4byte.directory lookups (when available) or operator entry.

If nothing resolves, the log/call gets `decode_status: unknown` and is
still indexed — analysts can audit unknown selectors in Kibana.

## 12.2 Auto-generated catalog

\pagebreak

{{< include ../_generated/abi_registry.md >}}

## 12.3 Per-ABI summary

### `erc20.json`
- Standard ERC-20: `Transfer`, `Approval` events; `transfer`,
  `transferFrom`, `approve` functions.
- Every project-deployed token defaults to this if no protocol ABI is
  registered.

### `VulnerableVault.json` / `vulnerable_vault.json`
- Mock vault used by the `reentrancy-drain` simulation.
- Events: `Deposit`, `Withdraw`. Functions: `deposit`, `withdraw`,
  `claimReward`, `donateToPool`, plus the reentrancy-vulnerable
  variant.

### `LendingPool.json`
- Used by `flash-loan-oracle` simulation.
- Events: `FlashLoan`, `Borrow`, `Repay`, `Liquidate`. Six functions:
  `flashLoan`, `borrow`, `repay`, `deposit`, `withdraw`, `liquidate`.

### `SimpleOracle.json`
- Manipulated by the `flash-loan-oracle` scenario.
- One event `PriceUpdated`, three functions: `getPrice`, `update`,
  `latestRoundData`.

### `SimpleDEX.json`
- Mock constant-product DEX used by `mev-sandwich`.
- Events: `Swap`, `LiquidityAdded`, `LiquidityRemoved`. Nine functions
  covering the AMM API surface.

### `MockUniswapPool.json`
- Sibling of `SimpleDEX` used by some oracle tests. Three events
  (`Swap`, `Mint`, `Burn`), six functions matching Uniswap V2 minimum.

### `GovernanceToken.json`
- Used by `admin-key-abuse`. Events: `Transfer`, `Approval`,
  `OwnershipTransferred`, `Mint`. Eleven functions including
  `mint(address, uint256)` (the abused privilege).

The exact counts (events / functions per ABI) live in the auto-generated
table above and update on every `make catalogs`.

## 12.4 Selector cache (`selector_registry.json`)

A flat JSON dictionary `{ "0x12345678": "transfer(address,uint256)" }`.
Read every run, written when a previously-unknown selector is decoded
via 4byte lookup. Persist across investigations — over time, the cache
captures the long tail of contracts the operator's analysts encounter.
