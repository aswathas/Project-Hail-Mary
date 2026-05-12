# 4. Scenario: `admin-key-abuse`

## 4.1 Attack class

Compromised admin key transfers ownership, mints tokens, dumps. Maps to
`AP-012 ownership_hijack` and `AP-020 mint_and_dump`.

## 4.2 Contracts

| Folder | Files |
|--------|-------|
| `src/victim/` | `GovernanceToken.sol`, `Treasury.sol` |

## 4.3 Scripts

| Script | Phase |
|--------|-------|
| `01_DeployProtocol.s.sol` | Deploys `GovernanceToken` + small treasury |
| `02_NormalActivity.s.sol` | Token transfers + approvals among a community of EOAs |
| `03_ExecuteAttack.s.sol` | Attacker (with compromised owner key) calls `transferOwnership`, then `mint`, then dumps the minted supply via a DEX |
| `04_PostAttack.s.sol` | Funds dispersion |
| `RunAll.s.sol` | Chains all of the above |

## 4.4 Expected output

| Layer | Document |
|-------|----------|
| Signal (`CRIT`) | `ownership_transfer_then_drain`, `mint_to_dump_ratio`, `rapid_token_dump` |
| Signal (`WARN`) | `governance_instant_execution`, `value_dispersion`, `same_block_deploy_and_attack` |
| Alert | `AP-012 ownership_hijack` (confidence ≥ 0.9) |
| Alert | `AP-020 mint_and_dump` (confidence ≥ 0.85) |
| Alert | `AP-031 fund_dispersion` |
| Case verdict | "Admin-key compromise. Ownership transferred to attacker, who then minted tokens and dumped them into the open market within `N` blocks." |
