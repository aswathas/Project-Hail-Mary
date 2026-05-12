# 7. Cookbook: add a new derived event

Derived events are Python modules under `chainsentinel/pipeline/derived/`
that subclass the `Builder` contract in `_base.py`.

## 7.1 Pick a `derived_type`

Use a `snake_case` noun phrase. For example, `flashbots_bundle_marker`.

## 7.2 Write the module

`chainsentinel/pipeline/derived/flashbots_bundle_marker.py`:

```python
"""
Flag transactions whose miner/builder coinbase is a known Flashbots
relay. Useful as input for MEV signals.
"""

from typing import Iterable
from ._base import Builder, PipelineContext

FLASHBOTS_BUILDERS = {
    "0xdafea492d9c6733ae3d56b7ed1adb60692c98bc5",
    "0x690b9a9e9aa1c9db991c7721a92d351db4fac990",
    # ...
}

class FlashbotsBundleMarker(Builder):
    derived_type = "flashbots_bundle_marker"
    requires     = []  # raw fields are enough

    def emit(self, ctx: PipelineContext) -> Iterable[dict]:
        tx = ctx.tx
        miner = tx.get("miner") or tx.get("coinbase")
        if not miner:
            return
        miner = miner.lower()
        if miner not in FLASHBOTS_BUILDERS:
            return
        yield {
            "investigation_id": ctx.investigation_id,
            "chain_id":         ctx.chain_id,
            "@timestamp":       ctx.now,
            "block_number":     tx["blockNumber"],
            "block_datetime":   ctx.block_datetime,
            "tx_hash":          tx["hash"],
            "layer":            "derived",
            "derived_type":     self.derived_type,
            "source_tx_hash":   tx["hash"],
            "source_layer":     "decoded",
            "metadata": {
                "miner": miner,
            },
        }
```

## 7.3 Register

`pipeline/derived/__init__.py` discovers modules automatically. Confirm
the module imports cleanly:

```bash
python -c "from chainsentinel.pipeline.derived.flashbots_bundle_marker import FlashbotsBundleMarker; print(FlashbotsBundleMarker.derived_type)"
```

## 7.4 Test

Mirror the existing test under `chainsentinel/tests/` (`test_derived_*.py`)
with a fixture transaction whose `miner` matches a known builder.

## 7.5 Document

Run `make catalogs` to update `src/_generated/derived_events.md`. The
module docstring becomes the description, so write a good one-paragraph
summary at the top of the file.

If the new builder consumes other derived layers (`requires` is
non-empty), document the dependency in **D4 §11.3**.
