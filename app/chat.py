"""Chat integration with Ollama for database performance insights."""

import json
from collections.abc import AsyncGenerator

import httpx

from .config import get_chat_config


def get_system_prompt(recent_checks: list[dict] | None = None) -> str:
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
                prompt += (
                    f"- {region}: {check_type} - {metric:.2f} {check.get('metric_unit', '')}\n"
                )
            elif not success:
                prompt += f"- {region}: {check_type} - FAILED\n"

    return prompt


async def chat_with_ollama(
    message: str, model: str | None = None, context: str | None = None
) -> AsyncGenerator[str, None]:
    """Stream chat responses from Ollama."""
    
    config = get_chat_config()
    if not config.enabled:
        yield "Chat functionality is disabled. Set CHAT_ENABLED=true to enable."
        return
    
    model = model or config.model

    messages = []

    # Add system prompt if context provided
    if context:
        messages.append({"role": "system", "content": context})

    # Add user message
    messages.append({"role": "user", "content": message})

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            async with client.stream(
                "POST",
                f"{config.base_url}/api/chat",
                json={"model": model, "messages": messages, "stream": True},
            ) as response:
                if response.status_code != 200:
                    yield f"Error: Ollama service returned status {response.status_code}"
                    return
                    
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
    except httpx.ConnectError:
        yield "Error: Cannot connect to Ollama service. Make sure Ollama is running and accessible."


async def get_chat_response(
    message: str, recent_checks: list[dict] | None = None, model: str | None = None
) -> str:
    """Get a complete chat response from Ollama (non-streaming)."""
    
    config = get_chat_config()
    if not config.enabled:
        return "Chat functionality is disabled. Set CHAT_ENABLED=true to enable."
    
    model = model or config.model
    system_prompt = get_system_prompt(recent_checks or [])

    messages = [{"role": "system", "content": system_prompt}, {"role": "user", "content": message}]

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{config.base_url}/api/chat",
                json={"model": model, "messages": messages, "stream": False},
            )

            if response.status_code == 200:
                data = response.json()
                return data.get("message", {}).get("content", "Sorry, I couldn't generate a response.")
            else:
                return f"Error: Unable to connect to Ollama (status {response.status_code})"
    except httpx.ConnectError:
        return "Error: Cannot connect to Ollama service. Make sure Ollama is running and accessible."
