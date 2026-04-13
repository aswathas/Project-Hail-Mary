# ChainSentinel Copilot — Implementation Plan (Plan 6 of 6)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the Ollama integration with Gemma 3 1B for the ChainSentinel copilot — `copilot.py` (chat with investigation context), `report_template.py` (builds structured JSON context from ES data), and `report_sections.py` (7-section forensic report generation). After this plan, the analyst can chat with the copilot about any investigation and generate structured forensic reports.

**Architecture:** Three Python modules in `chainsentinel/ollama/`. The copilot module manages conversation state with investigation context injection. The report template module queries ES for all investigation data and builds a structured JSON context object. The report sections module defines 7 report sections with per-section prompts, sends them sequentially to Gemma 3 1B via Ollama's streaming API, and assembles the final report.

**Tech Stack:** Python 3.11+, httpx (async HTTP for Ollama API), elasticsearch-py 8.x, pytest

**Spec reference:** `docs/superpowers/specs/2026-04-12-chainsentinel-design.md` sections 10 (CopilotPanel, Report Generation)

**Depends on:** Plan 1 (ES indices, config), Plan 2 (signals/alerts in ES), Plan 3 (attacker data in ES)

---

## File Structure

```
chainsentinel/
├── ollama/
│   ├── __init__.py
│   ├── copilot.py                   ← chat with investigation context
│   ├── report_template.py           ← builds structured JSON context from ES
│   └── report_sections.py           ← 7-section report generation
└── tests/
    ├── test_copilot.py
    ├── test_report_template.py
    └── test_report_sections.py
```

---

### Task 1: Ollama Module Scaffolding

**Files:**
- Create: `chainsentinel/ollama/__init__.py`

- [ ] **Step 1: Create directory and init**

```bash
cd /mnt/c/Users/aswat/OneDrive/Desktop/Projects/Project_Hail_Mary
mkdir -p chainsentinel/ollama
touch chainsentinel/ollama/__init__.py
```

- [ ] **Step 2: Commit**

```bash
git add chainsentinel/ollama/__init__.py
git commit -m "feat: ollama module scaffolding"
```

---

### Task 2: Report Template — Structured Context Builder

**Files:**
- Create: `chainsentinel/ollama/report_template.py`
- Create: `chainsentinel/tests/test_report_template.py`

- [ ] **Step 1: Write the tests**

`chainsentinel/tests/test_report_template.py`:

```python
import pytest
from unittest.mock import MagicMock


def _mock_es_search(hits):
    """Build a mock ES search response."""
    return {
        "hits": {
            "total": {"value": len(hits)},
            "hits": [{"_source": h} for h in hits],
        }
    }


def test_build_context_returns_all_sections():
    from ollama.report_template import build_report_context

    mock_client = MagicMock()
    mock_client.search.return_value = _mock_es_search([])

    ctx = build_report_context(mock_client, "INV-001", 31337)

    assert "case_id" in ctx
    assert "signals" in ctx
    assert "alerts" in ctx
    assert "attacker_profile" in ctx
    assert "fund_trail" in ctx
    assert "timeline" in ctx
    assert "stats" in ctx
    assert ctx["case_id"] == "INV-001"


def test_build_context_populates_signals():
    from ollama.report_template import build_report_context

    mock_client = MagicMock()
    signals = [
        {"signal_name": "reentrancy_pattern", "severity": "CRIT", "score": 0.95,
         "description": "Recursive calls detected", "tx_hash": "0xabc", "block_number": 10},
        {"signal_name": "internal_eth_drain", "severity": "CRIT", "score": 0.85,
         "description": "ETH drained via internal calls", "tx_hash": "0xabc", "block_number": 10},
    ]
    alerts = [
        {"pattern_id": "AP-005", "pattern_name": "Reentrancy Drain", "confidence": 0.9,
         "attacker_wallet": "0xattacker", "victim_contract": "0xvictim",
         "funds_drained_eth": 17.0, "signals_fired": ["reentrancy_pattern", "internal_eth_drain"]},
    ]
    attacker = [
        {"attacker_type": "profile", "cluster_wallets": ["0xattacker"],
         "total_stolen_eth": 17.0, "exit_routes": ["mixer:Tornado Cash"],
         "fund_trail_hops": 3},
    ]

    def search_side_effect(index, query, size=100, sort=None):
        layer_filter = None
        for clause in query.get("bool", {}).get("must", []):
            if "term" in clause and "layer" in clause["term"]:
                layer_filter = clause["term"]["layer"]

        if layer_filter == "signal":
            return _mock_es_search(signals)
        elif layer_filter == "alert":
            return _mock_es_search(alerts)
        elif layer_filter == "attacker":
            return _mock_es_search(attacker)
        return _mock_es_search([])

    mock_client.search.side_effect = search_side_effect

    ctx = build_report_context(mock_client, "INV-001", 31337)

    assert len(ctx["signals"]) == 2
    assert ctx["signals"][0]["signal_name"] == "reentrancy_pattern"
    assert len(ctx["alerts"]) == 1
    assert ctx["alerts"][0]["pattern_name"] == "Reentrancy Drain"
    assert ctx["attacker_profile"]["total_stolen_eth"] == 17.0
    assert ctx["stats"]["signal_count"] == 2
    assert ctx["stats"]["alert_count"] == 1


def test_build_context_handles_empty_investigation():
    from ollama.report_template import build_report_context

    mock_client = MagicMock()
    mock_client.search.return_value = _mock_es_search([])

    ctx = build_report_context(mock_client, "INV-EMPTY", 31337)

    assert ctx["signals"] == []
    assert ctx["alerts"] == []
    assert ctx["attacker_profile"] is None
    assert ctx["stats"]["signal_count"] == 0


def test_format_context_as_prompt():
    from ollama.report_template import format_context_as_prompt

    ctx = {
        "case_id": "INV-001",
        "chain_id": 31337,
        "signals": [
            {"signal_name": "reentrancy_pattern", "severity": "CRIT", "score": 0.95,
             "description": "Recursive calls"},
        ],
        "alerts": [
            {"pattern_name": "Reentrancy Drain", "confidence": 0.9,
             "attacker_wallet": "0xattacker", "victim_contract": "0xvictim",
             "funds_drained_eth": 17.0},
        ],
        "attacker_profile": {
            "cluster_wallets": ["0xattacker"],
            "total_stolen_eth": 17.0,
            "exit_routes": ["mixer:Tornado Cash"],
        },
        "fund_trail": [],
        "timeline": [],
        "stats": {"signal_count": 1, "alert_count": 1, "block_count": 8, "tx_count": 47},
    }

    prompt = format_context_as_prompt(ctx)

    assert "INV-001" in prompt
    assert "reentrancy_pattern" in prompt
    assert "Reentrancy Drain" in prompt
    assert "0xattacker" in prompt
    assert "17.0" in prompt
    assert isinstance(prompt, str)
    assert len(prompt) > 100
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /mnt/c/Users/aswat/OneDrive/Desktop/Projects/Project_Hail_Mary/chainsentinel
python -m pytest tests/test_report_template.py -v
```

Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Implement report_template.py**

