# 1. Prerequisites

## 1.1 Hardware

| Workload | Min | Recommended |
|----------|-----|-------------|
| RAM | 8 GB | 16 GB+ (ES uses 1 GB heap by default, Ollama 2 GB+) |
| CPU | 4 cores | 8 cores |
| Disk | 20 GB | 50 GB (room for ES data + Ollama models) |
| OS | Linux x86_64 / macOS arm64+x86_64 / Windows WSL2 | — |

## 1.2 Software

| Component | Version | Where |
|-----------|---------|-------|
| Docker    | 24+     | for ES + Kibana via `docker-compose.yml` |
| Python    | 3.11+   | for the pipeline and FastAPI server |
| Node.js   | 20+     | for the Vite frontend |
| Ollama    | 0.1.30+ | https://ollama.com (download & install) |
| Foundry   | nightly | only for `simulation` mode (`curl -L https://foundry.paradigm.xyz \| bash; foundryup`) |

You can also run the entire stack via Docker (`docker-compose.yml`) and
skip installing Python / Node / Foundry on the host. The trade-off is
slower hot-reload during development.

## 1.3 Network

By default everything binds to `localhost`:

| Port | Service | Notes |
|------|---------|-------|
| 5173 | Vite frontend | dev server, hot-reload |
| 8000 | FastAPI | SSE + REST |
| 8545 | Anvil | simulation mode only |
| 9200 | Elasticsearch | no auth in dev |
| 5601 | Kibana | optional dashboards |
| 11434 | Ollama | local LLM |

For multi-user deployments, bind each service to a private interface
and front the analyst's browser access to FastAPI via an authenticated
reverse proxy.
