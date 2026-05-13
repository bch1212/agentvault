"""AgentVault — AI-native credential management for autonomous agents.

FastAPI application entry point.
"""

import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api import database
from api.database import init_db, Base
from api.routers import users, agents, credentials, vault, audit, budgets, billing
from api.config import get_settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database on startup."""
    settings = get_settings()
    init_db(settings.database_url)

    # Create tables (use Alembic migrations in production).
    # database.engine is rebound by init_db(); referencing via the module ensures
    # we read the live binding rather than the None captured at import time.
    async with database.engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Initialize Stripe
    if settings.stripe_secret_key:
        billing.init_stripe()

    yield

    # Cleanup
    if database.engine is not None:
        await database.engine.dispose()


app = FastAPI(
    title="AgentVault",
    description="AI-native credential management — store, proxy, and audit API keys for autonomous agents",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount routers
app.include_router(users.router, prefix="/api/v1")
app.include_router(agents.router, prefix="/api/v1")
app.include_router(credentials.router, prefix="/api/v1")
app.include_router(vault.router, prefix="/api/v1")
app.include_router(audit.router, prefix="/api/v1")
app.include_router(budgets.router, prefix="/api/v1")
app.include_router(billing.router, prefix="/api/v1")


@app.get("/health")
async def health():
    settings = get_settings()
    return {
        "status": "ok",
        "version": "1.0.0",
        "environment": settings.environment,
    }


@app.get("/")
async def root():
    return {
        "name": "AgentVault",
        "description": "AI-native credential management for autonomous agents",
        "docs": "/docs",
        "version": "1.0.0",
    }


# MCP info endpoint — the actual MCP server runs as a stdio subprocess
# in client configs (see /docs and BUILD_SUMMARY for Claude Desktop / Cursor setup).
@app.get("/mcp")
async def mcp_info():
    return {
        "transport": "stdio",
        "package": "agentvault-mcp",
        "command": "python -m mcp_server",
        "env": ["AGENTVAULT_API_URL", "AGENTVAULT_AGENT_KEY"],
        "note": "Configure as a stdio MCP server in Claude Desktop or Cursor — point AGENTVAULT_API_URL at this host and provide an avk_ agent key.",
    }


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=port)
