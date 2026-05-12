# 9. Test strategy

ChainSentinel ships with ~20 Python test files under
`chainsentinel/tests/` and a Vitest setup in `chainsentinel/frontend/`.

## 9.1 Backend test categories

| Category | Files | Covers |
|----------|-------|--------|
| Pipeline | `test_collector.py`, `test_normalizer.py`, `test_decoder.py`, `test_derived*.py`, `test_ingest.py` | Per-module unit tests with mocked RPC and ES |
| Detection | `test_signal_engine.py`, `test_pattern_engine.py`, `test_signal_queries.py` | Engine plumbing + per-query smoke tests against fixture data |
| Correlation | `test_clustering.py`, `test_mixer_detect.py`, `test_label_db.py`, `test_fund_trace.py` | Pure-Python — no ES required |
| Ollama | `test_copilot_integration.py`, `test_report_template.py`, `test_report_sections.py` | Prompt-construction and context-bundling correctness |
| ES | `test_es_setup.py` | Mapping creation + idempotency |
| E2E | `test_e2e_full_pipeline.py`, `test_detection_integration.py`, `test_correlation_integration.py` | Full-stack runs against a containerised ES |

## 9.2 Running the suite

```bash
cd chainsentinel
pytest                                 # everything (≈ 130 tests)
pytest -m "not e2e"                    # skip E2E (faster)
pytest tests/test_signal_queries.py    # signal smoke tests only
pytest -k reentrancy                   # keyword filter
pytest --maxfail=1                     # stop on first failure
```

Markers in use:

| Marker | Meaning |
|--------|---------|
| `slow` | Runs > 5 s |
| `e2e`  | Requires running ES + Anvil |
| `ollama` | Requires running Ollama |

## 9.3 Fixtures and helpers

Shared fixtures in `conftest.py`:

- `es_client` — async ES connected to `localhost:9200`.
- `mock_w3` — `unittest.mock` async-web3.
- `simulation_payload` — a captured Anvil tx for the
  `reentrancy-drain` scenario.

`chainsentinel/e2e_helpers/` houses orchestration utilities used by
the E2E suite:

| Module | Role |
|--------|------|
| `pipeline_runner` | Wraps `pipeline/runner.py` for offline harnessing — drains every SSE event into a list for assertion. |
| `validator` | Cross-checks ES results against a per-scenario *expected* fixture (which signals must fire, which patterns must match). |
| `repair` | Best-effort cleanup between E2E runs: deletes scratch indices, resets `selector_registry.json` if a test mutated it. |

## 9.4 Frontend tests

```bash
cd chainsentinel/frontend
npm test           # vitest watch mode
npm run test:run   # single run, CI-style
```

Test files live alongside components with `.test.jsx` suffix.

## 9.5 Continuous integration

The repository's CI (when configured) should run:

1. `pip install -r chainsentinel/requirements.txt`
2. `pytest chainsentinel/tests/ -m "not e2e"`
3. `cd chainsentinel/frontend && npm ci && npm run test:run`
4. Linting via `ruff check chainsentinel/`
5. Optionally, an E2E job that spins up the `docker-compose.yml`
   services and runs the `-m e2e` tests.
