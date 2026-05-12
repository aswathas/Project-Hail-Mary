# 3.14–3.17 ES setup and Ollama copilot

## 3.14 `es/setup.py`

**Purpose.** Idempotent creation of the two indices and their strict mappings.

**Public function:**

- `async setup_elasticsearch(es) -> dict` — returns
  `{"forensics-raw": "created"|"exists", "forensics": "created"|"exists"}`.

**Behaviour.** Reads `es/mappings/forensics-raw.json` and
`es/mappings/forensics.json`, creates the indices if absent, applies the
mappings if the index existed but has a stale mapping (best-effort —
ES strict mappings make some migrations impossible without reindex).

**Adding a mapping field.**

1. Edit the JSON file under `es/mappings/`.
2. If the index already exists, either:
   - Drop and recreate (acceptable in dev), or
   - Issue a `PUT _mapping` for new top-level fields (mapping is strict
     but new fields can still be added — what is forbidden is
     auto-creation of unmapped fields).

## 3.15 `ollama/copilot.py`

**Purpose.** Streaming chat interface to Ollama with strict prompt
discipline.

**Public functions:**

- `async chat(investigation_id, question) -> AsyncIterable[str]` —
  yields token chunks.
- `async generate_section(investigation_id, section_name) -> str` —
  one-shot generation of one of the 7 report sections.

**Implementation.**

1. Calls `report_template.build_context(investigation_id)` to get the
   structured JSON bundle.
2. Calls `report_sections.prompt_for(section_name, context, question)`
   to build the full prompt.
3. Streams from Ollama via `httpx.AsyncClient.stream("POST", "/api/generate")`.

## 3.16 `ollama/report_template.py`

**Purpose.** Build the per-investigation context bundle for the copilot.

**Public function:**

- `async build_context(es, investigation_id) -> dict` — returns:

```json
{
  "investigation_id": "...",
  "summary": { "tx_hashes": [...], "block_range": [a, b], "victim": "0x..." },
  "signals": [ /* signal_name, score, severity, tx_hash */ ],
  "alerts":  [ /* pattern_id, confidence, required_signals */ ],
  "derived_event_counts": { "value_flow_intra_tx": 12, "approval_registry": 3, ... },
  "fund_flow_edges": [ ... up to 50, sorted by taint desc ... ],
  "attacker_clusters": [ ... ]
}
```

Hard cap on each list (50 by default) to keep the context bundle under
Ollama's working window for `gemma3:1b`. The cap is configurable via
`config.json` — see **D6 §5**.

## 3.17 `ollama/report_sections.py`

**Purpose.** Define the 7 report sections and their strict prompts.

**Sections:**

1. **Executive Summary** — 2–3 paragraphs, plain English, no jargon.
2. **Attack Timeline** — block-by-block narrative.
3. **Technical Mechanism** — explains the exploit logic.
4. **Attacker Attribution** — cluster and label summary.
5. **Fund Trail** — origin → destination, hop-by-hop, with taint scores.
6. **Signal Evidence** — lists firing signals with brief explanations.
7. **Remediation Actions** — suggested fixes for the victim contract.

**Public function:**

- `prompt_for(section: str, context: dict, question: str | None) -> str`

Each section's prompt template lives in a `SECTIONS` dict. Every prompt
ends with the strict "do not invent" instruction (see **D3 §6.3**).
