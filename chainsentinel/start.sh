#!/usr/bin/env bash
# ChainSentinel — one-command startup
# Brings up: Elasticsearch, Ollama, Anvil (simulation mode), FastAPI server, Vite dev server
set -e

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
CONFIG="$ROOT_DIR/config.json"

# Read mode from config.json
MODE=$(python3 -c "import json; print(json.load(open('$CONFIG'))['mode'])" 2>/dev/null || echo "simulation")
OLLAMA_MODEL=$(python3 -c "import json; print(json.load(open('$CONFIG'))['ollama_model'])" 2>/dev/null || echo "gemma3:1b")

echo "=== ChainSentinel Startup ==="
echo "Mode: $MODE"
echo "Ollama model: $OLLAMA_MODEL"
echo ""

# --- 1. Elasticsearch (Docker) -----------------------------------------------
echo "[1/5] Starting Elasticsearch..."
if docker ps --format '{{.Names}}' | grep -q chainsentinel-es; then
    echo "  Elasticsearch already running"
else
    docker run -d \
        --name chainsentinel-es \
        -p 9200:9200 \
        -e "discovery.type=single-node" \
        -e "xpack.security.enabled=false" \
        -e "ES_JAVA_OPTS=-Xms512m -Xmx512m" \
        elasticsearch:8.12.0 \
        > /dev/null 2>&1 || echo "  Container exists, starting..." && docker start chainsentinel-es > /dev/null 2>&1 || true
    echo "  Waiting for Elasticsearch..."
    for i in $(seq 1 30); do
        if curl -s http://localhost:9200/_cluster/health > /dev/null 2>&1; then
            echo "  Elasticsearch ready"
            break
        fi
        sleep 2
    done
fi

# --- 2. Ollama ----------------------------------------------------------------
echo "[2/5] Starting Ollama..."
if pgrep -x ollama > /dev/null 2>&1; then
    echo "  Ollama already running"
else
    ollama serve > /dev/null 2>&1 &
    sleep 2
    echo "  Ollama started"
fi

# Pull model if not present
if ! ollama list 2>/dev/null | grep -q "$OLLAMA_MODEL"; then
    echo "  Pulling $OLLAMA_MODEL..."
    ollama pull "$OLLAMA_MODEL"
else
    echo "  Model $OLLAMA_MODEL already available"
fi

# --- 3. Anvil (simulation mode only) -----------------------------------------
if [ "$MODE" = "simulation" ]; then
    echo "[3/5] Starting Anvil..."
    if pgrep -f "anvil" > /dev/null 2>&1; then
        echo "  Anvil already running"
    else
        anvil --chain-id 31337 --host 0.0.0.0 > /dev/null 2>&1 &
        sleep 1
        echo "  Anvil started on port 8545"
    fi
else
    echo "[3/5] Skipping Anvil (mode: $MODE)"
fi

# --- 4. FastAPI server --------------------------------------------------------
echo "[4/5] Starting FastAPI server..."
cd "$ROOT_DIR"
if [ -d ".venv" ]; then
    source .venv/bin/activate
fi
uvicorn server:app --host 0.0.0.0 --port 8000 --reload > /dev/null 2>&1 &
sleep 1
echo "  FastAPI server started on port 8000"

# --- 5. Vite dev server -------------------------------------------------------
echo "[5/5] Starting Vite dev server..."
cd "$ROOT_DIR/frontend"
if [ ! -d "node_modules" ]; then
    echo "  Installing frontend dependencies..."
    npm install > /dev/null 2>&1
fi
npm run dev > /dev/null 2>&1 &
sleep 2
echo "  Vite dev server started on port 5173"

echo ""
echo "=== ChainSentinel Ready ==="
echo "  Frontend:  http://localhost:5173"
echo "  API:       http://localhost:8000"
echo "  ES:        http://localhost:9200"
echo "  Ollama:    http://localhost:11434"
if [ "$MODE" = "simulation" ]; then
    echo "  Anvil:     http://localhost:8545"
fi
echo ""
echo "Press Ctrl+C to stop all services"

# Wait and cleanup on exit
trap 'echo "Shutting down..."; kill $(jobs -p) 2>/dev/null; exit 0' INT TERM
wait
