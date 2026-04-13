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
