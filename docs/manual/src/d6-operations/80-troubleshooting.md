# 8. Troubleshooting matrix

Symptom → likely cause → fix.

| Symptom | Cause | Fix |
|---------|-------|-----|
| `start.sh` hangs at `[1/5] Waiting for Elasticsearch...` | Port 9200 in use by another ES, or Docker daemon down | `lsof -iTCP:9200` to identify; `docker ps -a` to find a stopped container; `docker start chainsentinel-es` or remove the stale container. |
| ES container exits with `bootstrap check failure` | Linux `vm.max_map_count` too low | `sudo sysctl -w vm.max_map_count=262144` (persist via `/etc/sysctl.d/`). |
| `POST /analyze` returns `503 Cannot connect to RPC` | Anvil not running, or `rpc_url` points elsewhere | In sim mode, `pgrep -f anvil` and restart `start.sh`; in mainnet mode, verify the Alchemy/Infura key in `config.json`. |
| SSE stream stops after `phase: decode` | `decode_status: unknown` for every log — no ABI loaded | Drop the client's ABIs into `pipeline/abi_registry/cases/{investigation_id}/`, or check the manifest path. |
| Signals all return zero rows | ES index `forensics` is empty / not refreshed | `curl http://localhost:9200/forensics/_refresh`; verify the pipeline phase `derive` produced docs by querying for `layer:"derived"`. |
| Patterns never fire even though signals do | Signals fire below `signal_score_threshold` | Lower the threshold in `config.json` or boost the per-signal score in the `.esql`. |
| Copilot replies "I cannot find information about X" | Context bundle did not include X | Increase the `report_template` per-list cap; ensure the relevant `derived` layer was produced. |
| Ollama replies with garbage | Model not pulled, or wrong model in config | `ollama list`; `ollama pull gemma3:1b`. |
| Vite shows blank page | `npm install` did not complete | `cd chainsentinel/frontend && rm -rf node_modules && npm install`. |
| Frontend SSE stuck at "Connecting" | CORS misconfigured | The FastAPI `CORSMiddleware` allows only `:5173`. If you run Vite on another port, update `server.py`'s `allow_origins`. |
| `make catalogs` exits without output | Repo layout changed; script's paths are stale | Re-read `docs/manual/scripts/generate_catalog_tables.py` and adjust the `CHAINSENTINEL = REPO_ROOT / "chainsentinel"` line. |
| `make d4` says "missing image" | Mermaid sources changed but not re-rendered | Run `make diagrams`. Requires `mmdc` (`npm i -g @mermaid-js/mermaid-cli`). |
| ES strict-mapping rejection on ingest | A derived builder emitted a new field that is not in `forensics.json` mapping | Either remove the field from the builder, or add it to `es/mappings/forensics.json` and `PUT _mapping`. |
| `pytest -m e2e` fails because Anvil not in $PATH | Foundry installed but PATH not set | `source ~/.foundry/bin/env` or add to your shell rc. |
