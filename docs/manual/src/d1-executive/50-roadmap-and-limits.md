# 5. Roadmap and limits

## 5.1 What is shipped today

| Capability | Status |
|------------|--------|
| Pipeline (collector → ingest → derive) | Complete |
| Detection engine (60 signals, 38 patterns) | Complete |
| Correlation (fund trace, clustering, mixer detection) | Complete |
| React frontend (3-column workspace) | Complete |
| Ollama copilot (7-section reports) | Complete |
| Foundry simulations (5 scenarios) | Complete |
| `tx` mode, `range` mode | Working |
| Docker Compose deployment | Working |

## 5.2 What is planned (not yet wired)

| Capability | Notes |
|------------|-------|
| `wallet` mode | Architectural support is in; runner not yet implemented. |
| `watch` mode | Continuous new-block polling for ongoing incidents. |
| `POST /simulate` endpoint | Currently a placeholder; would deploy scenarios via the API. |
| Auto-loading client manifest from frontend | Today done via static file drop. |
| Commercial intel feed integration | Plug-in point exists (`correlation/label_db.py`); not wired to Chainalysis / TRM. |
| Cross-chain support | Architecturally tied to a single `chain_id` per investigation. |

## 5.3 Explicit limits

- **EVM only.** No Solana, no Cosmos, no Bitcoin. Architectural rather
  than software-engineering choice.
- **Single-tenant.** Multi-analyst-on-same-machine works, but the
  default ES setup has no auth — fine for a single analyst, not fine
  for a shared production cluster.
- **No automated legal artefact production.** ChainSentinel reproduces
  evidence deterministically but does not produce court-admissible
  chain-of-custody documents.
- **Detection is what it knows.** Novel attack classes will not match
  any of the 38 patterns. The remedy is to add a pattern; the cookbook
  is in **D5 §6**.

## 5.4 What the engineering team is watching

- **ES|QL coverage gaps.** Some detections are awkward in pure ES|QL
  and require derived-event support. The team adds builders as needed.
- **Copilot quality.** Gemma 3 1B is excellent for summaries but can
  fumble long sequences. The team evaluates new local models as they
  appear.
- **Performance at high TX volume.** The pipeline is async-first but
  RPC is the dominant cost. Adding a caching layer is on the
  roadmap.
