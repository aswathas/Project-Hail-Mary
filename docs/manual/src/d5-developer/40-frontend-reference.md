# 4. Frontend reference

React 18 + Vite + d3 + plain CSS (Wise design system tokens defined in
`App.css` `:root`). No state-management library — context and hooks
only.

![Component × hook × API graph](../../diagrams/rendered/11-frontend-component-graph.png)

## 4.1 Components (`src/components/`)

### `Sidebar.jsx`
- **Props:** none.
- **Hooks:** `useAnalysis`, `useLocalStorage`.
- **Responsibility:** mode selector (tx / range / wallet / watch),
  manifest file input, stored analyses list.

### `PipelineFeed.jsx`
- **Props:** `{ events: PipelineEvent[] }`.
- **Hooks:** `useAnalysis` (subscribes to SSE).
- **Responsibility:** render the SSE event stream as a live log with
  severity-coloured rows.

### `InvestigationView.jsx`
- **Props:** `{ investigationId, isRunning }`.
- **Hooks:** `useElasticsearch`.
- **Responsibility:** state machine. While `isRunning=true`, renders
  `PipelineFeed`; on completion, auto-flips to the investigation
  report and `EntityGraph`.

### `EntityGraph.jsx`
- **Props:** `{ investigationId }`.
- **Hooks:** `useElasticsearch`.
- **Responsibility:** fetches `fund_flow_edge` documents and renders a
  d3 force-directed graph. Address nodes are coloured by `label_dst`.

### `CopilotPanel.jsx`
- **Props:** `{ investigationId, ready }`.
- **Hooks:** `useOllama`, `useLocalStorage` (persists chat history).
- **Responsibility:** chat input + section selector + status badges.

### `StoredAnalyses.jsx`
- **Props:** `{ onSelect: (id) => void }`.
- **Hooks:** `useLocalStorage`, `useElasticsearch`.
- **Responsibility:** lists past `investigation_id`s with a brief preview.

## 4.2 Hooks (`src/hooks/`)

| Hook | Returns |
|------|---------|
| `useAnalysis` | `{ start(mode, target), events, status, investigationId }` |
| `useElasticsearch` | `{ query(body), isLoading, error }` |
| `useOllama` | `{ ask(question), generateSection(name), tokens, isStreaming }` |
| `useLocalStorage` | `[value, setValue]` — typed wrapper around `localStorage` |

## 4.3 API modules (`src/api/`)

### `api/pipeline.js`
- `startAnalysis(req): EventSource` — opens an SSE connection to
  `POST /analyze`.
- `getAnalysis(id): Promise<object>` — wraps `GET /analysis/{id}`.

### `api/elasticsearch.js`
- `esQuery(body): Promise<object>` — direct REST call against the
  configured ES URL. Read-only by convention.

### `api/ollama.js`
- `streamCompletion(prompt, model): AsyncIterable<string>` — token stream.

## 4.4 Styling

Tokens defined in `App.css`:

```css
:root {
  --near-black: #0e0f0c;
  --wise-green: #9fe870;
  --dark-green: #163300;
  --light-mint: #e2f6d5;
  --danger-red: #d03238;
  --warning-yellow: #ffd11a;
  --gray: #868685;
  --radius-pill: 9999px;
  --radius-card: 30px;
}
```

Typography:
- `font-family: 'Inter', system-ui` — weight 600 body, 900 headings.
- `font-family: 'JetBrains Mono', monospace` for hashes, addresses, amounts.

Per-component CSS files (`Sidebar.css`, `PipelineFeed.css`, etc.) sit
next to their `.jsx` and use the tokens. No CSS-in-JS.
