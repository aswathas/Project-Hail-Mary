import pytest
from unittest.mock import MagicMock


def test_classify_address_tornado_cash():
    from correlation.mixer_detect import classify_address

    result = classify_address("0xd90e2f925da726b50c4ed8d0fb90ad053324f31b")
    assert result["category"] == "mixer"
    assert result["protocol"] == "Tornado Cash Router"
    assert result["risk_level"] == "critical"


def test_classify_address_bridge():
    from correlation.mixer_detect import classify_address

    result = classify_address("0xb8901acb165ed027e32754e0ffe830802919727f")
    assert result["category"] == "bridge"
    assert result["risk_level"] == "high"


def test_classify_address_cex():
    from correlation.mixer_detect import classify_address

    result = classify_address("0x28c6c06298d514db089934071355e5743bf21d60")
    assert result["category"] == "cex"
    assert result["risk_level"] == "medium"


def test_classify_address_unknown():
    from correlation.mixer_detect import classify_address

    result = classify_address("0x0000000000000000000000000000000000000001")
    assert result["category"] == "unknown"
    assert result["risk_level"] == "low"


def test_detect_exit_routes_finds_mixer_deposits():
    from correlation.mixer_detect import detect_exit_routes

    mock_client = MagicMock()
    mock_client.search.return_value = {
        "hits": {
            "hits": [
                {
                    "_source": {
                        "to_address": "0xd90e2f925da726b50c4ed8d0fb90ad053324f31b",
                        "from_address": "0xattacker",
                        "value_eth": 50.0,
                        "tx_hash": "0xexit1",
                        "block_number": 100,
                    }
                },
                {
                    "_source": {
                        "to_address": "0x28c6c06298d514db089934071355e5743bf21d60",
                        "from_address": "0xattacker",
                        "value_eth": 30.0,
                        "tx_hash": "0xexit2",
                        "block_number": 101,
                    }
                },
            ]
        }
    }

    exits = detect_exit_routes(mock_client, "0xattacker", "INV-001")

    assert len(exits) == 2
    mixer_exit = [e for e in exits if e["category"] == "mixer"][0]
    assert mixer_exit["value_eth"] == 50.0
    cex_exit = [e for e in exits if e["category"] == "cex"][0]
    assert cex_exit["value_eth"] == 30.0


def test_detect_exit_routes_no_results():
    from correlation.mixer_detect import detect_exit_routes

    mock_client = MagicMock()
    mock_client.search.return_value = {"hits": {"hits": []}}

    exits = detect_exit_routes(mock_client, "0xclean", "INV-001")
    assert exits == []


def test_compute_taint_haircut_mixer():
    from correlation.mixer_detect import compute_taint_haircut

    result = compute_taint_haircut(1.0, "mixer")
    assert result == pytest.approx(0.7)


def test_compute_taint_haircut_bridge():
    from correlation.mixer_detect import compute_taint_haircut

    result = compute_taint_haircut(1.0, "bridge")
    assert result == pytest.approx(0.8)


def test_compute_taint_haircut_cex():
    from correlation.mixer_detect import compute_taint_haircut

    result = compute_taint_haircut(1.0, "cex")
    assert result == pytest.approx(0.9)


def test_compute_taint_haircut_unknown():
    from correlation.mixer_detect import compute_taint_haircut

    result = compute_taint_haircut(1.0, "unknown")
    assert result == pytest.approx(1.0)


def test_taint_never_reaches_zero():
    from correlation.mixer_detect import compute_taint_haircut

    taint = 1.0
    for _ in range(100):
        taint = compute_taint_haircut(taint, "mixer")
    assert taint > 0.0
