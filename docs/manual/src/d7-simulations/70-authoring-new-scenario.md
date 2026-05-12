# 7. Authoring a new scenario

The drop-a-folder pattern works for scenarios too.

## 7.1 Skeleton

```text
simulations/scenarios/<your-scenario>/
├── src/
│   ├── victim/      *.sol
│   ├── attacker/    *.sol
│   └── activity/    *.sol   (optional, for backdrop traffic)
├── script/
│   ├── 01_DeployProtocol.s.sol
│   ├── 02_NormalActivity.s.sol
│   ├── 03_ExecuteAttack.s.sol
│   ├── 04_PostAttack.s.sol
│   └── RunAll.s.sol
└── client/
    ├── manifest.json
    └── <ContractName>.json   (ABIs)
```

## 7.2 `manifest.json`

The output the simulator pretends a real client handed over:

```json
{
  "investigation_id": "SIM-MYATTACK-001",
  "chain_id": 31337,
  "window": { "from_block": <deploy>, "to_block": <attack + 5> },
  "contracts": [
    { "address": "0x...", "name": "VictimContract", "abi": [ ... ] }
  ]
}
```

Write the manifest at the end of `03_ExecuteAttack.s.sol` using
`vm.writeFile`.

## 7.3 Wiring into `docker-compose.yml`

To make your scenario the default demo, modify the `simulator` service's
command to run your scenario's `RunAll.s.sol`, and mount your
`client/` into the pipeline's ABI registry path:

```yaml
volumes:
  - ./simulations/scenarios/<your-scenario>/client:/app/pipeline/abi_registry/cases/SIM-MYATTACK-001
```

## 7.4 Documenting

1. Add a chapter to this document (`docs/manual/src/d7-simulations/`).
2. Run `make catalogs` — `src/_generated/scenarios.md` will pick up the
   new folder automatically.
3. Update `docs/manual/diagrams/src/13-scenario-matrix.mmd` to point
   from your scenario to the patterns it is expected to trigger.