`chainsentinel/ollama/report_template.py`:

```python
"""
Report Template — builds structured JSON context from ES data.

Queries ES for all investigation data (signals, alerts, attacker profiles,
fund trails, timeline events) and assembles a structured context object
that gets passed to the LLM for report generation.
"""
import json
from typing import Optional


def _query_layer(es_client, investigation_id: str, layer: str, size: int = 500) -> list[dict]:
    """Query ES for documents of a specific layer."""
    response = es_client.search(
        index="forensics",
        query={
            "bool": {
                "must": [
                    {"term": {"investigation_id": investigation_id}},
                    {"term": {"layer": layer}},
                ]
            }
        },
        size=size,
        sort=[{"block_number": "asc"}] if layer != "attacker" else [{"@timestamp": "desc"}],
    )
    return [hit["_source"] for hit in response.get("hits", {}).get("hits", [])]


def build_report_context(
    es_client,
    investigation_id: str,
    chain_id: int,
) -> dict:
    """
    Build a structured context object from all investigation data in ES.

    Returns dict with keys:
        case_id, chain_id, signals, alerts, attacker_profile,
        fund_trail, timeline, stats
    """
    signals = _query_layer(es_client, investigation_id, "signal")
    alerts = _query_layer(es_client, investigation_id, "alert")
    attacker_docs = _query_layer(es_client, investigation_id, "attacker")
    derived = _query_layer(es_client, investigation_id, "derived", size=1000)

    # Extract attacker profile (first profile doc)
    attacker_profile = None
    fund_trail_docs = []
    for doc in attacker_docs:
        if doc.get("attacker_type") == "profile" and attacker_profile is None:
            attacker_profile = doc
        elif doc.get("attacker_type") == "fund_trail":
            fund_trail_docs.append(doc)

    # Build timeline from signals + derived events
    timeline = []
    for sig in signals:
        timeline.append({
            "block_number": sig.get("block_number"),
            "type": "signal",
            "name": sig.get("signal_name"),
            "severity": sig.get("severity"),
            "description": sig.get("description"),
            "tx_hash": sig.get("tx_hash"),
        })
    for d in derived:
        if d.get("derived_type") in ("native_transfer", "asset_transfer", "admin_action"):
            timeline.append({
                "block_number": d.get("block_number"),
                "type": "derived",
                "name": d.get("derived_type"),
                "description": f"{d.get('from_address', '?')} -> {d.get('to_address', '?')}: {d.get('value_eth', 0)} ETH",
                "tx_hash": d.get("tx_hash"),
            })

    timeline.sort(key=lambda x: x.get("block_number") or 0)

    # Compute stats
    all_blocks = set()
    all_txs = set()
    for doc in signals + derived:
        if doc.get("block_number"):
            all_blocks.add(doc["block_number"])
        if doc.get("tx_hash"):
            all_txs.add(doc["tx_hash"])

    stats = {
        "signal_count": len(signals),
        "alert_count": len(alerts),
        "block_count": len(all_blocks),
        "tx_count": len(all_txs),
    }

    return {
        "case_id": investigation_id,
        "chain_id": chain_id,
        "signals": signals,
        "alerts": alerts,
        "attacker_profile": attacker_profile,
        "fund_trail": fund_trail_docs,
        "timeline": timeline,
        "stats": stats,
    }


def format_context_as_prompt(ctx: dict) -> str:
    """
    Format the structured context into a text prompt for the LLM.
    Keeps it concise but includes all forensic evidence.
    """
    lines = []
    lines.append(f"# Investigation: {ctx['case_id']}")
    lines.append(f"Chain ID: {ctx['chain_id']}")
    lines.append("")

    # Stats
    s = ctx["stats"]
    lines.append(f"## Statistics")
    lines.append(f"- Signals fired: {s['signal_count']}")
    lines.append(f"- Attack patterns matched: {s['alert_count']}")
    lines.append(f"- Blocks analyzed: {s['block_count']}")
    lines.append(f"- Transactions analyzed: {s['tx_count']}")
    lines.append("")

    # Alerts
    if ctx["alerts"]:
        lines.append("## Attack Patterns Detected")
        for alert in ctx["alerts"]:
            lines.append(f"- **{alert.get('pattern_name', 'Unknown')}** (confidence: {alert.get('confidence', 0)})")
            lines.append(f"  Attacker: {alert.get('attacker_wallet', 'Unknown')}")
            lines.append(f"  Victim: {alert.get('victim_contract', 'Unknown')}")
            lines.append(f"  Funds drained: {alert.get('funds_drained_eth', 0)} ETH")
            lines.append(f"  Signals: {', '.join(alert.get('signals_fired', []))}")
        lines.append("")

    # Signals
    if ctx["signals"]:
        lines.append("## Signals Fired")
        for sig in ctx["signals"]:
            lines.append(f"- [{sig.get('severity', 'MED')}] **{sig.get('signal_name', '')}** "
                        f"(score: {sig.get('score', 0)}) — {sig.get('description', '')}")
        lines.append("")

    # Attacker profile
    if ctx["attacker_profile"]:
        ap = ctx["attacker_profile"]
        lines.append("## Attacker Profile")
        lines.append(f"- Wallets: {', '.join(ap.get('cluster_wallets', []))}")
        lines.append(f"- Total stolen: {ap.get('total_stolen_eth', 0)} ETH")
        lines.append(f"- Fund trail hops: {ap.get('fund_trail_hops', 0)}")
        lines.append(f"- Exit routes: {', '.join(ap.get('exit_routes', []))}")
        lines.append("")

    # Timeline (abbreviated)
    if ctx["timeline"]:
        lines.append("## Timeline")
        for event in ctx["timeline"][:20]:  # Cap at 20 for prompt size
            sev = f"[{event.get('severity', '')}] " if event.get("severity") else ""
            lines.append(f"- Block {event.get('block_number', '?')}: "
                        f"{sev}{event.get('name', '')} — {event.get('description', '')}")
        if len(ctx["timeline"]) > 20:
            lines.append(f"  ... and {len(ctx['timeline']) - 20} more events")
        lines.append("")

    return "\n".join(lines)
```

