"""
Derived Log Registry — auto-discovers all derived log modules in this package.

Each module must export a `derive(raw_data, investigation_id, config)` async function.
The module filename (without .py) is used as the derived_type name.

Also exports backward-compatible shim functions (derive_events, derive_events_from_tx,
derive_events_from_trace) so existing callers (runner.py, tests) keep working.
"""
import importlib
import inspect
import pkgutil
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Registry — auto-discovery of new-style derived builders
# ---------------------------------------------------------------------------

_registry: dict[str, callable] = {}
_discovered = False


def _discover():
    """Scan this package for modules exporting a `derive` async function."""
    global _discovered
    if _discovered:
        return

    package_dir = Path(__file__).parent
    for finder, module_name, is_pkg in pkgutil.iter_modules([str(package_dir)]):
        if module_name.startswith("_"):
            continue
        try:
            mod = importlib.import_module(f"pipeline.derived.{module_name}")
            derive_fn = getattr(mod, "derive", None)
            if derive_fn is not None and (inspect.iscoroutinefunction(derive_fn) or callable(derive_fn)):
                _registry[module_name] = derive_fn
        except Exception:
            pass

    _discovered = True


def get_all_derived_builders() -> dict[str, callable]:
    """Return dict mapping derived_type name to its derive function."""
    _discover()
    return dict(_registry)


def get_derived_builder(name: str):
    """Return a single derive function by name, or None."""
    _discover()
    return _registry.get(name)


def reset_registry():
    """Reset discovery state — useful for testing."""
    global _discovered
    _registry.clear()
    _discovered = False


# ---------------------------------------------------------------------------
# Backward-compatible shim — preserves the original derived.py API
# ---------------------------------------------------------------------------

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

            if from_addr == "0x" + "0" * 40:
                doc["transfer_type"] = "mint"
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
    block_datetime: str, investigation_id: str, depth: int = 0,
    _counter: list = None
) -> list[dict]:
    """Recursively derive execution_edge events from a call trace."""
    if _counter is None:
        _counter = [0]

    results = []

    value_hex = trace.get("value", "0x0")
    value_int = _hex_to_int(value_hex)
    value_eth = value_int / 1e18 if value_int else 0.0

    call_index = _counter[0]
    _counter[0] += 1

    doc = _base_doc(tx_hash, block_number, block_datetime,
                   investigation_id, "execution_edge", source_log_index=call_index,
                   source_layer="trace")
    doc.update({
        "caller_address": str(trace.get("from", "")).lower(),
        "callee_address": str(trace.get("to", "")).lower(),
        "call_type": trace.get("type", "CALL"),
        "function_name": None,
        "value_eth": value_eth,
        "call_depth": depth,
        "call_index": call_index,
        "gas_used": _hex_to_int(trace.get("gasUsed", 0)),
        "success": True,
    })

    input_data = trace.get("input", "0x")
    if input_data and len(input_data) >= 10:
        doc["function_name"] = input_data[:10]

    results.append(doc)

    for sub_call in trace.get("calls", []):
        results.extend(derive_events_from_trace(
            sub_call, tx_hash, block_number, block_datetime,
            investigation_id, depth + 1, _counter
        ))

    return results
