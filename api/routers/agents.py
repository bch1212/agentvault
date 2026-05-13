"""Agent identity management endpoints."""

import json
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from api.database import get_db
from api.middleware.user_auth import get_current_user
from api.models.db import AgentIdentity, User
from api.models.schemas import AgentCreate, AgentUpdate, AgentResponse, AgentCreatedResponse
from api.services.auth import generate_api_key, hash_api_key, get_key_prefix
from api.config import get_settings

router = APIRouter(prefix="/agents", tags=["agents"])


@router.post("", response_model=AgentCreatedResponse, status_code=201)
async def create_agent(
    body: AgentCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new agent identity and return its API key (shown once)."""
    # Check plan limits
    settings = get_settings()
    limits = settings.plan_limits.get(user.plan.value, settings.plan_limits["free"])
    max_agents = limits["max_agents"]

    if max_agents > 0:
        count_result = await db.execute(
            select(func.count()).select_from(AgentIdentity).where(AgentIdentity.user_id == user.id)
        )
        current_count = count_result.scalar()
        if current_count >= max_agents:
            raise HTTPException(
                status_code=403,
                detail=f"Agent limit reached ({max_agents}). Upgrade your plan for more.",
            )

    api_key = generate_api_key()
    agent = AgentIdentity(
        user_id=user.id,
        name=body.name,
        api_key_hash=hash_api_key(api_key),
        api_key_prefix=get_key_prefix(api_key),
        permissions=json.dumps(body.permissions),
        budget_daily=body.budget_daily,
        budget_monthly=body.budget_monthly,
    )
    db.add(agent)
    await db.flush()

    return AgentCreatedResponse(
        id=agent.id,
        name=agent.name,
        api_key_prefix=agent.api_key_prefix,
        permissions=agent.permissions,
        budget_daily=agent.budget_daily,
        budget_monthly=agent.budget_monthly,
        active=agent.active,
        created_at=agent.created_at,
        api_key=api_key,
    )


@router.get("", response_model=list[AgentResponse])
async def list_agents(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all agent identities for the current user."""
    result = await db.execute(
        select(AgentIdentity).where(AgentIdentity.user_id == user.id).order_by(AgentIdentity.created_at.desc())
    )
    return list(result.scalars().all())


@router.get("/{agent_id}", response_model=AgentResponse)
async def get_agent(
    agent_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a specific agent identity."""
    result = await db.execute(
        select(AgentIdentity).where(AgentIdentity.id == agent_id, AgentIdentity.user_id == user.id)
    )
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent


@router.patch("/{agent_id}", response_model=AgentResponse)
async def update_agent(
    agent_id: UUID,
    body: AgentUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update an agent identity."""
    result = await db.execute(
        select(AgentIdentity).where(AgentIdentity.id == agent_id, AgentIdentity.user_id == user.id)
    )
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    if body.name is not None:
        agent.name = body.name
    if body.permissions is not None:
        agent.permissions = json.dumps(body.permissions)
    if body.budget_daily is not None:
        agent.budget_daily = body.budget_daily
    if body.budget_monthly is not None:
        agent.budget_monthly = body.budget_monthly
    if body.active is not None:
        agent.active = body.active

    await db.flush()
    return agent


@router.delete("/{agent_id}", status_code=204)
async def delete_agent(
    agent_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete an agent identity."""
    result = await db.execute(
        select(AgentIdentity).where(AgentIdentity.id == agent_id, AgentIdentity.user_id == user.id)
    )
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    await db.delete(agent)