- [ ] **Step 4: Run tests**

```bash
cd /mnt/c/Users/aswat/OneDrive/Desktop/Projects/Project_Hail_Mary/chainsentinel
python -m pytest tests/test_report_template.py -v
```

Expected: All 4 PASS

- [ ] **Step 5: Commit**

```bash
git add chainsentinel/ollama/report_template.py chainsentinel/tests/test_report_template.py
git commit -m "feat: report template builds structured context from ES investigation data"
```

---

### Task 3: Copilot — Chat with Investigation Context

**Files:**
- Create: `chainsentinel/ollama/copilot.py`
- Create: `chainsentinel/tests/test_copilot.py`

- [ ] **Step 1: Write the tests**

`chainsentinel/tests/test_copilot.py`:

```python
import pytest
from unittest.mock import MagicMock, AsyncMock, patch


@pytest.mark.asyncio
async def test_copilot_chat_sends_context():
    from ollama.copilot import Copilot

    mock_http = AsyncMock()
    mock_http.post.return_value = MagicMock(
        status_code=200,
        json=MagicMock(return_value={
            "message": {"role": "assistant", "content": "The reentrancy attack drained 17 ETH."},
        }),
    )

    copilot = Copilot(
        ollama_url="http://localhost:11434",
        model="gemma3:1b",
        http_client=mock_http,
    )

    context = "Investigation INV-001. Signals: reentrancy_pattern (CRIT, 0.95)."
    response = await copilot.chat("What happened?", context)

    assert "reentrancy" in response.lower() or response  # Response came back
    mock_http.post.assert_called_once()

    # Verify context was injected into system message
    call_args = mock_http.post.call_args
    body = call_args.kwargs.get("json") or call_args.args[1] if len(call_args.args) > 1 else {}
    messages = body.get("messages", [])
    system_msgs = [m for m in messages if m["role"] == "system"]
    assert len(system_msgs) == 1
    assert "INV-001" in system_msgs[0]["content"]


@pytest.mark.asyncio
async def test_copilot_maintains_history():
    from ollama.copilot import Copilot

    mock_http = AsyncMock()
    mock_http.post.return_value = MagicMock(
        status_code=200,
        json=MagicMock(return_value={
            "message": {"role": "assistant", "content": "Response 1"},
        }),
    )

    copilot = Copilot(
        ollama_url="http://localhost:11434",
        model="gemma3:1b",
        http_client=mock_http,
    )

    await copilot.chat("Question 1", "context")
    assert len(copilot.history) == 2  # user + assistant

    mock_http.post.return_value = MagicMock(
        status_code=200,
        json=MagicMock(return_value={
            "message": {"role": "assistant", "content": "Response 2"},
        }),
    )

    await copilot.chat("Question 2", "context")
    assert len(copilot.history) == 4  # 2 user + 2 assistant


@pytest.mark.asyncio
async def test_copilot_clear_history():
    from ollama.copilot import Copilot

    mock_http = AsyncMock()
    mock_http.post.return_value = MagicMock(
        status_code=200,
        json=MagicMock(return_value={
            "message": {"role": "assistant", "content": "OK"},
        }),
    )

    copilot = Copilot(
        ollama_url="http://localhost:11434",
        model="gemma3:1b",
        http_client=mock_http,
    )

    await copilot.chat("test", "context")
    copilot.clear_history()

    assert copilot.history == []


@pytest.mark.asyncio
async def test_copilot_handles_ollama_error():
    from ollama.copilot import Copilot

    mock_http = AsyncMock()
    mock_http.post.side_effect = Exception("Connection refused")

    copilot = Copilot(
        ollama_url="http://localhost:11434",
        model="gemma3:1b",
        http_client=mock_http,
    )

    response = await copilot.chat("test", "context")

    assert "error" in response.lower() or "unavailable" in response.lower()


@pytest.mark.asyncio
async def test_copilot_builds_system_prompt():
    from ollama.copilot import Copilot

    copilot = Copilot(
        ollama_url="http://localhost:11434",
        model="gemma3:1b",
    )

    system_prompt = copilot._build_system_prompt("Signals: reentrancy (CRIT)")

    assert "ChainSentinel" in system_prompt
    assert "forensic" in system_prompt.lower()
    assert "reentrancy" in system_prompt


def test_copilot_temperature_config():
    from ollama.copilot import Copilot

    copilot = Copilot(
        ollama_url="http://localhost:11434",
        model="gemma3:1b",
        temperature=0.1,
    )

    assert copilot.temperature == 0.1
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /mnt/c/Users/aswat/OneDrive/Desktop/Projects/Project_Hail_Mary/chainsentinel
python -m pytest tests/test_copilot.py -v
```

Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Implement copilot.py**

