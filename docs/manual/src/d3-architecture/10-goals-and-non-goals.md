# 1. Goals and non-goals

## 1.1 What ChainSentinel is for

ChainSentinel is a **standalone EVM blockchain forensics tool**. Given a
transaction hash, wallet address, or block range — plus a client-supplied
manifest of ABIs and deployed contract addresses — it runs a full forensic
pipeline:

1. Collects raw chain data from an RPC endpoint (Anvil, testnet, or mainnet).
2. Decodes it using the client's ABIs and a registry of standards.
3. Synthesises higher-level *derived events* (value flows, reentrancy
   patterns, governance actions, …).
4. Runs **60 ES|QL signals and 38 EQL attack patterns** against the indexed
   data.
5. Traces funds across up to five hops and clusters related wallets.
6. Surfaces findings in a React investigation workspace with an
   Ollama-powered copilot that explains them in plain English.

The real-world workflow it targets: *"a client comes to SISA and says they
were exploited. They hand over their RPC endpoint, contract ABIs, deployed
addresses, and an approximate time window. The analyst loads this into
ChainSentinel and the tool tells them what happened — purely from on-chain
data plus the client's ABIs."*

## 1.2 Hard goals

| # | Goal | Mechanism |
|---|------|-----------|
| G1 | Detection logic readable by anyone who knows Elasticsearch | All signals are `.esql` files, all patterns are `.eql` files — no Python logic. |
| G2 | Raw evidence never mixed with interpretations | Two strict ES indices: `forensics-raw` (untouched) and `forensics` (everything derived). |
| G3 | Modular growth | Add a signal = drop a `.esql` file. Add a pattern = drop a `.eql` file. Add a derived event = add a `.py` builder. Engines auto-discover. |
| G4 | Switch between Anvil, testnet, mainnet with one URL change | No node-specific conditional logic; only `rpc_url` and `chain_id` differ across deployments. |
| G5 | Idempotent re-ingestion | Every ES document has a deterministic `_id`; replaying the same data yields the same documents. |
| G6 | Graceful degradation | Tool works on basic RPC (receipts + logs) and degrades from there. Full traces are an enhancement, not a requirement. |
| G7 | Fully demonstrable offline | Foundry simulations on local Anvil reproduce real client engagements end-to-end. |
| G8 | One-command stack startup | `chainsentinel/start.sh` brings up ES, Ollama, Anvil, FastAPI, and the React frontend. |
| G9 | Copilot never invents data | Ollama is fed structured JSON context, never raw ES documents; prompts forbid invented addresses, amounts, hashes, or block numbers. |

## 1.3 Explicit non-goals

- **Not a SIEM.** ChainSentinel ingests *one investigation at a time*; it
  is not designed for continuous, multi-tenant ingestion.
- **Not a generic blockchain indexer.** The forensic schema is opinionated.
  Use The Graph, Subsquid, or a custom indexer for product analytics.
- **Not a paid intel feed.** Address labels (OFAC, known exploiters,
  mixers, bridges, CEX wallets) ship as a small local DB; integration with
  commercial intel providers is out of scope.
- **Not a chain-of-custody system.** ChainSentinel reproduces evidence
  deterministically but does not produce court-admissible artefacts.
- **No cross-VM support.** Solana, Cosmos, Bitcoin are out of scope; this
  is EVM-only.

## 1.4 Trust boundaries

The system has four trust regions:

1. **Client handover** — manifest + ABIs + RPC URL. Treated as untrusted
   input: invalid ABIs degrade decode rather than crash; out-of-range
   blocks produce an error event, not silent partial results.
2. **RPC endpoint** — assumed honest about chain state but may be slow,
   rate-limited, or partial (no debug traces). The collector tolerates
   missing fields and records `decode_status = unknown` when needed.
3. **Local infrastructure** — Elasticsearch, Ollama, the FastAPI server,
   and the frontend all run on the analyst's machine (or a single locked-
   down VM). Network exposure is unnecessary; defaults bind to localhost.
4. **Operator inputs** — the analyst chooses what to investigate, but the
   copilot never accepts free-form SQL or ES queries via the chat
   interface. Questions are routed through `report_sections.py` which
   builds structured prompts.
