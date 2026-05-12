# 7. Index lifecycle, monitoring, backups

## 7.1 Index lifecycle (ILM)

Not enabled by default. Most analysts keep all data. Sample policy for
a shared deployment that retains 180 days of evidence:

```text
PUT _ilm/policy/forensics-policy
{
  "policy": {
    "phases": {
      "hot":    { "actions": { "rollover": { "max_age": "7d", "max_size": "20gb" } } },
      "warm":   { "min_age": "14d", "actions": { "set_priority": { "priority": 50 }, "forcemerge": { "max_num_segments": 1 } } },
      "delete": { "min_age": "180d", "actions": { "delete": {} } }
    }
  }
}

PUT forensics/_settings   { "index.lifecycle.name": "forensics-policy" }
PUT forensics-raw/_settings { "index.lifecycle.name": "forensics-policy" }
```

## 7.2 Resource sizing

Single-analyst laptop (default `docker-compose.yml`):
- ES heap 1 GB, 1 shard, 0 replicas — fine for hundreds of
  investigations.

Team deployment:
- ES heap 4–8 GB per node, 2 nodes minimum, 1 replica.
- Move ES off the analyst's laptop to a shared VM/cluster.
- Set `es_bulk_chunk_size` higher (1000–2000).

## 7.3 Health monitoring

The `/health` endpoint is the lightest monitor:

```bash
curl -s http://localhost:8000/health | jq
# { "rpc": "ok", "elasticsearch": "ok", "ollama": "ok" }
```

For production, scrape this every 30 s into your monitoring system and
alert when any value is `error` for ≥ 2 min.

Additional metrics to watch:

| Metric | Source |
|--------|--------|
| ES cluster status | `GET /_cluster/health` |
| Anvil block height | `GET /` JSON-RPC `eth_blockNumber` |
| FastAPI request rate | Add `prometheus-fastapi-instrumentator` if needed |
| Ollama queue length | `ollama ps` |

## 7.4 Backups

ES has snapshot/restore built in:

```text
PUT _snapshot/forensics_repo
{
  "type": "fs",
  "settings": { "location": "/mnt/backups/forensics" }
}

PUT _snapshot/forensics_repo/snap-20260512?wait_for_completion=true
{
  "indices": "forensics,forensics-raw",
  "include_global_state": false
}
```

Schedule weekly with cron + `curl` or use Elastic SLM (Snapshot
Lifecycle Management). The `selector_registry.json` file should also
be backed up alongside the ES snapshots — it grows over time and is
not regenerated automatically.