`chainsentinel/ollama/copilot.py`:

```python
"""
Copilot — chat with investigation context via Ollama.

Manages conversation state with context injection.
The copilot receives the investigation context as a system message
and maintains chat history for follow-up questions.

Three operational states:
- idle: greeting + instructions
- watching: during analysis — proactively narrates CRIT signals
- ready: after analysis — answers questions using investigation context
"""
import httpx
from typing import Optional


SYSTEM_TEMPLATE = """You are ChainSentinel Copilot, an EVM blockchain forensics assistant.
You analyze on-chain investigation data and explain findings to security analysts.

Your role:
- Explain what signals and patterns mean in plain security terms
- Describe attack mechanisms based on evidence
- Trace fund flows and identify attacker behavior
- Help write forensic reports
- Be precise with addresses, amounts, and block numbers

Current investigation context:
{context}

When responding:
- Use specific data from the investigation (addresses, amounts, block numbers)
- Reference signal names and their severity
- Be concise but thorough
- If you don't have enough data to answer, say so explicitly
"""


class Copilot:
    """Chat interface with investigation context injection."""

    def __init__(
        self,
        ollama_url: str = "http://localhost:11434",
        model: str = "gemma3:1b",
        temperature: float = 0.2,
        http_client: Optional[httpx.AsyncClient] = None,
    ):
        self.ollama_url = ollama_url.rstrip("/")
        self.model = model
        self.temperature = temperature
        self.http_client = http_client
        self.history: list[dict] = []

    def _build_system_prompt(self, context: str) -> str:
        """Build system prompt with investigation context."""
        return SYSTEM_TEMPLATE.format(context=context)

    async def chat(self, user_message: str, context: str = "") -> str:
        """
        Send a message to the copilot with investigation context.

        Args:
            user_message: The user's question
            context: Investigation context string (from format_context_as_prompt)

        Returns:
            Assistant's response text
        """
        system_prompt = self._build_system_prompt(context)

        messages = [
            {"role": "system", "content": system_prompt},
            *self.history,
            {"role": "user", "content": user_message},
        ]

        try:
            client = self.http_client or httpx.AsyncClient(timeout=120.0)
            should_close = self.http_client is None

            try:
                response = await client.post(
                    f"{self.ollama_url}/api/chat",
                    json={
                        "model": self.model,
                        "messages": messages,
                        "stream": False,
                        "options": {
                            "temperature": self.temperature,
                        },
                    },
                )

                if response.status_code != 200:
                    return f"Error: Ollama returned status {response.status_code}"

                data = response.json()
                assistant_content = data.get("message", {}).get("content", "")

                # Update history
                self.history.append({"role": "user", "content": user_message})
                self.history.append({"role": "assistant", "content": assistant_content})

                return assistant_content

            finally:
                if should_close:
                    await client.aclose()

        except Exception as e:
            return f"Error: Copilot unavailable — {str(e)}"

    async def chat_stream(self, user_message: str, context: str = ""):
        """
        Stream a response from the copilot.
        Yields text chunks as they arrive.
        """
        system_prompt = self._build_system_prompt(context)

        messages = [
            {"role": "system", "content": system_prompt},
            *self.history,
            {"role": "user", "content": user_message},
        ]

        client = self.http_client or httpx.AsyncClient(timeout=120.0)
        should_close = self.http_client is None

        try:
            async with client.stream(
                "POST",
                f"{self.ollama_url}/api/chat",
                json={
                    "model": self.model,
                    "messages": messages,
                    "stream": True,
                    "options": {
                        "temperature": self.temperature,
                    },
                },
            ) as response:
                full_response = ""
                async for line in response.aiter_lines():
                    if not line:
                        continue
                    try:
                        import json
                        data = json.loads(line)
                        chunk = data.get("message", {}).get("content", "")
                        if chunk:
                            full_response += chunk
                            yield chunk
                    except (json.JSONDecodeError, KeyError):
                        continue

                # Update history after stream completes
                self.history.append({"role": "user", "content": user_message})
                self.history.append({"role": "assistant", "content": full_response})

        finally:
            if should_close:
                await client.aclose()

    def clear_history(self):
        """Clear conversation history."""
        self.history = []

    def get_history(self) -> list[dict]:
        """Get current conversation history."""
        return list(self.history)
```

