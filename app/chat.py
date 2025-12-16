"""Chat integration with Ollama for database performance insights."""

import json
from collections.abc import AsyncGenerator

import httpx

from .config import get_chat_config
from .database import get_connection, get_dsn
from .db_manager_postgres import DatabaseConnection


async def get_expensive_queries() -> list[dict]:
    """Get expensive queries from last 30 days, prioritized by mean execution time."""
    dsn = get_dsn()
    if not dsn:
        return []

    try:
        async with get_connection(dsn) as conn:
            # Check if pg_stat_statements extension exists
            ext_check = await conn.fetchval(
                "SELECT EXISTS(SELECT 1 FROM pg_extension WHERE extname = 'pg_stat_statements')"
            )

            if not ext_check:
                return []

            # Get expensive queries from last 30 days (no query text for privacy)
            rows = await conn.fetch(
                """
                SELECT
                    queryid,
                    calls,
                    ROUND(total_exec_time::numeric, 2) as total_time_ms,
                    ROUND(mean_exec_time::numeric, 2) as mean_time_ms,
                    ROUND(max_exec_time::numeric, 2) as max_time_ms,
                    ROUND(stddev_exec_time::numeric, 2) as stddev_time_ms,
                    ROUND((100.0 * shared_blks_hit / NULLIF(shared_blks_hit + shared_blks_read, 0))::numeric, 2) as cache_hit_pct,
                    shared_blks_hit,
                    shared_blks_read,
                    local_blks_hit,
                    local_blks_read,
                    temp_blks_read,
                    temp_blks_written
                FROM pg_stat_statements
                WHERE calls >= 1
                  AND mean_exec_time > 1
                  AND query NOT LIKE '%pg_stat_statements%'
                  AND query NOT LIKE '%pg_catalog%'
                  AND query NOT LIKE '%<insufficient privilege>%'
                  AND queryid IS NOT NULL
                ORDER BY mean_exec_time DESC
                LIMIT 15
                """
            )

            expensive_queries = []
            for i, row in enumerate(rows, 1):
                expensive_queries.append(
                    {
                        "rank": i,
                        "queryid": str(row["queryid"]) if row["queryid"] else f"query_{i}",
                        "calls": int(row["calls"]),
                        "total_time_ms": float(row["total_time_ms"]),
                        "mean_time_ms": float(row["mean_time_ms"]),
                        "max_time_ms": float(row["max_time_ms"]),
                        "stddev_time_ms": (
                            float(row["stddev_time_ms"]) if row["stddev_time_ms"] else 0
                        ),
                        "cache_hit_pct": float(row["cache_hit_pct"]) if row["cache_hit_pct"] else 0,
                        "shared_blks_hit": int(row["shared_blks_hit"]),
                        "shared_blks_read": int(row["shared_blks_read"]),
                        "local_blks_hit": int(row["local_blks_hit"]),
                        "local_blks_read": int(row["local_blks_read"]),
                        "temp_blks_read": int(row["temp_blks_read"]),
                        "temp_blks_written": int(row["temp_blks_written"]),
                    }
                )

            return expensive_queries
    except Exception:
        return []


def format_expensive_queries(queries: list[dict]) -> str:
    """Format expensive queries for display in system prompt."""
    if not queries:
        return "No expensive query data available."

    formatted = "🔍 Top Expensive Queries (Last 30 Days, by Mean Execution Time):\n\n"

    for query in queries[:10]:  # Show top 10
        formatted += (
            f"📊 Query #{query['rank']}:\n"
            f"   ⏱️  Mean Time: {query['mean_time_ms']:.2f}ms\n"
            f"   📈 Calls: {query['calls']:,}\n"
            f"   ⚡ Max Time: {query['max_time_ms']:.2f}ms\n"
            f"   💾 Cache Hit: {query['cache_hit_pct']:.1f}%\n"
            f"   🔥 Total Impact: {query['total_time_ms']:.2f}ms\n"
        )

        # Add performance insights
        if query["temp_blks_read"] > 0 or query["temp_blks_written"] > 0:
            formatted += "   ⚠️  Uses temporary files (potential optimization needed)\n"

        if query["cache_hit_pct"] < 90:
            formatted += "   💡 Low cache hit ratio (consider indexing)\n"

        if query["mean_time_ms"] > 1000:
            formatted += "   🚨 High average execution time (investigate query plan)\n"

        formatted += "\n"

    return formatted


