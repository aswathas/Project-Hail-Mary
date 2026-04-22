#!/usr/bin/env bash
# ChainSentinel Full Demo
# Runs: Docker (ES + Kibana) → Anvil → Foundry simulation → Pipeline → Kibana setup
set -e

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
CHAINSENTINEL_DIR="$ROOT_DIR/chainsentinel"
SIMULATIONS_DIR="$ROOT_DIR/simulations"
VENV="$CHAINSENTINEL_DIR/.venv"

# Detect Python in venv
if [ -f "$VENV/Scripts/python.exe" ]; then
    PYTHON="$VENV/Scripts/python.exe"
elif [ -f "$VENV/bin/python" ]; then
    PYTHON="$VENV/bin/python"
else
    PYTHON="python"
fi

# Anvil pre-funded test accounts (Hardhat/Anvil defaults)
export DEPLOYER_KEY="0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"
export USER1_KEY="0x59c6995e998f97a5a0044966f0945389dc9e86dae88c7a8412f4603b6b78690d"
export USER2_KEY="0x5de4111afa1a4b94908f83103eb1f1706367c2e68ca870fc3fb9a804cdab365a"
export USER3_KEY="0x7c852118294e51e653712a81e05800f419141751be58f605c371e15141b007a6"
export USER4_KEY="0x47e179ec197488593b187f80a00eb0da91f1b9d0b13f8733639f19c30a34926a"
export USER5_KEY="0x8b3a350cf5c34c9194ca85829a2df0ec3153be0318b5e2d3348e872092edffba"
export ATTACKER_KEY="0x92db14e403b83dfe3df233f83dfa3a0d7096f21ca9b0d6d6b8d88b2b4ec1564e"
export FRESH1_KEY="0x4bbbf85ce3377467afe5d46f804f221813b2bb87f24d81f60f1fcdbf7cbf4356"
export FRESH2_KEY="0xdbda1821b80551c9d65939329250298aa3472ba22feea921c0cf5d620ea67b97"
export FRESH3_KEY="0x2a871d0798f97d79848a013d4936a73bf4cc922c825d33c1cf7073dff6d409c6"

echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "║       ChainSentinel — Full Demo                          ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""

# --- Step 1: Elasticsearch + Kibana ------------------------------------------
echo "[1/5] Starting Elasticsearch + Kibana (Docker)..."
cd "$ROOT_DIR"

# Check each container using docker ps filters (avoids CRLF parse issues)
_container_running() { docker ps -q --filter "name=^$1$" 2>/dev/null | grep -q .; }
_container_exists()  { docker ps -aq --filter "name=^$1$" 2>/dev/null | grep -q .; }

all_running=true
for cname in chainsentinel-es chainsentinel-kibana; do
    if _container_running "$cname"; then
        echo "  $cname already running"
    elif _container_exists "$cname"; then
        echo "  Starting stopped container $cname..."
        docker start "$cname" > /dev/null
    else
        all_running=false
    fi
done

if [ "$all_running" = false ]; then
    echo "  Launching via docker compose..."
    docker compose up -d
fi

echo "  Waiting for Elasticsearch..."
for i in $(seq 1 60); do
    if curl -s http://localhost:9200/_cluster/health > /dev/null 2>&1; then
        echo "  Elasticsearch ready (${i}s)"
        break
    fi
    sleep 2
done

# Verify ES is actually up
if ! curl -s http://localhost:9200/_cluster/health > /dev/null 2>&1; then
    echo "ERROR: Elasticsearch not reachable. Is Docker Desktop running?"
    echo "  Start Docker Desktop and re-run this script."
    exit 1
fi

