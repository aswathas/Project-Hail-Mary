# 9. Architecture decision records

Short-form ADRs. Each captures the choice, the alternatives considered,
and the consequence.

---

## ADR-001 — Detection logic lives in ES queries, not Python

**Context.** ChainSentinel needs a detection layer that domain experts
(SISA analysts) can modify without learning Python.

**Decision.** Every signal is a `.esql` file under `detection/signals/`.
Every attack pattern is a `.eql` file under `detection/patterns/`. The
Python engines do nothing but file discovery + parameter substitution +
ES execution + result indexing.

**Alternatives considered.**

- Python rules with a DSL (Sigma-like). Rejected: requires teaching the
  DSL to analysts and re-implementing query primitives ES already has.
- A no-code rule builder. Rejected: heavy UI investment, hard to version-
  control, opaque to debugging.

**Consequence.** Anyone with Kibana access can read, edit, and contribute
detection rules. The trade-off is that some detections are awkward in
ES|QL (recursive joins, for instance); those move into derived-event
builders instead.

---

## ADR-002 — Two strict ES indices

**Context.** Forensic outputs must not pollute raw evidence.

**Decision.** Two indices: `forensics-raw` (transactions, logs, traces — never
modified) and `forensics` (decoded, derived, signal, alert, attacker,
case). Both are `dynamic: strict`; new fields require an explicit mapping
update.

**Alternatives considered.**

- Single index with a `layer` field. Rejected: makes evidence-integrity
  guarantees less obvious and risks accidental rewrites.
- Index per layer. Rejected: too many indices for a single-tenant tool;
  pattern queries that cross layers would need cross-index searches.

**Consequence.** A field rename requires a mapping migration; this is
deliberate. The strict mapping has caught at least one bug where a
builder emitted a typo'd field name.

---

## ADR-003 — Deterministic document IDs

**Context.** Pipelines that re-ingest the same data must not create
duplicates.

**Decision.** Every document `_id` is derived from `(chain_id, tx_hash,
log_index, layer/derived_type)`. Re-runs produce the same IDs and ES
performs upserts.

**Alternatives considered.** Random UUIDs + a "current run" filter.
Rejected: requires a sweeper to delete previous run data, complicates
goal G7 (offline demos).

**Consequence.** Investigations are safely replay-able. The ID scheme is
documented in **D3 §3.4** and **D5 §3.3**.

---

## ADR-004 — Local Ollama, no cloud LLM

**Context.** The copilot must work offline (goal G7).

**Decision.** Run Ollama on the analyst's machine with `gemma3:1b` by
default. Prompts forbid invented data and are fed structured JSON
context, never raw documents.

**Alternatives considered.**

- OpenAI / Anthropic API. Rejected: introduces a network dependency,
  data-handling concerns for client cases, and per-token cost.
- No copilot. Rejected: report writing dominates analyst time; even a
  small model produces credible drafts.

**Consequence.** Reports are slower than they would be with a frontier
model but completely self-contained. Operators can swap in a larger
model with one config change.

---

## ADR-005 — Python is plumbing, never policy

**Context.** Tempting to embed detection logic in Python where it would
be easier to write than in ES|QL.

**Decision.** Python in this project is restricted to: I/O,
serialisation/deserialisation, ES bulk writes, glue around the runner,
and the explicit *derived event* layer. Anything that decides "is this
suspicious?" lives in `.esql` or `.eql`.

**Consequence.** Detection coverage scales with the number of analysts
who can write ES queries, not with the number of Python engineers.

---

## ADR-006 — Mermaid + Pandoc for documentation

**Context.** Documentation must be diff-friendly, version-controllable,
and produce shareable Word documents for stakeholders.

**Decision.** Author in Markdown + Mermaid sources; render to DOCX via
Pandoc with a `reference.docx` style template; render Mermaid to PNG +
SVG via `mmdc` ahead of Pandoc.

**Alternatives considered.**

- Confluence / Notion. Rejected: not version-controllable with the code.
- LaTeX. Rejected: tooling overhead disproportionate to audience.
- Pure DOCX hand-authored. Rejected: terrible for diff review and reuse.

**Consequence.** Catalog tables are regenerated from source on every
build (`scripts/generate_catalog_tables.py`) so the reference cannot
drift from the code.
