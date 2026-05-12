# 1. Foundry environment

## 1.1 `foundry.toml`

```toml
[profile.default]
solc_version = "0.8.24"
evm_version  = "cancun"
optimizer    = true
optimizer_runs = 200
ffi          = false
via_ir       = false
src          = "scenarios"
script       = "scenarios"
remappings   = ["@shared/=shared/"]

[rpc_endpoints]
anvil = "http://127.0.0.1:8545"
```

## 1.2 Workflow

Every scenario has three phases:

1. **Deploy victim** — sets up the legitimate protocol.
2. **Normal activity** — generates a backdrop of legitimate transactions
   so the attack does not look anomalous purely because it is the only
   activity in the chain. Default `tx_history_limit`-aligned (~200 txs).
3. **Execute attack** — the malicious transaction or sequence.

Output of each scenario:

- Block range `[deploy_block, attack_block]` for the analyst to feed
  into ChainSentinel's range mode.
- `client/` directory with ABIs and a `manifest.json`.

## 1.3 Shared contracts

Under `simulations/shared/contracts/`:

| File | Purpose |
|------|---------|
| `MockERC20.sol` | Standard ERC-20 with `mint(address,uint256)` for tests. Used as base asset in every scenario. |
| `MockWETH.sol`  | Minimal wrapped-ETH mock. Used by DEX scenarios. |
| `UserActivity.sol` | Helper that emits varied activity (transfers, approvals, swaps) to populate the chain. Used by the *normal activity* phase. |

## 1.4 Running a scenario

```bash
cd simulations
forge script scenarios/reentrancy-drain/script/RunAll.s.sol \
  --rpc-url anvil \
  --broadcast \
  --private-key 0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80 \
  -vv
```

`RunAll.s.sol` chains the per-phase scripts (`01_…`, `02_…`, `03_…`,
`04_…`) so a single command produces the entire scenario.
