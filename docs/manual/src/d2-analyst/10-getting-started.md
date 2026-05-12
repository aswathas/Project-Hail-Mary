# 1. Getting started

## 1.1 What you need from the client

To run an investigation you need four things:

1. **RPC URL** — the client's node endpoint (Alchemy / Infura / their
   own archive node) or a local Anvil if testing simulations.
2. **Contract ABIs** — JSON files for every contract involved in the
   suspected exploit. These tell ChainSentinel how to read the chain
   data. For ERC-20 tokens the registry already has standard ABIs;
   you only need the custom contracts.
3. **Deployed contract addresses** — the on-chain addresses for those
   ABIs.
4. **Approximate window** — a block range, transaction hash, or wallet
   address. "Last Tuesday around lunchtime" is enough if you know the
   victim contract.

Bundle these into a `manifest.json` (see **D5 §8.4** for the schema or
copy from any `simulations/scenarios/*/client/manifest.json`).

## 1.2 Starting the tool

If the operator has set things up, just open the URL they gave you —
typically `http://localhost:5173`. If not, run:

```bash
./chainsentinel/start.sh
```

Wait until the terminal shows `=== ChainSentinel Ready ===`, then open
the frontend.

## 1.3 The three-column workspace

![Three-column layout](../../diagrams/rendered/10-frontend-layout.png)

| Column | Purpose |
|--------|---------|
| Sidebar (left) | Pick a mode, load a manifest, see past investigations. |
| Workspace (centre) | Live pipeline log while running; investigation report when complete. |
| Copilot (right) | Ask follow-up questions; generate the 7 report sections. |

You will spend most of your time in the centre column. The sidebar is
for control, the copilot is for explanation.
