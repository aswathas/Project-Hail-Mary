"""Contract Deployments — derives deployment records from to=null transactions."""
from pipeline.derived._base import base_doc


async def derive(raw_data: dict, investigation_id: str, config: dict) -> list[dict]:
    """Derive contract_deployments records from normalized transactions.

    raw_data keys: normalized_tx (a single normalized transaction dict)
    """
    results = []
    normalized_tx = raw_data.get("normalized_tx")
    if not normalized_tx:
        return results

    to_addr = normalized_tx.get("to_address", "")
    # Contract creation: to_address is null/empty/zero
    if not to_addr or to_addr == "0x" + "0" * 40:
        contract_addr = normalized_tx.get("contract_address", "")
        input_data = normalized_tx.get("input", "0x")
        bytecode_size = (len(input_data) - 2) // 2 if input_data and len(input_data) > 2 else 0

        doc = base_doc(
            normalized_tx["tx_hash"],
            normalized_tx["block_number"],
            normalized_tx["block_datetime"],
            investigation_id, "contract_deployments",
            source_layer="raw",
        )
        doc.update({
            "deployer_address": normalized_tx.get("from_address", ""),
            "contract_address": contract_addr,
            "success": normalized_tx.get("success", False),
            "bytecode_size_bytes": bytecode_size,
            "value_eth": normalized_tx.get("value_eth", 0),
            "gas_used": normalized_tx.get("gas_used", 0),
        })
        results.append(doc)

    return results
