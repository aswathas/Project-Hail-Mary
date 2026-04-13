"""
Mixer Detection — identifies interactions with mixers, bridges, and CEX deposits.

Classifies destination addresses and computes taint haircut scores
for fund tracing through obfuscation layers.

Haircut values (from spec):
  - Mixer (Tornado Cash): taint * 0.7
  - Bridge: taint * 0.8
  - CEX: taint * 0.9
  - Unknown/direct: taint * 1.0 (no reduction)
  - Taint never reaches zero (minimum 0.01)
"""
from correlation.label_db import (
    get_label, is_mixer, is_bridge, is_cex, is_ofac_sanctioned,
)


# Haircut multipliers per category
TAINT_HAIRCUTS = {
    "mixer": 0.7,
    "bridge": 0.8,
    "cex": 0.9,
    "unknown": 1.0,
    "known_exploiter": 1.0,
    "protocol_treasury": 1.0,
}

RISK_LEVELS = {
    "mixer": "critical",
    "bridge": "high",
    "cex": "medium",
    "known_exploiter": "critical",
    "protocol_treasury": "low",
    "unknown": "low",
}

# Category mapping from label_db types
CATEGORY_MAP = {
    "mixer_contract": "mixer",
    "bridge_contract": "bridge",
    "cex_deposit": "cex",
    "known_exploiter": "known_exploiter",
    "protocol_treasury": "protocol_treasury",
    "unknown": "unknown",
}


def classify_address(address: str) -> dict:
    """
    Classify an address by its role in fund obfuscation.
    Returns: {category, protocol, risk_level, ofac}
    """
    label = get_label(address)
    label_type = label["type"]
    category = CATEGORY_MAP.get(label_type, "unknown")

    return {
        "address": address.lower(),
        "category": category,
        "protocol": label["name"],
        "risk_level": RISK_LEVELS.get(category, "low"),
        "ofac": is_ofac_sanctioned(address),
    }


def detect_exit_routes(
    es_client,
    wallet_address: str,
    investigation_id: str,
) -> list[dict]:
    """
    Query ES for all outgoing transfers from a wallet to known exit routes
    (mixers, bridges, CEX deposits).
    """
    query = {
        "bool": {
            "must": [
                {"term": {"investigation_id": investigation_id}},
                {"term": {"from_address": wallet_address.lower()}},
                {"term": {"layer": "derived"}},
                {"terms": {"derived_type": ["native_transfer", "asset_transfer"]}},
            ]
        }
    }

    response = es_client.search(
        index="forensics",
        query=query,
        size=1000,
        sort=[{"block_number": "asc"}],
    )

    exits = []
    for hit in response.get("hits", {}).get("hits", []):
        src = hit["_source"]
        to_addr = src.get("to_address", "")
        classification = classify_address(to_addr)

        if classification["category"] in ("mixer", "bridge", "cex"):
            exits.append({
                "to_address": to_addr,
                "category": classification["category"],
                "protocol": classification["protocol"],
                "risk_level": classification["risk_level"],
                "ofac": classification["ofac"],
                "value_eth": src.get("value_eth", 0.0),
                "tx_hash": src.get("tx_hash"),
                "block_number": src.get("block_number"),
            })

    return exits


def compute_taint_haircut(
    current_taint: float,
    category: str,
    min_taint: float = 0.01,
) -> float:
    """
    Apply haircut to taint score based on the category of address
    the funds passed through. Taint never reaches zero.
    """
    multiplier = TAINT_HAIRCUTS.get(category, 1.0)
    new_taint = current_taint * multiplier
    return max(new_taint, min_taint)
