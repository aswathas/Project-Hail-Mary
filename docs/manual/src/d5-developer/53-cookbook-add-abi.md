# 8. Cookbook: add a new ABI

Two contexts: a *protocol* ABI usable across investigations, or a
*case* ABI scoped to one investigation.

## 8.1 Protocol ABI

For ABIs you expect to reuse:

1. Drop the ABI JSON in `chainsentinel/pipeline/abi_registry/protocols/`.
   Either an `abi`-keyed wrapper:
   ```json
   { "name": "AaveV3Pool", "abi": [ { "type": "event", ... }, ... ] }
   ```
   or a bare JSON array (the decoder handles both).
2. Use a descriptive lowercase filename: `aave_v3_pool.json`.
3. No registration needed — `ABIRegistry` discovers everything under
   `protocols/` on every import.

## 8.2 Standard ABI

For ABIs that all chains share (`erc20.json`, `erc721.json`, etc.) drop
under `chainsentinel/pipeline/abi_registry/standards/`. Same shape as
above.

## 8.3 Case ABI

For client-specific contracts:

1. Drop under `chainsentinel/pipeline/abi_registry/cases/{investigation_id}/`.
2. The case path takes the highest precedence in the resolution order
   (see **D4 §12.1**).
3. The frontend's manifest loader writes case ABIs into this path
   automatically when the analyst attaches a manifest.

## 8.4 Manifest format

`manifest.json` carried by the client and ingested by the frontend:

```json
{
  "investigation_id": "client_acme_2026Q2",
  "chain_id": 1,
  "window": { "from_block": 19_500_000, "to_block": 19_500_500 },
  "contracts": [
    { "address": "0x...", "name": "AcmeVault", "abi": [ ... ] },
    { "address": "0x...", "name": "AcmeOracle", "abi": [ ... ] }
  ]
}
```

When the analyst loads this in the Sidebar, the frontend:

1. POSTs the manifest to a `/manifest` endpoint (future work; today done
   via static file drop).
2. Writes each contract's ABI to
   `pipeline/abi_registry/cases/{investigation_id}/{name}.json`.
3. Saves the manifest under `cases/{investigation_id}/manifest.json`.

## 8.5 Refreshing the catalog

Run `make catalogs` to refresh `src/_generated/abi_registry.md`. The
event and function counts come from parsing the JSON, so the table
stays accurate even for very large ABIs.
