"""Run Foundry simulations and capture block ranges + tx hashes."""
import subprocess
import json
import os
from pathlib import Path

# Repo root: chainsentinel/e2e_helpers/simulator.py → go up 3 levels
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent

SCENARIOS = {
    "reentrancy-drain":  str(_REPO_ROOT / "simulations/scenarios/reentrancy-drain"),
    "flash-loan-oracle": str(_REPO_ROOT / "simulations/scenarios/flash-loan-oracle"),
    "admin-key-abuse":   str(_REPO_ROOT / "simulations/scenarios/admin-key-abuse"),
    "mev-sandwich":      str(_REPO_ROOT / "simulations/scenarios/mev-sandwich"),
}


def run_all_scenarios(anvil_url: str = "http://127.0.0.1:8545") -> dict:
    """Run all 4 scenarios, return {scenario_name: {block_from, block_to, tx_count}}.

    Each scenario runs on the same Anvil instance (block ranges don't overlap).
    """
    results = {}
    for name, path in SCENARIOS.items():
        print(f"[Simulator] Running {name}...")
        result = run_scenario(name, path, anvil_url)
        results[name] = result
    return results


def run_scenario(name: str, path: str, anvil_url: str) -> dict:
    """Run single scenario via forge script and read block range from manifest."""
    cmd = (
        f"cd {path} && forge script script/RunAll.s.sol "
        f"--rpc-url {anvil_url} --broadcast"
    )
    # Explicitly pass environment dict (copy of os.environ)
    env = dict(os.environ)
    proc = subprocess.run(cmd, shell=True, capture_output=True, text=True, env=env)

    if proc.returncode != 0:
        raise RuntimeError(f"Scenario {name} failed:\n{proc.stderr}")

    manifest_path = Path(path) / "client" / "manifest.json"
    with open(manifest_path) as f:
        manifest = json.load(f)

    return {
        "block_from": manifest.get("block_range", {}).get("from"),
        "block_to":   manifest.get("block_range", {}).get("to"),
        "tx_count":   0,  # Will count from ES after pipeline
    }


if __name__ == "__main__":
    results = run_all_scenarios()
    print(json.dumps(results, indent=2))
