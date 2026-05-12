---
title: "ChainSentinel — Detection Reference"
subtitle: "Document D4 of the ChainSentinel Manual"
author: "ChainSentinel Engineering"
date: "2026-05-12"
version: "1.0"
---

# About this document

This is the **catalog reference** for ChainSentinel's detection layer.
It is intentionally long. The first 60 entries describe every signal;
the next 38 describe every attack pattern; the remaining sections cover
derived events, ABIs, ES mappings, and the scoring model.

Every signal-, pattern-, and derived-event row in this document is
**generated from the source tree** by
`docs/manual/scripts/generate_catalog_tables.py`. Regenerate the catalog
tables before building this document:

```bash
make catalogs    # writes src/_generated/*.md
make d4          # builds ChainSentinel-D4-Detection-Reference.docx
```

Companion documents:

- **D3 Architecture & Design** — the model these catalogs implement.
- **D5 Developer Guide** — how to add new signals / patterns / builders.
- **D7 Simulation Guide** — scenarios that exercise these detections end-to-end.
