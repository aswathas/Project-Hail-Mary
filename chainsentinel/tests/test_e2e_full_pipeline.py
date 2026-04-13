"""E2E full pipeline test: 4 simulations → ES validation."""
import pytest
from pathlib import Path
from e2e_helpers.simulator import run_all_scenarios


def test_simulator_runs_all_scenarios():
    """Verify all 4 scenarios execute without error and return valid block ranges."""
    results = run_all_scenarios()

    assert len(results) == 4
    assert "reentrancy-drain" in results
    assert "flash-loan-oracle" in results
    assert "admin-key-abuse" in results
    assert "mev-sandwich" in results

    for name, data in results.items():
        assert "block_from" in data, f"{name} missing block_from"
        assert "block_to" in data, f"{name} missing block_to"
        assert data["block_from"] < data["block_to"], (
            f"{name}: block_from ({data['block_from']}) must be < block_to ({data['block_to']})"
        )


@pytest.mark.asyncio
async def test_pipeline_ingests_all_scenarios():
    """Verify pipeline ingests all 4 scenarios into ES.

    Uses hardcoded block ranges that match the manifests written during Task 1.
    Each scenario's investigation_id is deterministic:
      reentrancy-drain  → INV-REEN-0001
      flash-loan-oracle → INV-FLAS-0101
      admin-key-abuse   → INV-ADMI-0151
      mev-sandwich      → INV-MEVS-0201
    """
    from e2e_helpers.pipeline_runner import run_all_pipelines

    sim_results = {
        "reentrancy-drain":  {"block_from": 1,   "block_to": 100},
        "flash-loan-oracle": {"block_from": 101,  "block_to": 150},
        "admin-key-abuse":   {"block_from": 151,  "block_to": 200},
        "mev-sandwich":      {"block_from": 201,  "block_to": 250},
    }

    results = await run_all_pipelines(sim_results)

    assert len(results) == 4, f"Expected 4 results, got {len(results)}"

    for scenario_name, data in results.items():
        assert data["investigation_id"].startswith("INV-"), (
            f"{scenario_name}: investigation_id must start with 'INV-', "
            f"got {data['investigation_id']!r}"
        )
        assert data["stats"]["raw_docs"] > 0, (
            f"{scenario_name}: expected raw_docs > 0, got {data['stats']['raw_docs']}"
        )


@pytest.mark.asyncio
async def test_e2e_full_pipeline():
    """
    Master E2E test:
    1. Run all 4 Foundry simulations (200+ txs)
    2. Execute ChainSentinel pipeline (collector → derived → ingest)
    3. Validate ES: counts for txs, decoded, derived, signals, alerts
    4. Repair: diagnose & fix failures if any
    """
    import asyncio
    import json
    import os
    from datetime import datetime
    from pathlib import Path
    from e2e_helpers.pipeline_runner import run_all_pipelines
    from e2e_helpers.validator import Validator
    from e2e_helpers.repair import Repair

    # Set Foundry environment variables (Anvil pre-funded accounts - MUST match Anvil's defaults)
    os.environ["DEPLOYER_KEY"] = "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"
    os.environ["USER1_KEY"] = "0x59c6995e998f97a5a0044966f0945389dc9e86dae88c7a8412f4603b6b78690d"
    os.environ["USER2_KEY"] = "0x5de4111afa1a4b94908f83103eb1f1706367c2e68ca870fc3fb9a804cdab365a"
    os.environ["USER3_KEY"] = "0x7c852118294e51e653712a81e05800f419141751be58f605c371e15141b007a6"
    os.environ["USER4_KEY"] = "0x47e179ec197488593b187f80a00eb0da91f1b9d0b13f8733639f19c30a34926a"
    os.environ["USER5_KEY"] = "0x8b3a350cf5c34c9194ca85829a2df0ec3153be0318b5e2d3348e872092edffba"
    os.environ["ATTACKER_KEY"] = "0x92db14e403b83dfe3df233f83dfa3a0d7096f21ca9b0d6d6b8d88b2b4ec1564e"
    os.environ["FRESH1_KEY"] = "0x4bbbf85ce3377467afe5d46f804f221813b2bb87f24d81f60f1fcdbf7cbf4356"
    os.environ["FRESH2_KEY"] = "0xdbda1821b80551c9d65939329250298aa3472ba22feea921c0cf5d620ea67b97"
    os.environ["FRESH3_KEY"] = "0x2a871d0798f97d79848a013d4936a73bf4cc922c825d33c1cf7073dff6d409c6"

    print("\n" + "=" * 70)
    print("E2E FULL PIPELINE TEST")
    print("=" * 70)

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
        failed_checks = {
            k: v for k, v in validation_results["checks"].items()
            if not v.get("passed")
        }
        diagnosis = repair.diagnose(failed_checks)
        print(f"  Issue: {diagnosis.get('issue')}")
        print(f"  Fix: {diagnosis.get('fix')}")
        pytest.fail(f"Validation failed (see repair suggestions above)")

    # Save results
    output_file = (
        Path("chainsentinel/e2e_results") /
        f"test-results-E2E-{datetime.now().strftime('%Y%m%d-%H%M%S')}.json"
    )
    output_file.parent.mkdir(exist_ok=True)
    with open(output_file, "w") as f:
        json.dump(
            {
                "timestamp": datetime.now().isoformat(),
                "simulations": sim_results,
                "pipeline": pipeline_results,
                "validation": validation_results,
            },
            f,
            indent=2,
            default=str,
        )

    print(f"\n✓ E2E TEST PASSED")
    print(f"  Results: {output_file}")
    print("=" * 70)
