"""
Derived Event Builder — produces security-shaped records from decoded data.
9 derived types: asset_transfer, native_transfer, swap_summary, approval_usage,
admin_action, execution_edge, fund_flow_edge, contract_interaction, balance_delta.
"""
from datetime import datetime, timezone


def _hex_to_int(val):
    if isinstance(val, str) and val.startswith("0x"):
        return int(val, 16)
    if isinstance(val, int):
        return val
    return 0


def _base_doc(tx_hash, block_number, block_datetime, investigation_id, derived_type,
              source_log_index=None, source_layer="decoded"):
    return {
        "investigation_id": investigation_id,
        "layer": "derived",
        "derived_type": derived_type,
        "tx_hash": tx_hash,
        "block_number": block_number,
        "block_datetime": block_datetime,
        "@timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source_tx_hash": tx_hash,
        "source_log_index": source_log_index,
        "source_layer": source_layer,
    }


def derive_events(decoded_events: list[dict], investigation_id: str) -> list[dict]:
    """Derive security events from a list of decoded event logs."""
    results = []

    for event in decoded_events:
        name = event.get("event_name")
        args = event.get("event_args", {})
        tx_hash = event.get("tx_hash", "")
        block_number = event.get("block_number", 0)
        block_datetime = event.get("block_datetime", "")
        log_index = event.get("log_index", 0)

        if name == "Transfer":
            doc = _base_doc(tx_hash, block_number, block_datetime,
                           investigation_id, "asset_transfer", log_index)
            from_addr = str(args.get("from", "")).lower()
            to_addr = str(args.get("to", "")).lower()
            raw_value = args.get("value", 0)
            decimals = event.get("token_decimals", 18)
            amount = raw_value / (10 ** decimals) if decimals else raw_value

            doc.update({
                "from_address": from_addr,
                "to_address": to_addr,
                "token_address": event.get("log_address", ""),
                "token_symbol": event.get("token_symbol", ""),
                "amount_decimal": amount,
                "value_wei": str(raw_value),
                "transfer_type": "erc20",
            })

            # Detect mint (from zero address)
            if from_addr == "0x" + "0" * 40:
                doc["transfer_type"] = "mint"
            # Detect burn (to zero address)
            elif to_addr == "0x" + "0" * 40:
                doc["transfer_type"] = "burn"

            results.append(doc)

        elif name == "Approval":
            doc = _base_doc(tx_hash, block_number, block_datetime,
                           investigation_id, "approval_usage", log_index)
            doc.update({
                "owner_address": str(args.get("owner", "")).lower(),
                "spender_address": str(args.get("spender", "")).lower(),
                "token_address": event.get("log_address", ""),
                "amount_decimal": args.get("value", 0),
                "was_consumed": False,
                "consumed_tx_hash": None,
            })
            results.append(doc)

        elif name in ("OwnershipTransferred", "RoleGranted", "RoleRevoked",
                       "Upgraded", "Paused", "Unpaused"):
            doc = _base_doc(tx_hash, block_number, block_datetime,
                           investigation_id, "admin_action", log_index)

            action_map = {
                "OwnershipTransferred": "ownership_transfer",
                "RoleGranted": "role_grant",
                "RoleRevoked": "role_revoke",
                "Upgraded": "upgrade",
                "Paused": "pause",
                "Unpaused": "unpause",
            }

            actor = ""
            new_value = ""
            if name == "OwnershipTransferred":
                actor = str(args.get("newOwner", "")).lower()
                new_value = actor
            elif name == "RoleGranted":
                actor = str(args.get("account", "")).lower()
                new_value = str(args.get("role", ""))
            elif name == "Upgraded":
                new_value = str(args.get("implementation", "")).lower()

            doc.update({
                "action_type": action_map.get(name, name.lower()),
                "actor_address": actor,
                "contract_address": event.get("log_address", ""),
                "new_value": new_value,
            })
            results.append(doc)

        elif name == "Swap":
            doc = _base_doc(tx_hash, block_number, block_datetime,
                           investigation_id, "swap_summary", log_index)
            doc.update({
                "pool_address": event.get("log_address", ""),
                "trader_address": str(args.get("sender", args.get("recipient", ""))).lower(),
                "amount_in": abs(args.get("amount0In", args.get("amount0", 0))),
                "amount_out": abs(args.get("amount1Out", args.get("amount1", 0))),
                "token_in": "",
                "token_out": "",
                "protocol_name": "",
                "price_impact_pct": 0.0,
            })
            results.append(doc)

    return results


def derive_events_from_tx(normalized_tx: dict, investigation_id: str) -> list[dict]:
    """Derive events from a normalized transaction (native ETH transfers)."""
    results = []

    value_eth = normalized_tx.get("value_eth", 0)
    if value_eth > 0 and normalized_tx.get("success", False):
        doc = _base_doc(
            normalized_tx["tx_hash"],
            normalized_tx["block_number"],
            normalized_tx["block_datetime"],
            investigation_id, "native_transfer",
            source_layer="raw",
        )
        doc.update({
            "from_address": normalized_tx.get("from_address", ""),
            "to_address": normalized_tx.get("to_address", ""),
            "value_eth": value_eth,
            "value_wei": normalized_tx.get("value_wei", "0"),
        })
        results.append(doc)

    # Contract interaction
    if normalized_tx.get("input", "0x") != "0x" and normalized_tx.get("to_address"):
        doc = _base_doc(
            normalized_tx["tx_hash"],
            normalized_tx["block_number"],
            normalized_tx["block_datetime"],
            investigation_id, "contract_interaction",
            source_layer="raw",
        )
        doc.update({
            "user_address": normalized_tx.get("from_address", ""),
            "contract_address": normalized_tx.get("to_address", ""),
            "function_name": None,
            "protocol_name": None,
            "success": normalized_tx.get("success", False),
        })
        results.append(doc)

    return results


def derive_events_from_trace(
    trace: dict, tx_hash: str, block_number: int,
    block_datetime: str, investigation_id: str, depth: int = 0
) -> list[dict]:
    """Recursively derive execution_edge events from a call trace."""
    results = []

    value_hex = trace.get("value", "0x0")
    value_int = _hex_to_int(value_hex)
    value_eth = value_int / 1e18 if value_int else 0.0

    doc = _base_doc(tx_hash, block_number, block_datetime,
                   investigation_id, "execution_edge", source_layer="trace")
    doc.update({
        "caller_address": str(trace.get("from", "")).lower(),
        "callee_address": str(trace.get("to", "")).lower(),
        "call_type": trace.get("type", "CALL"),
        "function_name": None,
        "value_eth": value_eth,
        "call_depth": depth,
        "gas_used": _hex_to_int(trace.get("gasUsed", 0)),
        "success": True,
    })

    # Try to extract function selector
    input_data = trace.get("input", "0x")
    if input_data and len(input_data) >= 10:
        doc["function_name"] = input_data[:10]

    results.append(doc)

    # Recurse into sub-calls
    for sub_call in trace.get("calls", []):
        results.extend(derive_events_from_trace(
            sub_call, tx_hash, block_number, block_datetime,
            investigation_id, depth + 1
        ))

    return results
