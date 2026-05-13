"""AgentVault MCP Server — exposes vault operations as MCP tools.

Run standalone:  python -m mcp_server.server
Or mount as SSE transport on the FastAPI app.
"""

import os
import httpx
from mcp.server.fastmcp import FastMCP

mcp = FastMCP(
    "AgentVault",
    description="Credential vault for AI agents — store, retrieve, and manage API keys securely",
)

# The MCP server calls the AgentVault API using the agent's API key.
# All vault/credential routes live under /api/v1.
_RAW_BASE = os.getenv("AGENTVAULT_API_URL", "http://localhost:8000").rstrip("/")
API_BASE = _RAW_BASE if _RAW_BASE.endswith("/api/v1") else f"{_RAW_BASE}/api/v1"
HEALTH_BASE = _RAW_BASE.rsplit("/api/v1", 1)[0] if _RAW_BASE.endswith("/api/v1") else _RAW_BASE
AGENT_KEY = os.getenv("AGENTVAULT_AGENT_KEY", "")


def _headers():
    return {"X-Agent-Key": AGENT_KEY, "Content-Type": "application/json"}


@mcp.tool()
async def list_credentials() -> str:
    """List all credential names available to this agent."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{API_BASE}/vault/list", headers=_headers())
        if resp.status_code != 200:
            return f"Error: {resp.status_code} — {resp.text}"
        names = resp.json()
        if not names:
            return "No credentials available."
        return "Available credentials:\n" + "\n".join(f"  - {n}" for n in names)


@mcp.tool()
async def get_credential(name: str, cost: float = 0.0) -> str:
    """
    Retrieve a decrypted credential value from the vault.

    Args:
        name: The credential name (e.g., "stripe_key", "openai_api_key")
        cost: Optional cost to track against this agent's budget (in dollars)
    """
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{API_BASE}/vault/get/{name}",
            headers=_headers(),
            params={"cost": cost},
        )
        if resp.status_code != 200:
            return f"Error: {resp.status_code} — {resp.text}"
        data = resp.json()
        return data["value"]


@mcp.tool()
async def set_budget(agent_id: str, daily: float | None = None, monthly: float | None = None) -> str:
    """
    Set spending budget for an agent.

    Args:
        agent_id: The agent identity UUID
        daily: Daily budget limit in dollars (None = no limit)
        monthly: Monthly budget limit in dollars (None = no limit)
    """
    body = {}
    if daily is not None:
        body["budget_daily"] = daily
    if monthly is not None:
        body["budget_monthly"] = monthly

    # This endpoint requires user auth, not agent auth
    # In MCP context, the agent would need elevated permissions
    return f"Budget update requires user-level authentication. Use the dashboard or API with user credentials."


@mcp.tool()
async def view_audit_log(limit: int = 20) -> str:
    """
    View recent credential access logs (requires Pro plan).

    Args:
        limit: Number of log entries to retrieve (max 100)
    """
    return "Audit log access requires user-level authentication. Use the dashboard or API with user credentials."


@mcp.tool()
async def vault_status() -> str:
    """Check vault connection status and agent identity."""
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(f"{HEALTH_BASE}/health")
            if resp.status_code == 200:
                health = resp.json()
                return f"Vault connected: {HEALTH_BASE} (v{health.get('version', '?')}, {health.get('environment', '?')})"
            return f"Vault returned {resp.status_code}"
        except Exception as e:
            return f"Cannot reach vault at {HEALTH_BASE}: {e}"


if __name__ == "__main__":
    mcp.run(transport="stdio")
