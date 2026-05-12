# 9. Upgrade procedure

ChainSentinel follows a simple upgrade discipline: pull, install, restart.

## 9.1 Standard upgrade

```bash
cd /path/to/Project_Hail_Mary
git pull
cd chainsentinel
pip install -r requirements.txt --upgrade
cd frontend
npm install
cd ..
./start.sh
```

The ES indices persist (volume-backed) and the signal/pattern engines
discover new `.esql` / `.eql` files automatically.

## 9.2 ES mapping migration

If `es/mappings/forensics.json` changed in a way that adds a top-level
field, ES strict mapping accepts the change via `PUT _mapping` — apply
manually:

```bash
curl -X PUT http://localhost:9200/forensics/_mapping \
     -H 'Content-Type: application/json' \
     -d @chainsentinel/es/mappings/forensics.json
```

If the change *renames* or *retypes* a field, you must reindex. Two
options:

1. **Drop and recreate** (acceptable in dev):
   ```bash
   curl -X DELETE http://localhost:9200/forensics
   ```
   ES will recreate it on the next `/analyze` call.
2. **Reindex** (production):
   ```bash
   PUT forensics-v2/_mapping  { ... }
   POST _reindex { "source": {"index": "forensics"}, "dest": {"index": "forensics-v2"} }
   PUT forensics/_alias  { "actions": [...] }
   ```

## 9.3 Model upgrade (Ollama)

```bash
ollama pull llama3:8b
# edit config.json: "ollama_model": "llama3:8b"
# restart FastAPI (or wait for hot reload)
```

The copilot's prompt templates work with any chat-format model. Larger
models produce better reports at the cost of latency.

## 9.4 Rollback

Because nothing is destroyed by an upgrade (ES data persists, no
schema rewrites by default), rollback is `git checkout <prev>` plus
the standard install steps. The `selector_registry.json` file may
contain entries learned by the newer version — leave it; older
versions ignore unknown keys.
