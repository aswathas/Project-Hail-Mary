# 10. Frequently asked questions

## 10.1 Can ChainSentinel find every exploit?

No. ChainSentinel has 60 signals and 38 patterns. It will catch every
exploit class it has been taught to recognise — reentrancy, flash-loan
oracle manipulation, admin-key abuse, sandwiches, vault inflation,
many more. It will **miss** novel attack classes the same way an
antivirus misses zero-days. The remedy is to add a signal or a pattern
— see **D5 §5–6**.

## 10.2 Can it analyse contracts I don't have the source for?

Yes — ABIs only. The decoder reads function selectors and event
signatures from the ABI; no source is required. If the client cannot
provide an ABI, the contract's calls will appear as `unknown` decoded
records, which is still useful but limits the detection coverage.

## 10.3 Can it look back further than a few hundred blocks?

Yes — `tx_history_limit` is configurable. Practical limits come from
your RPC: free Alchemy / Infura tiers throttle aggressively. For very
deep history (months / years) point at an archive node.

## 10.4 Does it support chains other than Ethereum?

It supports any EVM-compatible chain (set `chain_id` and `rpc_url` in
`config.json`). It does **not** support non-EVM chains (Solana, Cosmos,
Bitcoin).

## 10.5 Can the copilot post on my behalf to the client?

No. The copilot only generates text. It has no integration with email,
chat, ticketing systems, etc. Copy and paste.

## 10.6 What if the copilot says something wrong?

Cross-check against the entity graph, the signal list, and the
underlying Kibana data. The analysis layer is ground truth. Report
hallucinations to the operator so they can tune prompts.

## 10.7 Can I rerun the same investigation?

Yes. The deterministic document IDs (see **D3 §3.4**) mean re-running
an analysis upserts existing documents — you won't get duplicates.
Useful when:

- A new signal `.esql` was added and you want to apply it to old data.
- An ABI was updated and you want to re-decode.

## 10.8 Where do my investigations live?

Three places:

1. The Elasticsearch index `forensics` (and the raw evidence in
   `forensics-raw`).
2. The browser's `localStorage` — for quick navigation and the
   "Stored Analyses" sidebar list.
3. Optionally, exported PDFs / DOCX from the copilot output.

If you wipe the ES indices, the sidebar history becomes stale links —
nothing in `localStorage` resolves anymore.

## 10.9 Is anything sent to the cloud?

By default, **no**. RPC fetches go wherever you point them. Ollama
runs locally. Elasticsearch runs locally. The frontend is also
served locally. If you point at a cloud RPC (Alchemy / Infura), that
provider sees your queries — same as any blockchain explorer.

## 10.10 How do I get help?

Three layers of help:

1. Tooltip help inline in the UI — hover any signal name.
2. This manual — **D4 Detection Reference** has the full catalog.
3. Your operator / the engineering team — see **D5 §10** for the
   contribution workflow.
