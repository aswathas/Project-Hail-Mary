"""Contract Creator Graph — links deployer EOA to deployed contract address."""
from pipeline.derived._base import base_doc


async def derive(raw_data: dict, investigation_id: str, config: dict) -> list[dict]:
    """Derive contract_creator_graph records from deployment transactions.

    raw_data keys: normalized_tx
    """
    results = []
    normalized_tx = raw_data.get("normalized_tx")
    if not normalized_tx:
        return results

    to_address = normalized_tx.get("to_address", "")
    # Only deployment transactions
    if to_address and to_address != "0x" + "0" * 40:
        return results

    contract_address = normalized_tx.get("contract_address", "")
    if not contract_address:
        return results

    tx_hash = normalized_tx.get("tx_hash", "")
    block_number = normalized_tx.get("block_number", 0)
    block_datetime = normalized_tx.get("block_datetime", "")
    deployer_address = normalized_tx.get("from_address", "")
    input_data = normalized_tx.get("input", "0x")
    bytecode_size = (len(input_data) - 2) // 2 if input_data and len(input_data) > 2 else 0

    doc = base_doc(tx_hash, block_number, block_datetime,
                   investigation_id, "contract_creator_graph",
                   source_layer="raw")
    doc.update({
        "deployer_address": deployer_address,
        "contract_address": contract_address,
        "bytecode_size_bytes": bytecode_size,
    })
    results.append(doc)

    return results
