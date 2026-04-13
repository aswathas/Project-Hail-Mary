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
