# 3. Reading what ChainSentinel found

## 3.1 Three things you'll always see

When `complete` fires, the workspace shows:

1. **Verdict card** at the top — a one-line summary (e.g. *"Classic
   reentrancy exploit drained 1,237 ETH from `0xVault`"*).
2. **Signals & alerts** in the middle — chips for each fired signal
   grouped by family, plus alert cards for each matched pattern.
3. **Entity graph** at the bottom — d3 force-directed layout of the
   fund flow.

The right column's CopilotPanel automatically flips to **Ready** so you
can ask questions.

## 3.2 What a signal means

A signal is **one piece of evidence**. Example: `drain_ratio_exceeded`
fires when a contract's balance dropped by more than 30 % in a single
transaction. That, alone, does not prove anything malicious — a
treasury withdrawal can match. The point of signals is to *gather all
the relevant evidence* before applying judgement.

Signals carry three pieces of information you care about:

- **Name** — what kind of evidence (e.g. `flashloan_bracket_detected`).
- **Severity** — `INFO` (grey), `WARN` (yellow), or `CRIT` (red).
- **Score** — a number `[0,1]` indicating how strong this individual
  piece of evidence is.

Read severity colour first, then dig into the signals that fired with
high score.

## 3.3 What a pattern means

A pattern (a.k.a. *alert*, `AP-NNN`) is **a combination of signals
fired in the right order**. Pattern matches are much more meaningful
than individual signals because they encode the *shape* of an attack.

The shipping catalogue is 38 patterns — see **D4 §10** for the full
table. The common ones:

| Pattern | One-line verdict |
|---------|-------------------|
| `AP-001 classic_reentrancy` | Recursive `withdraw` drained the contract. |
| `AP-006 flash_loan_oracle` | Flash loan used to manipulate an oracle. |
| `AP-012 ownership_hijack` | Admin key transferred, then funds moved. |
| `AP-016 sandwich_attack` | Three swaps in one block; the middle one is the victim. |
| `AP-021 infinite_approval_drain` | Token approval abused to drain wallet. |
| `AP-033 mixer_bridge_detection` | Funds passed through Tornado Cash or a bridge. |

## 3.4 What the entity graph means

![Fund-trace BFS walk](../../diagrams/rendered/09-fund-trace-bfs.png)

The graph shows **who paid whom**, hop by hop:

- **Red nodes** — the victim contract or the attacker EOA, derived
  from the manifest and the analysis.
- **Yellow nodes** — addresses the analyst should treat as suspect.
- **Mint nodes** — known mixers (Tornado Cash, …).
- **Light-green nodes** — known centralised-exchange deposit
  addresses.
- **Pale-blue nodes** — known bridge contracts.
- **Plain nodes** — unknown EOAs.

Edge thickness is value transferred; edge dashing reflects *taint
strength*. A solid edge is fully tainted (=1.0); a dashed edge has
passed through a mixer or bridge and the taint has been haircut.

The graph is interactive: click a node to highlight its hops, click an
edge to see the transaction hash and value.

## 3.5 Severity colour key

This is the same colour key everywhere in the UI:

| Colour | Severity | Meaning |
|--------|----------|---------|
| Grey | `INFO` | Evidence noted; no action required. |
| Wise green | `ok` | Phase completed without issue. |
| Yellow | `WARN` | Suspicious but not conclusive. |
| Red | `CRIT` | Strong evidence of malicious activity. |
