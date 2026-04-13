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
