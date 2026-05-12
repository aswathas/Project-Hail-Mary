# 6. Glossary

| Term | Meaning |
|------|---------|
| **ABI** | Application Binary Interface — the JSON description of a smart contract's functions and events. The decoder uses ABIs to turn raw call data into human-readable records. |
| **Anvil** | Foundry's local EVM node. Used for offline simulations. |
| **ChainSentinel** | This tool. |
| **Copilot** | The Ollama-backed assistant that turns analysis findings into prose. |
| **Derived event** | A higher-level fact synthesised by the pipeline (e.g. "value flowed from X to Y") that signals run against. |
| **EQL** | Event Query Language — Elasticsearch's sequence-query language. Used for attack patterns. |
| **ES&#124;QL** | Elasticsearch Query Language — the SQL-like language used for signals. |
| **Fund trace** | The BFS walk over value-transfer edges that ChainSentinel performs to follow funds. |
| **Haircut** | The factor by which taint is reduced at each hop (mixer × 0.7, bridge × 0.8, CEX × 0.9). |
| **Investigation** | One unit of forensic work, identified by an `investigation_id`. |
| **Manifest** | The client-supplied JSON containing ABIs, addresses, and time window. |
| **Mixer** | A contract designed to obscure transaction lineage (e.g. Tornado Cash). |
| **Ollama** | The local LLM runtime used by the copilot. |
| **Pattern (AP-NNN)** | A multi-signal attack pattern; matched by EQL sequence queries. |
| **Pipeline** | The Python plumbing that fetches, normalises, decodes, and derives data. |
| **Severity** | One of `INFO`, `WARN`, `CRIT` — used to colour signals and alerts. |
| **Signal** | A single piece of detection evidence; matched by an ES&#124;QL query. |
| **SISA** | The forensics organisation ChainSentinel was built for. |
| **Taint** | The propagation strength of "this money came from the exploit". A scalar in `[0,1]`. |
| **Trace** | The full execution call tree of a transaction (requires `debug_traceTransaction` from the RPC). |
| **Wise design system** | The UI palette and typography used by the frontend. |
