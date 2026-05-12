# 2. Running an investigation

## 2.1 Four modes

Pick the right mode from the sidebar.

| Mode | When to use | What to enter |
|------|-------------|---------------|
| `tx` | The client gave you a specific transaction hash. | The 66-character `0x…` hash. |
| `range` | The client gave you a block window. | `from_block` and `to_block`. |
| `wallet` | The client gave you a wallet address. | The 42-character `0x…` address. |
| `watch` | You want to watch new blocks as they arrive (e.g. an exploit unfolding live). | Nothing — leave it running. |

> The `wallet` and `watch` modes are planned in the architecture but
> not yet wired in the shipping code. If you select them, the SSE feed
> tells you so. Use `tx` or `range` for everything today.

## 2.2 Loading the manifest

1. Click **Load manifest** in the sidebar.
2. Pick the client's `manifest.json`.
3. The sidebar shows the investigation ID, chain ID, window, and the
   list of contracts.
4. The frontend writes the manifest's ABIs into the right place on disk
   automatically — no manual file-copying required.

## 2.3 Hitting "Analyze"

You will see:

- The status pill at the top of the workspace flips to **Running**.
- The `PipelineFeed` lights up with phase events:
  - `collect` (grey) — fetching from RPC
  - `decode`  (grey) — applying ABIs
  - `derive`  (grey) — synthesising events
  - `ingest`  (grey) — writing to Elasticsearch
  - `signals` (yellow / red) — counts how many fired
  - `patterns`(yellow / red) — counts how many matched
  - `complete` (green)
- When `complete` arrives, the workspace **auto-flips** to the
  investigation report and renders the entity graph.

## 2.4 If something looks wrong

- **No signals at all.** Either the client's manifest didn't include
  the right ABIs (so the decoder couldn't make sense of the logs), or
  the time window doesn't cover the suspicious activity. The
  `PipelineFeed` shows decoded vs unknown counts at the `decode`
  phase — if "unknown" dominates, you are missing ABIs.
- **Pipeline crashed.** A red `error` event explains what failed.
  Common causes are wrong RPC URL, ES not reachable, or a malformed
  ABI in the manifest.
- **Pipeline stuck at "collect" for ages.** The RPC is slow or rate-
  limited. Free Alchemy / Infura tiers throttle aggressively on big
  ranges — switch to a paid key or shrink the window.
