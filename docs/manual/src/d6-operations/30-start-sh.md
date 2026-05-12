# 3. `start.sh` — one-command host startup

`chainsentinel/start.sh` is the development startup script. It reads
`mode` and `ollama_model` from `config.json`, then launches five things
in order:

| Step | What | Idempotency |
|------|------|-------------|
| 1 | Elasticsearch via `docker run -d --name chainsentinel-es elasticsearch:8.12.0` | If the container already exists it is started; if running it is left alone. |
| 2 | Ollama (`ollama serve &` if not running) and `ollama pull <model>` if not present | Both steps no-op when already in place. |
| 3 | Anvil (`anvil --chain-id 31337 --host 0.0.0.0`) — **only in simulation mode** | Skipped if a running `anvil` process exists. |
| 4 | FastAPI (`uvicorn server:app --host 0.0.0.0 --port 8000 --reload`) | Always started; runs in the background. |
| 5 | Vite (`npm run dev` after `npm install` if needed) | npm install only runs when `node_modules/` is missing. |

A `trap` handler on `INT TERM` kills all child processes on `Ctrl+C`.

## 3.1 Running

```bash
cd chainsentinel
./start.sh
```

Output ends with:

```
=== ChainSentinel Ready ===
  Frontend:  http://localhost:5173
  API:       http://localhost:8000
  ES:        http://localhost:9200
  Ollama:    http://localhost:11434
  Anvil:     http://localhost:8545     (simulation mode only)

Press Ctrl+C to stop all services
```

## 3.2 Stopping

`Ctrl+C` in the terminal kills the children spawned by the script. The
ES container keeps running because it was started detached — stop it
with:

```bash
docker stop chainsentinel-es
```

## 3.3 Mode switching

Edit `config.json`:

```json
{
  "rpc_url": "https://eth-mainnet.g.alchemy.com/v2/<key>",
  "chain_id": 1,
  "mode": "mainnet",
  ...
}
```

`start.sh` will skip Anvil. Everything else is unchanged. Same for
`mode: "testnet"` with a Sepolia endpoint and `chain_id: 11155111`.
