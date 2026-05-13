"""Budget management endpoints (user-facing)."""

from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from api.database import get_db
from api.middleware.user_auth import get_current_user
from api.models.db import AgentIdentity, User
from api.models.schemas import BudgetResponse, BudgetSetRequest
from api.services.budget import get_budget_summary
from api.config import get_settings

router = APIRouter(prefix="/budgets", tags=["budgets"])


@router.get("/{agent_id}", response_model=dict)
async def get_agent_budget(
    agent_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get current budget usage for an agent."""
    settings = get_settings()
    limits = settings.plan_limits.get(user.plan.value, settings.plan_limits["free"])
    if not limits.get("budget_controls"):
        raise HTTPException(status_code=403, detail="Budget controls require Business plan or higher")

    result = await db.execute(
        select(AgentIdentity).where(AgentIdentity.id == agent_id, AgentIdentity.user_id == user.id)
    )
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    return await get_budget_summary(db, agent)


@router.put("/{agent_id}")
async def set_agent_budget(
    agent_id: UUID,
    body: BudgetSetRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Set daily/monthly budget limits for an agent."""
    settings = get_settings()
    limits = settings.plan_limits.get(user.plan.value, settings.plan_limits["free"])
    if not limits.get("budget_controls"):
        raise HTTPException(status_code=403, detail="Budget controls require Business plan or higher")

    result = await db.execute(
        select(AgentIdentity).where(AgentIdentity.id == agent_id, AgentIdentity.user_id == user.id)
    )
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    if body.budget_daily is not None:
        agent.budget_daily = body.budget_daily
    if body.budget_monthly is not None:
        agent.budget_monthly = body.budget_monthly

    await db.flush()
    return {"status": "updated", "agent_id": str(agent.id)}
