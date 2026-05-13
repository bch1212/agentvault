"""Audit log query endpoints (user-facing)."""

from datetime import datetime
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from api.database import get_db
from api.middleware.user_auth import get_current_user
from api.models.db import User
from api.models.schemas import AuditLogResponse
from api.services.audit import query_logs
from api.config import get_settings

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("/logs", response_model=list[AuditLogResponse])
async def get_audit_logs(
    agent_id: UUID | None = Query(None),
    credential_id: UUID | None = Query(None),
    action: str | None = Query(None),
    start_date: datetime | None = Query(None),
    end_date: datetime | None = Query(None),
    limit: int = Query(100, le=1000),
    offset: int = Query(0),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Query audit logs. Requires Pro plan or higher."""
    settings = get_settings()
    limits = settings.plan_limits.get(user.plan.value, settings.plan_limits["free"])
    if not limits.get("audit_logs"):
        raise HTTPException(
            status_code=403,
            detail="Audit logs require Pro plan or higher. Upgrade at /billing/checkout",
        )

    logs = await query_logs(
        db,
        user_id=user.id,
        agent_id=agent_id,
        credential_id=credential_id,
        action=action,
        start_date=start_date,
        end_date=end_date,
        limit=limit,
        offset=offset,
    )
    return logs
