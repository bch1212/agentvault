"""Budget enforcement service — tracks per-agent spending against daily/monthly limits."""

from datetime import datetime, timezone, timedelta
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from api.models.db import AgentIdentity, BudgetUsage, PeriodType


def _period_start(period: PeriodType, now: datetime | None = None) -> datetime:
    """Get the start of the current budget period."""
    now = now or datetime.now(timezone.utc)
    if period == PeriodType.daily:
        return now.replace(hour=0, minute=0, second=0, microsecond=0)
    else:  # monthly
        return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


async def get_or_create_usage(
    db: AsyncSession, agent_id: UUID, period: PeriodType, limit_amount: float
) -> BudgetUsage:
    """Get or create a budget usage record for the current period."""
    start = _period_start(period)
    result = await db.execute(
        select(BudgetUsage).where(
            BudgetUsage.agent_id == agent_id,
            BudgetUsage.period_type == period,
            BudgetUsage.period_start == start,
        )
    )
    usage = result.scalar_one_or_none()
    if usage:
        # Update limit if it changed
        if usage.limit_amount != limit_amount:
            usage.limit_amount = limit_amount
        return usage

    usage = BudgetUsage(
        agent_id=agent_id,
        period_type=period,
        period_start=start,
        amount_used=0.0,
        limit_amount=limit_amount,
    )
    db.add(usage)
    await db.flush()
    return usage


async def check_budget(db: AsyncSession, agent: AgentIdentity, cost: float) -> tuple[bool, str]:
    """
    Check if the agent has budget remaining for the requested cost.
    Returns (allowed: bool, reason: str).
    """
    if cost <= 0:
        return True, "ok"

    # Check daily budget
    if agent.budget_daily is not None:
        daily = await get_or_create_usage(db, agent.id, PeriodType.daily, agent.budget_daily)
        if daily.amount_used + cost > daily.limit_amount:
            return False, f"Daily budget exceeded: ${daily.amount_used:.2f} used of ${daily.limit_amount:.2f} limit"

    # Check monthly budget
    if agent.budget_monthly is not None:
        monthly = await get_or_create_usage(db, agent.id, PeriodType.monthly, agent.budget_monthly)
        if monthly.amount_used + cost > monthly.limit_amount:
            return False, f"Monthly budget exceeded: ${monthly.amount_used:.2f} used of ${monthly.limit_amount:.2f} limit"

    return True, "ok"


async def record_spend(db: AsyncSession, agent: AgentIdentity, cost: float):
    """Record a spend against the agent's daily and monthly budgets."""
    if cost <= 0:
        return

    if agent.budget_daily is not None:
        daily = await get_or_create_usage(db, agent.id, PeriodType.daily, agent.budget_daily)
        daily.amount_used += cost

    if agent.budget_monthly is not None:
        monthly = await get_or_create_usage(db, agent.id, PeriodType.monthly, agent.budget_monthly)
        monthly.amount_used += cost


async def get_budget_summary(db: AsyncSession, agent: AgentIdentity) -> dict:
    """Get current budget status for an agent."""
    result = {"agent_id": str(agent.id), "agent_name": agent.name}

    if agent.budget_daily is not None:
        daily = await get_or_create_usage(db, agent.id, PeriodType.daily, agent.budget_daily)
        result["daily_used"] = daily.amount_used
        result["daily_limit"] = daily.limit_amount
        result["daily_remaining"] = max(0, daily.limit_amount - daily.amount_used)
    else:
        result["daily_used"] = 0.0
        result["daily_limit"] = None
        result["daily_remaining"] = None

    if agent.budget_monthly is not None:
        monthly = await get_or_create_usage(db, agent.id, PeriodType.monthly, agent.budget_monthly)
        result["monthly_used"] = monthly.amount_used
        result["monthly_limit"] = monthly.limit_amount
        result["monthly_remaining"] = max(0, monthly.limit_amount - monthly.amount_used)
    else:
        result["monthly_used"] = 0.0
        result["monthly_limit"] = None
        result["monthly_remaining"] = None

    return result
