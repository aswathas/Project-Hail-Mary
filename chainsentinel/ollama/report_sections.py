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
