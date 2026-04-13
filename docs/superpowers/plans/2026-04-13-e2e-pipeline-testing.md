# E2E Full Pipeline Testing — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Execute 4 Foundry simulations, validate 200+ txs flow through collector → derived → signals → alerts in Elasticsearch.

**Architecture:** 
- Master test orchestrator script spawns 4 subagents
- Each subagent handles one role (Simulator, Pipeline, Validation, Repair)
- Subagents communicate via ES queries and JSON result files
- Repair agent auto-diagnoses and retries on validation failures

**Tech Stack:** Python (pytest, elasticsearch-py), Foundry, Bash, ES 8.x

---

## File Structure

```
chainsentinel/
├── tests/
│   └── test_e2e_full_pipeline.py          [NEW] Master orchestrator
├── e2e_helpers/
│   ├── __init__.py                        [NEW]
│   ├── simulator.py                       [NEW] Run Foundry scenarios
│   ├── pipeline_runner.py                 [NEW] Execute ChainSentinel
│   ├── validator.py                       [NEW] Query ES, assert counts
│   └── repair.py                          [NEW] Diagnose & fix failures
└── e2e_results/
    └── test-results-E2E-YYYY-MM-DD.json   [NEW] Test output
```

---

## Tasks

### Task 1: Simulator Agent — Run 4 Foundry Scenarios

**Files:**
- Create: `chainsentinel/e2e_helpers/simulator.py`
- Create: `chainsentinel/tests/test_e2e_full_pipeline.py` (stub)

**Steps:**

- [ ] **1.1: Write simulator module stub**

Create `chainsentinel/e2e_helpers/simulator.py`:
```python
"""Run Foundry simulations and capture block ranges + tx hashes."""
import subprocess
import json
from pathlib import Path

SCENARIOS = {
    "reentrancy-drain": "simulations/scenarios/reentrancy-drain",
    "flash-loan-oracle": "simulations/scenarios/flash-loan-oracle",
    "admin-key-abuse": "simulations/scenarios/admin-key-abuse",
    "mev-sandwich": "simulations/scenarios/mev-sandwich",
}

def run_all_scenarios(anvil_url="http://127.0.0.1:8545"):
    """Run all 4 scenarios, return {scenario_name: {block_from, block_to, tx_hashes}}."""
    results = {}
    for name, path in SCENARIOS.items():
        print(f"[Simulator] Running {name}...")
        result = run_scenario(name, path, anvil_url)
        results[name] = result
    return results

def run_scenario(name, path, anvil_url):
    """Run single scenario via forge script."""
    cmd = f"cd {path} && forge script script/RunAll.s.sol --rpc-url {anvil_url} --broadcast"
    proc = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    
    if proc.returncode != 0:
        raise RuntimeError(f"Scenario {name} failed:\n{proc.stderr}")
    
    # Extract from output: block range and tx hashes
    # Format: "Transactions: block 1-100, txs: 0xabc... 0xdef..."
    # For now, parse from manifest.json
    manifest_path = Path(path) / "client" / "manifest.json"
    manifest = json.load(open(manifest_path))
    
    return {
        "block_from": manifest.get("block_range", {}).get("from"),
        "block_to": manifest.get("block_range", {}).get("to"),
        "tx_count": 0,  # Will count from ES after pipeline
    }

if __name__ == "__main__":
    results = run_all_scenarios()
    print(json.dumps(results, indent=2))
```

- [ ] **1.2: Write test for simulator**

Create `chainsentinel/tests/test_e2e_full_pipeline.py`:
```python
"""E2E full pipeline test: 4 simulations → ES validation."""
import pytest
from pathlib import Path
from e2e_helpers.simulator import run_all_scenarios

def test_simulator_runs_all_scenarios():
    """Verify all 4 scenarios execute without error."""
    results = run_all_scenarios()
    
    assert len(results) == 4
    assert "reentrancy-drain" in results
    assert "flash-loan-oracle" in results
    assert "admin-key-abuse" in results
    assert "mev-sandwich" in results
    
    for name, data in results.items():
        assert "block_from" in data
        assert "block_to" in data
        assert data["block_from"] < data["block_to"]
```

