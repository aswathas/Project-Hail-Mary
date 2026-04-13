"""
Label Database — known address classification.

Provides labels for known addresses: OFAC sanctioned entities,
known exploiter wallets, CEX hot wallets, mixer contracts,
bridge contracts, and protocol treasuries.

All addresses are stored and compared in lowercase.
"""


# -- Tornado Cash contracts (OFAC sanctioned) ---------------------------------
TORNADO_CASH = {
    "0xd90e2f925da726b50c4ed8d0fb90ad053324f31b": "Tornado Cash Router",
    "0x12d66f87a04a9e220743712ce6d9bb1b5616b8fc": "Tornado Cash 0.1 ETH",
    "0x47ce0c6ed5b0ce3d3a51fdb1c52dc66a7c3c2936": "Tornado Cash 1 ETH",
    "0x910cbd523d972eb0a6f4cae4618ad62622b39dbf": "Tornado Cash 10 ETH",
    "0xa160cdab225685da1d56aa342ad8841c3b53f291": "Tornado Cash 100 ETH",
    "0xd4b88df4d29f5cedd6857912842cff3b20c8cfa3": "Tornado Cash 100 DAI",
    "0xfd8610d20aa15b7b2e3be39b396a1bc3516c7144": "Tornado Cash 1000 DAI",
    "0x07687e702b410fa43f4cb4af7fa097918ffd2730": "Tornado Cash 10000 DAI",
    "0x94a1b5cdb22c43faab4abeb5c74999895464bdaf": "Tornado Cash Governance",
    "0x722122df12d4e14e13ac3b6895a86e84145b6967": "Tornado Cash Proxy",
}

# -- Bridge contracts ----------------------------------------------------------
BRIDGES = {
    "0xb8901acb165ed027e32754e0ffe830802919727f": "Hop Protocol Bridge",
    "0x3ee18b2214aff97000d974cf647e7c347e8fa585": "Wormhole Token Bridge",
    "0x3014ca10b91cb3d0ad85fef7a3cb95bcac9c0f79": "LayerZero Endpoint",
    "0x4d73adb72bc3dd368966edd0f0b2148401a178e2": "Across Protocol Bridge",
    "0x8731d54e9d02c286767d56ac03e8037c07e01e98": "Stargate Finance Router",
    "0x99c9fc46f92e8a1c0dec1b1747d010903e884be1": "Optimism Gateway",
    "0x3307d64cf6deab3b02e1f36fd0bfce6cba76f11c": "Arbitrum Gateway",
    "0xa0c68c638235ee32657e8f720a23cec1bfc6c4d4": "Polygon Bridge",
}

# -- CEX hot wallets -----------------------------------------------------------
CEX_WALLETS = {
    "0x28c6c06298d514db089934071355e5743bf21d60": "Binance Hot Wallet 14",
    "0x21a31ee1afc51d94c2efccaa2092ad1028285549": "Binance Hot Wallet 15",
    "0xdfd5293d8e347dfe59e90efd55b2956a1343963d": "Binance Hot Wallet 16",
    "0x56eddb7aa87536c09ccc2793473599fd21a8b17f": "Binance Hot Wallet 17",
    "0xa9d1e08c7793af67e9d92fe308d5697fb81d3e43": "Coinbase Hot Wallet 10",
    "0x71660c4005ba85c37ccec55d0c4493e66fe775d3": "Coinbase Hot Wallet 11",
    "0x503828976d22510aad0201ac7ec88293211d23da": "Coinbase Hot Wallet 12",
    "0x6cc5f688a315f3dc28a7781717a9a798a59fda7b": "OKX Hot Wallet",
    "0x98ec059dc3adfbdd63429227d09cb52bc0a7586d": "Kraken Hot Wallet 13",
    "0x267be1c1d684f78cb4f6a176c4911b741e4ffdc0": "Kraken Hot Wallet 14",
    "0xf89d7b9c864f589bbf53a82105107622b35eaa40": "Bybit Hot Wallet",
}

# -- Known exploiter wallets ---------------------------------------------------
KNOWN_EXPLOITERS = {
    "0xb624c4aecfad7eb036c29f22cc3c7e5400b4470e": "Ronin Bridge Exploiter",
    "0x098b716b8aaf21512996dc57eb0615e2383e2f96": "Wormhole Exploiter",
    "0x0248f752802b2cfb4373cc0c3bc3964429385c26": "Nomad Bridge Exploiter",
}

# -- Protocol treasuries / known safe ------------------------------------------
PROTOCOL_TREASURIES = {
    "0x40ec5b33f54e0e8a33a975908c5ba1c14e5bbbdf": "Polygon Treasury",
    "0xbe8e3e3618f7474f8cb1d074a26affef007e98fb": "Lido DAO Treasury",
}


# -- Build unified lookup (all lowercase) --------------------------------------
_LABEL_DB: dict[str, dict] = {}


def _init_db():
    global _LABEL_DB
    if _LABEL_DB:
        return

    for addr, name in TORNADO_CASH.items():
        _LABEL_DB[addr.lower()] = {
            "type": "mixer_contract",
            "name": name,
            "ofac": True,
            "tags": ["mixer_contract", "ofac_sanctioned"],
        }

    for addr, name in BRIDGES.items():
        _LABEL_DB[addr.lower()] = {
            "type": "bridge_contract",
            "name": name,
            "ofac": False,
            "tags": ["bridge_contract"],
        }

    for addr, name in CEX_WALLETS.items():
        _LABEL_DB[addr.lower()] = {
            "type": "cex_deposit",
            "name": name,
            "ofac": False,
            "tags": ["cex_deposit"],
        }

    for addr, name in KNOWN_EXPLOITERS.items():
        _LABEL_DB[addr.lower()] = {
            "type": "known_exploiter",
            "name": name,
            "ofac": True,
            "tags": ["known_exploiter", "ofac_sanctioned"],
        }

    for addr, name in PROTOCOL_TREASURIES.items():
        _LABEL_DB[addr.lower()] = {
            "type": "protocol_treasury",
            "name": name,
            "ofac": False,
            "tags": ["protocol_treasury"],
        }


def get_label(address: str) -> dict:
    """Get the primary label for an address."""
    _init_db()
    entry = _LABEL_DB.get(address.lower())
    if entry:
        return {"type": entry["type"], "name": entry["name"]}
    return {"type": "unknown", "name": "Unknown"}


def is_ofac_sanctioned(address: str) -> bool:
    """Check if address is on OFAC sanctions list."""
    _init_db()
    entry = _LABEL_DB.get(address.lower())
    return entry.get("ofac", False) if entry else False


def is_mixer(address: str) -> bool:
    """Check if address is a known mixer contract."""
    _init_db()
    entry = _LABEL_DB.get(address.lower())
    return entry.get("type") == "mixer_contract" if entry else False


def is_bridge(address: str) -> bool:
    """Check if address is a known bridge contract."""
    _init_db()
    entry = _LABEL_DB.get(address.lower())
    return entry.get("type") == "bridge_contract" if entry else False


def is_cex(address: str) -> bool:
    """Check if address is a known CEX hot wallet."""
    _init_db()
    entry = _LABEL_DB.get(address.lower())
    return entry.get("type") == "cex_deposit" if entry else False


def get_all_labels(address: str) -> list[str]:
    """Get all tags for an address."""
    _init_db()
    entry = _LABEL_DB.get(address.lower())
    if entry:
        return entry["tags"]
    return ["unknown"]


def batch_label(addresses: list[str]) -> dict[str, dict]:
    """Label multiple addresses at once."""
    return {addr: get_label(addr) for addr in addresses}
