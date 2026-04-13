import pytest


def test_label_known_tornado_cash_address():
    from correlation.label_db import get_label

    label = get_label("0xd90e2f925da726b50c4ed8d0fb90ad053324f31b")
    assert label["type"] == "mixer_contract"
    assert "tornado" in label["name"].lower()


def test_label_known_cex_address():
    from correlation.label_db import get_label

    # Binance hot wallet
    label = get_label("0x28c6c06298d514db089934071355e5743bf21d60")
    assert label["type"] == "cex_deposit"
    assert "binance" in label["name"].lower()


def test_label_unknown_address():
    from correlation.label_db import get_label

    label = get_label("0x0000000000000000000000000000000000000001")
    assert label["type"] == "unknown"
    assert label["name"] == "Unknown"


def test_label_case_insensitive():
    from correlation.label_db import get_label

    label_lower = get_label("0xd90e2f925da726b50c4ed8d0fb90ad053324f31b")
    label_upper = get_label("0xD90e2f925DA726b50C4Ed8D0Fb90AD053324f31b")
    assert label_lower["type"] == label_upper["type"]


def test_is_ofac_sanctioned_true():
    from correlation.label_db import is_ofac_sanctioned

    # Tornado Cash Router
    assert is_ofac_sanctioned("0xd90e2f925da726b50c4ed8d0fb90ad053324f31b") is True


def test_is_ofac_sanctioned_false():
    from correlation.label_db import is_ofac_sanctioned

    assert is_ofac_sanctioned("0x0000000000000000000000000000000000000001") is False


def test_is_mixer_true():
    from correlation.label_db import is_mixer

    assert is_mixer("0xd90e2f925da726b50c4ed8d0fb90ad053324f31b") is True


def test_is_mixer_false():
    from correlation.label_db import is_mixer

    assert is_mixer("0x28c6c06298d514db089934071355e5743bf21d60") is False


def test_is_bridge_true():
    from correlation.label_db import is_bridge

    # Hop Protocol bridge
    assert is_bridge("0xb8901acb165ed027e32754e0ffe830802919727f") is True


def test_is_cex_true():
    from correlation.label_db import is_cex

    assert is_cex("0x28c6c06298d514db089934071355e5743bf21d60") is True


def test_get_all_labels_for_address():
    from correlation.label_db import get_all_labels

    labels = get_all_labels("0xd90e2f925da726b50c4ed8d0fb90ad053324f31b")
    assert "mixer_contract" in labels
    assert "ofac_sanctioned" in labels


def test_get_all_labels_unknown():
    from correlation.label_db import get_all_labels

    labels = get_all_labels("0x0000000000000000000000000000000000000001")
    assert labels == ["unknown"]


def test_batch_label_multiple_addresses():
    from correlation.label_db import batch_label

    addresses = [
        "0xd90e2f925da726b50c4ed8d0fb90ad053324f31b",
        "0x28c6c06298d514db089934071355e5743bf21d60",
        "0x0000000000000000000000000000000000000001",
    ]
    results = batch_label(addresses)

    assert len(results) == 3
    assert results["0xd90e2f925da726b50c4ed8d0fb90ad053324f31b"]["type"] == "mixer_contract"
    assert results["0x28c6c06298d514db089934071355e5743bf21d60"]["type"] == "cex_deposit"
    assert results["0x0000000000000000000000000000000000000001"]["type"] == "unknown"
