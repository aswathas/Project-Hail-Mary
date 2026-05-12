# 6. Case study: flash-loan-oracle

## 6.1 Setup

```bash
./run_demo.sh flash-loan-oracle
```

The terminal shows the lending pool deployment, the seeded liquidity,
~200 normal swap/lend txs, then the attack: a flash loan, a price
swing, a profitable liquidation, and the loan repayment — all in one
transaction.

## 6.2 What you see

- **Verdict card:** *"Flash-loan-funded oracle manipulation. Attacker
  borrowed `X` ETH, manipulated the spot price on MockUniswapPool to
  trigger a profitable liquidation, then repaid the loan in the same
  tx."*
- **Alerts:** `AP-006 flash_loan_oracle` (0.94), `AP-009 amm_spot_price`
  (0.81), `AP-033 mixer_bridge_detection` (0.62).
- **CRIT signals:** `flashloan_bracket_detected`, `spot_price_manipulation`,
  `drain_ratio_exceeded`.
- **WARN signals:** `multi_oracle_divergence`, `price_read_during_callback`,
  `bridge_interaction_detected`.

## 6.3 Reading the trace

Open the workspace's **Trace** tab. The call tree shows:

```
flashLoan(X)
  ├─ onFlashLoan() callback
  │   ├─ Pool.swap(big amount) — moves spot price
  │   ├─ LendingPool.liquidate(victimPosition) — uses inflated price
  │   └─ Pool.swap(reverse) — recovers the asset
  └─ Pool.repay(X + fee)
```

Two price reads, with a value swap in between — that's why
`price_before_after_mismatch` fired.

## 6.4 Copilot helpers

Try *"Walk me through the attack step by step."* The copilot will
produce a numbered list reflecting the trace, citing the tx hash and
block number for each step.

## 6.5 Lessons

1. The flash-loan bracket is the **scaffold** — the actual harm is
   the oracle manipulation. `AP-006` requires both.
2. The same evidence also matches `AP-009 amm_spot_price` at lower
   confidence. ChainSentinel surfaces both; the higher confidence is
   the verdict, the lower is a corroborating perspective.
3. If the lending pool had used a TWAP instead of a spot price,
   `AP-006` would not have fired — but `AP-010 twap_manipulation`
   would have, if the attacker sustained the manipulation across
   blocks.
