# E2E Full Pipeline Testing — ChainSentinel

**Date:** 2026-04-13  
**Status:** APPROVED  
**Goal:** Validate collector → derived → signal → pattern flow across 4 simulations (200+ txs)

---

## Test Flow

1. **Simulator**: Run all 4 Foundry scenarios sequentially
   - reentrancy-drain, flash-loan-oracle, admin-key-abuse, mev-sandwich
   - Capture: block ranges, tx hashes, deployer contracts
   - Output: investigation manifests

2. **Pipeline**: For each scenario, run ChainSentinel pipeline
   - Collector → Normalizer → Decoder → Derived (35 types) → Ingest
   - Track stats: tx count, log count, derived count

3. **Validation**: Query ES after ingestion completes
   - forensics-raw: 200 tx documents
   - forensics (layer=decoded): 200+ log documents  
   - forensics (layer=derived): 2000+ derived events (all 35 types represented)
   - forensics (layer=signal): 300+ signal documents (all 60 signals represented)
   - forensics (layer=alert): 80+ pattern matches (main attack patterns)

4. **Repair**: If validation fails, diagnose and retry

---

## Success Criteria

- All 200 txs ingested to forensics-raw
- All derived types fire (≥1 doc each)
- All signal families produce output
- All attack pattern families have matches
- E2E time: <5 min wall-clock

---

## Deliverables

- `test_e2e_full_pipeline.py` - orchestration script
- `test-results-E2E-YYYY-MM-DD.json` - metrics
- Console summary report (pass/fail per component/scenario)

---

## Subagents

1. **Simulator Agent** - Run Foundry scripts
2. **Pipeline Agent** - Execute ChainSentinel pipeline  
3. **Validation Agent** - Query ES, assert counts, generate report
4. **Repair Agent** - Diagnose & fix failures

Tools: Bash (execute), Elasticsearch/Kibana APIs (query), Read/Write (logs)