def get_system_prompt(
    recent_checks: list[dict] | None = None,
    expensive_queries: list[dict] | None = None,
    connections: list[DatabaseConnection] | None = None,
) -> str:
    """Generate system prompt with database context."""
    prompt = """🎯 You are an expert PostgreSQL database performance analyst helping users optimize their multi-region database infrastructure.

🚨 CRITICAL INSTRUCTIONS - READ CAREFULLY:
- ONLY use the exact data provided below in the "Recent Performance Checks" and "Expensive Queries" sections
- DO NOT invent, hallucinate, or make up any database names, metrics, or performance data
- DO NOT mention databases that are not listed in the provided data
- If no specific databases are mentioned in the data, say "I don't see specific database connections in the provided data"
- When you see database connection IDs (like "4" or "5"), refer to them as "Connection ID 4" or "Connection ID 5" - DO NOT invent names like "Database 3" or "US East"

📊 You have access ONLY to the following data:
- Recent Performance Checks (exact data provided below)
- Expensive Queries (exact data provided below, if any)

💡 When answering questions:
1. Use ONLY the metrics and data shown below
2. Be concise and actionable with specific recommendations
3. If multiple connections exist, reference them by their actual IDs from the data
4. If data shows failed checks, address those specifically
5. If expensive queries exist, analyze the exact metrics shown
6. If no data is available, say "No recent performance data available"

 """

    if expensive_queries:
        prompt += format_expensive_queries(expensive_queries)
        prompt += "\n"

    if recent_checks:
        prompt += "📈 Recent Performance Checks:\n"
        for check in recent_checks[:5]:
            region = check.get("region_id", "unknown")
            check_type = check.get("check_type", "unknown")
            success = check.get("success", False)
            metric = check.get("metric_value")

            if success and metric:
                prompt += (
                    f"   ✅ {region}: {check_type} - {metric:.2f} {check.get('metric_unit', '')}\n"
                )
            elif not success:
                prompt += f"   ❌ {region}: {check_type} - FAILED\n"

    # Add database connection context if available
    if connections:
        prompt += "\n🏢 Database Connections Being Analyzed:\n"
        for conn in connections[:5]:  # Show up to 5 connections
            conn_info = f"   📊 {conn.name}"
            if conn.region:
                conn_info += f" (🌍 {conn.region})"
            if conn.cloud_provider:
                conn_info += f" - {conn.cloud_provider}"
            if conn.host:
                conn_info += f" - {conn.host}:{conn.port}"
            prompt += conn_info + "\n"
        prompt += "\n"

    prompt += "\n🔧 Provide specific, actionable recommendations based on the data above."
    prompt += " When referencing databases, specify which connection/region you're talking about."

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
    message: str,
    recent_checks: list[dict] | None = None,
    expensive_queries: list[dict] | None = None,
    connections: list[object] | None = None,
    model: str | None = None,
) -> str:
    """Get a complete chat response from Ollama (non-streaming)."""

    config = get_chat_config()
    if not config.enabled:
        return "Chat functionality is disabled. Set CHAT_ENABLED=true to enable."

    model = model or config.model

    system_prompt = get_system_prompt(
        recent_checks or [], expensive_queries or [], connections or []
    )

    messages = [{"role": "system", "content": system_prompt}, {"role": "user", "content": message}]

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{config.base_url}/api/chat",
                json={"model": model, "messages": messages, "stream": False},
            )

            if response.status_code == 200:
                data = response.json()
                return data.get("message", {}).get(
                    "content", "Sorry, I couldn't generate a response."
                )
            else:
                return f"Error: Unable to connect to Ollama (status {response.status_code})"
    except httpx.ConnectError:
        return (
            "Error: Cannot connect to Ollama service. Make sure Ollama is running and accessible."
        )
