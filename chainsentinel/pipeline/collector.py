"""
Collector — fetches raw chain data from any EVM RPC endpoint.
Merges transaction + receipt into one document.
Optionally fetches debug_traceTransaction (graceful if unavailable).
"""
import httpx
import logging
from typing import Optional

_log = logging.getLogger("chainsentinel.collector")


async def _fetch_trace(rpc_url: str, tx_hash: str) -> dict | None:
    """Fetch debug_traceTransaction via direct HTTP call (bypasses web3 async issues)."""
    payload = {
        "jsonrpc": "2.0",
        "method": "debug_traceTransaction",
        "params": [tx_hash, {"tracer": "callTracer"}],
        "id": 1,
    }
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(rpc_url, json=payload)
            data = resp.json()
            return data.get("result")
    except Exception:
        return None


def _hex_to_int(val):
    """Convert hex string to int, pass through if already int."""
    if isinstance(val, str) and val.startswith("0x"):
        return int(val, 16)
    return val


def _extract_hash(val):
    """Extract hex string from various web3 return types. Always returns 0x-prefixed."""
    if hasattr(val, "hex"):
        h = val.hex()
        return h if h.startswith("0x") else "0x" + h
    if isinstance(val, bytes):
        return "0x" + val.hex()
    s = str(val)
    return s if s.startswith("0x") else "0x" + s


async def collect_transaction(w3, tx_hash: str, include_trace: bool = False, rpc_url: str = "http://127.0.0.1:8545") -> dict:
    """
    Fetch a transaction + receipt + block timestamp, merge into one document.
    Optionally fetch debug_traceTransaction.
    """
    tx = await w3.eth.get_transaction(tx_hash)
    receipt = await w3.eth.get_transaction_receipt(tx_hash)
    block = await w3.eth.get_block(_hex_to_int(tx.get("blockNumber", tx.get("block_number", 0))))

    logs = []
    for log in receipt.get("logs", []):
        logs.append({
            "log_index": _hex_to_int(log.get("logIndex", log.get("log_index", 0))),
            "address": _extract_hash(log.get("address", "")),
            "topics": [_extract_hash(t) for t in log.get("topics", [])],
            "data": _extract_hash(log.get("data", "0x")),
        })

    doc = {
        "tx_hash": _extract_hash(tx.get("hash", tx_hash)),
        "block_number": _hex_to_int(tx.get("blockNumber", tx.get("block_number", 0))),
        "block_timestamp": _hex_to_int(block.get("timestamp", 0)),
        "tx_index": _hex_to_int(tx.get("transactionIndex", tx.get("transaction_index", 0))),
        "from": _extract_hash(tx.get("from", "")),
        "to": _extract_hash(tx.get("to", "") or ""),
        "value": _hex_to_int(tx.get("value", 0)),
        "gas": _hex_to_int(tx.get("gas", 0)),
        "gas_price": _hex_to_int(tx.get("gasPrice", tx.get("gas_price", 0))),
        "nonce": _hex_to_int(tx.get("nonce", 0)),
        "input": _extract_hash(tx.get("input", "0x")),
        "status": _hex_to_int(receipt.get("status", 0)),
        "gas_used": _hex_to_int(receipt.get("gasUsed", receipt.get("gas_used", 0))),
        "cumulative_gas_used": _hex_to_int(
            receipt.get("cumulativeGasUsed", receipt.get("cumulative_gas_used", 0))
        ),
        "contract_address": str(receipt.get("contractAddress", receipt.get("contract_address", "")))
            if receipt.get("contractAddress", receipt.get("contract_address"))
            else None,
        "logs": logs,
        "trace": None,
    }

    if include_trace:
        trace = await _fetch_trace(rpc_url, tx_hash)
        doc["trace"] = dict(trace) if trace else None

    return doc


async def collect_block_range(
    w3, from_block: int, to_block: int, include_traces: bool = False, rpc_url: str = "http://127.0.0.1:8545"
) -> list[dict]:
    """Fetch all transactions in a block range."""
    results = []

    for block_num in range(from_block, to_block + 1):
        block = await w3.eth.get_block(block_num, full_transactions=True)
        timestamp = _hex_to_int(block.get("timestamp", 0))

        for tx in block.get("transactions", []):
            tx_hash = _extract_hash(tx.get("hash", ""))
            receipt = await w3.eth.get_transaction_receipt(tx_hash)

            logs = []
            for log in receipt.get("logs", []):
                logs.append({
                    "log_index": _hex_to_int(
                        log.get("logIndex", log.get("log_index", 0))
                    ),
                    "address": _extract_hash(log.get("address", "")),
                    "topics": [_extract_hash(t) for t in log.get("topics", [])],
                    "data": _extract_hash(log.get("data", "0x")),
                })

            doc = {
                "tx_hash": tx_hash,
                "block_number": block_num,
                "block_timestamp": timestamp,
                "tx_index": _hex_to_int(
                    tx.get("transactionIndex", tx.get("transaction_index", 0))
                ),
                "from": _extract_hash(tx.get("from", "")),
                "to": _extract_hash(tx.get("to", "") or ""),
                "value": _hex_to_int(tx.get("value", 0)),
                "gas": _hex_to_int(tx.get("gas", 0)),
                "gas_price": _hex_to_int(
                    tx.get("gasPrice", tx.get("gas_price", 0))
                ),
                "nonce": _hex_to_int(tx.get("nonce", 0)),
                "input": _extract_hash(tx.get("input", "0x")),
                "status": _hex_to_int(receipt.get("status", 0)),
                "gas_used": _hex_to_int(
                    receipt.get("gasUsed", receipt.get("gas_used", 0))
                ),
                "cumulative_gas_used": _hex_to_int(
                    receipt.get("cumulativeGasUsed", receipt.get("cumulative_gas_used", 0))
                ),
                "contract_address": str(
                    receipt.get("contractAddress", receipt.get("contract_address", ""))
                ) if receipt.get("contractAddress", receipt.get("contract_address")) else None,
                "logs": logs,
                "trace": None,
            }

            if include_traces:
                trace = await _fetch_trace(rpc_url, tx_hash)
                doc["trace"] = dict(trace) if trace else None
                _log.info("Trace fetch %s -> %s", tx_hash[:12], "ok" if trace else "none")

            results.append(doc)

    return results


async def collect_logs(w3, from_block: int, to_block: int) -> list[dict]:
    """Fetch all event logs in a block range via eth_getLogs."""
    raw_logs = await w3.eth.get_logs({
        "fromBlock": from_block,
        "toBlock": to_block,
    })

    return [
        {
            "tx_hash": _extract_hash(log.get("transactionHash", log.get("transaction_hash", ""))),
            "block_number": _hex_to_int(log.get("blockNumber", log.get("block_number", 0))),
            "log_index": _hex_to_int(log.get("logIndex", log.get("log_index", 0))),
            "address": _extract_hash(log.get("address", "")),
            "topics": [_extract_hash(t) for t in log.get("topics", [])],
            "data": _extract_hash(log.get("data", "0x")),
        }
        for log in raw_logs
    ]
