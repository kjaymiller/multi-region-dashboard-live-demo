"""Chat integration with Ollama for database performance insights."""

import json
from collections.abc import AsyncGenerator

import httpx

OLLAMA_BASE_URL = "http://localhost:11434"
DEFAULT_MODEL = "llama3.2:latest"


def get_system_prompt(recent_checks: list[dict] = None) -> str:
    """Generate system prompt with database context."""
    prompt = """You are an AI assistant helping users understand their multi-region PostgreSQL database performance.

You have access to information about:
- Connection tests across multiple regions (US East, EU West, Asia Pacific)
- Latency measurements and performance metrics
- Load testing results
- Database health metrics (cache hit ratios, connection counts, etc.)

When answering questions:
1. Be concise and actionable
2. Focus on performance insights and recommendations
3. Explain database concepts in simple terms
4. Reference specific metrics when available
5. Suggest optimizations when relevant

"""

    if recent_checks:
        prompt += "\nRecent check data:\n"
        for check in recent_checks[:5]:
            region = check.get("region_id", "unknown")
            check_type = check.get("check_type", "unknown")
            success = check.get("success", False)
            metric = check.get("metric_value")

            if success and metric:
                prompt += f"- {region}: {check_type} - {metric:.2f} {check.get('metric_unit', '')}\n"
            elif not success:
                prompt += f"- {region}: {check_type} - FAILED\n"

    return prompt


async def chat_with_ollama(
    message: str,
    model: str = DEFAULT_MODEL,
    context: str = None
) -> AsyncGenerator[str, None]:
    """Stream chat responses from Ollama."""

    messages = []

    # Add system prompt if context provided
    if context:
        messages.append({
            "role": "system",
            "content": context
        })

    # Add user message
    messages.append({
        "role": "user",
        "content": message
    })

    async with httpx.AsyncClient(timeout=60.0) as client:
        async with client.stream(
            "POST",
            f"{OLLAMA_BASE_URL}/api/chat",
            json={
                "model": model,
                "messages": messages,
                "stream": True
            }
        ) as response:
            async for line in response.aiter_lines():
                if line.strip():
                    try:
                        data = json.loads(line)
                        if "message" in data and "content" in data["message"]:
                            content = data["message"]["content"]
                            if content:
                                yield content
                    except json.JSONDecodeError:
                        continue


async def get_chat_response(
    message: str,
    recent_checks: list[dict] = None,
    model: str = DEFAULT_MODEL
) -> str:
    """Get a complete chat response from Ollama (non-streaming)."""

    system_prompt = get_system_prompt(recent_checks)

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": message}
    ]

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            f"{OLLAMA_BASE_URL}/api/chat",
            json={
                "model": model,
                "messages": messages,
                "stream": False
            }
        )

        if response.status_code == 200:
            data = response.json()
            return data.get("message", {}).get("content", "Sorry, I couldn't generate a response.")
        else:
            return f"Error: Unable to connect to Ollama (status {response.status_code})"
