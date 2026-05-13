"""Middleware/dependency for agent API key authentication."""

from fastapi import Header, HTTPException, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from api.database import get_db
from api.services.auth import authenticate_agent
from api.models.db import AgentIdentity


async def get_agent_from_key(
    request: Request,
    x_agent_key: str = Header(..., alias="X-Agent-Key"),
    db: AsyncSession = Depends(get_db),
) -> AgentIdentity:
    """Extract and validate agent API key from X-Agent-Key header."""
    agent = await authenticate_agent(db, x_agent_key)
    if not agent:
        raise HTTPException(status_code=401, detail="Invalid or inactive agent API key")
    # Stash the raw key on request state for audit
    request.state.agent_key = x_agent_key
    return agent
