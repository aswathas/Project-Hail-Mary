# 4. Working with the copilot

## 4.1 What the copilot can do

The copilot summarises and explains. It does **not** invent. It cannot
access the internet, query the blockchain directly, or write new
detection rules. What it does is take the data ChainSentinel produced
and turn it into prose.

Two modes:

1. **Section generation.** Pick one of the 7 sections and the copilot
   writes a draft for it. Useful when you need to write a client
   report fast.
2. **Free-form Q&A.** Ask it anything about the current investigation.
   "Why did `AP-006` fire?" "Which addresses received funds after the
   exploit?" "Summarise the timeline in two paragraphs."

## 4.2 The seven sections

| Section | Typical content |
|---------|-----------------|
| Executive Summary | Two paragraphs you can paste at the top of a client report. |
| Attack Timeline | Block-by-block narrative. |
| Technical Mechanism | How the exploit worked. |
| Attacker Attribution | What the clustering and label DB say. |
| Fund Trail | Where the money went, hop by hop, with taint. |
| Signal Evidence | Bullet list of firing signals and what each means. |
| Remediation Actions | Suggestions for the victim contract. |

Each section is regenerable — click **Refresh** to get a new draft.

## 4.3 Guardrails

The copilot is constrained by its prompt:

- Every address, hash, amount, and block number it mentions **must**
  appear in the analysis. If you see something invented, treat it as a
  bug and report it.
- If the analysis does not have an answer, the copilot must say so
  rather than guess.
- The copilot will refuse to write detection rules, blockchain
  transactions, or any code that would execute outside the report.

If you suspect the copilot has invented something, cross-check against
the entity graph and the signal list. The analysis layer is the ground
truth.

## 4.4 Picking a different model

If the operator configured a larger model (e.g. `llama3:8b`), reports
will be slower but more polished. The copilot's behaviour is otherwise
identical.