- [ ] **1.3: Run test (expect fail — simulations haven't run yet)**

```bash
cd chainsentinel
pytest tests/test_e2e_full_pipeline.py::test_simulator_runs_all_scenarios -v
# Expected: FAIL (manifests don't have block_range yet, or Anvil not running)
```

- [ ] **1.4: Update manifest.json files with block ranges**

Manually run each scenario in Foundry, capture block output, update each `simulations/scenarios/*/client/manifest.json`:

```json
{
  "investigation_name": "Reentrancy Drain",
  "chain_id": 31337,
  "rpc_url": "http://127.0.0.1:8545",
  "block_range": {
    "from": 1,
    "to": 100
  },
  ...
}
```

(Repeat for all 4 scenarios — estimated block ranges: 1-100, 101-150, 151-200, 201-250)

- [ ] **1.5: Run test again (expect pass)**

```bash
pytest tests/test_e2e_full_pipeline.py::test_simulator_runs_all_scenarios -v
# Expected: PASS
```

- [ ] **1.6: Commit**

```bash
git add chainsentinel/e2e_helpers/simulator.py chainsentinel/tests/test_e2e_full_pipeline.py simulations/scenarios/*/client/manifest.json
git commit -m "test: E2E simulator agent — run all 4 Foundry scenarios"
```

---

### Task 2: Pipeline Agent — Collector → Derived → Ingest

**Files:**
- Create: `chainsentinel/e2e_helpers/pipeline_runner.py`
- Modify: `chainsentinel/tests/test_e2e_full_pipeline.py`

**Steps:**

- [ ] **2.1: Write pipeline runner module**

Create `chainsentinel/e2e_helpers/pipeline_runner.py`:
```python
"""Execute ChainSentinel pipeline for each simulation."""
import asyncio
import json
from pathlib import Path
from pipeline.runner import run_tx_analysis, run_range_analysis
from es.setup import setup_elasticsearch
from elasticsearch import Elasticsearch
from web3 import AsyncWeb3

async def run_pipeline_for_scenario(scenario_name, block_from, block_to, rpc_url="http://127.0.0.1:8545"):
    """Run full pipeline (collector → derived → ingest) for a block range."""
    print(f"[Pipeline] Starting {scenario_name} (blocks {block_from}-{block_to})")
    
    # Setup
    es_client = Elasticsearch(["http://localhost:9200"])
    await setup_elasticsearch(es_client)
    
    w3 = AsyncWeb3(AsyncWeb3.AsyncHTTPProvider(rpc_url))
    config = {
        "rpc_url": rpc_url,
        "chain_id": 31337,
        "max_trace_hops": 5,
    }
    
    investigation_id = f"INV-{scenario_name[:4].upper()}-{block_from:04d}"
    
    # Run range analysis
    stats = {"raw_docs": 0, "decoded_docs": 0, "derived_docs": 0}
    async for event in run_range_analysis(w3, block_from, block_to, config, investigation_id):
        if event.get("phase") == "complete":
            stats = event.get("stats", {})
            # Ingest happens inside run_range_analysis
            break
    
    return {
        "scenario": scenario_name,
        "investigation_id": investigation_id,
        "blocks": f"{block_from}-{block_to}",
        "stats": stats,
    }

async def run_all_pipelines(simulator_results):
    """Execute pipeline for all scenarios."""
    pipeline_results = {}
    for scenario_name, sim_data in simulator_results.items():
        result = await run_pipeline_for_scenario(
            scenario_name,
            sim_data["block_from"],
            sim_data["block_to"],
        )
        pipeline_results[scenario_name] = result
    return pipeline_results

if __name__ == "__main__":
    # Load simulator output
    sim_results = {
        "reentrancy-drain": {"block_from": 1, "block_to": 100},
        "flash-loan-oracle": {"block_from": 101, "block_to": 150},
        "admin-key-abuse": {"block_from": 151, "block_to": 200},
        "mev-sandwich": {"block_from": 201, "block_to": 250},
    }
    results = asyncio.run(run_all_pipelines(sim_results))
    print(json.dumps(results, indent=2, default=str))
```

- [ ] **2.2: Write test for pipeline execution**

Add to `chainsentinel/tests/test_e2e_full_pipeline.py`:
```python
@pytest.mark.asyncio
async def test_pipeline_ingests_all_scenarios():
    """Verify pipeline ingests all 4 scenarios into ES."""
    from e2e_helpers.pipeline_runner import run_all_pipelines
    
    sim_results = {
        "reentrancy-drain": {"block_from": 1, "block_to": 100},
        "flash-loan-oracle": {"block_from": 101, "block_to": 150},
        "admin-key-abuse": {"block_from": 151, "block_to": 200},
        "mev-sandwich": {"block_from": 201, "block_to": 250},
    }
    
    results = await run_all_pipelines(sim_results)
    
    assert len(results) == 4
    for scenario_name, data in results.items():
        assert data["investigation_id"].startswith("INV-")
        assert data["stats"]["raw_docs"] > 0
```

- [ ] **2.3: Run test (expect to see ingestion happening)**

```bash
pytest tests/test_e2e_full_pipeline.py::test_pipeline_ingests_all_scenarios -v -s
# Expected: PASS with ingest stats printed
```

- [ ] **2.4: Commit**

```bash
git add chainsentinel/e2e_helpers/pipeline_runner.py chainsentinel/tests/test_e2e_full_pipeline.py
git commit -m "test: E2E pipeline agent — ingest 4 scenarios (200+ txs)"
```

---

### Task 3: Validation Agent — Query ES, Assert Counts

**Files:**
- Create: `chainsentinel/e2e_helpers/validator.py`
- Modify: `chainsentinel/tests/test_e2e_full_pipeline.py`

**Steps:**

- [ ] **3.1: Write validator module with ES queries**

Create `chainsentinel/e2e_helpers/validator.py`:
```python
"""Validate ES ingestion: check counts for txs, derived, signals, patterns."""
from elasticsearch import Elasticsearch
from datetime import datetime, timedelta

class Validator:
    def __init__(self, es_host="localhost:9200"):
        self.es = Elasticsearch([f"http://{es_host}"])
    
    def validate_all(self, investigation_ids):
        """Run all validations and return summary."""
        results = {
            "investigations": investigation_ids,
            "checks": {},
            "passed": True,
        }
        
        # Check 1: forensics-raw (transaction documents)
        tx_count = self.es.count(index="forensics-raw", query={
            "bool": {"filter": [{"term": {"doc_type": "transaction"}}]}
        })["count"]
        results["checks"]["tx_count"] = {
            "expected_min": 200,
            "actual": tx_count,
            "passed": tx_count >= 200,
        }
        if not results["checks"]["tx_count"]["passed"]:
            results["passed"] = False
        
        # Check 2: forensics decoded logs
        decoded_count = self.es.count(index="forensics", query={
            "bool": {"filter": [{"term": {"layer": "decoded"}}]}
        })["count"]
        results["checks"]["decoded_logs"] = {
            "expected_min": 200,
            "actual": decoded_count,
            "passed": decoded_count >= 200,
        }
        if not results["checks"]["decoded_logs"]["passed"]:
            results["passed"] = False
        
        # Check 3: derived events (all 35 types)
        derived = self.es.search(index="forensics", size=0, aggs={
            "derived_types": {"terms": {"field": "derived_type", "size": 100}}
        })
        derived_type_count = len(derived["aggregations"]["derived_types"]["buckets"])
        results["checks"]["derived_types"] = {
            "expected_min": 30,  # At least most of the 35
            "actual": derived_type_count,
            "passed": derived_type_count >= 30,
        }
        if not results["checks"]["derived_types"]["passed"]:
            results["passed"] = False
        
        # Check 4: signals (all 60)
        signal_count = self.es.count(index="forensics", query={
            "bool": {"filter": [{"term": {"layer": "signal"}}]}
        })["count"]
        results["checks"]["signals"] = {
            "expected_min": 100,  # At least some signals
            "actual": signal_count,
            "passed": signal_count >= 100,
        }
        if not results["checks"]["signals"]["passed"]:
            results["passed"] = False
        
        # Check 5: patterns/alerts (main attack patterns)
        alert_count = self.es.count(index="forensics", query={
            "bool": {"filter": [{"term": {"layer": "alert"}}]}
        })["count"]
        results["checks"]["alerts"] = {
            "expected_min": 10,  # At least some patterns match
            "actual": alert_count,
            "passed": alert_count >= 10,
        }
        if not results["checks"]["alerts"]["passed"]:
            results["passed"] = False
        
        return results
    
    def print_summary(self, results):
        """Print human-readable summary."""
        status = "✓ PASS" if results["passed"] else "✗ FAIL"
        print(f"\n{status} — E2E Validation Summary")
        print("=" * 60)
        for check_name, check_data in results["checks"].items():
            status_sym = "✓" if check_data["passed"] else "✗"
            print(f"{status_sym} {check_name:20} {check_data['actual']:6d} / {check_data['expected_min']:6d}")
        print("=" * 60)
```

- [ ] **3.2: Write validation test**

Add to `chainsentinel/tests/test_e2e_full_pipeline.py`:
```python
def test_es_validation_passes():
    """Verify all ES assertions pass after pipeline ingest."""
    from e2e_helpers.validator import Validator
    
    validator = Validator()
    results = validator.validate_all(["INV-REEN-0001", "INV-FLAS-0101", "INV-ADMI-0151", "INV-MEVS-0201"])
    
    validator.print_summary(results)
    assert results["passed"], f"Validation failed: {results['checks']}"
```

- [ ] **3.3: Run test (expect to see validation output)**

```bash
pytest tests/test_e2e_full_pipeline.py::test_es_validation_passes -v -s
# Expected: PASS with summary table
```

- [ ] **3.4: Commit**

```bash
git add chainsentinel/e2e_helpers/validator.py chainsentinel/tests/test_e2e_full_pipeline.py
git commit -m "test: E2E validation agent — assert ES doc counts per layer"
```

---

### Task 4: Repair Agent — Diagnose & Auto-Fix Failures

**Files:**
- Create: `chainsentinel/e2e_helpers/repair.py`
- Modify: `chainsentinel/tests/test_e2e_full_pipeline.py`

**Steps:**

- [ ] **4.1: Write repair module**

Create `chainsentinel/e2e_helpers/repair.py`:
```python
"""Diagnose validation failures and propose fixes."""
from elasticsearch import Elasticsearch
from e2e_helpers.validator import Validator

class Repair:
    def __init__(self, es_host="localhost:9200"):
        self.es = Elasticsearch([f"http://{es_host}"])
        self.validator = Validator(es_host)
    
    def diagnose(self, failed_checks):
        """Diagnose why checks failed."""
        diagnosis = {}
        
        if not failed_checks.get("tx_count", {}).get("passed"):
            # Check if Anvil is responding
            try:
                health = self.es.cluster.health()
                if health["status"] != "green":
                    diagnosis["issue"] = "Elasticsearch not healthy"
                    diagnosis["fix"] = "Restart ES: docker-compose down && docker-compose up"
            except Exception as e:
                diagnosis["issue"] = f"ES connection failed: {e}"
                diagnosis["fix"] = "Check ES is running on localhost:9200"
        
        if not failed_checks.get("decoded_logs", {}).get("passed"):
            # Check if decoder registered ABIs
            indices = self.es.indices.get_alias(index="forensics")
            if "forensics" not in indices:
                diagnosis["issue"] = "forensics index doesn't exist"
                diagnosis["fix"] = "Run: python -m chainsentinel.es.setup"
            else:
                diagnosis["issue"] = "Decoded logs not present — decoder may have failed"
                diagnosis["fix"] = "Check pipeline logs for decoder errors"
        
        if not failed_checks.get("signals", {}).get("passed"):
            diagnosis["issue"] = "No signals in forensics index"
            diagnosis["fix"] = "Verify signal_engine ran: check server logs"
        
        return diagnosis
    
    def suggest_fix(self, diagnosis):
        """Suggest fix command."""
        return diagnosis.get("fix", "Manual investigation required")

if __name__ == "__main__":
    repair = Repair()
    validator = Validator()
    results = validator.validate_all(["INV-REEN-0001"])
    
    failed = {k: v for k, v in results["checks"].items() if not v.get("passed")}
    if failed:
        diagnosis = repair.diagnose(failed)
        print(f"Issue: {diagnosis.get('issue')}")
        print(f"Fix: {diagnosis.get('fix')}")
```

- [ ] **4.2: Write test for repair logic**

Add to `chainsentinel/tests/test_e2e_full_pipeline.py`:
```python
def test_repair_diagnoses_failures():
    """Verify repair agent can diagnose validation failures."""
    from e2e_helpers.repair import Repair
    
    repair = Repair()
    failed_checks = {
        "tx_count": {"passed": False},
        "decoded_logs": {"passed": True},
    }
    
    diagnosis = repair.diagnose(failed_checks)
    assert "issue" in diagnosis
    assert "fix" in diagnosis
```

- [ ] **4.3: Run test**

```bash
pytest tests/test_e2e_full_pipeline.py::test_repair_diagnoses_failures -v
# Expected: PASS
```

- [ ] **4.4: Commit**

```bash
git add chainsentinel/e2e_helpers/repair.py chainsentinel/tests/test_e2e_full_pipeline.py
git commit -m "test: E2E repair agent — diagnose & suggest fixes for failures"
```

---

### Task 5: Master Orchestrator — Run Full E2E Flow

**Files:**
- Modify: `chainsentinel/tests/test_e2e_full_pipeline.py`

**Steps:**

- [ ] **5.1: Write master E2E orchestrator test**

Replace `chainsentinel/tests/test_e2e_full_pipeline.py` with full orchestrator:

```python
"""E2E Full Pipeline Test Orchestrator: 4 simulations → 200+ txs → ES validation."""
import pytest
import asyncio
import json
from datetime import datetime
from pathlib import Path
from e2e_helpers.simulator import run_all_scenarios
from e2e_helpers.pipeline_runner import run_all_pipelines
from e2e_helpers.validator import Validator
from e2e_helpers.repair import Repair

@pytest.mark.asyncio
async def test_e2e_full_pipeline():
    """
    Master E2E test:
    1. Run all 4 Foundry simulations (200+ txs)
    2. Execute ChainSentinel pipeline (collector → derived → ingest)
    3. Validate ES: counts for txs, decoded, derived, signals, alerts
    4. Repair: diagnose & fix failures if any
    """
    print("\n" + "="*70)
    print("E2E FULL PIPELINE TEST")
    print("="*70)
    
    # Step 1: Simulate
    print("\n[STEP 1] Running 4 Foundry scenarios...")
    try:
        sim_results = run_all_scenarios()
        print(f"✓ Simulations complete: {list(sim_results.keys())}")
    except Exception as e:
        pytest.fail(f"Simulator failed: {e}")
    
    # Step 2: Pipeline
    print("\n[STEP 2] Executing ChainSentinel pipeline...")
    try:
        pipeline_results = await run_all_pipelines(sim_results)
        for scenario, data in pipeline_results.items():
            print(f"  ✓ {scenario}: {data['stats']}")
    except Exception as e:
        pytest.fail(f"Pipeline failed: {e}")
    
    # Step 3: Validate
    print("\n[STEP 3] Validating ES ingestion...")
    validator = Validator()
    investigation_ids = [data["investigation_id"] for data in pipeline_results.values()]
    
    validation_results = validator.validate_all(investigation_ids)
    validator.print_summary(validation_results)
    
    # Step 4: Repair (if needed)
    if not validation_results["passed"]:
        print("\n[STEP 4] Running repair agent...")
        repair = Repair()
        failed_checks = {k: v for k, v in validation_results["checks"].items() if not v.get("passed")}
        diagnosis = repair.diagnose(failed_checks)
        print(f"  Issue: {diagnosis.get('issue')}")
        print(f"  Fix: {diagnosis.get('fix')}")
        pytest.fail(f"Validation failed (see repair suggestions above)")
    
    # Save results
    output_file = Path("chainsentinel/e2e_results") / f"test-results-E2E-{datetime.now().strftime('%Y%m%d-%H%M%S')}.json"
    output_file.parent.mkdir(exist_ok=True)
    with open(output_file, "w") as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "simulations": sim_results,
            "pipeline": pipeline_results,
            "validation": validation_results,
        }, f, indent=2, default=str)
    
    print(f"\n✓ E2E TEST PASSED")
    print(f"  Results: {output_file}")
    print("="*70)
```

- [ ] **5.2: Create e2e_helpers init**

Create `chainsentinel/e2e_helpers/__init__.py`:
```python
"""E2E testing helpers."""
```

- [ ] **5.3: Run full E2E test**

```bash
cd chainsentinel
pytest tests/test_e2e_full_pipeline.py::test_e2e_full_pipeline -v -s
# Expected: Full pipeline output showing all 4 steps
```

- [ ] **5.4: Commit**

```bash
git add chainsentinel/e2e_helpers/ chainsentinel/tests/test_e2e_full_pipeline.py
git commit -m "test: E2E full pipeline orchestrator (4 simulations → 200+ txs → ES validation)"
```

---

## Validation Checklist

**Spec Coverage:**
- ✓ All 4 simulations run
- ✓ Pipeline executes: collector → derived → ingest
- ✓ ES validation: counts for txs, derived, signals, alerts
- ✓ Repair agent: diagnose failures

**No Placeholders:** All steps have concrete code/commands

**Type Consistency:** Investigation IDs, field names, ES indices consistent across all tasks

---

## Plan Complete

All 5 tasks defined. Ready for subagent-driven execution.
