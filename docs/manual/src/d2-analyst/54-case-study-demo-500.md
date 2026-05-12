# 9. Case study: demo-500 (live presentation)

## 9.1 What `demo-500` is

A scripted scenario that packs 500 transactions — most of them benign
— around two distinct exploits: a reentrancy drain and a sandwich
attack. Designed for live demos to a non-technical audience.

## 9.2 Running it

The default `docker-compose` workflow runs `demo-500` end-to-end:

```bash
docker compose up
```

When `chainsentinel-pipeline` exits, open the frontend and you'll see
the analysis already complete.

## 9.3 What to highlight

When demoing:

1. Show the `PipelineFeed` while it's running — the rapid-fire phase
   events make the system feel alive.
2. Once `complete` fires, open the alerts panel. There will be **two**
   patterns: `AP-001` (reentrancy) and `AP-016` (sandwich). This is
   the magic moment — ChainSentinel found two unrelated exploits in
   the same 500-tx window without being told what to look for.
3. Open the entity graph. The attacker and the sandwich bot are
   different addresses, both visible.
4. Click the CopilotPanel and generate the Executive Summary. Two
   paragraphs that tell the story.

## 9.4 Caveats

- `demo-500` is deterministic — the same private keys, same nonces,
  same outcomes. If you need novelty, modify the script or pull a
  real on-chain incident.
- The copilot output is *not* deterministic with default `gemma3:1b`;
  expect minor wording variation between runs.
