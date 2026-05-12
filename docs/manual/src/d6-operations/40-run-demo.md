# 4. `run_demo.sh` — end-to-end demo

`run_demo.sh` (at the project root) automates a complete demo:

1. Starts the stack via `start.sh` (or docker-compose, depending on the
   variant).
2. Deploys a chosen scenario (default `demo-500`) on Anvil.
3. Submits an analysis request to the FastAPI server.
4. Waits for completion, then opens the frontend at the resulting
   investigation URL.

![End-to-end demo storyboard](../../diagrams/rendered/14-demo-storyboard.png)

## 4.1 Running

```bash
./run_demo.sh                  # uses demo-500
./run_demo.sh reentrancy-drain # any scenario from D7
```

## 4.2 What an analyst should see

1. **Terminal:** sequential `[1/5]` … `[5/5]` startup banners, then
   `=== ChainSentinel Ready ===`.
2. **Anvil log (foreground or `tail`):** ~500 transactions for the demo
   scenario, then the attack transaction.
3. **Frontend at `http://localhost:5173`:**
   - Sidebar shows a new investigation.
   - `PipelineFeed` streams phase events.
   - On completion, `InvestigationView` flips to the verdict report.
   - `EntityGraph` renders the fund-flow d3 layout.
   - `CopilotPanel` is `Ready` — analyst can ask follow-ups.
