# 2. Scenario: `reentrancy-drain`

## 2.1 Attack class

Classic recursive `withdraw` against a vulnerable vault. Maps to
`AP-001 classic_reentrancy`.

## 2.2 Contracts

| Folder | Files |
|--------|-------|
| `src/victim/` | `VulnerableVault.sol`, `LegitimateVault.sol` (the "safe" comparison) |
| `src/attacker/` | `ReentrantAttacker.sol`, helper EOA deployments |
| `src/activity/` | Routine `UserActivity` script |

The victim implements:

```solidity
function withdraw(uint256 amount) external {
    require(balances[msg.sender] >= amount, "insufficient");
    (bool ok,) = msg.sender.call{value: amount}("");
    require(ok, "transfer failed");
    balances[msg.sender] -= amount;   // <-- update after call
}
```

The classic "update after external call" reentrancy pattern.

## 2.3 Scripts (phases)

| Script | Phase |
|--------|-------|
| `01_DeployProtocol.s.sol` | Deploys `VulnerableVault` + `MockERC20` |
| `02_NormalActivity.s.sol` | ~200 user deposits + withdrawals |
| `03_ExecuteAttack.s.sol` | Deploys `ReentrantAttacker`, calls `attack()` which recursively re-enters `withdraw` |
| `04_FundDispersion.s.sol` | Splits drained ETH across several EOAs |
| `05_ExtendedTest.s.sol` | Adds a Tornado-cash-style mixer interaction for graph signals |
| `RunAll.s.sol` | Chains all of the above |

## 2.4 Expected ChainSentinel output

| Layer | Document |
|-------|----------|
| Signal (`CRIT`) | `cross_function_reentry`, `recursive_depth_pattern`, `value_drain_per_depth`, `drain_ratio_exceeded` |
| Signal (`WARN`) | `same_block_deploy_and_attack`, `contract_deployed_before_attack`, `storage_update_delay`, `fund_dispersion_post_attack` |
| Alert | `AP-001 classic_reentrancy` (confidence ≥ 0.85) |
| Alert | `AP-030 attacker_deployment` (confidence ≥ 0.7) |
| Alert | `AP-031 fund_dispersion` (confidence ≥ 0.7) |
| Case verdict | "Classic reentrancy exploit. Recursive `withdraw` drained the vault before balance update." |
