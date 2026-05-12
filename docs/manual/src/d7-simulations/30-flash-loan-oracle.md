# 3. Scenario: `flash-loan-oracle`

## 3.1 Attack class

Flash-loan-financed oracle manipulation. Borrow → push spot price →
exploit lending position → repay flash loan. Maps to
`AP-006 flash_loan_oracle`.

## 3.2 Contracts

| Folder | Files |
|--------|-------|
| `src/victim/` | `LendingPool.sol`, `SimpleOracle.sol`, `MockUniswapPool.sol` |
| `src/attacker/` | `OracleManipulator.sol` |

## 3.3 Scripts

| Script | Phase |
|--------|-------|
| `01_DeployProtocol.s.sol` | Deploys lending pool, oracle, AMM pool, seeds liquidity |
| `02_NormalActivity.s.sol` | Routine swaps + lending activity for ~200 txs |
| `03_ExecuteAttack.s.sol` | `OracleManipulator` takes a flash loan, swaps to drive oracle price, liquidates a victim position, repays |
| `04_PostAttack.s.sol` | Disperses funds via bridge mock |
| `RunAll.s.sol` | Chains all of the above |

## 3.4 Expected output

| Layer | Document |
|-------|----------|
| Signal (`CRIT`) | `flashloan_bracket_detected`, `spot_price_manipulation`, `drain_ratio_exceeded` |
| Signal (`WARN`) | `multi_oracle_divergence`, `price_read_during_callback`, `bridge_interaction_detected` |
| Alert | `AP-006 flash_loan_oracle` (confidence ≥ 0.9) |
| Alert | `AP-009 amm_spot_price` (also matches the same evidence at confidence ≥ 0.7) |
| Alert | `AP-033 mixer_bridge_detection` |
| Case verdict | "Flash-loan-funded oracle manipulation. Borrowed funds were used to skew spot price, then a position was liquidated against the manipulated price." |
