# 5. Case study: reentrancy-drain

A first walkthrough using the `reentrancy-drain` simulation. Steps an
analyst takes start-to-finish.

## 5.1 Setup

Run:

```bash
./run_demo.sh reentrancy-drain
```

The terminal logs deployment, then ~200 normal txs, then the attack.
At the end it prints:

```
Investigation: SIM-REENTRANCY-001
Block range: 5..212
Open: http://localhost:5173?investigation=SIM-REENTRANCY-001
```

## 5.2 Open the investigation

1. The sidebar shows the new investigation already loaded.
2. The workspace shows the `PipelineFeed` is at `complete` (the demo
   script analyzes automatically).

## 5.3 What you see

- **Verdict card:** *"Classic reentrancy exploit. Attacker recursively
  re-entered `withdraw()` on VulnerableVault and drained the contract
  before the balance update."*
- **Alerts:** `AP-001 classic_reentrancy` at `0.92`, `AP-030
  attacker_deployment` at `0.78`, `AP-031 fund_dispersion` at `0.71`.
- **CRIT signals:** `cross_function_reentry`, `recursive_depth_pattern`,
  `value_drain_per_depth`, `drain_ratio_exceeded`.
- **WARN signals:** `same_block_deploy_and_attack`,
  `contract_deployed_before_attack`, `storage_update_delay`,
  `fund_dispersion_post_attack`.
- **Entity graph:** the attacker EOA (yellow) is connected to the
  vault (red), to two helper EOAs, and eventually to a Tornado Cash
  contract (mint).

## 5.4 Confirming the verdict in the data

Open Kibana (or the Discover button in the workspace) and filter by
`investigation_id` + `layer:"derived"` + `derived_type:"reentrancy_patterns"`.
You will see the recursive `withdraw` calls at increasing call depth,
each with `value_eth > 0`. This is the underlying evidence the
`recursive_depth_pattern` signal fired on.

## 5.5 Asking the copilot

Click into the CopilotPanel and try:

- *"Generate the Executive Summary."* — two paragraphs you can paste
  into a client report.
- *"Summarise the fund trail."* — narrative form of the entity graph.
- *"How could the victim have prevented this?"* — the copilot will
  produce a Remediation Actions section pointing at the
  checks-effects-interactions pattern and OpenZeppelin's
  `ReentrancyGuard`.

## 5.6 Lessons

Three things to internalise:

1. The strongest evidence here is `cross_function_reentry` (score 0.95)
   and `recursive_depth_pattern` (score 0.7). One of those alone would
   already be enough — together, the verdict is unambiguous.
2. The pattern `AP-001` required only the reentrancy + drain signals,
   *not* the flash-loan bracket — reentrancy doesn't need flash loans.
3. The entity graph would have shown the same fund flow even if the
   attacker had used a hand-funded EOA instead of self-deployment.
