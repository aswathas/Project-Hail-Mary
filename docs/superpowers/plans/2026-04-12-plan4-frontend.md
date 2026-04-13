# ChainSentinel Frontend — Implementation Plan (Plan 4 of 6)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the React frontend with Vite — Wise design system CSS, all 6 components (Sidebar, PipelineFeed, InvestigationView, EntityGraph, CopilotPanel, StoredAnalyses), custom hooks (useAnalysis, useElasticsearch, useOllama, useLocalStorage), and API modules (pipeline, elasticsearch, ollama). After this plan, the analyst has a fully interactive investigation workspace.

**Architecture:** Single-page React 18 app built with Vite. Three-column layout: Sidebar (252px left), Workspace (center, state-machine driven), CopilotPanel (280px right). The workspace transitions between PipelineFeed (running state — SSE log stream) and InvestigationView (complete state — timeline + signals + entity graph). All state managed via hooks. No Redux. Direct ES queries from frontend for investigation data. Ollama API calls for copilot. LocalStorage for case persistence.

**Tech Stack:** React 18, Vite 5, D3.js, plain CSS with CSS variables (Wise design system), Vitest + React Testing Library

**Spec reference:** `docs/superpowers/specs/2026-04-12-chainsentinel-design.md` sections 10, 11

**Depends on:** Plan 1 (FastAPI server endpoints), Plan 2 (signal/pattern data in ES), Plan 3 (correlation data in ES)

---

## File Structure

```
chainsentinel/frontend/
├── package.json
├── vite.config.js
├── index.html
├── vitest.config.js
└── src/
    ├── main.jsx
    ├── App.jsx
    ├── App.css                       ← Wise design system CSS variables + layout
    ├── components/
    │   ├── Sidebar.jsx
    │   ├── Sidebar.css
    │   ├── PipelineFeed.jsx
    │   ├── PipelineFeed.css
    │   ├── InvestigationView.jsx
    │   ├── InvestigationView.css
    │   ├── EntityGraph.jsx
    │   ├── EntityGraph.css
    │   ├── CopilotPanel.jsx
    │   ├── CopilotPanel.css
    │   ├── StoredAnalyses.jsx
    │   └── StoredAnalyses.css
    ├── hooks/
    │   ├── useAnalysis.js
    │   ├── useElasticsearch.js
    │   ├── useOllama.js
    │   └── useLocalStorage.js
    ├── api/
    │   ├── pipeline.js
    │   ├── elasticsearch.js
    │   └── ollama.js
    └── __tests__/
        ├── setup.js
        ├── useAnalysis.test.js
        ├── useLocalStorage.test.js
        ├── Sidebar.test.jsx
        ├── PipelineFeed.test.jsx
        └── InvestigationView.test.jsx
```

---

### Task 1: Project Scaffolding

**Files:**
- Create: `chainsentinel/frontend/package.json`
- Create: `chainsentinel/frontend/vite.config.js`
- Create: `chainsentinel/frontend/vitest.config.js`
- Create: `chainsentinel/frontend/index.html`
- Create: `chainsentinel/frontend/src/main.jsx`

- [ ] **Step 1: Create directory structure**

```bash
cd /mnt/c/Users/aswat/OneDrive/Desktop/Projects/Project_Hail_Mary
mkdir -p chainsentinel/frontend/src/{components,hooks,api,__tests__}
```

- [ ] **Step 2: Create package.json**

`chainsentinel/frontend/package.json`:

```json
{
  "name": "chainsentinel-frontend",
  "private": true,
  "version": "0.1.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "preview": "vite preview",
    "test": "vitest run",
    "test:watch": "vitest"
  },
  "dependencies": {
    "d3": "^7.9.0",
    "react": "^18.3.1",
    "react-dom": "^18.3.1"
  },
  "devDependencies": {
    "@testing-library/jest-dom": "^6.4.0",
    "@testing-library/react": "^14.2.0",
    "@types/react": "^18.3.0",
    "@vitejs/plugin-react": "^4.2.0",
    "jsdom": "^24.0.0",
    "vite": "^5.4.0",
    "vitest": "^1.6.0"
  }
}
```

- [ ] **Step 3: Create vite.config.js**

`chainsentinel/frontend/vite.config.js`:

```javascript
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/analyze': 'http://localhost:8000',
      '/analysis': 'http://localhost:8000',
      '/health': 'http://localhost:8000',
      '/simulate': 'http://localhost:8000',
    },
  },
});
```

- [ ] **Step 4: Create vitest.config.js**

`chainsentinel/frontend/vitest.config.js`:

```javascript
import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    setupFiles: ['./src/__tests__/setup.js'],
    globals: true,
  },
});
```

- [ ] **Step 5: Create test setup**

`chainsentinel/frontend/src/__tests__/setup.js`:

```javascript
import '@testing-library/jest-dom';
```

- [ ] **Step 6: Create index.html**

`chainsentinel/frontend/index.html`:

```html
<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>ChainSentinel — EVM Forensics</title>
    <link rel="preconnect" href="https://fonts.googleapis.com" />
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;900&family=JetBrains+Mono:wght@400;600&display=swap" rel="stylesheet" />
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.jsx"></script>
  </body>
</html>
```

- [ ] **Step 7: Create main.jsx**

`chainsentinel/frontend/src/main.jsx`:

```jsx
import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';
import './App.css';

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
```

- [ ] **Step 8: Install dependencies and verify**

```bash
cd /mnt/c/Users/aswat/OneDrive/Desktop/Projects/Project_Hail_Mary/chainsentinel/frontend
npm install
```

- [ ] **Step 9: Commit**

```bash
git add chainsentinel/frontend/package.json chainsentinel/frontend/vite.config.js chainsentinel/frontend/vitest.config.js chainsentinel/frontend/index.html chainsentinel/frontend/src/main.jsx chainsentinel/frontend/src/__tests__/setup.js
git commit -m "feat: frontend scaffolding with Vite, React 18, Vitest, D3.js"
```

---

### Task 2: Wise Design System CSS

**Files:**
- Create: `chainsentinel/frontend/src/App.css`

- [ ] **Step 1: Create App.css with Wise design system**

`chainsentinel/frontend/src/App.css`:

```css
/* ── Wise Design System — CSS Variables ──────────────────────────────── */
:root {
  /* Colors */
  --near-black: #0e0f0c;
  --wise-green: #9fe870;
  --dark-green: #163300;
  --light-mint: #e2f6d5;
  --danger-red: #d03238;
  --warning-yellow: #ffd11a;
  --gray: #868685;
  --gray-light: #c4c4c3;
  --white: #ffffff;
  --off-white: #f7f7f6;
  --surface: #fafaf9;
  --border: rgba(14, 15, 12, 0.12);

  /* Severity colors */
  --severity-crit: #d03238;
  --severity-high: #e67e22;
  --severity-med: #3498db;
  --severity-low: #868685;

  /* Typography */
  --font-body: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
  --font-mono: 'JetBrains Mono', 'Fira Code', monospace;
  --fw-normal: 400;
  --fw-semibold: 600;
  --fw-black: 900;

  /* Layout */
  --sidebar-width: 252px;
  --copilot-width: 280px;
  --header-height: 0px;

  /* Radii */
  --radius-pill: 9999px;
  --radius-card: 30px;
  --radius-sm: 12px;
  --radius-xs: 8px;

  /* Shadows */
  --shadow-ring: rgba(14, 15, 12, 0.12) 0px 0px 0px 1px;
  --shadow-hover: rgba(14, 15, 12, 0.08) 0px 2px 8px;
}

/* ── Reset ───────────────────────────────────────────────────────────── */
*,
*::before,
*::after {
  box-sizing: border-box;
  margin: 0;
  padding: 0;
}

html {
  font-size: 14px;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

body {
  font-family: var(--font-body);
  font-weight: var(--fw-semibold);
  font-feature-settings: "calt";
  color: var(--near-black);
  background: var(--near-black);
  overflow: hidden;
  height: 100vh;
}

#root {
  height: 100vh;
  display: flex;
}

/* ── App Layout — Three Columns ──────────────────────────────────────── */
.app-layout {
  display: flex;
  width: 100%;
  height: 100vh;
}

.app-sidebar {
  width: var(--sidebar-width);
  min-width: var(--sidebar-width);
  height: 100vh;
  background: var(--white);
  border-right: 1px solid var(--border);
  overflow-y: auto;
  display: flex;
  flex-direction: column;
}

.app-workspace {
  flex: 1;
  height: 100vh;
  overflow-y: auto;
  background: var(--near-black);
  color: var(--white);
}

.app-copilot {
  width: var(--copilot-width);
  min-width: var(--copilot-width);
  height: 100vh;
  background: var(--white);
  border-left: 1px solid var(--border);
  display: flex;
  flex-direction: column;
}

/* ── Shared Component Styles ─────────────────────────────────────────── */

/* Pill buttons */
.btn-pill {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 5px 16px;
  border-radius: var(--radius-pill);
  border: none;
  font-family: var(--font-body);
  font-weight: var(--fw-semibold);
  font-size: 0.875rem;
  cursor: pointer;
  transition: transform 0.15s ease;
  user-select: none;
}

.btn-pill:hover {
  transform: scale(1.05);
}

.btn-pill:active {
  transform: scale(0.95);
}

.btn-pill--primary {
  background: var(--wise-green);
  color: var(--dark-green);
}

.btn-pill--primary:disabled {
  background: var(--gray-light);
  color: var(--gray);
  cursor: not-allowed;
  transform: none;
}

.btn-pill--secondary {
  background: var(--off-white);
  color: var(--near-black);
  box-shadow: var(--shadow-ring);
}

.btn-pill--danger {
  background: var(--danger-red);
  color: var(--white);
}

/* Cards */
.card {
  background: var(--white);
  border-radius: var(--radius-card);
  box-shadow: var(--shadow-ring);
  padding: 20px;
}

.card--dark {
  background: rgba(255, 255, 255, 0.06);
  border: 1px solid rgba(255, 255, 255, 0.1);
  color: var(--white);
}

/* Severity badges */
.badge {
  display: inline-flex;
  align-items: center;
  padding: 2px 10px;
  border-radius: var(--radius-pill);
  font-size: 0.75rem;
  font-weight: var(--fw-semibold);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.badge--crit {
  background: var(--severity-crit);
  color: var(--white);
}

.badge--high {
  background: var(--severity-high);
  color: var(--white);
}

.badge--med {
  background: var(--severity-med);
  color: var(--white);
}

.badge--low {
  background: var(--off-white);
  color: var(--gray);
}

/* Monospace text */
.mono {
  font-family: var(--font-mono);
  font-size: 0.8125rem;
}

/* Status dots */
.status-dot {
  display: inline-block;
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.status-dot--ok {
  background: var(--wise-green);
}

.status-dot--error {
  background: var(--danger-red);
}

.status-dot--pending {
  background: var(--warning-yellow);
}

/* Heading styles */
h1, h2, h3 {
  font-weight: var(--fw-black);
  letter-spacing: -0.02em;
}

/* Input fields */
.input-field {
  width: 100%;
  padding: 6px 12px;
  border: 1px solid var(--border);
  border-radius: var(--radius-xs);
  font-family: var(--font-mono);
  font-size: 0.8125rem;
  background: var(--off-white);
  color: var(--near-black);
  outline: none;
  transition: border-color 0.15s;
}

.input-field:focus {
  border-color: var(--wise-green);
}

/* Scrollbar styling */
::-webkit-scrollbar {
  width: 6px;
}

::-webkit-scrollbar-track {
  background: transparent;
}

::-webkit-scrollbar-thumb {
  background: var(--gray-light);
  border-radius: 3px;
}
```

