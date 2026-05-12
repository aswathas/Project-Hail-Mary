# 5. Scenario: `mev-sandwich`

## 5.1 Attack class

Classic three-tx sandwich: front-run buy → victim swap → back-run sell.
Maps to `AP-016 sandwich_attack`.

## 5.2 Contracts

| Folder | Files |
|--------|-------|
| `src/victim/` | `SimpleDEX.sol`, `VictimSwapper.sol` |
| `src/attacker/` | `SandwichBot.sol` |
| `src/activity/` | Backdrop activity script |

## 5.3 Script

`RunAll.s.sol` performs:

1. Deploy `SimpleDEX` and seed liquidity.
2. Generate normal swap activity for ~150 blocks.
3. Submit three transactions inside the same block:
   - Attacker buys `T` of `tokenB`.
   - Victim swaps `V` of `tokenA → tokenB`.
   - Attacker sells `T'` of `tokenB`, profiting from the inflated price.

## 5.4 Expected output

| Layer | Document |
|-------|----------|
| Signal (`CRIT`) | (sequence) attacker swap-buy → victim swap → attacker swap-sell, all in one block |
| Signal (`WARN`) | `reserve_ratio_spike`, `value_concentration`, `high_gas_anomaly` |
| Alert | `AP-016 sandwich_attack` (confidence ≥ 0.9) |
| Alert | `AP-017 frontrunning` |
| Case verdict | "Sandwich attack. Attacker bracketed the victim's swap with a front-run buy and a back-run sell in the same block." |
