import pytest
from pathlib import Path


SIGNALS_DIR = Path(__file__).parent.parent / "detection" / "signals"
PATTERNS_DIR = Path(__file__).parent.parent / "detection" / "patterns"


def test_all_value_signals_have_required_headers():
    """Every .esql in value/ must have signal, severity, score, description headers."""
    value_dir = SIGNALS_DIR / "value"
    for esql_file in value_dir.glob("*.esql"):
        content = esql_file.read_text()
        assert "-- signal:" in content, f"{esql_file.name} missing signal header"
        assert "-- severity:" in content, f"{esql_file.name} missing severity header"
        assert "-- score:" in content, f"{esql_file.name} missing score header"
        assert "-- description:" in content, f"{esql_file.name} missing description header"
        assert "FROM forensics" in content, f"{esql_file.name} missing FROM forensics"


def test_all_value_signals_exist():
    value_dir = SIGNALS_DIR / "value"
    expected = ["large_outflow", "large_token_transfer", "max_approval", "value_spike"]
    for name in expected:
        assert (value_dir / f"{name}.esql").exists(), f"Missing {name}.esql"


def test_signal_files_are_valid_esql():
    """Basic syntax check: every signal must start with comments then FROM forensics."""
    for esql_file in SIGNALS_DIR.rglob("*.esql"):
        content = esql_file.read_text()
        # Strip comment lines, first non-comment line should start with FROM
        lines = [l.strip() for l in content.splitlines() if l.strip() and not l.strip().startswith("--")]
        assert len(lines) > 0, f"{esql_file.name} is empty after removing comments"
        assert lines[0].startswith("FROM "), f"{esql_file.name} first query line must start with FROM"


def test_all_flash_loan_signals_exist():
    flash_dir = SIGNALS_DIR / "flash_loan"
    expected = ["flash_loan_detected", "flash_loan_with_drain"]
    for name in expected:
        assert (flash_dir / f"{name}.esql").exists(), f"Missing {name}.esql"


def test_all_flash_loan_signals_have_headers():
    flash_dir = SIGNALS_DIR / "flash_loan"
    for esql_file in flash_dir.glob("*.esql"):
        content = esql_file.read_text()
        assert "-- signal:" in content, f"{esql_file.name} missing signal header"
        assert "FROM forensics" in content, f"{esql_file.name} missing FROM forensics"


def test_all_access_signals_exist():
    access_dir = SIGNALS_DIR / "access"
    expected = ["ownership_transferred", "role_granted", "proxy_upgraded"]
    for name in expected:
        assert (access_dir / f"{name}.esql").exists(), f"Missing {name}.esql"


def test_all_structural_signals_exist():
    struct_dir = SIGNALS_DIR / "structural"
    expected = ["reentrancy_pattern", "call_depth_anomaly", "repeated_external_call", "internal_eth_drain"]
    for name in expected:
        assert (struct_dir / f"{name}.esql").exists(), f"Missing {name}.esql"


def test_all_deployment_signals_exist():
    deploy_dir = SIGNALS_DIR / "deployment"
    expected = ["new_contract_deployed", "failed_high_gas"]
    for name in expected:
        assert (deploy_dir / f"{name}.esql").exists(), f"Missing {name}.esql"


def test_all_liquidity_signals_exist():
    liq_dir = SIGNALS_DIR / "liquidity"
    expected = ["large_liquidity_removal"]
    for name in expected:
        assert (liq_dir / f"{name}.esql").exists(), f"Missing {name}.esql"


def test_all_defi_signals_exist():
    defi_dir = SIGNALS_DIR / "defi"
    expected = ["vault_first_deposit_tiny", "liquidation_event"]
    for name in expected:
        assert (defi_dir / f"{name}.esql").exists(), f"Missing {name}.esql"


def test_all_behavioural_signals_exist():
    behav_dir = SIGNALS_DIR / "behavioural"
    expected = ["new_wallet_high_value", "burst_transactions"]
    for name in expected:
        assert (behav_dir / f"{name}.esql").exists(), f"Missing {name}.esql"


def test_wave1_total_signal_count():
    """Wave 1 should have exactly 20 signals."""
    count = len(list(SIGNALS_DIR.rglob("*.esql")))
    assert count == 20, f"Expected 20 Wave 1 signals, found {count}"


def test_wave1_patterns_exist():
    expected = [
        "AP-001_flash_loan_oracle",
        "AP-005_reentrancy_drain",
        "AP-008_access_control_abuse",
        "AP-014_mev_sandwich",
    ]
    for name in expected:
        assert (PATTERNS_DIR / f"{name}.eql").exists(), f"Missing {name}.eql"


def test_wave1_pattern_count():
    count = len(list(PATTERNS_DIR.glob("*.eql")))
    assert count == 4, f"Expected 4 Wave 1 patterns, found {count}"


def test_all_patterns_have_required_headers():
    for eql_file in PATTERNS_DIR.glob("*.eql"):
        content = eql_file.read_text()
        assert "pattern:" in content, f"{eql_file.name} missing pattern header"
        assert "confidence:" in content, f"{eql_file.name} missing confidence header"
        assert "required_signals:" in content, f"{eql_file.name} missing required_signals"
        assert "sequence" in content, f"{eql_file.name} missing sequence keyword"


def test_all_patterns_have_valid_id_in_filename():
    import re
    for eql_file in PATTERNS_DIR.glob("*.eql"):
        assert re.match(r"AP-\d{3}_", eql_file.stem), f"{eql_file.name} doesn't match AP-NNN_ format"