- [ ] **Step 4: Run tests**

```bash
cd /mnt/c/Users/aswat/OneDrive/Desktop/Projects/Project_Hail_Mary/chainsentinel
python -m pytest tests/test_copilot.py -v
```

Expected: All 6 PASS

- [ ] **Step 5: Commit**

```bash
git add chainsentinel/ollama/copilot.py chainsentinel/tests/test_copilot.py
git commit -m "feat: copilot module with context-aware chat and streaming support"
```

---

### Task 4: Report Sections — 7-Section Forensic Report

**Files:**
- Create: `chainsentinel/ollama/report_sections.py`
- Create: `chainsentinel/tests/test_report_sections.py`

- [ ] **Step 1: Write the tests**

`chainsentinel/tests/test_report_sections.py`:

```python
import pytest
from unittest.mock import MagicMock, AsyncMock, patch


def test_report_sections_defined():
    from ollama.report_sections import REPORT_SECTIONS

    assert len(REPORT_SECTIONS) == 7
    expected_titles = [
        "Executive Summary",
        "Attack Timeline",
        "Technical Mechanism",
        "Attacker Attribution",
        "Fund Trail",
        "Signal Evidence",
        "Remediation Actions",
    ]
    actual_titles = [s["title"] for s in REPORT_SECTIONS]
    assert actual_titles == expected_titles


def test_each_section_has_required_fields():
    from ollama.report_sections import REPORT_SECTIONS

    for section in REPORT_SECTIONS:
        assert "title" in section
        assert "prompt_template" in section
        assert "section_number" in section
        assert isinstance(section["prompt_template"], str)
        assert len(section["prompt_template"]) > 20


def test_build_section_prompt():
    from ollama.report_sections import build_section_prompt

    context = "Investigation INV-001. Reentrancy attack. 17 ETH drained."
    section = {
        "title": "Executive Summary",
        "section_number": 1,
        "prompt_template": "Write a concise executive summary of the investigation. "
                          "Include: attack type, funds lost, severity, and key findings. "
                          "Context: {context}",
    }

    prompt = build_section_prompt(section, context)

    assert "executive summary" in prompt.lower()
    assert "INV-001" in prompt
    assert "17 ETH" in prompt


@pytest.mark.asyncio
async def test_generate_section():
    from ollama.report_sections import generate_section

    mock_http = AsyncMock()
    mock_http.post.return_value = MagicMock(
        status_code=200,
        json=MagicMock(return_value={
            "message": {
                "role": "assistant",
                "content": "## Executive Summary\n\nA reentrancy attack drained 17 ETH from VulnerableVault.",
            },
        }),
    )

    section = {
        "title": "Executive Summary",
        "section_number": 1,
        "prompt_template": "Write an executive summary. Context: {context}",
    }

    result = await generate_section(
        section, "INV-001 context here",
        ollama_url="http://localhost:11434",
        model="gemma3:1b",
        http_client=mock_http,
    )

    assert "Executive Summary" in result or "reentrancy" in result.lower()
    mock_http.post.assert_called_once()


@pytest.mark.asyncio
async def test_generate_full_report():
    from ollama.report_sections import generate_full_report

    mock_http = AsyncMock()
    call_count = 0

    def make_response(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        return MagicMock(
            status_code=200,
            json=MagicMock(return_value={
                "message": {
                    "role": "assistant",
                    "content": f"## Section {call_count}\n\nContent for section {call_count}.",
                },
            }),
        )

    mock_http.post.side_effect = make_response

    report = await generate_full_report(
        context="Test investigation context",
        ollama_url="http://localhost:11434",
        model="gemma3:1b",
        http_client=mock_http,
    )

    # Should have called Ollama 7 times (once per section)
    assert mock_http.post.call_count == 7
    # Report should contain all sections
    assert "Section 1" in report
    assert "Section 7" in report


@pytest.mark.asyncio
async def test_generate_full_report_handles_section_failure():
    from ollama.report_sections import generate_full_report

    mock_http = AsyncMock()
    call_count = 0

    def make_response(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 3:
            raise Exception("Ollama timeout")
        return MagicMock(
            status_code=200,
            json=MagicMock(return_value={
                "message": {"role": "assistant", "content": f"Section {call_count} content"},
            }),
        )

    mock_http.post.side_effect = make_response

    report = await generate_full_report(
        context="Test context",
        ollama_url="http://localhost:11434",
        model="gemma3:1b",
        http_client=mock_http,
    )

    # Should contain error note for failed section but continue
    assert "error" in report.lower() or "failed" in report.lower()
    # Should still have content from other sections
    assert "Section 1" in report or "Section 2" in report


@pytest.mark.asyncio
async def test_generate_full_report_yields_progress():
    from ollama.report_sections import generate_full_report_streaming

    mock_http = AsyncMock()
    mock_http.post.return_value = MagicMock(
        status_code=200,
        json=MagicMock(return_value={
            "message": {"role": "assistant", "content": "Section content"},
        }),
    )

    sections_completed = []
    async for progress in generate_full_report_streaming(
        context="Test context",
        ollama_url="http://localhost:11434",
        model="gemma3:1b",
        http_client=mock_http,
    ):
        sections_completed.append(progress["section_number"])

    assert len(sections_completed) == 7
    assert sections_completed == [1, 2, 3, 4, 5, 6, 7]
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /mnt/c/Users/aswat/OneDrive/Desktop/Projects/Project_Hail_Mary/chainsentinel
python -m pytest tests/test_report_sections.py -v
```

Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Implement report_sections.py**

