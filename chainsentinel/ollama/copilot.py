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
