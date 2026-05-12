# 10. Contributing workflow

## 10.1 Branching

- `main` is protected and ships releases.
- Feature work lives on `feature/<short-slug>` branches.
- Documentation work lives on `docs/<short-slug>` branches.
- The branch this documentation set was authored on is
  `claude/create-documentation-pGKXL`.

## 10.2 Commits

Commit-message style follows what already exists in `git log`:

- Sentence-case subject, ≤ 72 chars, no trailing period.
- Optional body explaining *why* the change is needed.
- Reference issue numbers as `Refs #123` or `Closes #123`.

## 10.3 Pull requests

1. Open a PR against `main`.
2. Run `pytest -m "not e2e"` and `npm run test:run` locally first.
3. If your change touches detection logic, add or extend a test that
   exercises a representative scenario (often from `simulations/`).
4. If your change touches ES mappings, also update the strict mapping
   JSON and run `make catalogs` so the doc tables refresh.
5. PR description must include:
   - **What** changed
   - **Why** (link to issue or scenario)
   - **Test plan** (commands the reviewer can run)
   - Screenshots for UI changes

## 10.4 Code style

- **Python**: PEP 8 + 100-char line limit + `ruff` for linting.
  Type hints required on all public functions.
- **JavaScript/JSX**: 2-space indent; Prettier defaults; no class
  components (function + hooks only).
- **ES queries**: lowercase keywords (`from`, `where`, `eval`), one
  clause per line, trailing comments OK.
- **Comments**: default to none. Only justify a non-obvious *why*.

## 10.5 Documentation updates

If a code change affects something documented in this manual:

1. Edit the relevant `.md` file under `docs/manual/src/`.
2. If you added a signal / pattern / builder / ABI / endpoint, run
   `make catalogs` to refresh `src/_generated/`.
3. If a diagram is now wrong, edit the corresponding
   `diagrams/src/*.mmd` and run `make diagrams`.
4. Run `make verify` to make sure the new identifiers are referenced
   in `docs/manual/src/`.