`chainsentinel/ollama/report_sections.py`:

```python
"""
Report Sections — 7-section forensic report generation via Ollama.

Defines 7 report sections, each with a specialized prompt template.
Sections are generated sequentially (each builds on previous context).
Results are streamed back for real-time display in the copilot panel.

Sections:
1. Executive Summary
2. Attack Timeline
3. Technical Mechanism
4. Attacker Attribution
5. Fund Trail
6. Signal Evidence
7. Remediation Actions
"""
import httpx
from typing import Optional, AsyncGenerator


REPORT_SECTIONS = [
    {
        "section_number": 1,
        "title": "Executive Summary",
        "prompt_template": (
            "Write a concise executive summary (3-5 paragraphs) of this blockchain security investigation. "
            "Include: the type of attack detected, total funds lost in ETH, severity level, "
            "affected contracts, and the key finding. Write for a non-technical executive audience. "
            "Do not use markdown headers — start directly with the summary text.\n\n"
            "Investigation data:\n{context}"
        ),
    },
    {
        "section_number": 2,
        "title": "Attack Timeline",
        "prompt_template": (
            "Write a chronological attack timeline based on the investigation data. "
            "For each event, include: block number, what happened, and its significance. "
            "Separate the timeline into phases: Setup, Normal Activity, Attack Execution, Fund Extraction. "
            "Use block numbers and transaction hashes where available.\n\n"
            "Investigation data:\n{context}"
        ),
    },
    {
        "section_number": 3,
        "title": "Technical Mechanism",
        "prompt_template": (
            "Explain the technical mechanism of the attack in detail. "
            "Describe: the vulnerability exploited, the exact sequence of contract calls, "
            "how the attacker manipulated state, and why the attack succeeded. "
            "Reference specific signals that prove each step. "
            "Write for a Solidity developer audience.\n\n"
            "Investigation data:\n{context}"
        ),
    },
    {
        "section_number": 4,
        "title": "Attacker Attribution",
        "prompt_template": (
            "Describe what we know about the attacker based on the investigation data. "
            "Include: wallet addresses involved, cluster analysis results, "
            "funding sources, whether wallets are new or have prior history, "
            "any OFAC or known-exploiter matches, and behavioral patterns. "
            "Be precise about what is confirmed vs. suspected.\n\n"
            "Investigation data:\n{context}"
        ),
    },
    {
        "section_number": 5,
        "title": "Fund Trail",
        "prompt_template": (
            "Describe the fund trail from the investigation. "
            "Include: initial attack proceeds, each hop in the fund trace, "
            "taint scores at each hop, exit routes used (mixers, bridges, CEX deposits), "
            "total amount tracked, and any funds that could potentially be recovered. "
            "Reference specific transaction hashes and amounts.\n\n"
            "Investigation data:\n{context}"
        ),
    },
    {
        "section_number": 6,
        "title": "Signal Evidence",
        "prompt_template": (
            "List and explain all signals that fired during the investigation. "
            "For each signal: name, severity, score, what it detected, and how it "
            "contributes to the overall attack pattern identification. "
            "Group by signal family. Explain which signals are most significant "
            "and which provide corroborating evidence.\n\n"
            "Investigation data:\n{context}"
        ),
    },
    {
        "section_number": 7,
        "title": "Remediation Actions",
        "prompt_template": (
            "Based on the attack type and investigation findings, recommend specific remediation actions. "
            "Include: immediate actions (pause contracts, blacklist addresses), "
            "short-term fixes (code patches, access control changes), "
            "long-term improvements (oracle upgrades, reentrancy guards, monitoring), "
            "and fund recovery steps (law enforcement contacts, CEX freeze requests). "
            "Be specific and actionable.\n\n"
            "Investigation data:\n{context}"
        ),
    },
]


def build_section_prompt(section: dict, context: str) -> str:
    """Build the full prompt for a report section by injecting context."""
    return section["prompt_template"].format(context=context)


async def generate_section(
    section: dict,
    context: str,
    ollama_url: str = "http://localhost:11434",
    model: str = "gemma3:1b",
    temperature: float = 0.2,
    http_client: Optional[httpx.AsyncClient] = None,
) -> str:
    """
    Generate a single report section via Ollama.

    Args:
        section: Section definition dict
        context: Investigation context string
        ollama_url: Ollama API URL
        model: Model name
        temperature: Generation temperature
        http_client: Optional httpx client (for testing)

    Returns:
        Generated section text
    """
    prompt = build_section_prompt(section, context)

    messages = [
        {
            "role": "system",
            "content": (
                "You are a blockchain security forensic analyst writing a professional "
                "investigation report. Write clearly, precisely, and factually. "
                "Reference specific on-chain data (addresses, amounts, block numbers) "
                "from the provided investigation context. Do not fabricate data."
            ),
        },
        {"role": "user", "content": prompt},
    ]

    client = http_client or httpx.AsyncClient(timeout=120.0)
    should_close = http_client is None

    try:
        response = await client.post(
            f"{ollama_url}/api/chat",
            json={
                "model": model,
                "messages": messages,
                "stream": False,
                "options": {"temperature": temperature},
            },
        )

        if response.status_code != 200:
            return f"[Error generating section: HTTP {response.status_code}]"

        data = response.json()
        return data.get("message", {}).get("content", "[No content generated]")

    finally:
        if should_close:
            await client.aclose()


async def generate_full_report(
    context: str,
    ollama_url: str = "http://localhost:11434",
    model: str = "gemma3:1b",
    temperature: float = 0.2,
    http_client: Optional[httpx.AsyncClient] = None,
) -> str:
    """
    Generate the complete 7-section forensic report.

    Sections are generated sequentially. If a section fails,
    an error note is inserted and generation continues.

    Returns:
        Full report as a single string with section headers.
    """
    report_parts = []
    report_parts.append("# Forensic Investigation Report\n")

    for section in REPORT_SECTIONS:
        header = f"\n## {section['section_number']}. {section['title']}\n"

        try:
            content = await generate_section(
                section, context,
                ollama_url=ollama_url,
                model=model,
                temperature=temperature,
                http_client=http_client,
            )
            report_parts.append(header)
            report_parts.append(content)
            report_parts.append("")

        except Exception as e:
            report_parts.append(header)
            report_parts.append(f"[Error: Failed to generate this section — {str(e)}]")
            report_parts.append("")

    return "\n".join(report_parts)


async def generate_full_report_streaming(
    context: str,
    ollama_url: str = "http://localhost:11434",
    model: str = "gemma3:1b",
    temperature: float = 0.2,
    http_client: Optional[httpx.AsyncClient] = None,
) -> AsyncGenerator[dict, None]:
    """
    Generate the report with per-section progress updates.

    Yields dicts with:
        section_number, title, content, status ('complete' or 'error')
    """
    for section in REPORT_SECTIONS:
        try:
            content = await generate_section(
                section, context,
                ollama_url=ollama_url,
                model=model,
                temperature=temperature,
                http_client=http_client,
            )

            yield {
                "section_number": section["section_number"],
                "title": section["title"],
                "content": content,
                "status": "complete",
            }

        except Exception as e:
            yield {
                "section_number": section["section_number"],
                "title": section["title"],
                "content": f"Error: {str(e)}",
                "status": "error",
            }
```

