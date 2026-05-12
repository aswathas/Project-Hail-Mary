# 1. The problem ChainSentinel solves

When a DeFi protocol is exploited, the first 48 hours determine whether
funds are recovered, the attacker is identified, and the protocol
survives. Today that window is consumed by **manual forensic work**:

- An analyst pulls transactions one at a time from a block explorer.
- They eyeball traces in Tenderly or Phalcon.
- They piece together the attack timeline in a Notion doc.
- They write the client report from scratch.

Each step is slow, error-prone, and depends entirely on the analyst's
experience. Two analysts looking at the same incident often arrive at
different verdicts.

ChainSentinel changes the unit of work. Instead of "analyse one
transaction at a time", the unit becomes "answer the question *was
this an exploit, and if so, which kind?*" for a whole window of
on-chain activity. The analyst still applies judgement; they just no
longer carry the entire forensic load by hand.

## 1.1 What an analyst's day looks like before and after

| Before | After |
|--------|-------|
| Manually open every tx in a block explorer | Click "Analyze" on the window |
| Eyeball traces in a separate tool | Trace renders inside the investigation view |
| Write detection logic mentally | 60 signals + 38 patterns run automatically |
| Write the report in Notion | Copilot drafts the 7 sections |
| 2–5 days to first verdict | 5–15 minutes |

## 1.2 What ChainSentinel does **not** do

- Stop attacks in progress. ChainSentinel is read-only; it analyses, it
  does not intervene.
- Recover funds. It tells you where they went; chain analysis providers
  and law enforcement handle recovery.
- Replace the analyst. It accelerates them. Every verdict is auditable
  back to the underlying transaction data.
