# 1. Repository layout

```
Project_Hail_Mary/
├── CLAUDE.md                       # codebase index, AI-agent rules
├── DESIGN.md                       # high-level design brief
├── README.md                       # human-facing quickstart
├── docker-compose.yml              # ES + Kibana
├── run_demo.sh                     # demo orchestrator
├── docs/
│   ├── manual/                     # ← this manual
│   ├── superpowers/specs/          # design spec
│   ├── superpowers/plans/          # 6 implementation plans + e2e
│   ├── CHAINSENTINEL_TECHNICAL_DEEP_DIVE.md
│   └── CHAINSENTINEL_PPT_PROMPT.md
├── chainsentinel/                  # the forensic tool
│   ├── config.json                 # single source of truth
│   ├── server.py                   # FastAPI + SSE
│   ├── start.sh                    # one-command startup
│   ├── requirements.txt
│   ├── Dockerfile
│   ├── pipeline/
│   ├── detection/
│   ├── correlation/
│   ├── es/
│   ├── ollama/
│   ├── frontend/                   # React + Vite
│   ├── e2e_helpers/                # pipeline_runner, validator, repair — E2E test orchestration
│   ├── docker_run.py               # entrypoint used by chainsentinel-pipeline container
│   ├── kibana_setup.py             # Kibana data-view + saved-object provisioning
│   ├── dashboard.py                # optional CLI dashboard
│   └── tests/
└── simulations/                    # Foundry simulations
    ├── foundry.toml
    ├── shared/contracts/           # MockERC20, MockWETH, UserActivity
    └── scenarios/                  # 5 attack scenarios
```

Source-of-truth file: `chainsentinel/config.json`. Source-of-truth
detection: `.esql` and `.eql` files. Source-of-truth ES schemas:
`chainsentinel/es/mappings/*.json`. Nothing else is authoritative.
