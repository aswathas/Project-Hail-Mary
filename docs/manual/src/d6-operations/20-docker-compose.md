# 2. `docker-compose.yml` walk-through

The repo ships a single `docker-compose.yml` at the project root. Six
services:

| Service | Purpose | Depends on |
|---------|---------|------------|
| `elasticsearch` | Single-node ES 8.12.0 with security disabled, persistent `esdata` volume | — |
| `kibana`        | Kibana 8.12.0 for dashboards | `elasticsearch` healthy |
| `anvil`         | Foundry's Anvil RPC node, chain-id 31337, 10 accounts, 10000 ETH each | — |
| `simulator`     | One-shot Foundry container that runs `scenarios/demo-500/script/RunAll.s.sol` against Anvil | `anvil` healthy |
| `pipeline`      | The ChainSentinel pipeline (`Dockerfile` under `chainsentinel/`) — analyses the simulated data | `elasticsearch` healthy, `simulator` completed |
| `kibana-setup`  | Creates Kibana saved objects via `kibana_setup.py` | `kibana` healthy, `pipeline` completed |

## 2.1 Running

```bash
# Bring up ES + Kibana (long-running)
docker compose up -d elasticsearch kibana

# Run the full demo-500 pipeline (one-shot)
docker compose up anvil simulator pipeline kibana-setup
```

`docker compose down -v` removes the `esdata` volume — useful between
demos.

## 2.2 Health checks

Every service has a healthcheck. `docker compose ps` shows status:

```text
NAME                         STATUS
chainsentinel-es             Up 2 minutes (healthy)
chainsentinel-kibana         Up 1 minute (healthy)
chainsentinel-anvil          Up 1 minute (healthy)
chainsentinel-simulator      Exited (0)
chainsentinel-pipeline       Exited (0)
chainsentinel-kibana-setup   Exited (0)
```

## 2.3 Volumes & data persistence

- `esdata` — ES storage; lives between `up` / `down` without `-v`.
- `./simulations` mounted into the simulator at `/sim`.
- `./chainsentinel` mounted into the pipeline at `/app`.
- `./simulations/scenarios/demo-500/client` mounted into the pipeline
  at `/app/pipeline/abi_registry/cases/INV-DEMO-500` — this is how
  the case ABIs from the simulation become available to the decoder.

## 2.4 Environment variables

The pipeline service reads:

| Var | Default | Notes |
|-----|---------|-------|
| `ES_URL` | `http://elasticsearch:9200` | Used in the compose network |
| `RPC_URL` | `http://anvil:8545` | Same |
| `INVESTIGATION_ID` | `INV-DEMO-500` | Override per run |

For production deployments, point `ES_URL` at your managed ES cluster
and remove the `anvil`, `simulator`, and `kibana-setup` services.
