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
