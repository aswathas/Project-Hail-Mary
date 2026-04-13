import re
import pytest
from pathlib import Path


SIGNALS_DIR = Path(__file__).parent.parent / "detection" / "signals"
PATTERNS_DIR = Path(__file__).parent.parent / "detection" / "patterns"


# ---------------------------------------------------------------------------
# Signal header checks — all families
# ---------------------------------------------------------------------------

def _check_headers(esql_file: Path):
    content = esql_file.read_text()
    assert "-- signal:" in content, f"{esql_file.name} missing signal header"
    assert "-- severity:" in content, f"{esql_file.name} missing severity header"
    assert "-- score:" in content, f"{esql_file.name} missing score header"
    assert "-- description:" in content, f"{esql_file.name} missing description header"
    assert "FROM forensics" in content, f"{esql_file.name} missing FROM forensics"


def test_all_signals_have_required_headers():
    """Every .esql file must have the standard comment headers."""
    for esql_file in SIGNALS_DIR.rglob("*.esql"):
        _check_headers(esql_file)


def test_signal_files_are_valid_esql():
    """First non-comment query line must start with FROM."""
    for esql_file in SIGNALS_DIR.rglob("*.esql"):
        content = esql_file.read_text()
        lines = [l.strip() for l in content.splitlines()
                 if l.strip() and not l.strip().startswith("--")]
        assert len(lines) > 0, f"{esql_file.name} is empty after removing comments"
        assert lines[0].startswith("FROM "), (
            f"{esql_file.name} first query line must start with FROM"
        )


# ---------------------------------------------------------------------------
# Total count
# ---------------------------------------------------------------------------

def test_total_signal_count():
    """Bible v2: 60 signals total."""
    count = len(list(SIGNALS_DIR.rglob("*.esql")))
    assert count == 60, f"Expected 60 signals, found {count}"


# ---------------------------------------------------------------------------
# Per-family existence checks
# ---------------------------------------------------------------------------

def test_structural_signals_exist():
    family = SIGNALS_DIR / "structural"
    expected = [
        "recursive_depth_pattern",
        "cross_function_reentry",
        "value_drain_per_depth",
        "storage_update_delay",
        "hook_callback_detected",
        "delegatecall_storage_write",
        "proxy_implementation_change",
        "selfdestruct_detected",
        "flashloan_bracket_detected",
        "initialize_on_live_contract",
        "create2_redeployment",
    ]
    for name in expected:
        assert (family / f"{name}.esql").exists(), f"Missing structural/{name}.esql"


def test_value_signals_exist():
    family = SIGNALS_DIR / "value"
    expected = [
        "large_value_inflow_spike",
        "drain_ratio_exceeded",
        "value_concentration",
        "value_dispersion",
        "net_negative_contract_balance",
        "mint_to_dump_ratio",
        "liquidity_removal_spike",
        "vault_share_price_spike",
        "multiple_asset_drain_same_tx",
    ]
    for name in expected:
        assert (family / f"{name}.esql").exists(), f"Missing value/{name}.esql"


def test_sequence_signals_exist():
    family = SIGNALS_DIR / "sequence"
    expected = [
        "deposit_withdraw_same_tx",
        "event_order_violation",
        "duplicate_event_emission",
        "missing_expected_event",
        "event_parameter_mismatch",
        "ownership_transfer_then_drain",
    ]
    for name in expected:
        assert (family / f"{name}.esql").exists(), f"Missing sequence/{name}.esql"


def test_behavioural_signals_exist():
    family = SIGNALS_DIR / "behavioural"
    expected = [
        "new_address_first_interaction",
        "contract_deployed_before_attack",
        "address_funded_before_attack",
        "nonce_gap_detected",
        "high_gas_anomaly",
        "failed_attempts_before_success",
        "approval_for_max_amount",
        "same_block_deploy_and_attack",
        "contract_size_anomaly",
    ]
    for name in expected:
        assert (family / f"{name}.esql").exists(), f"Missing behavioural/{name}.esql"


def test_oracle_signals_exist():
    family = SIGNALS_DIR / "oracle"
    expected = [
        "price_read_during_callback",
        "spot_price_manipulation",
        "reserve_ratio_spike",
        "twap_drift_detected",
        "multi_oracle_divergence",
        "price_before_after_mismatch",
        "donation_balance_inflation",
    ]
    for name in expected:
        assert (family / f"{name}.esql").exists(), f"Missing oracle/{name}.esql"


def test_graph_signals_exist():
    family = SIGNALS_DIR / "graph"
    expected = [
        "fund_dispersion_post_attack",
        "mixer_interaction_detected",
        "bridge_interaction_detected",
        "address_cluster_identified",
        "contract_creator_linked",
        "multi_hop_fund_trail",
    ]
    for name in expected:
        assert (family / f"{name}.esql").exists(), f"Missing graph/{name}.esql"


def test_additional_signals_exist():
    family = SIGNALS_DIR / "additional"
    expected = [
        "integer_overflow_detected",
        "liquidation_cascade_trigger",
        "eip712_replay_detected",
        "fee_on_transfer_discrepancy",
        "rebasing_balance_manipulation",
        "cross_contract_state_dependency",
        "governance_instant_execution",
        "permit_used_before_owner_approval",
    ]
    for name in expected:
        assert (family / f"{name}.esql").exists(), f"Missing additional/{name}.esql"


# ---------------------------------------------------------------------------
# Pattern checks
# ---------------------------------------------------------------------------

def test_total_pattern_count():
    """Bible v2: 38 attack patterns."""
    count = len(list(PATTERNS_DIR.glob("*.eql")))
    assert count == 38, f"Expected 38 patterns, found {count}"


def test_all_patterns_have_valid_id_in_filename():
    for eql_file in PATTERNS_DIR.glob("*.eql"):
        assert re.match(r"AP-\d{3}_", eql_file.stem), (
            f"{eql_file.name} doesn't match AP-NNN_ format"
        )


def test_all_patterns_have_required_headers():
    """Every .eql file must have pattern, confidence, and sequence keyword."""
    for eql_file in PATTERNS_DIR.glob("*.eql"):
        content = eql_file.read_text()
        assert "// pattern:" in content, f"{eql_file.name} missing pattern header"
        assert "// confidence:" in content, f"{eql_file.name} missing confidence header"
        assert "sequence" in content, f"{eql_file.name} missing sequence keyword"


def test_core_patterns_exist():
    """Spot-check a representative pattern from each family."""
    expected = [
        "AP-001_classic_reentrancy",
        "AP-005_classic_flash_loan",
        "AP-009_amm_spot_price",
        "AP-012_ownership_hijack",
        "AP-016_sandwich_attack",
        "AP-019_liquidity_rug",
        "AP-023_donation_attack",
        "AP-030_attacker_deployment",
        "AP-035_governance_manipulation",
    ]
    for name in expected:
        assert (PATTERNS_DIR / f"{name}.eql").exists(), f"Missing {name}.eql"