- [ ] **Step 2: Commit**

```bash
git add chainsentinel/frontend/src/App.css
git commit -m "feat: Wise design system CSS with variables, layout, shared component styles"
```

---

### Task 3: API Modules

**Files:**
- Create: `chainsentinel/frontend/src/api/pipeline.js`
- Create: `chainsentinel/frontend/src/api/elasticsearch.js`
- Create: `chainsentinel/frontend/src/api/ollama.js`

- [ ] **Step 1: Create pipeline.js**

`chainsentinel/frontend/src/api/pipeline.js`:

```javascript
/**
 * Pipeline API — communicates with FastAPI backend.
 * POST /analyze — starts pipeline, returns SSE stream
 * GET /health — checks service connectivity
 */

const BASE_URL = '';

export async function checkHealth() {
  const res = await fetch(`${BASE_URL}/health`);
  if (!res.ok) throw new Error(`Health check failed: ${res.status}`);
  return res.json();
}

export function startAnalysis(config) {
  const url = `${BASE_URL}/analyze`;
  const eventSource = new EventSource(url + '?' + new URLSearchParams({
    mode: config.mode,
    rpc_url: config.rpcUrl,
    target: config.target || '',
    investigation_id: config.investigationId,
    manifest_path: config.manifestPath || '',
    from_block: config.fromBlock || '',
    to_block: config.toBlock || '',
  }));
  return eventSource;
}

export async function startAnalysisPost(config) {
  const res = await fetch(`${BASE_URL}/analyze`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      mode: config.mode,
      rpc_url: config.rpcUrl,
      target: config.target || '',
      investigation_id: config.investigationId,
      manifest_path: config.manifestPath || '',
      from_block: config.fromBlock ? parseInt(config.fromBlock) : null,
      to_block: config.toBlock ? parseInt(config.toBlock) : null,
    }),
  });
  if (!res.ok) throw new Error(`Analysis failed: ${res.status}`);
  return res.body;
}

export async function getAnalysis(investigationId) {
  const res = await fetch(`${BASE_URL}/analysis/${investigationId}`);
  if (!res.ok) throw new Error(`Fetch analysis failed: ${res.status}`);
  return res.json();
}

export async function runSimulation(scenario) {
  const res = await fetch(`${BASE_URL}/simulate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ scenario }),
  });
  if (!res.ok) throw new Error(`Simulation failed: ${res.status}`);
  return res.json();
}
```

- [ ] **Step 2: Create elasticsearch.js**

`chainsentinel/frontend/src/api/elasticsearch.js`:

```javascript
/**
 * Elasticsearch API — direct ES queries from frontend.
 * Used for investigation data retrieval after pipeline completes.
 */

const DEFAULT_ES_URL = 'http://localhost:9200';

export function createEsClient(esUrl = DEFAULT_ES_URL) {
  return {
    async search(index, query, size = 100) {
      const res = await fetch(`${esUrl}/${index}/_search`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query, size, sort: [{ block_number: 'asc' }] }),
      });
      if (!res.ok) throw new Error(`ES search failed: ${res.status}`);
      return res.json();
    },

    async getSignals(investigationId) {
      return this.search('forensics', {
        bool: {
          must: [
            { term: { investigation_id: investigationId } },
            { term: { layer: 'signal' } },
          ],
        },
      }, 500);
    },

    async getAlerts(investigationId) {
      return this.search('forensics', {
        bool: {
          must: [
            { term: { investigation_id: investigationId } },
            { term: { layer: 'alert' } },
          ],
        },
      }, 100);
    },

    async getDerived(investigationId, derivedType = null) {
      const must = [
        { term: { investigation_id: investigationId } },
        { term: { layer: 'derived' } },
      ];
      if (derivedType) {
        must.push({ term: { derived_type: derivedType } });
      }
      return this.search('forensics', { bool: { must } }, 1000);
    },

    async getAttackerData(investigationId) {
      return this.search('forensics', {
        bool: {
          must: [
            { term: { investigation_id: investigationId } },
            { term: { layer: 'attacker' } },
          ],
        },
      }, 100);
    },

    async getTimeline(investigationId) {
      const res = await fetch(`${esUrl}/forensics/_search`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          query: {
            bool: {
              must: [
                { term: { investigation_id: investigationId } },
                { terms: { layer: ['signal', 'alert', 'derived'] } },
              ],
            },
          },
          size: 500,
          sort: [{ block_number: 'asc' }, { '@timestamp': 'asc' }],
        }),
      });
      if (!res.ok) throw new Error(`ES timeline failed: ${res.status}`);
      return res.json();
    },
  };
}
```

- [ ] **Step 3: Create ollama.js**

`chainsentinel/frontend/src/api/ollama.js`:

```javascript
/**
 * Ollama API — chat and report generation via local LLM.
 */

const DEFAULT_OLLAMA_URL = 'http://localhost:11434';

export function createOllamaClient(ollamaUrl = DEFAULT_OLLAMA_URL) {
  return {
    async chat(messages, model = 'gemma3:1b', temperature = 0.2) {
      const res = await fetch(`${ollamaUrl}/api/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          model,
          messages,
          stream: false,
          options: { temperature },
        }),
      });
      if (!res.ok) throw new Error(`Ollama chat failed: ${res.status}`);
      const data = await res.json();
      return data.message?.content || '';
    },

    async chatStream(messages, model = 'gemma3:1b', temperature = 0.2) {
      const res = await fetch(`${ollamaUrl}/api/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          model,
          messages,
          stream: true,
          options: { temperature },
        }),
      });
      if (!res.ok) throw new Error(`Ollama stream failed: ${res.status}`);
      return res.body;
    },

    async checkModel(model = 'gemma3:1b') {
      try {
        const res = await fetch(`${ollamaUrl}/api/tags`);
        if (!res.ok) return false;
        const data = await res.json();
        return data.models?.some(m => m.name === model) || false;
      } catch {
        return false;
      }
    },
  };
}
```

- [ ] **Step 4: Commit**

```bash
git add chainsentinel/frontend/src/api/
git commit -m "feat: API modules for pipeline, Elasticsearch, and Ollama"
```

---

### Task 4: Custom Hooks

**Files:**
- Create: `chainsentinel/frontend/src/hooks/useLocalStorage.js`
- Create: `chainsentinel/frontend/src/hooks/useAnalysis.js`
- Create: `chainsentinel/frontend/src/hooks/useElasticsearch.js`
- Create: `chainsentinel/frontend/src/hooks/useOllama.js`
- Create: `chainsentinel/frontend/src/__tests__/useLocalStorage.test.js`
- Create: `chainsentinel/frontend/src/__tests__/useAnalysis.test.js`

- [ ] **Step 1: Write useLocalStorage test**

`chainsentinel/frontend/src/__tests__/useLocalStorage.test.js`:

```javascript
import { renderHook, act } from '@testing-library/react';
import { useLocalStorage } from '../hooks/useLocalStorage';

describe('useLocalStorage', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it('returns initial value when no stored value exists', () => {
    const { result } = renderHook(() => useLocalStorage('test-key', 'default'));
    expect(result.current[0]).toBe('default');
  });

  it('returns stored value when it exists', () => {
    localStorage.setItem('test-key', JSON.stringify('stored-value'));
    const { result } = renderHook(() => useLocalStorage('test-key', 'default'));
    expect(result.current[0]).toBe('stored-value');
  });

  it('updates localStorage when setValue is called', () => {
    const { result } = renderHook(() => useLocalStorage('test-key', 'default'));
    act(() => {
      result.current[1]('new-value');
    });
    expect(result.current[0]).toBe('new-value');
    expect(JSON.parse(localStorage.getItem('test-key'))).toBe('new-value');
  });

  it('handles object values', () => {
    const obj = { id: 'INV-001', signals: 5 };
    const { result } = renderHook(() => useLocalStorage('test-obj', null));
    act(() => {
      result.current[1](obj);
    });
    expect(result.current[0]).toEqual(obj);
  });

  it('handles array values', () => {
    const { result } = renderHook(() => useLocalStorage('test-arr', []));
    act(() => {
      result.current[1]([{ id: 1 }, { id: 2 }]);
    });
    expect(result.current[0]).toHaveLength(2);
  });
});
```

- [ ] **Step 2: Implement useLocalStorage**

`chainsentinel/frontend/src/hooks/useLocalStorage.js`:

```javascript
import { useState, useCallback } from 'react';

export function useLocalStorage(key, initialValue) {
  const [storedValue, setStoredValue] = useState(() => {
    try {
      const item = localStorage.getItem(key);
      return item ? JSON.parse(item) : initialValue;
    } catch (error) {
      console.error(`Error reading localStorage key "${key}":`, error);
      return initialValue;
    }
  });

  const setValue = useCallback((value) => {
    try {
      const valueToStore = value instanceof Function ? value(storedValue) : value;
      setStoredValue(valueToStore);
      localStorage.setItem(key, JSON.stringify(valueToStore));
    } catch (error) {
      console.error(`Error setting localStorage key "${key}":`, error);
    }
  }, [key, storedValue]);

  return [storedValue, setValue];
}
```

- [ ] **Step 3: Write useAnalysis test**

`chainsentinel/frontend/src/__tests__/useAnalysis.test.js`:

```javascript
import { renderHook, act } from '@testing-library/react';
import { useAnalysis } from '../hooks/useAnalysis';

