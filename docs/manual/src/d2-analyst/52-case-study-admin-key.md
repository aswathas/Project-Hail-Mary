# 7. Case study: admin-key-abuse

## 7.1 Setup

```bash
./run_demo.sh admin-key-abuse
```

## 7.2 What you see

- **Verdict card:** *"Admin-key compromise. Ownership of GovernanceToken
  was transferred to attacker EOA at block N, who then minted 10×
  the existing supply and dumped it into the AMM."*
- **Alerts:** `AP-012 ownership_hijack` (0.93), `AP-020 mint_and_dump`
  (0.88), `AP-031 fund_dispersion` (0.7).
- **CRIT signals:** `ownership_transfer_then_drain`, `mint_to_dump_ratio`,
  `rapid_token_dump`.

## 7.3 Distinguishing legitimate ownership transfers

Not every `OwnershipTransferred` event is malicious — multisigs migrate
admin keys all the time. `AP-012` requires the drain to happen *within
a short window* of the transfer. Open the **Timeline** view in
`InvestigationView` and you'll see:

```
block N      OwnershipTransferred(prev, new=0xAttacker)
block N+1    GovernanceToken.mint(0xAttacker, 1e25)
block N+2    SimpleDEX.swap(token, weth) ×3  — dump
```

Three blocks. That is what makes this malicious.

## 7.4 What the copilot says

*"Generate Remediation Actions."* You'll get:

1. Migrate admin to a multisig (2-of-3 minimum) before re-issuing.
2. Time-lock all owner-only functions; the abused `mint` should have
   a 24-hour delay.
3. Add a per-block mint cap (e.g. max `1 %` of supply per day).
4. Subscribe to ChainSentinel watch-mode on the victim contract going
   forward.

## 7.5 Lessons

1. Ownership signals on their own are weak. The strength comes from
   pattern AP-012, which requires the *transfer → drain* sequence.
2. The `mint_to_dump_ratio` signal would have fired even without the
   ownership transfer if a malicious owner had been in place from
   day one — useful for catching slow rugs.
