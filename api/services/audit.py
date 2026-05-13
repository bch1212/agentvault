"""Audit logging service — records every vault access."""

from datetime import datetime, timezone
from uuid import UUID
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from api.models.db import CredentialAccessLog


async def log_access(
    db: AsyncSession,
    agent_id: UUID,
    credential_id: UUID,
    action: str,
    success: bool = True,
    ip_address: str | None = None,
    user_agent: str | None = None,
    error_message: str | None = None,
) -> CredentialAccessLog:
    """Create an audit log entry."""
    entry = CredentialAccessLog(
        agent_id=agent_id,
        credential_id=credential_id,
        action=action,
        success=success,
        ip_address=ip_address,
        user_agent=user_agent,
        error_message=error_message,
    )
    db.add(entry)
    await db.flush()
    return entry


async def query_logs(
    db: AsyncSession,
    user_id: UUID,
    agent_id: UUID | None = None,
    credential_id: UUID | None = None,
    action: str | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[CredentialAccessLog]:
    """Query audit logs with filters. Scoped to credentials owned by user_id."""
    from api.models.db import AgentIdentity

    # Build query — join through agent to ensure user ownership
    query = (
        select(CredentialAccessLog)
        .join(AgentIdentity, CredentialAccessLog.agent_id == AgentIdentity.id)
        .where(AgentIdentity.user_id == user_id)
    )

    if agent_id:
        query = query.where(CredentialAccessLog.agent_id == agent_id)
    if credential_id:
        query = query.where(CredentialAccessLog.credential_id == credential_id)
    if action:
        query = query.where(CredentialAccessLog.action == action)
    if start_date:
        query = query.where(CredentialAccessLog.timestamp >= start_date)
    if end_date:
        query = query.where(CredentialAccessLog.timestamp <= end_date)

    query = query.order_by(CredentialAccessLog.timestamp.desc()).offset(offset).limit(limit)
    result = await db.execute(query)
    return list(result.scalars().all())