describe('useAnalysis', () => {
  it('starts in idle state', () => {
    const { result } = renderHook(() => useAnalysis());
    expect(result.current.state).toBe('idle');
    expect(result.current.logs).toEqual([]);
    expect(result.current.stats).toEqual({
      blocks: 0, txs: 0, signals: 0, indexed: 0,
    });
  });

  it('transitions to running when startAnalysis is called', () => {
    const { result } = renderHook(() => useAnalysis());

    // Mock EventSource
    const mockEventSource = {
      addEventListener: vi.fn(),
      close: vi.fn(),
    };
    global.EventSource = vi.fn(() => mockEventSource);

    act(() => {
      result.current.startRun({ mode: 'range', rpcUrl: 'http://localhost:8545' });
    });

    expect(result.current.state).toBe('running');
  });

  it('addLog appends to logs array', () => {
    const { result } = renderHook(() => useAnalysis());

    act(() => {
      result.current.addLog({
        phase: 'collector',
        msg: 'Block 5 fetched',
        severity: 'ok',
        ts: '12:04:02',
      });
    });

    expect(result.current.logs).toHaveLength(1);
    expect(result.current.logs[0].phase).toBe('collector');
  });

  it('complete transitions state and sets investigation data', () => {
    const { result } = renderHook(() => useAnalysis());

    act(() => {
      result.current.completeRun({
        investigationId: 'INV-2026-0001',
        stats: { blocks: 8, txs: 47, signals: 5, indexed: 189 },
      });
    });

    expect(result.current.state).toBe('complete');
    expect(result.current.investigationId).toBe('INV-2026-0001');
    expect(result.current.stats.blocks).toBe(8);
  });

  it('reset returns to idle', () => {
    const { result } = renderHook(() => useAnalysis());

    act(() => {
      result.current.completeRun({
        investigationId: 'INV-001',
        stats: { blocks: 1, txs: 1, signals: 0, indexed: 1 },
      });
    });

    act(() => {
      result.current.reset();
    });

    expect(result.current.state).toBe('idle');
    expect(result.current.logs).toEqual([]);
  });
});
```

- [ ] **Step 4: Implement useAnalysis**

`chainsentinel/frontend/src/hooks/useAnalysis.js`:

```javascript
import { useState, useCallback, useRef } from 'react';

/**
 * useAnalysis — SSE connection + state machine for pipeline runs.
 *
 * States: idle -> running -> complete
 *
 * During 'running': receives SSE events, updates logs and stats.
 * On 'complete': stores investigation ID and final stats.
 */
export function useAnalysis() {
  const [state, setState] = useState('idle'); // idle | running | complete
  const [logs, setLogs] = useState([]);
  const [stats, setStats] = useState({ blocks: 0, txs: 0, signals: 0, indexed: 0 });
  const [investigationId, setInvestigationId] = useState(null);
  const eventSourceRef = useRef(null);

  const addLog = useCallback((logEntry) => {
    setLogs((prev) => [...prev, logEntry]);

    // Update stats from log if it contains stat info
    if (logEntry.stats) {
      setStats(logEntry.stats);
    }
  }, []);

  const startRun = useCallback((config) => {
    setState('running');
    setLogs([]);
    setStats({ blocks: 0, txs: 0, signals: 0, indexed: 0 });
    setInvestigationId(config.investigationId || null);

    // SSE connection would be established here by the component
    // using startAnalysis from api/pipeline.js
  }, []);

  const completeRun = useCallback((data) => {
    setState('complete');
    if (data.investigationId) {
      setInvestigationId(data.investigationId);
    }
    if (data.stats) {
      setStats(data.stats);
    }

    // Close SSE connection
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }
  }, []);

  const reset = useCallback(() => {
    setState('idle');
    setLogs([]);
    setStats({ blocks: 0, txs: 0, signals: 0, indexed: 0 });
    setInvestigationId(null);

    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }
  }, []);

  const restoreCase = useCallback((caseData) => {
    setState('complete');
    setInvestigationId(caseData.investigationId);
    setStats(caseData.stats || { blocks: 0, txs: 0, signals: 0, indexed: 0 });
    setLogs(caseData.logs || []);
  }, []);

  return {
    state,
    logs,
    stats,
    investigationId,
    eventSourceRef,
    addLog,
    startRun,
    completeRun,
    reset,
    restoreCase,
  };
}
```

- [ ] **Step 5: Implement useElasticsearch**

`chainsentinel/frontend/src/hooks/useElasticsearch.js`:

```javascript
import { useState, useCallback, useMemo } from 'react';
import { createEsClient } from '../api/elasticsearch';

/**
 * useElasticsearch — ES query hook for investigation data.
 */
export function useElasticsearch(esUrl = 'http://localhost:9200') {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const client = useMemo(() => createEsClient(esUrl), [esUrl]);

  const fetchSignals = useCallback(async (investigationId) => {
    setLoading(true);
    setError(null);
    try {
      const res = await client.getSignals(investigationId);
      return res.hits?.hits?.map(h => h._source) || [];
    } catch (err) {
      setError(err.message);
      return [];
    } finally {
      setLoading(false);
    }
  }, [client]);

  const fetchAlerts = useCallback(async (investigationId) => {
    setLoading(true);
    setError(null);
    try {
      const res = await client.getAlerts(investigationId);
      return res.hits?.hits?.map(h => h._source) || [];
    } catch (err) {
      setError(err.message);
      return [];
    } finally {
      setLoading(false);
    }
  }, [client]);

  const fetchTimeline = useCallback(async (investigationId) => {
    setLoading(true);
    setError(null);
    try {
      const res = await client.getTimeline(investigationId);
      return res.hits?.hits?.map(h => h._source) || [];
    } catch (err) {
      setError(err.message);
      return [];
    } finally {
      setLoading(false);
    }
  }, [client]);

  const fetchAttackerData = useCallback(async (investigationId) => {
    setLoading(true);
    setError(null);
    try {
      const res = await client.getAttackerData(investigationId);
      return res.hits?.hits?.map(h => h._source) || [];
    } catch (err) {
      setError(err.message);
      return [];
    } finally {
      setLoading(false);
    }
  }, [client]);

  const fetchDerived = useCallback(async (investigationId, derivedType) => {
    setLoading(true);
    setError(null);
    try {
      const res = await client.getDerived(investigationId, derivedType);
      return res.hits?.hits?.map(h => h._source) || [];
    } catch (err) {
      setError(err.message);
      return [];
    } finally {
      setLoading(false);
    }
  }, [client]);

  return {
    loading,
    error,
    fetchSignals,
    fetchAlerts,
    fetchTimeline,
    fetchAttackerData,
    fetchDerived,
  };
}
```

- [ ] **Step 6: Implement useOllama**

`chainsentinel/frontend/src/hooks/useOllama.js`:

```javascript
import { useState, useCallback, useMemo } from 'react';
import { createOllamaClient } from '../api/ollama';

/**
 * useOllama — Ollama chat + report generation hook.
 */
export function useOllama(ollamaUrl = 'http://localhost:11434', model = 'gemma3:1b') {
  const [loading, setLoading] = useState(false);
  const [streaming, setStreaming] = useState(false);
  const [error, setError] = useState(null);
  const client = useMemo(() => createOllamaClient(ollamaUrl), [ollamaUrl]);

  const chat = useCallback(async (messages) => {
    setLoading(true);
    setError(null);
    try {
      const response = await client.chat(messages, model);
      return response;
    } catch (err) {
      setError(err.message);
      return null;
    } finally {
      setLoading(false);
    }
  }, [client, model]);

  const chatStream = useCallback(async (messages, onChunk) => {
    setStreaming(true);
    setError(null);
    try {
      const stream = await client.chatStream(messages, model);
      const reader = stream.getReader();
      const decoder = new TextDecoder();
      let fullText = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value);
        const lines = chunk.split('\n').filter(Boolean);

        for (const line of lines) {
          try {
            const data = JSON.parse(line);
            if (data.message?.content) {
              fullText += data.message.content;
              onChunk(fullText);
            }
          } catch {
            // Skip non-JSON lines
          }
        }
      }

      return fullText;
    } catch (err) {
      setError(err.message);
      return null;
    } finally {
      setStreaming(false);
    }
  }, [client, model]);

  const checkAvailable = useCallback(async () => {
    return client.checkModel(model);
  }, [client, model]);

  return {
    loading,
    streaming,
    error,
    chat,
    chatStream,
    checkAvailable,
  };
}
```

- [ ] **Step 7: Run hook tests**

```bash
cd /mnt/c/Users/aswat/OneDrive/Desktop/Projects/Project_Hail_Mary/chainsentinel/frontend
npx vitest run src/__tests__/useLocalStorage.test.js src/__tests__/useAnalysis.test.js
```

Expected: All PASS

- [ ] **Step 8: Commit**

```bash
git add chainsentinel/frontend/src/hooks/ chainsentinel/frontend/src/__tests__/useLocalStorage.test.js chainsentinel/frontend/src/__tests__/useAnalysis.test.js
git commit -m "feat: custom hooks — useAnalysis, useElasticsearch, useOllama, useLocalStorage"
```

---

### Task 5: Sidebar Component

**Files:**
- Create: `chainsentinel/frontend/src/components/Sidebar.jsx`
- Create: `chainsentinel/frontend/src/components/Sidebar.css`
- Create: `chainsentinel/frontend/src/__tests__/Sidebar.test.jsx`

- [ ] **Step 1: Write Sidebar test**

`chainsentinel/frontend/src/__tests__/Sidebar.test.jsx`:

```javascript
import { render, screen, fireEvent } from '@testing-library/react';
import { Sidebar } from '../components/Sidebar';

