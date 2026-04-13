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
    body = call_args.kwargs.get("json") or (call_args.args[1] if len(call_args.args) > 1 else {})
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
