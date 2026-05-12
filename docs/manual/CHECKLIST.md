# Documentation Completion Checklist

## Per-document content

- [ ] D1 Executive Overview — all 7 chapters, hero infographics (#1, #13, #14) embedded
- [ ] D2 Analyst Handbook — 5 case studies complete, UI tour screenshots captured
- [ ] D3 Architecture & Design — ADRs (5–7) drafted, diagrams (#1, #2, #4, #6, #8, #10, #11, #12) embedded
- [ ] D4 Detection Reference — 60 signals, 38 patterns, 36 derived events, 8 ABIs, both ES mappings catalogued
- [ ] D5 Developer Guide — every module under `chainsentinel/` documented with API contracts, 4 cookbooks complete
- [ ] D6 Operations Guide — config.json reference complete, troubleshooting matrix populated
- [ ] D7 Simulation Guide — 5 scenarios documented with expected signals/patterns

## Diagrams (14 total)

- [ ] #1  System Architecture (Mermaid)
- [ ] #2  Pipeline Data Flow (Mermaid sequence)
- [ ] #3  Derived Event Builder Map (Mermaid)
- [ ] #4  ES Index Model (Mermaid ER / draw.io)
- [ ] #5  Signal Family Taxonomy (Mermaid mindmap)
- [ ] #6  Signal → Pattern → Incident Hierarchy (Mermaid)
- [ ] #7  Detection Engine Sequence (Mermaid sequence)
- [ ] #8  Correlation Subsystem (Mermaid)
- [ ] #9  Fund-Trace BFS Walk (draw.io / Mermaid)
- [ ] #10 Frontend Three-Column Layout (Mermaid / draw.io)
- [ ] #11 Frontend Component × Hook × API Graph (Mermaid)
- [ ] #12 Ollama Copilot Flow (Mermaid sequence)
- [ ] #13 Simulation Scenario Matrix (infographic)
- [ ] #14 End-to-End Demo Storyboard (infographic)

## Build pipeline

- [ ] `make catalogs` runs cleanly and produces `src/_generated/*.md`
- [ ] `make diagrams` renders every `.mmd` to PNG + SVG with zero errors
- [ ] `make all` produces 7 `.docx` files in `build/` with no missing-image warnings
- [ ] `make verify` reports 100% code-to-doc coverage

## Visual QA

- [ ] Each `.docx` opens in Word / LibreOffice with no broken images
- [ ] Headings, tables, code blocks all use the reference template styles
- [ ] Cross-references resolve (TOC, footnotes if any)

## Reviewer sign-off

- [ ] Analyst reviewer signs off on D2 + skims D1, D7
- [ ] Developer reviewer signs off on D5 + skims D3, D4
- [ ] Operator reviewer signs off on D6 + skims D7
- [ ] Executive reviewer signs off on D1