describe('Sidebar', () => {
  const defaultProps = {
    config: { rpcUrl: '', esUrl: '', ollamaUrl: '' },
    onConfigChange: vi.fn(),
    health: { rpc: false, es: false, ollama: false },
    mode: 'range',
    onModeChange: vi.fn(),
    target: {},
    onTargetChange: vi.fn(),
    onRun: vi.fn(),
    isRunning: false,
    savedCases: [],
    onRestoreCase: vi.fn(),
  };

  it('renders connection config inputs', () => {
    render(<Sidebar {...defaultProps} />);
    expect(screen.getByPlaceholderText(/rpc url/i)).toBeInTheDocument();
    expect(screen.getByPlaceholderText(/es url/i)).toBeInTheDocument();
    expect(screen.getByPlaceholderText(/ollama url/i)).toBeInTheDocument();
  });

  it('shows health status dots', () => {
    render(<Sidebar {...defaultProps} health={{ rpc: true, es: true, ollama: false }} />);
    const dots = document.querySelectorAll('.status-dot');
    expect(dots.length).toBeGreaterThanOrEqual(3);
  });

  it('renders mode selector cards', () => {
    render(<Sidebar {...defaultProps} />);
    expect(screen.getByText(/watch/i)).toBeInTheDocument();
    expect(screen.getByText(/range/i)).toBeInTheDocument();
    expect(screen.getByText(/tx analysis/i)).toBeInTheDocument();
    expect(screen.getByText(/wallet hunt/i)).toBeInTheDocument();
  });

  it('calls onModeChange when mode card is clicked', () => {
    render(<Sidebar {...defaultProps} />);
    fireEvent.click(screen.getByText(/wallet hunt/i));
    expect(defaultProps.onModeChange).toHaveBeenCalledWith('wallet');
  });

  it('shows Run Analysis button', () => {
    render(<Sidebar {...defaultProps} />);
    expect(screen.getByText(/run analysis/i)).toBeInTheDocument();
  });

  it('disables Run button when not connected', () => {
    render(<Sidebar {...defaultProps} health={{ rpc: false, es: false, ollama: false }} />);
    const btn = screen.getByText(/run analysis/i);
    expect(btn).toBeDisabled();
  });

  it('shows Running state during analysis', () => {
    render(<Sidebar {...defaultProps} isRunning={true} />);
    expect(screen.getByText(/running/i)).toBeInTheDocument();
  });

  it('displays saved cases list', () => {
    const cases = [
      { investigationId: 'INV-001', attackType: 'Reentrancy', severity: 'CRIT', timestamp: '2026-04-12' },
    ];
    render(<Sidebar {...defaultProps} savedCases={cases} />);
    expect(screen.getByText('INV-001')).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Implement Sidebar.jsx**

`chainsentinel/frontend/src/components/Sidebar.jsx`:

```jsx
import React from 'react';
import './Sidebar.css';

const MODES = [
  { key: 'watch', label: 'Watch', desc: 'Live block monitoring' },
  { key: 'range', label: 'Range', desc: 'Block range analysis' },
  { key: 'tx', label: 'Tx Analysis', desc: 'Single transaction' },
  { key: 'wallet', label: 'Wallet Hunt', desc: 'Trace wallet activity' },
];

export function Sidebar({
  config,
  onConfigChange,
  health,
  mode,
  onModeChange,
  target,
  onTargetChange,
  onRun,
  isRunning,
  savedCases,
  onRestoreCase,
}) {
  const allConnected = health.rpc && health.es;
  const canRun = allConnected && !isRunning;

  return (
    <div className="sidebar">
      {/* Connection Config */}
      <div className="sidebar__section">
        <h3 className="sidebar__heading">Connection</h3>
        <div className="sidebar__field">
          <label className="sidebar__label">
            <span className={`status-dot ${health.rpc ? 'status-dot--ok' : 'status-dot--error'}`} />
            RPC
          </label>
          <input
            className="input-field"
            placeholder="RPC URL"
            value={config.rpcUrl}
            onChange={(e) => onConfigChange({ ...config, rpcUrl: e.target.value })}
          />
        </div>
        <div className="sidebar__field">
          <label className="sidebar__label">
            <span className={`status-dot ${health.es ? 'status-dot--ok' : 'status-dot--error'}`} />
            ES
          </label>
          <input
            className="input-field"
            placeholder="ES URL"
            value={config.esUrl}
            onChange={(e) => onConfigChange({ ...config, esUrl: e.target.value })}
          />
        </div>
        <div className="sidebar__field">
          <label className="sidebar__label">
            <span className={`status-dot ${health.ollama ? 'status-dot--ok' : 'status-dot--error'}`} />
            Ollama
          </label>
          <input
            className="input-field"
            placeholder="Ollama URL"
            value={config.ollamaUrl}
            onChange={(e) => onConfigChange({ ...config, ollamaUrl: e.target.value })}
          />
        </div>
      </div>

      {/* Mode Selector */}
      <div className="sidebar__section">
        <h3 className="sidebar__heading">Mode</h3>
        <div className="sidebar__modes">
          {MODES.map((m) => (
            <button
              key={m.key}
              className={`sidebar__mode-card ${mode === m.key ? 'sidebar__mode-card--active' : ''}`}
              onClick={() => onModeChange(m.key)}
            >
              <span className="sidebar__mode-label">{m.label}</span>
              <span className="sidebar__mode-desc">{m.desc}</span>
            </button>
          ))}
        </div>
      </div>

      {/* Target Inputs */}
      <div className="sidebar__section">
        <h3 className="sidebar__heading">Target</h3>
        {mode === 'range' && (
          <>
            <input
              className="input-field"
              placeholder="From block"
              value={target.fromBlock || ''}
              onChange={(e) => onTargetChange({ ...target, fromBlock: e.target.value })}
            />
            <input
              className="input-field"
              placeholder="To block"
              value={target.toBlock || ''}
              onChange={(e) => onTargetChange({ ...target, toBlock: e.target.value })}
              style={{ marginTop: 6 }}
            />
          </>
        )}
        {mode === 'tx' && (
          <input
            className="input-field"
            placeholder="Transaction hash"
            value={target.txHash || ''}
            onChange={(e) => onTargetChange({ ...target, txHash: e.target.value })}
          />
        )}
        {mode === 'wallet' && (
          <input
            className="input-field"
            placeholder="Wallet address"
            value={target.walletAddress || ''}
            onChange={(e) => onTargetChange({ ...target, walletAddress: e.target.value })}
          />
        )}
        {mode === 'watch' && (
          <p className="sidebar__hint">No target needed — monitors live blocks</p>
        )}
      </div>

      {/* Run Button */}
      <div className="sidebar__section">
        <button
          className="btn-pill btn-pill--primary sidebar__run-btn"
          onClick={onRun}
          disabled={!canRun}
        >
          {isRunning ? 'Running...' : 'Run Analysis'}
        </button>
      </div>

      {/* Saved Analyses */}
      {savedCases.length > 0 && (
        <div className="sidebar__section sidebar__saved">
          <h3 className="sidebar__heading">Saved Analyses</h3>
          <div className="sidebar__cases">
            {savedCases.map((c) => (
              <button
                key={c.investigationId}
                className="sidebar__case-item"
                onClick={() => onRestoreCase(c)}
              >
                <span className="mono">{c.investigationId}</span>
                <span className={`badge badge--${(c.severity || 'low').toLowerCase()}`}>
                  {c.severity || 'N/A'}
                </span>
                <span className="sidebar__case-type">{c.attackType || 'Unknown'}</span>
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 3: Create Sidebar.css**

`chainsentinel/frontend/src/components/Sidebar.css`:

```css
.sidebar {
  display: flex;
  flex-direction: column;
  gap: 0;
  padding: 16px;
}

.sidebar__section {
  padding: 12px 0;
  border-bottom: 1px solid var(--border);
}

.sidebar__section:last-child {
  border-bottom: none;
}

.sidebar__heading {
  font-size: 0.75rem;
  font-weight: var(--fw-black);
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--gray);
  margin-bottom: 10px;
}

.sidebar__field {
  margin-bottom: 8px;
}

.sidebar__label {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 0.75rem;
  font-weight: var(--fw-semibold);
  color: var(--gray);
  margin-bottom: 4px;
}

.sidebar__modes {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 6px;
}

.sidebar__mode-card {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  padding: 8px 10px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--border);
  background: var(--off-white);
  cursor: pointer;
  transition: all 0.15s;
}

.sidebar__mode-card:hover {
  border-color: var(--wise-green);
}

.sidebar__mode-card--active {
  background: var(--light-mint);
  border-color: var(--wise-green);
}

.sidebar__mode-label {
  font-size: 0.8125rem;
  font-weight: var(--fw-semibold);
}

.sidebar__mode-desc {
  font-size: 0.6875rem;
  color: var(--gray);
}

.sidebar__run-btn {
  width: 100%;
  padding: 10px 16px;
  font-size: 1rem;
}

.sidebar__hint {
  font-size: 0.75rem;
  color: var(--gray);
  font-style: italic;
}

.sidebar__cases {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.sidebar__case-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 8px;
  border-radius: var(--radius-xs);
  border: 1px solid var(--border);
  background: var(--off-white);
  cursor: pointer;
  width: 100%;
  text-align: left;
}

.sidebar__case-item:hover {
  background: var(--light-mint);
}

.sidebar__case-type {
  font-size: 0.6875rem;
  color: var(--gray);
  margin-left: auto;
}
```

- [ ] **Step 4: Run Sidebar test**

```bash
cd /mnt/c/Users/aswat/OneDrive/Desktop/Projects/Project_Hail_Mary/chainsentinel/frontend
npx vitest run src/__tests__/Sidebar.test.jsx
```

Expected: All 8 PASS

- [ ] **Step 5: Commit**

```bash
git add chainsentinel/frontend/src/components/Sidebar.jsx chainsentinel/frontend/src/components/Sidebar.css chainsentinel/frontend/src/__tests__/Sidebar.test.jsx
git commit -m "feat: Sidebar component with connection config, mode selector, run button, saved cases"
```

---

### Task 6: PipelineFeed Component

**Files:**
- Create: `chainsentinel/frontend/src/components/PipelineFeed.jsx`
- Create: `chainsentinel/frontend/src/components/PipelineFeed.css`
- Create: `chainsentinel/frontend/src/__tests__/PipelineFeed.test.jsx`

- [ ] **Step 1: Write PipelineFeed test**

`chainsentinel/frontend/src/__tests__/PipelineFeed.test.jsx`:

```javascript
import { render, screen } from '@testing-library/react';
import { PipelineFeed } from '../components/PipelineFeed';

describe('PipelineFeed', () => {
  it('renders stats bar', () => {
    const stats = { blocks: 8, txs: 47, signals: 5, indexed: 189 };
    render(<PipelineFeed logs={[]} stats={stats} />);
    expect(screen.getByText('8')).toBeInTheDocument();
    expect(screen.getByText('47')).toBeInTheDocument();
    expect(screen.getByText('5')).toBeInTheDocument();
    expect(screen.getByText('189')).toBeInTheDocument();
  });

  it('renders log entries with severity colors', () => {
    const logs = [
      { phase: 'collector', msg: 'Block 5 fetched', severity: 'ok', ts: '12:04:02' },
      { phase: 'signals', msg: 'reentrancy_pattern fired (0.95)', severity: 'crit', ts: '12:04:06' },
    ];
    render(<PipelineFeed logs={logs} stats={{ blocks: 0, txs: 0, signals: 0, indexed: 0 }} />);
    expect(screen.getByText(/Block 5 fetched/)).toBeInTheDocument();
    expect(screen.getByText(/reentrancy_pattern/)).toBeInTheDocument();
  });

  it('groups logs by phase', () => {
    const logs = [
      { phase: 'collector', msg: 'Start', severity: 'ok', ts: '12:00:00' },
      { phase: 'collector', msg: 'Done', severity: 'ok', ts: '12:00:01' },
      { phase: 'normalizer', msg: 'Start', severity: 'ok', ts: '12:00:02' },
    ];
    render(<PipelineFeed logs={logs} stats={{ blocks: 0, txs: 0, signals: 0, indexed: 0 }} />);
    expect(screen.getByText('collector')).toBeInTheDocument();
    expect(screen.getByText('normalizer')).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Implement PipelineFeed.jsx**

`chainsentinel/frontend/src/components/PipelineFeed.jsx`:

```jsx
import React, { useEffect, useRef } from 'react';
import './PipelineFeed.css';

const SEVERITY_CLASS = {
  ok: 'feed__log--ok',
  info: 'feed__log--info',
  warn: 'feed__log--warn',
  high: 'feed__log--high',
  crit: 'feed__log--crit',
  error: 'feed__log--error',
};

export function PipelineFeed({ logs, stats }) {
  const feedEndRef = useRef(null);

  useEffect(() => {
    feedEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [logs]);

  // Group logs by phase for headers
  let currentPhase = null;

  return (
    <div className="feed">
      {/* Stats Bar */}
      <div className="feed__stats">
        <div className="feed__stat">
          <span className="feed__stat-value">{stats.blocks}</span>
          <span className="feed__stat-label">Blocks</span>
        </div>
        <div className="feed__stat">
          <span className="feed__stat-value">{stats.txs}</span>
          <span className="feed__stat-label">Transactions</span>
        </div>
        <div className="feed__stat">
          <span className="feed__stat-value">{stats.signals}</span>
          <span className="feed__stat-label">Signals</span>
        </div>
        <div className="feed__stat">
          <span className="feed__stat-value">{stats.indexed}</span>
          <span className="feed__stat-label">Indexed</span>
        </div>
      </div>

      {/* Log Stream */}
      <div className="feed__logs">
        {logs.map((log, i) => {
          const showPhaseHeader = log.phase !== currentPhase;
          currentPhase = log.phase;

          return (
            <React.Fragment key={i}>
              {showPhaseHeader && (
                <div className="feed__phase-header">{log.phase}</div>
              )}
              <div className={`feed__log ${SEVERITY_CLASS[log.severity] || ''}`}>
                <span className="feed__log-ts mono">{log.ts}</span>
                <span className="feed__log-msg">{log.msg}</span>
              </div>
            </React.Fragment>
          );
        })}
        <div ref={feedEndRef} />
      </div>
    </div>
  );
}
```

- [ ] **Step 3: Create PipelineFeed.css**

`chainsentinel/frontend/src/components/PipelineFeed.css`:

```css
.feed {
  display: flex;
  flex-direction: column;
  height: 100%;
  padding: 20px;
}

.feed__stats {
  display: flex;
  gap: 24px;
  padding: 16px 20px;
  background: rgba(255, 255, 255, 0.06);
  border-radius: var(--radius-sm);
  margin-bottom: 16px;
}

.feed__stat {
  display: flex;
  flex-direction: column;
  align-items: center;
}

.feed__stat-value {
  font-family: var(--font-mono);
  font-size: 1.5rem;
  font-weight: var(--fw-black);
  color: var(--wise-green);
}

.feed__stat-label {
  font-size: 0.6875rem;
  color: var(--gray);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.feed__logs {
  flex: 1;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.feed__phase-header {
  font-size: 0.6875rem;
  font-weight: var(--fw-black);
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--wise-green);
  padding: 12px 0 4px;
  border-top: 1px solid rgba(255, 255, 255, 0.08);
  margin-top: 8px;
}

.feed__phase-header:first-child {
  margin-top: 0;
  border-top: none;
}

.feed__log {
  display: flex;
  align-items: baseline;
  gap: 12px;
  padding: 3px 8px;
  border-radius: 4px;
  font-size: 0.8125rem;
}

.feed__log-ts {
  color: var(--gray);
  min-width: 70px;
  font-size: 0.75rem;
}

.feed__log-msg {
  color: rgba(255, 255, 255, 0.8);
}

.feed__log--crit {
  background: rgba(208, 50, 56, 0.15);
}
.feed__log--crit .feed__log-msg {
  color: var(--severity-crit);
  font-weight: var(--fw-semibold);
}

.feed__log--high {
  background: rgba(230, 126, 34, 0.1);
}
.feed__log--high .feed__log-msg {
  color: var(--severity-high);
}

.feed__log--warn {
  color: var(--warning-yellow);
}

.feed__log--error {
  background: rgba(208, 50, 56, 0.2);
  color: var(--severity-crit);
}
```

- [ ] **Step 4: Run test**

```bash
cd /mnt/c/Users/aswat/OneDrive/Desktop/Projects/Project_Hail_Mary/chainsentinel/frontend
npx vitest run src/__tests__/PipelineFeed.test.jsx
```

- [ ] **Step 5: Commit**

```bash
git add chainsentinel/frontend/src/components/PipelineFeed.jsx chainsentinel/frontend/src/components/PipelineFeed.css chainsentinel/frontend/src/__tests__/PipelineFeed.test.jsx
git commit -m "feat: PipelineFeed component with stats bar and severity-colored SSE log stream"
```

---

### Task 7: InvestigationView Component

**Files:**
- Create: `chainsentinel/frontend/src/components/InvestigationView.jsx`
- Create: `chainsentinel/frontend/src/components/InvestigationView.css`
- Create: `chainsentinel/frontend/src/__tests__/InvestigationView.test.jsx`

- [ ] **Step 1: Write InvestigationView test**

`chainsentinel/frontend/src/__tests__/InvestigationView.test.jsx`:

```javascript
import { render, screen, fireEvent } from '@testing-library/react';
import { InvestigationView } from '../components/InvestigationView';

describe('InvestigationView', () => {
  const defaultProps = {
    investigationId: 'INV-2026-0001',
    severity: 'CRIT',
    attackType: 'Reentrancy Drain',
    attacker: '0xdeadbeef...',
    victim: '0x12345678...',
    fundsDrained: 150.5,
    blockRange: { from: 10, to: 18 },
    timeline: [
      { block_number: 10, event_name: 'Deposit', severity: 'ok', description: 'Normal deposit' },
      { block_number: 15, signal_name: 'reentrancy_pattern', severity: 'crit', description: 'Recursive calls detected' },
    ],
    signals: [
      { signal_name: 'reentrancy_pattern', severity: 'CRIT', score: 0.95, description: 'Recursive withdraw calls' },
      { signal_name: 'internal_eth_drain', severity: 'CRIT', score: 0.85, description: 'ETH drained via internal calls' },
    ],
    totalSignals: 61,
    activeTab: 'timeline',
    onTabChange: vi.fn(),
    onAction: vi.fn(),
  };

  it('renders severity badge and attack type', () => {
    render(<InvestigationView {...defaultProps} />);
    expect(screen.getByText('CRIT')).toBeInTheDocument();
    expect(screen.getByText('Reentrancy Drain')).toBeInTheDocument();
  });

  it('renders case ID in monospace', () => {
    render(<InvestigationView {...defaultProps} />);
    expect(screen.getByText('INV-2026-0001')).toBeInTheDocument();
  });

  it('renders meta bar with attacker and victim info', () => {
    render(<InvestigationView {...defaultProps} />);
    expect(screen.getByText(/0xdeadbeef/)).toBeInTheDocument();
    expect(screen.getByText(/0x12345678/)).toBeInTheDocument();
    expect(screen.getByText(/150\.5/)).toBeInTheDocument();
  });

  it('renders timeline events', () => {
    render(<InvestigationView {...defaultProps} activeTab="timeline" />);
    expect(screen.getByText(/Normal deposit/)).toBeInTheDocument();
    expect(screen.getByText(/Recursive calls detected/)).toBeInTheDocument();
  });

  it('renders signal count header', () => {
    render(<InvestigationView {...defaultProps} />);
    expect(screen.getByText(/2 of 61 signals fired/)).toBeInTheDocument();
  });

  it('renders action buttons', () => {
    render(<InvestigationView {...defaultProps} />);
    expect(screen.getByText(/explain signals/i)).toBeInTheDocument();
    expect(screen.getByText(/trace funds/i)).toBeInTheDocument();
    expect(screen.getByText(/generate report/i)).toBeInTheDocument();
  });

  it('calls onAction when action button clicked', () => {
    render(<InvestigationView {...defaultProps} />);
    fireEvent.click(screen.getByText(/generate report/i));
    expect(defaultProps.onAction).toHaveBeenCalledWith('generate_report');
  });
});
```

- [ ] **Step 2: Implement InvestigationView.jsx**

`chainsentinel/frontend/src/components/InvestigationView.jsx`:

```jsx
import React from 'react';
import './InvestigationView.css';

const SEVERITY_DOT = {
  crit: '#d03238',
  high: '#e67e22',
  med: '#3498db',
  low: '#868685',
  ok: '#3498db',
  info: '#868685',
};

export function InvestigationView({
  investigationId,
  severity,
  attackType,
  attacker,
  victim,
  fundsDrained,
  blockRange,
  timeline,
  signals,
  totalSignals,
  activeTab,
  onTabChange,
  onAction,
}) {
  return (
    <div className="investigation">
      {/* Top Bar */}
      <div className="investigation__topbar">
        <span className={`badge badge--${(severity || 'low').toLowerCase()}`}>
          {severity}
        </span>
        <span className="investigation__attack-type">{attackType}</span>
        <span className="investigation__case-id mono">{investigationId}</span>
        <div className="investigation__tabs">
          {['timeline', 'graph', 'raw'].map((tab) => (
            <button
              key={tab}
              className={`investigation__tab ${activeTab === tab ? 'investigation__tab--active' : ''}`}
              onClick={() => onTabChange(tab)}
            >
              {tab.charAt(0).toUpperCase() + tab.slice(1)}
            </button>
          ))}
        </div>
      </div>

      {/* Meta Bar */}
      <div className="investigation__meta">
        <div className="investigation__meta-cell">
          <span className="investigation__meta-label">Attacker</span>
          <span className="mono">{attacker}</span>
        </div>
        <div className="investigation__meta-cell">
          <span className="investigation__meta-label">Victim</span>
          <span className="mono">{victim}</span>
        </div>
        <div className="investigation__meta-cell investigation__meta-cell--danger">
          <span className="investigation__meta-label">Funds Drained</span>
          <span className="mono">{fundsDrained} ETH</span>
        </div>
        <div className="investigation__meta-cell">
          <span className="investigation__meta-label">Block Range</span>
          <span className="mono">{blockRange?.from} - {blockRange?.to}</span>
        </div>
      </div>

      {/* Main Content */}
      <div className="investigation__content">
        {/* Timeline Panel */}
        <div className="investigation__timeline">
          <h3>Attack Timeline</h3>
          <div className="timeline">
            {(timeline || []).map((event, i) => {
              const sev = (event.severity || 'info').toLowerCase();
              return (
                <div key={i} className="timeline__event">
                  <div className="timeline__line" />
                  <div
                    className="timeline__dot"
                    style={{ background: SEVERITY_DOT[sev] || SEVERITY_DOT.info }}
                  />
                  <div className="timeline__body">
                    <span className="timeline__name">
                      {event.signal_name || event.event_name || 'Event'}
                    </span>
                    <span className="timeline__desc">{event.description}</span>
                    <span className="timeline__block mono">Block {event.block_number}</span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Signals Panel */}
        <div className="investigation__signals">
          <h3>{signals.length} of {totalSignals} signals fired</h3>
          <div className="signals-list">
            {signals.map((sig, i) => (
              <div key={i} className="signal-card card--dark">
                <div
                  className="signal-card__bar"
                  style={{
                    background: SEVERITY_DOT[(sig.severity || 'low').toLowerCase()] || SEVERITY_DOT.low,
                  }}
                />
                <div className="signal-card__body">
                  <span className="signal-card__name">{sig.signal_name}</span>
                  <span className="signal-card__desc">{sig.description}</span>
                  <span className="signal-card__score mono">Score: {sig.score}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Action Buttons */}
      <div className="investigation__actions">
        <button className="btn-pill btn-pill--secondary" onClick={() => onAction('explain_signals')}>
          Explain Signals
        </button>
        <button className="btn-pill btn-pill--secondary" onClick={() => onAction('trace_funds')}>
          Trace Funds
        </button>
        <button className="btn-pill btn-pill--secondary" onClick={() => onAction('pattern_match')}>
          Pattern Match
        </button>
        <button className="btn-pill btn-pill--primary" onClick={() => onAction('generate_report')}>
          Generate Report
        </button>
      </div>
    </div>
  );
}
```

- [ ] **Step 3: Create InvestigationView.css**

`chainsentinel/frontend/src/components/InvestigationView.css`:

```css
.investigation {
  display: flex;
  flex-direction: column;
  height: 100%;
  padding: 20px;
  gap: 16px;
}

.investigation__topbar {
  display: flex;
  align-items: center;
  gap: 12px;
}

.investigation__attack-type {
  font-weight: var(--fw-black);
  font-size: 1.125rem;
}

.investigation__case-id {
  color: var(--gray);
  font-size: 0.8125rem;
}

.investigation__tabs {
  margin-left: auto;
  display: flex;
  gap: 4px;
}

.investigation__tab {
  padding: 4px 12px;
  border-radius: var(--radius-pill);
  border: 1px solid rgba(255, 255, 255, 0.15);
  background: transparent;
  color: var(--gray);
  font-size: 0.8125rem;
  cursor: pointer;
}

.investigation__tab--active {
  background: rgba(255, 255, 255, 0.1);
  color: var(--white);
  border-color: var(--wise-green);
}

.investigation__meta {
  display: flex;
  gap: 16px;
  padding: 12px 16px;
  background: rgba(255, 255, 255, 0.04);
  border-radius: var(--radius-sm);
}

.investigation__meta-cell {
  display: flex;
  flex-direction: column;
  gap: 2px;
  flex: 1;
}

.investigation__meta-label {
  font-size: 0.6875rem;
  color: var(--gray);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.investigation__meta-cell--danger .mono {
  color: var(--danger-red);
  font-weight: var(--fw-semibold);
}

.investigation__content {
  display: flex;
  flex: 1;
  gap: 20px;
  overflow: hidden;
}

.investigation__timeline {
  flex: 1;
  overflow-y: auto;
}

.investigation__timeline h3,
.investigation__signals h3 {
  font-size: 0.8125rem;
  color: var(--gray);
  margin-bottom: 12px;
}

.timeline {
  display: flex;
  flex-direction: column;
  gap: 0;
  position: relative;
  padding-left: 20px;
}

.timeline__event {
  position: relative;
  padding: 8px 0 8px 16px;
}

.timeline__line {
  position: absolute;
  left: -14px;
  top: 0;
  bottom: 0;
  width: 2px;
  background: rgba(255, 255, 255, 0.1);
}

.timeline__dot {
  position: absolute;
  left: -18px;
  top: 12px;
  width: 10px;
  height: 10px;
  border-radius: 50%;
}

.timeline__name {
  font-weight: var(--fw-semibold);
  display: block;
}

.timeline__desc {
  font-size: 0.8125rem;
  color: rgba(255, 255, 255, 0.6);
  display: block;
}

.timeline__block {
  font-size: 0.75rem;
  color: var(--gray);
}

.investigation__signals {
  width: 300px;
  min-width: 300px;
  overflow-y: auto;
}

.signals-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.signal-card {
  display: flex;
  border-radius: var(--radius-sm);
  overflow: hidden;
}

.signal-card__bar {
  width: 4px;
  min-height: 100%;
}

.signal-card__body {
  padding: 10px 12px;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.signal-card__name {
  font-weight: var(--fw-semibold);
  font-size: 0.875rem;
}

.signal-card__desc {
  font-size: 0.75rem;
  color: rgba(255, 255, 255, 0.6);
}

.signal-card__score {
  font-size: 0.75rem;
  color: var(--wise-green);
}

.investigation__actions {
  display: flex;
  gap: 8px;
  padding-top: 12px;
  border-top: 1px solid rgba(255, 255, 255, 0.08);
}
```

- [ ] **Step 4: Run test**

```bash
cd /mnt/c/Users/aswat/OneDrive/Desktop/Projects/Project_Hail_Mary/chainsentinel/frontend
npx vitest run src/__tests__/InvestigationView.test.jsx
```

- [ ] **Step 5: Commit**

```bash
git add chainsentinel/frontend/src/components/InvestigationView.jsx chainsentinel/frontend/src/components/InvestigationView.css chainsentinel/frontend/src/__tests__/InvestigationView.test.jsx
git commit -m "feat: InvestigationView with timeline, signals panel, meta bar, action buttons"
```

---

### Task 8: EntityGraph Component

**Files:**
- Create: `chainsentinel/frontend/src/components/EntityGraph.jsx`
- Create: `chainsentinel/frontend/src/components/EntityGraph.css`

- [ ] **Step 1: Implement EntityGraph.jsx**

`chainsentinel/frontend/src/components/EntityGraph.jsx`:

```jsx
import React, { useEffect, useRef } from 'react';
import * as d3 from 'd3';
import './EntityGraph.css';

const NODE_COLORS = {
  attacker: '#d03238',
  victim: '#d03238',
  protocol: '#3498db',
  mixer: '#868685',
  bridge: '#868685',
  cex: '#e67e22',
  unknown: '#555555',
};

const EDGE_COLORS = {
  value: '#d03238',
  structural: '#555555',
};

export function EntityGraph({ nodes = [], edges = [], onNodeClick }) {
  const svgRef = useRef(null);
  const containerRef = useRef(null);

  useEffect(() => {
    if (!svgRef.current || nodes.length === 0) return;

    const svg = d3.select(svgRef.current);
    svg.selectAll('*').remove();

    const container = containerRef.current;
    const width = container?.clientWidth || 800;
    const height = container?.clientHeight || 600;

    svg.attr('viewBox', `0 0 ${width} ${height}`);

    const g = svg.append('g');

    // Zoom
    const zoom = d3.zoom()
      .scaleExtent([0.3, 5])
      .on('zoom', (event) => g.attr('transform', event.transform));
    svg.call(zoom);

    // Simulation
    const simulation = d3.forceSimulation(nodes)
      .force('link', d3.forceLink(edges).id(d => d.id).distance(120))
      .force('charge', d3.forceManyBody().strength(-300))
      .force('center', d3.forceCenter(width / 2, height / 2))
      .force('collision', d3.forceCollide(40));

    // Edges
    const link = g.append('g')
      .selectAll('line')
      .data(edges)
      .join('line')
      .attr('stroke', d => EDGE_COLORS[d.type] || EDGE_COLORS.structural)
      .attr('stroke-width', d => d.type === 'value' ? 2 : 1)
      .attr('stroke-opacity', 0.6);

    // Edge labels
    const linkLabel = g.append('g')
      .selectAll('text')
      .data(edges.filter(d => d.label))
      .join('text')
      .attr('font-size', '10px')
      .attr('fill', '#868685')
      .attr('font-family', 'JetBrains Mono, monospace')
      .attr('text-anchor', 'middle')
      .text(d => d.label);

    // Nodes
    const node = g.append('g')
      .selectAll('circle')
      .data(nodes)
      .join('circle')
      .attr('r', d => d.role === 'attacker' || d.role === 'victim' ? 16 : 12)
      .attr('fill', d => NODE_COLORS[d.role] || NODE_COLORS.unknown)
      .attr('stroke', '#0e0f0c')
      .attr('stroke-width', 2)
      .style('cursor', 'pointer')
      .on('click', (event, d) => onNodeClick?.(d))
      .call(d3.drag()
        .on('start', (event, d) => {
          if (!event.active) simulation.alphaTarget(0.3).restart();
          d.fx = d.x;
          d.fy = d.y;
        })
        .on('drag', (event, d) => {
          d.fx = event.x;
          d.fy = event.y;
        })
        .on('end', (event, d) => {
          if (!event.active) simulation.alphaTarget(0);
          d.fx = null;
          d.fy = null;
        })
      );

    // Node labels
    const nodeLabel = g.append('g')
      .selectAll('text')
      .data(nodes)
      .join('text')
      .attr('font-size', '11px')
      .attr('fill', 'white')
      .attr('font-family', 'JetBrains Mono, monospace')
      .attr('text-anchor', 'middle')
      .attr('dy', 28)
      .text(d => d.label || `${d.id.slice(0, 6)}...${d.id.slice(-4)}`);

    // Tick
    simulation.on('tick', () => {
      link
        .attr('x1', d => d.source.x)
        .attr('y1', d => d.source.y)
        .attr('x2', d => d.target.x)
        .attr('y2', d => d.target.y);

      linkLabel
        .attr('x', d => (d.source.x + d.target.x) / 2)
        .attr('y', d => (d.source.y + d.target.y) / 2);

      node.attr('cx', d => d.x).attr('cy', d => d.y);
      nodeLabel.attr('x', d => d.x).attr('y', d => d.y);
    });

    return () => simulation.stop();
  }, [nodes, edges, onNodeClick]);

  return (
    <div className="entity-graph" ref={containerRef}>
      <svg ref={svgRef} className="entity-graph__svg" />
      <div className="entity-graph__legend">
        <span className="entity-graph__legend-item">
          <span className="entity-graph__legend-dot" style={{ background: NODE_COLORS.attacker }} />
          Attacker / Victim
        </span>
        <span className="entity-graph__legend-item">
          <span className="entity-graph__legend-dot" style={{ background: NODE_COLORS.protocol }} />
          Known Protocol
        </span>
        <span className="entity-graph__legend-item">
          <span className="entity-graph__legend-dot" style={{ background: NODE_COLORS.mixer }} />
          Mixer / Bridge
        </span>
        <span className="entity-graph__legend-item">
          <span className="entity-graph__legend-dot" style={{ background: NODE_COLORS.cex }} />
          CEX
        </span>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Create EntityGraph.css**

`chainsentinel/frontend/src/components/EntityGraph.css`:

```css
.entity-graph {
  width: 100%;
  height: 100%;
  position: relative;
  background: var(--near-black);
  border-radius: var(--radius-sm);
  overflow: hidden;
}

.entity-graph__svg {
  width: 100%;
  height: 100%;
}

.entity-graph__legend {
  position: absolute;
  bottom: 12px;
  left: 12px;
  display: flex;
  gap: 16px;
  padding: 8px 12px;
  background: rgba(0, 0, 0, 0.7);
  border-radius: var(--radius-xs);
  font-size: 0.6875rem;
  color: var(--gray);
}

.entity-graph__legend-item {
  display: flex;
  align-items: center;
  gap: 4px;
}

.entity-graph__legend-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}
```

- [ ] **Step 3: Commit**

```bash
git add chainsentinel/frontend/src/components/EntityGraph.jsx chainsentinel/frontend/src/components/EntityGraph.css
git commit -m "feat: EntityGraph with D3.js force-directed graph, color-coded nodes, zoom/pan"
```

---

### Task 9: CopilotPanel Component

**Files:**
- Create: `chainsentinel/frontend/src/components/CopilotPanel.jsx`
- Create: `chainsentinel/frontend/src/components/CopilotPanel.css`

- [ ] **Step 1: Implement CopilotPanel.jsx**

`chainsentinel/frontend/src/components/CopilotPanel.jsx`:

```jsx
import React, { useState, useRef, useEffect } from 'react';
import './CopilotPanel.css';

const QUICK_BUTTONS = [
  { label: 'What signals fired?', action: 'explain_signals' },
  { label: 'Trace fund flow', action: 'trace_funds' },
  { label: 'Known pattern?', action: 'pattern_match' },
  { label: 'Generate report', action: 'generate_report' },
  { label: "What's in ES?", action: 'es_summary' },
];

export function CopilotPanel({
  state = 'idle',
  messages = [],
  onSendMessage,
  onQuickAction,
  streaming = false,
  streamContent = '',
}) {
  const [input, setInput] = useState('');
  const chatEndRef = useRef(null);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, streamContent]);

  const handleSend = () => {
    const trimmed = input.trim();
    if (!trimmed) return;
    onSendMessage(trimmed);
    setInput('');
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="copilot">
      <div className="copilot__header">
        <h3>Copilot</h3>
        <span className={`badge badge--${state === 'idle' ? 'low' : state === 'watching' ? 'high' : 'med'}`}>
          {state}
        </span>
      </div>

      <div className="copilot__chat">
        {state === 'idle' && messages.length === 0 && (
          <div className="copilot__greeting">
            <p>ChainSentinel Copilot ready.</p>
            <p>Run an analysis to begin, or ask a question about a previous investigation.</p>
          </div>
        )}

        {messages.map((msg, i) => (
          <div key={i} className={`copilot__msg copilot__msg--${msg.role}`}>
            <div className="copilot__msg-content">{msg.content}</div>
          </div>
        ))}

        {streaming && streamContent && (
          <div className="copilot__msg copilot__msg--assistant">
            <div className="copilot__msg-content copilot__msg-content--streaming">
              {streamContent}
            </div>
          </div>
        )}

        <div ref={chatEndRef} />
      </div>

      {/* Quick Buttons */}
      {state === 'ready' && (
        <div className="copilot__quick">
          {QUICK_BUTTONS.map((btn) => (
            <button
              key={btn.action}
              className="btn-pill btn-pill--secondary copilot__quick-btn"
              onClick={() => onQuickAction(btn.action)}
            >
              {btn.label}
            </button>
          ))}
        </div>
      )}

      {/* Input */}
      <div className="copilot__input-row">
        <textarea
          className="copilot__input"
          placeholder="Ask about the investigation..."
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          rows={2}
          disabled={streaming}
        />
        <button
          className="btn-pill btn-pill--primary copilot__send"
          onClick={handleSend}
          disabled={streaming || !input.trim()}
        >
          Send
        </button>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Create CopilotPanel.css**

`chainsentinel/frontend/src/components/CopilotPanel.css`:

```css
.copilot {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.copilot__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  border-bottom: 1px solid var(--border);
}

.copilot__header h3 {
  font-size: 0.875rem;
}

.copilot__chat {
  flex: 1;
  overflow-y: auto;
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.copilot__greeting {
  padding: 20px 12px;
  text-align: center;
  color: var(--gray);
  font-size: 0.8125rem;
  line-height: 1.6;
}

.copilot__msg {
  max-width: 95%;
  padding: 8px 12px;
  border-radius: var(--radius-sm);
  font-size: 0.8125rem;
  line-height: 1.5;
}

.copilot__msg--user {
  align-self: flex-end;
  background: var(--light-mint);
  color: var(--dark-green);
}

.copilot__msg--assistant {
  align-self: flex-start;
  background: var(--off-white);
  color: var(--near-black);
}

.copilot__msg-content--streaming {
  border-right: 2px solid var(--wise-green);
  animation: blink 1s infinite;
}

@keyframes blink {
  50% { border-color: transparent; }
}

.copilot__quick {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  padding: 8px 12px;
  border-top: 1px solid var(--border);
}

.copilot__quick-btn {
  font-size: 0.6875rem;
  padding: 3px 10px;
}

.copilot__input-row {
  display: flex;
  gap: 6px;
  padding: 8px 12px;
  border-top: 1px solid var(--border);
  align-items: flex-end;
}

.copilot__input {
  flex: 1;
  resize: none;
  border: 1px solid var(--border);
  border-radius: var(--radius-xs);
  padding: 6px 10px;
  font-family: var(--font-body);
  font-size: 0.8125rem;
  outline: none;
}

.copilot__input:focus {
  border-color: var(--wise-green);
}

.copilot__send {
  padding: 6px 12px;
  font-size: 0.75rem;
}
```

- [ ] **Step 3: Commit**

```bash
git add chainsentinel/frontend/src/components/CopilotPanel.jsx chainsentinel/frontend/src/components/CopilotPanel.css
git commit -m "feat: CopilotPanel with chat, quick buttons, streaming indicator"
```

---

### Task 10: StoredAnalyses Component

**Files:**
- Create: `chainsentinel/frontend/src/components/StoredAnalyses.jsx`
- Create: `chainsentinel/frontend/src/components/StoredAnalyses.css`

- [ ] **Step 1: Implement StoredAnalyses.jsx**

`chainsentinel/frontend/src/components/StoredAnalyses.jsx`:

```jsx
import React from 'react';
import './StoredAnalyses.css';

export function StoredAnalyses({ cases = [], onRestore, onDelete }) {
  if (cases.length === 0) {
    return (
      <div className="stored">
        <div className="stored__empty">
          No saved analyses. Run an investigation to get started.
        </div>
      </div>
    );
  }

  return (
    <div className="stored">
      <table className="stored__table">
        <thead>
          <tr>
            <th>Case ID</th>
            <th>Mode</th>
            <th>Attack Type</th>
            <th>Severity</th>
            <th>Funds</th>
            <th>Date</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {cases.map((c) => (
            <tr
              key={c.investigationId}
              className="stored__row"
              onClick={() => onRestore(c)}
            >
              <td className="mono">{c.investigationId}</td>
              <td>{c.mode || '-'}</td>
              <td>{c.attackType || 'Unknown'}</td>
              <td>
                <span className={`badge badge--${(c.severity || 'low').toLowerCase()}`}>
                  {c.severity || 'N/A'}
                </span>
              </td>
              <td className="mono stored__funds">
                {c.fundsDrained ? `${c.fundsDrained} ETH` : '-'}
              </td>
              <td className="stored__date">{c.timestamp || '-'}</td>
              <td>
                <button
                  className="stored__delete"
                  onClick={(e) => { e.stopPropagation(); onDelete(c.investigationId); }}
                >
                  x
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
```

- [ ] **Step 2: Create StoredAnalyses.css**

`chainsentinel/frontend/src/components/StoredAnalyses.css`:

```css
.stored {
  padding: 20px;
}

.stored__empty {
  text-align: center;
  color: var(--gray);
  padding: 40px 20px;
  font-size: 0.875rem;
}

.stored__table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.8125rem;
}

.stored__table th {
  text-align: left;
  font-size: 0.6875rem;
  font-weight: var(--fw-black);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--gray);
  padding: 8px 12px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

.stored__table td {
  padding: 10px 12px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
}

.stored__row {
  cursor: pointer;
  transition: background 0.15s;
}

.stored__row:hover {
  background: rgba(255, 255, 255, 0.04);
}

.stored__funds {
  color: var(--danger-red);
}

.stored__date {
  color: var(--gray);
  font-size: 0.75rem;
}

.stored__delete {
  background: none;
  border: none;
  color: var(--gray);
  cursor: pointer;
  font-size: 0.875rem;
  padding: 2px 6px;
  border-radius: 4px;
}

.stored__delete:hover {
  color: var(--danger-red);
  background: rgba(208, 50, 56, 0.1);
}
```

- [ ] **Step 3: Commit**

```bash
git add chainsentinel/frontend/src/components/StoredAnalyses.jsx chainsentinel/frontend/src/components/StoredAnalyses.css
git commit -m "feat: StoredAnalyses component with case table, restore, delete"
```

---

### Task 11: App Component — Wire Everything Together

**Files:**
- Create: `chainsentinel/frontend/src/App.jsx`

- [ ] **Step 1: Implement App.jsx**

`chainsentinel/frontend/src/App.jsx`:

```jsx
import React, { useState, useEffect, useCallback } from 'react';
import { Sidebar } from './components/Sidebar';
import { PipelineFeed } from './components/PipelineFeed';
import { InvestigationView } from './components/InvestigationView';
import { EntityGraph } from './components/EntityGraph';
import { CopilotPanel } from './components/CopilotPanel';
import { StoredAnalyses } from './components/StoredAnalyses';
import { useAnalysis } from './hooks/useAnalysis';
import { useElasticsearch } from './hooks/useElasticsearch';
import { useOllama } from './hooks/useOllama';
import { useLocalStorage } from './hooks/useLocalStorage';
import { checkHealth, startAnalysisPost } from './api/pipeline';

export default function App() {
  // Config
  const [config, setConfig] = useState({
    rpcUrl: 'http://127.0.0.1:8545',
    esUrl: 'http://localhost:9200',
    ollamaUrl: 'http://localhost:11434',
  });

  // Health
  const [health, setHealth] = useState({ rpc: false, es: false, ollama: false });

  // Mode & Target
  const [mode, setMode] = useState('range');
  const [target, setTarget] = useState({});
  const [activeTab, setActiveTab] = useState('timeline');

  // Saved cases
  const [savedCases, setSavedCases] = useLocalStorage('chainsentinel-cases', []);

  // Analysis state machine
  const analysis = useAnalysis();

  // ES hook
  const es = useElasticsearch(config.esUrl);

  // Ollama hook
  const ollama = useOllama(config.ollamaUrl);

  // Investigation data
  const [signals, setSignals] = useState([]);
  const [alerts, setAlerts] = useState([]);
  const [timeline, setTimeline] = useState([]);
  const [attackerData, setAttackerData] = useState([]);
  const [graphData, setGraphData] = useState({ nodes: [], edges: [] });

  // Copilot
  const [copilotState, setCopilotState] = useState('idle');
  const [copilotMessages, setCopilotMessages] = useState([]);
  const [streamContent, setStreamContent] = useState('');

  // Health check on mount and config change
  useEffect(() => {
    const check = async () => {
      try {
        const h = await checkHealth();
        setHealth({
          rpc: h.rpc === 'ok',
          es: h.es === 'ok',
          ollama: h.ollama === 'ok',
        });
      } catch {
        setHealth({ rpc: false, es: false, ollama: false });
      }
    };
    check();
    const interval = setInterval(check, 15000);
    return () => clearInterval(interval);
  }, [config]);

  // Load investigation data when analysis completes
  useEffect(() => {
    if (analysis.state === 'complete' && analysis.investigationId) {
      loadInvestigationData(analysis.investigationId);
      setCopilotState('ready');
    }
  }, [analysis.state, analysis.investigationId]);

  const loadInvestigationData = async (invId) => {
    const [sigs, alts, tl, atk] = await Promise.all([
      es.fetchSignals(invId),
      es.fetchAlerts(invId),
      es.fetchTimeline(invId),
      es.fetchAttackerData(invId),
    ]);

    setSignals(sigs);
    setAlerts(alts);
    setTimeline(tl);
    setAttackerData(atk);

    // Build graph data from attacker + derived data
    buildGraphData(atk, sigs);
  };

  const buildGraphData = (attackerDocs, signalDocs) => {
    const nodesMap = new Map();
    const edges = [];

    for (const doc of attackerDocs) {
      if (doc.cluster_wallets) {
        for (const w of doc.cluster_wallets) {
          if (!nodesMap.has(w)) {
            nodesMap.set(w, { id: w, role: 'unknown' });
          }
        }
      }
      if (doc.attacker_wallet) {
        nodesMap.set(doc.attacker_wallet, { id: doc.attacker_wallet, role: 'attacker' });
      }
    }

    setGraphData({
      nodes: Array.from(nodesMap.values()),
      edges,
    });
  };

  const handleRun = async () => {
    const invId = `INV-${Date.now()}`;
    analysis.startRun({ ...config, mode, ...target, investigationId: invId });
    setCopilotState('watching');

    try {
      const stream = await startAnalysisPost({
        mode,
        rpcUrl: config.rpcUrl,
        investigationId: invId,
        ...target,
      });

      const reader = stream.getReader();
      const decoder = new TextDecoder();

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const lines = decoder.decode(value).split('\n').filter(Boolean);
        for (const line of lines) {
          try {
            const event = JSON.parse(line);
            if (event.phase === 'complete') {
              analysis.completeRun(event);
              // Save case
              setSavedCases((prev) => [
                { investigationId: invId, mode, severity: 'N/A', timestamp: new Date().toISOString(), ...event },
                ...prev,
              ]);
            } else {
              analysis.addLog(event);
            }
          } catch {
            // Skip non-JSON lines
          }
        }
      }
    } catch (err) {
      analysis.addLog({ phase: 'error', msg: err.message, severity: 'error', ts: new Date().toLocaleTimeString() });
    }
  };

  const handleRestoreCase = (caseData) => {
    analysis.restoreCase(caseData);
    if (caseData.investigationId) {
      loadInvestigationData(caseData.investigationId);
    }
  };

  const handleCopilotMessage = async (text) => {
    setCopilotMessages((prev) => [...prev, { role: 'user', content: text }]);

    const systemMsg = {
      role: 'system',
      content: `You are ChainSentinel Copilot analyzing investigation ${analysis.investigationId}. Signals fired: ${signals.map(s => s.signal_name).join(', ')}. Alerts: ${alerts.map(a => a.pattern_name).join(', ')}.`,
    };

    const response = await ollama.chat([
      systemMsg,
      ...copilotMessages,
      { role: 'user', content: text },
    ]);

    if (response) {
      setCopilotMessages((prev) => [...prev, { role: 'assistant', content: response }]);
    }
  };

  const handleCopilotAction = (action) => {
    const prompts = {
      explain_signals: 'Explain the signals that fired in this investigation and their significance.',
      trace_funds: 'Describe the fund flow from the attacker wallet. Where did the stolen funds go?',
      pattern_match: 'Does this match any known attack patterns? Explain which pattern and confidence.',
      generate_report: 'Generate a full forensic report with: Executive Summary, Attack Timeline, Technical Mechanism, Attacker Attribution, Fund Trail, Signal Evidence, and Remediation Actions.',
      es_summary: 'Summarize what data is stored in Elasticsearch for this investigation.',
    };
    handleCopilotMessage(prompts[action] || action);
  };

  const handleAction = (action) => {
    handleCopilotAction(action);
  };

  // Derive top-level investigation props
  const topAlert = alerts[0] || {};
  const topAttacker = attackerData.find(d => d.attacker_type === 'profile') || {};

  return (
    <div className="app-layout">
      <div className="app-sidebar">
        <Sidebar
          config={config}
          onConfigChange={setConfig}
          health={health}
          mode={mode}
          onModeChange={setMode}
          target={target}
          onTargetChange={setTarget}
          onRun={handleRun}
          isRunning={analysis.state === 'running'}
          savedCases={savedCases}
          onRestoreCase={handleRestoreCase}
        />
      </div>

      <div className="app-workspace">
        {analysis.state === 'running' && (
          <PipelineFeed logs={analysis.logs} stats={analysis.stats} />
        )}
        {analysis.state === 'complete' && activeTab !== 'graph' && (
          <InvestigationView
            investigationId={analysis.investigationId}
            severity={topAlert.severity || (signals.some(s => s.severity === 'CRIT') ? 'CRIT' : 'MED')}
            attackType={topAlert.pattern_name || 'Unknown Pattern'}
            attacker={topAttacker.cluster_wallets?.[0] || topAlert.attacker_wallet || 'Unknown'}
            victim={topAlert.victim_contract || 'Unknown'}
            fundsDrained={topAttacker.total_stolen_eth || topAlert.funds_drained_eth || 0}
            blockRange={{
              from: topAttacker.attack_block_range_from || topAlert.attack_block_range_from,
              to: topAttacker.attack_block_range_to || topAlert.attack_block_range_to,
            }}
            timeline={timeline}
            signals={signals}
            totalSignals={61}
            activeTab={activeTab}
            onTabChange={setActiveTab}
            onAction={handleAction}
          />
        )}
        {analysis.state === 'complete' && activeTab === 'graph' && (
          <EntityGraph
            nodes={graphData.nodes}
            edges={graphData.edges}
            onNodeClick={(node) => handleCopilotMessage(`Tell me about address ${node.id}`)}
          />
        )}
        {analysis.state === 'idle' && (
          <StoredAnalyses
            cases={savedCases}
            onRestore={handleRestoreCase}
            onDelete={(id) => setSavedCases((prev) => prev.filter(c => c.investigationId !== id))}
          />
        )}
      </div>

      <div className="app-copilot">
        <CopilotPanel
          state={copilotState}
          messages={copilotMessages}
          onSendMessage={handleCopilotMessage}
          onQuickAction={handleCopilotAction}
          streaming={ollama.streaming}
          streamContent={streamContent}
        />
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Run all frontend tests**

```bash
cd /mnt/c/Users/aswat/OneDrive/Desktop/Projects/Project_Hail_Mary/chainsentinel/frontend
npx vitest run
```

Expected: All tests PASS

- [ ] **Step 3: Verify build works**

```bash
cd /mnt/c/Users/aswat/OneDrive/Desktop/Projects/Project_Hail_Mary/chainsentinel/frontend
npx vite build
```

Expected: Build succeeds with no errors

- [ ] **Step 4: Commit**

```bash
git add chainsentinel/frontend/src/App.jsx
git commit -m "feat: App component wires Sidebar, PipelineFeed, InvestigationView, EntityGraph, CopilotPanel, StoredAnalyses"
```
