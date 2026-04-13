"""Liquidation Events — detects lending protocol liquidation events."""
from pipeline.derived._base import base_doc

LIQUIDATION_EVENTS = {
    "Liquidation",
    "LiquidationCall",
    "LiquidateBorrow",
    "Liquidated",
}


async def derive(raw_data: dict, investigation_id: str, config: dict) -> list[dict]:
    """Derive liquidation_events records from decoded lending protocol events.

    raw_data keys: normalized_tx, decoded_events
    """
    results = []
    decoded_events = raw_data.get("decoded_events", [])
    normalized_tx = raw_data.get("normalized_tx") or {}

    for event in decoded_events:
        event_name = event.get("event_name", "")
        if event_name not in LIQUIDATION_EVENTS:
            continue

        args = event.get("event_args", {})
        tx_hash = event.get("tx_hash", "")
        block_number = event.get("block_number", 0)
        block_datetime = event.get("block_datetime", "")
        log_index = event.get("log_index", 0)

        # Aave v2/v3 style: liquidator, user, liquidatedCollateralAmount, debtToCover
        # Compound style: liquidator, borrower, repayAmount, seizeTokens
        liquidator = str(args.get("liquidator", normalized_tx.get("from_address", ""))).lower()
        borrower = str(args.get("user", args.get("borrower", ""))).lower()

        raw_collateral = args.get("liquidatedCollateralAmount", args.get("seizeTokens", 0))
        raw_debt = args.get("debtToCover", args.get("repayAmount", 0))

        # Convert from wei (assume 18 decimals as baseline)
        collateral_eth = raw_collateral / 1e18 if isinstance(raw_collateral, (int, float)) else 0.0
        debt_eth = raw_debt / 1e18 if isinstance(raw_debt, (int, float)) else 0.0

        doc = base_doc(tx_hash, block_number, block_datetime,
                       investigation_id, "liquidation_events", log_index)
        doc.update({
            "from_address": liquidator,
            "borrower_address": borrower,
            "collateral_seized_eth": collateral_eth,
            "debt_repaid_eth": debt_eth,
        })
        results.append(doc)

    return results
