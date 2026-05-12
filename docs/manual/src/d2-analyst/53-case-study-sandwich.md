# 8. Case study: mev-sandwich

## 8.1 Setup

```bash
./run_demo.sh mev-sandwich
```

## 8.2 What you see

- **Verdict card:** *"MEV sandwich. Attacker bracketed a victim swap
  with a front-run buy and a back-run sell in the same block, profiting
  `N` USDC."*
- **Alerts:** `AP-016 sandwich_attack` (0.91), `AP-017 frontrunning`
  (0.74).
- **CRIT signals:** the sequence-based detections in `sequence/`.
- **WARN signals:** `reserve_ratio_spike`, `value_concentration`,
  `high_gas_anomaly`.

## 8.3 What makes this different

MEV sandwiches are unique among the shipped scenarios because the
exploit is purely **economic**, not contractual. The victim contract
has no bug; the victim user just paid a worse price.

That makes detection an **ordering** problem — three transactions in
one block, in a specific pattern. The pattern engine's EQL sequence
queries are the natural fit.

## 8.4 Copilot quirks

The copilot is allowed to mention prices and gas amounts only when
they appear in the derived events. Try *"What was the slippage?"* and
it will quote a figure straight from the `value_flow_intra_tx` data.

## 8.5 Lessons

1. Sandwich detection depends on **block ordering**, not call traces.
   `AP-016` is fundamentally a sequence query.
2. The attacker is generally a bot; clustering identifies them across
   thousands of past sandwiches if you re-run with a wider window.
