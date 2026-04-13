"""
Decoder — gives meaning to raw normalised structures.
Decodes event signatures from topic0, event arguments from ABI,
function selectors from input data.
"""
import json
from pathlib import Path
from web3 import Web3


REGISTRY_PATH = Path(__file__).parent / "selector_registry.json"
ABI_DIR = Path(__file__).parent / "abi_registry"


class Decoder:
    def __init__(self, abis: dict = None, case_manifest: dict = None):
        """
        abis: {"standards": [abi_list, ...], "protocols": [abi_list, ...]}
        case_manifest: {"contracts": [{"address": "0x...", "abi": "path.json"}, ...]}
        """
        self.event_map = {}      # topic0_hash -> {name, abi_entry}
        self.selector_map = {}   # bytes4 -> {name, abi_entry}
        self.address_abis = {}   # address -> abi_list (from case manifest)

        # Load selector registry cache
        if REGISTRY_PATH.exists():
            with open(REGISTRY_PATH) as f:
                cache = json.load(f)
                self.event_map.update(
                    {k: v for k, v in cache.get("event_signatures", {}).items()}
                )
                self.selector_map.update(
                    {k: v for k, v in cache.get("function_selectors", {}).items()}
                )

        # Load provided ABIs
        if abis:
            for category_abis in abis.values():
                for abi_list in category_abis:
                    self._index_abi(abi_list)

        # Load case-specific ABIs by address
        if case_manifest:
            for contract in case_manifest.get("contracts", []):
                addr = contract["address"].lower()
                abi_path = contract.get("abi_path")
                if abi_path and Path(abi_path).exists():
                    with open(abi_path) as f:
                        abi = json.load(f)
                    self.address_abis[addr] = abi
                    self._index_abi(abi)

    def _index_abi(self, abi: list):
        """Index all events and functions from an ABI."""
        for entry in abi:
            if entry.get("type") == "event":
                sig = self._event_signature(entry)
                topic0 = "0x" + Web3.keccak(text=sig).hex()
                self.event_map[topic0] = {
                    "name": entry["name"],
                    "inputs": entry.get("inputs", []),
                }
            elif entry.get("type") == "function":
                sig = self._function_signature(entry)
                selector = "0x" + Web3.keccak(text=sig).hex()[:8]
                self.selector_map[selector] = {
                    "name": entry["name"],
                    "inputs": entry.get("inputs", []),
                }

    def _event_signature(self, entry: dict) -> str:
        types = ",".join(inp["type"] for inp in entry.get("inputs", []))
        return f"{entry['name']}({types})"

    def _function_signature(self, entry: dict) -> str:
        types = ",".join(inp["type"] for inp in entry.get("inputs", []))
        return f"{entry['name']}({types})"

    def decode_log(self, log: dict) -> dict:
        """Decode an event log using topic0 lookup."""
        topics = log.get("topics", [])
        data = log.get("data", "0x")

        if not topics:
            return {
                "event_name": None,
                "event_args": {},
                "decode_status": "unknown",
                "topics": topics,
                "data": data,
            }

        topic0 = topics[0]
        entry = self.event_map.get(topic0)

        if not entry:
            return {
                "event_name": None,
                "event_args": {},
                "decode_status": "unknown",
                "topics": topics,
                "data": data,
            }

        # Decode arguments
        args = {}
        indexed_inputs = [i for i in entry["inputs"] if i.get("indexed")]
        data_inputs = [i for i in entry["inputs"] if not i.get("indexed")]

        # Decode indexed args from topics[1:]
        for idx, inp in enumerate(indexed_inputs):
            if idx + 1 < len(topics):
                raw = topics[idx + 1]
                if inp["type"] == "address":
                    args[inp["name"]] = "0x" + raw[-40:]
                elif inp["type"] in ("uint256", "uint128", "uint64", "uint32", "uint8", "int256"):
                    args[inp["name"]] = int(raw, 16)
                else:
                    args[inp["name"]] = raw

        # Decode non-indexed args from data
        if data and data != "0x" and data_inputs:
            data_bytes = data[2:]  # strip 0x
            offset = 0
            for inp in data_inputs:
                if offset + 64 <= len(data_bytes):
                    chunk = data_bytes[offset:offset + 64]
                    if inp["type"] in ("uint256", "uint128", "uint64", "uint32", "uint8", "int256"):
                        args[inp["name"]] = int(chunk, 16)
                    elif inp["type"] == "address":
                        args[inp["name"]] = "0x" + chunk[-40:]
                    elif inp["type"] == "bool":
                        args[inp["name"]] = int(chunk, 16) != 0
                    else:
                        args[inp["name"]] = "0x" + chunk
                    offset += 64

        return {
            "event_name": entry["name"],
            "event_args": args,
            "decode_status": "decoded",
            "topics": topics,
            "data": data,
        }

    def decode_function_input(self, input_data: str) -> dict:
        """Decode function selector + args from transaction input."""
        if not input_data or input_data == "0x" or len(input_data) < 10:
            return {
                "function_name": None,
                "function_args": {},
                "decode_status": "unknown",
            }

        selector = input_data[:10]
        entry = self.selector_map.get(selector)

        if not entry:
            return {
                "function_name": None,
                "function_args": {},
                "decode_status": "unknown",
            }

        args = {}
        data_hex = input_data[10:]
        offset = 0
        for inp in entry.get("inputs", []):
            if offset + 64 <= len(data_hex):
                chunk = data_hex[offset:offset + 64]
                if inp["type"] in ("uint256", "uint128", "uint64", "uint32", "uint8", "int256"):
                    args[inp["name"]] = int(chunk, 16)
                elif inp["type"] == "address":
                    args[inp["name"]] = "0x" + chunk[-40:]
                elif inp["type"] == "bool":
                    args[inp["name"]] = int(chunk, 16) != 0
                else:
                    args[inp["name"]] = "0x" + chunk
                offset += 64

        return {
            "function_name": entry["name"],
            "function_args": args,
            "decode_status": "decoded",
        }

    def save_registry(self):
        """Persist the selector registry cache."""
        cache = {
            "event_signatures": {
                k: {"name": v["name"]} for k, v in self.event_map.items()
            },
            "function_selectors": {
                k: {"name": v["name"]} for k, v in self.selector_map.items()
            },
        }
        with open(REGISTRY_PATH, "w") as f:
            json.dump(cache, f, indent=2)


def load_decoder(investigation_id: str = None) -> Decoder:
    """Factory: build a Decoder from the ABI registry + optional case ABIs."""
    abis = {"standards": [], "protocols": []}

    standards_dir = ABI_DIR / "standards"
    if standards_dir.exists():
        for f in standards_dir.glob("*.json"):
            with open(f) as fh:
                abis["standards"].append(json.load(fh))

    protocols_dir = ABI_DIR / "protocols"
    if protocols_dir.exists():
        for f in protocols_dir.glob("*.json"):
            with open(f) as fh:
                abis["protocols"].append(json.load(fh))

    case_manifest = None
    if investigation_id:
        case_dir = ABI_DIR / "cases" / investigation_id
        manifest_path = case_dir / "manifest.json"
        if manifest_path.exists():
            with open(manifest_path) as fh:
                case_manifest = json.load(fh)
            # Resolve ABI paths relative to case dir
            for contract in case_manifest.get("contracts", []):
                if "abi" in contract:
                    contract["abi_path"] = str(case_dir / "abis" / contract["abi"])

    return Decoder(abis=abis, case_manifest=case_manifest)