# --- Step 2: Anvil -----------------------------------------------------------
echo ""
echo "[2/5] Starting Anvil (fresh chain)..."
# Kill any existing Anvil so the simulation always starts from block 1
taskkill //F //IM anvil.exe > /dev/null 2>&1 || true
sleep 1
if true; then
    anvil --chain-id 31337 --host 127.0.0.1 --accounts 10 --balance 1000000 > /tmp/anvil.log 2>&1 &
    ANVIL_PID=$!
    # Wait up to 10s for port to open
    for i in $(seq 1 10); do
        sleep 1
        if curl -s --max-time 1 http://127.0.0.1:8545 -X POST \
            -H "Content-Type: application/json" \
            -d '{"jsonrpc":"2.0","method":"eth_blockNumber","params":[],"id":1}' \
            > /dev/null 2>&1; then
            echo "  Anvil started (PID $ANVIL_PID)"
            break
        fi
        if [ "$i" -eq 10 ]; then
            echo "ERROR: Anvil failed to start. Log:"
            cat /tmp/anvil.log
            exit 1
        fi
    done
fi

# --- Step 3: Foundry simulation ----------------------------------------------
echo ""
echo "[3/5] Running demo-500 simulation (~500 transactions)..."
SCENARIO_DIR="$SIMULATIONS_DIR/scenarios/demo-500"

cd "$SCENARIO_DIR"
echo "  Running forge script..."
forge script script/RunAll.s.sol --rpc-url http://127.0.0.1:8545 --broadcast 2>&1 | tail -5

echo "  Simulation complete"

# --- Step 4: ChainSentinel pipeline ------------------------------------------
# Get the actual latest block from Anvil (simulation may produce fewer than 100 blocks)
LATEST_BLOCK=$(curl -s http://127.0.0.1:8545 -X POST \
    -H "Content-Type: application/json" \
    -d '{"jsonrpc":"2.0","method":"eth_blockNumber","params":[],"id":1}' \
    | grep -o '"result":"0x[0-9a-f]*"' | grep -o '0x[0-9a-f]*' | head -1)
# Convert hex to decimal
BLOCK_TO=$(printf "%d" "$LATEST_BLOCK" 2>/dev/null || echo "50")

echo ""
echo "[4/5] Running ChainSentinel pipeline (blocks 1-${BLOCK_TO})..."
cd "$CHAINSENTINEL_DIR"

"$PYTHON" -c "
import asyncio
import sys
sys.path.insert(0, '.')

from e2e_helpers.pipeline_runner import run_pipeline_for_scenario
from e2e_helpers.validator import Validator

BLOCK_TO = int('${BLOCK_TO}')

async def main():
    print(f'  Executing pipeline (blocks 1-{BLOCK_TO})...')
    result = await run_pipeline_for_scenario(
        scenario_name='demo-500',
        block_from=1,
        block_to=BLOCK_TO,
    )
    stats = result['stats']
    print(f'  Raw docs:     {stats[\"raw_docs\"]}')
    print(f'  Decoded docs: {stats[\"decoded_docs\"]}')
    print(f'  Derived docs: {stats[\"derived_docs\"]}')
    print(f'  Signals:      {stats[\"signal_docs\"]}')
    print(f'  Alerts:       {stats[\"alert_docs\"]}')
    print(f'  Investigation: {result[\"investigation_id\"]}')

    v = Validator()
    vr = v.validate_all([result['investigation_id']])
    print()
    v.print_summary(vr)

asyncio.run(main())
"

# --- Step 5: Kibana setup ----------------------------------------------------
echo ""
echo "[5/5] Setting up Kibana dashboards..."
echo "  Waiting for Kibana to be ready..."
for i in $(seq 1 60); do
    STATUS=$(curl -s http://localhost:5601/api/status 2>/dev/null)
    if echo "$STATUS" | grep -q '"available"'; then
        echo "  Kibana ready (${i}s)"
        break
    fi
    sleep 3
done

cd "$CHAINSENTINEL_DIR"
"$PYTHON" kibana_setup.py

# --- Done -------------------------------------------------------------------
echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "║   Demo complete! Open Kibana to explore the findings:   ║"
echo "║                                                          ║"
echo "║   Kibana:    http://localhost:5601                       ║"
echo "║   Dashboard: Analytics → Dashboards → ChainSentinel     ║"
echo "║   Discover:  Analytics → Discover (forensics data view) ║"
echo "║   Dev Tools: Management → Dev Tools (ES|QL queries)     ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""
