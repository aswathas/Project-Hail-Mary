# ChainSentinel Manual

This folder holds the canonical user-facing documentation set for ChainSentinel.
Seven Word (`.docx`) documents are generated from the Markdown sources here.

## Documents

| ID | File group           | Audience               | Source folder                |
|----|----------------------|------------------------|------------------------------|
| D1 | Executive Overview   | Stakeholders           | `src/d1-executive/`          |
| D2 | Analyst Handbook     | Forensic analysts      | `src/d2-analyst/`            |
| D3 | Architecture & Design| Devs / senior ops      | `src/d3-architecture/`       |
| D4 | Detection Reference  | Devs / analysts        | `src/d4-detection-reference/`|
| D5 | Developer Guide      | Contributors           | `src/d5-developer/`          |
| D6 | Operations Guide     | Ops / DevOps           | `src/d6-operations/`         |
| D7 | Simulation & Demo    | Analysts / devs        | `src/d7-simulations/`        |

## Building the DOCX outputs

```bash
# Install toolchain (Debian/Ubuntu):
sudo apt install -y pandoc
sudo npm install -g @mermaid-js/mermaid-cli

# From this folder:
make all          # build all 7 .docx files
make d4           # build only D4 Detection Reference
make diagrams     # render Mermaid -> SVG + PNG
make catalogs     # regenerate auto-generated catalog tables
make verify       # check code -> doc coverage
make clean        # remove build/ outputs
```

Outputs land in `build/ChainSentinel-D*.docx`.

## Authoring

- **Prose**: Markdown (`.md`) — one file per chapter, prefixed `00-`, `10-`, etc.
  Pandoc concatenates them in lexical order.
- **Diagrams**: `.mmd` Mermaid sources in `diagrams/src/`; the build pipeline
  renders them to `diagrams/rendered/*.svg` + `*.png`. Embed in Markdown via
  `![Title](../diagrams/rendered/<name>.png)`.
- **Catalog tables** (signals, patterns, derived events, ES fields, endpoints):
  do **not** edit by hand. They are regenerated from source by
  `scripts/generate_catalog_tables.py` and dropped into `src/_generated/`.
  Documents include them with the `pandoc` markdown_include extension or
  simply by inlining the generated `.md` file's contents at build time.
- **Style**: heading levels match Pandoc defaults (`#` H1, `##` H2, etc.).
  Use fenced code blocks with language tags. Word styles are bound to the
  reference doc at `pandoc/reference.docx`.

## Verification

`scripts/verify_coverage.py` walks the source tree and produces
`coverage_report.md` listing every code module, signal, pattern, derived event,
ABI, ES field, frontend file, scenario, and endpoint, with a status flag for
whether it is referenced anywhere under `src/`. The target is 100% before final
DOCX builds. See also `CHECKLIST.md`.