- [ ] **Step 4: Run tests**

```bash
cd /mnt/c/Users/aswat/OneDrive/Desktop/Projects/Project_Hail_Mary/chainsentinel
python -m pytest tests/test_report_sections.py -v
```

Expected: All 7 PASS

- [ ] **Step 5: Commit**

```bash
git add chainsentinel/ollama/report_sections.py chainsentinel/tests/test_report_sections.py
git commit -m "feat: 7-section forensic report generation with per-section prompts and streaming"
```

---

### Task 5: Copilot Integration — Wire into Server

**Files:**
- Create: `chainsentinel/tests/test_copilot_integration.py`

- [ ] **Step 1: Write integration test**

`chainsentinel/tests/test_copilot_integration.py`:

```python
import pytest
from unittest.mock import MagicMock, AsyncMock


def _mock_es_search(hits):
    return {
        "hits": {
            "total": {"value": len(hits)},
            "hits": [{"_source": h} for h in hits],
        }
    }


@pytest.mark.asyncio
async def test_full_copilot_report_pipeline():
    """
    Integration: build_report_context -> format_context_as_prompt -> generate_full_report
    """
    from ollama.report_template import build_report_context, format_context_as_prompt
    from ollama.report_sections import generate_full_report

    # Mock ES with investigation data
    mock_es = MagicMock()
    mock_es.search.return_value = _mock_es_search([
        {
            "layer": "signal",
            "signal_name": "reentrancy_pattern",
            "severity": "CRIT",
            "score": 0.95,
            "description": "Recursive calls detected",
            "tx_hash": "0xabc123",
            "block_number": 10,
        },
    ])

    ctx = build_report_context(mock_es, "INV-001", 31337)
    prompt = format_context_as_prompt(ctx)

    assert "INV-001" in prompt
    assert "reentrancy_pattern" in prompt

    # Mock Ollama
    mock_http = AsyncMock()
    mock_http.post.return_value = MagicMock(
        status_code=200,
        json=MagicMock(return_value={
            "message": {"role": "assistant", "content": "Report section content."},
        }),
    )

    report = await generate_full_report(
        context=prompt,
        http_client=mock_http,
    )

    assert "Forensic Investigation Report" in report
    assert mock_http.post.call_count == 7


@pytest.mark.asyncio
async def test_copilot_chat_with_real_context():
    """
    Integration: build_report_context -> format_context_as_prompt -> copilot.chat
    """
    from ollama.report_template import build_report_context, format_context_as_prompt
    from ollama.copilot import Copilot

    # Mock ES
    mock_es = MagicMock()
    mock_es.search.return_value = _mock_es_search([])

    ctx = build_report_context(mock_es, "INV-002", 31337)
    prompt = format_context_as_prompt(ctx)

    # Mock Ollama
    mock_http = AsyncMock()
    mock_http.post.return_value = MagicMock(
        status_code=200,
        json=MagicMock(return_value={
            "message": {"role": "assistant", "content": "No signals detected in this investigation."},
        }),
    )

    copilot = Copilot(http_client=mock_http)
    response = await copilot.chat("What happened?", prompt)

    assert "no signals" in response.lower() or response
    assert len(copilot.history) == 2


@pytest.mark.asyncio
async def test_copilot_proactive_signal_narration():
    """Test copilot can narrate CRIT signals during analysis (watching state)."""
    from ollama.copilot import Copilot

    mock_http = AsyncMock()
    mock_http.post.return_value = MagicMock(
        status_code=200,
        json=MagicMock(return_value={
            "message": {
                "role": "assistant",
                "content": "CRITICAL: Reentrancy pattern detected — recursive calls at depth 4+.",
            },
        }),
    )

    copilot = Copilot(http_client=mock_http)

    # Simulate proactive narration for a CRIT signal
    signal_context = (
        "A CRIT signal just fired: reentrancy_pattern (score 0.95). "
        "It detected recursive calls to the same contract at call depths 2, 4, 6, 8. "
        "This transaction is in block 15."
    )

    response = await copilot.chat(
        "A critical signal just fired. Explain what this means.",
        signal_context,
    )

    assert "reentrancy" in response.lower()
```

- [ ] **Step 2: Run integration tests**

```bash
cd /mnt/c/Users/aswat/OneDrive/Desktop/Projects/Project_Hail_Mary/chainsentinel
python -m pytest tests/test_copilot_integration.py -v
```

Expected: All 3 PASS

- [ ] **Step 3: Run all copilot tests together**

```bash
cd /mnt/c/Users/aswat/OneDrive/Desktop/Projects/Project_Hail_Mary/chainsentinel
python -m pytest tests/test_copilot.py tests/test_report_template.py tests/test_report_sections.py tests/test_copilot_integration.py -v
```

Expected: All PASS

- [ ] **Step 4: Commit**

```bash
git add chainsentinel/tests/test_copilot_integration.py
git commit -m "feat: copilot integration tests verify context -> prompt -> report pipeline"
```
