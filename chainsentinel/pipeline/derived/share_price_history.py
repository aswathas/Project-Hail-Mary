"""Share Price History — tracks ERC4626 vault share price from Deposit/Withdraw events."""
from pipeline.derived._base import base_doc

ERC4626_EVENTS = {"Deposit", "Withdraw"}


async def derive(raw_data: dict, investigation_id: str, config: dict) -> list[dict]:
    """Derive share_price_history records from ERC4626 Deposit/Withdraw events.

    raw_data keys: normalized_tx, decoded_events
    ERC4626 events carry: assets (uint256), shares (uint256).
    share_price = assets / shares (in decimal units, assuming 18 decimals each).
    share_price_delta_pct is computed at query time in ES against prior records.
    """
    results = []
    decoded_events = raw_data.get("decoded_events", [])

    for event in decoded_events:
        event_name = event.get("event_name", "")
        if event_name not in ERC4626_EVENTS:
            continue

        args = event.get("event_args", {})
        tx_hash = event.get("tx_hash", "")
        block_number = event.get("block_number", 0)
        block_datetime = event.get("block_datetime", "")
        log_index = event.get("log_index", 0)

        # ERC4626 standard: assets and shares are in the event args
        raw_assets = args.get("assets", 0)
        raw_shares = args.get("shares", 0)

        # Convert from wei (18 decimals assumed)
        total_assets_eth = raw_assets / 1e18 if isinstance(raw_assets, (int, float)) else 0.0
        total_supply = raw_shares / 1e18 if isinstance(raw_shares, (int, float)) else 0.0

        # Compute instantaneous share price
        share_price = (total_assets_eth / total_supply) if total_supply > 0 else 0.0

        doc = base_doc(tx_hash, block_number, block_datetime,
                       investigation_id, "share_price_history", log_index)
        doc.update({
            "contract_address": event.get("log_address", ""),
            "total_assets_eth": total_assets_eth,
            "total_supply": total_supply,
            "share_price": share_price,
            "share_price_delta_pct": 0.0,  # computed at query time via ES
        })
        results.append(doc)

    return results
