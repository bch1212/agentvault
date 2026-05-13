"""Vault proxy endpoint — agents call this to get temporary credential values."""

import json
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from api.database import get_db
from api.middleware.agent_auth import get_agent_from_key
from api.models.db import AgentIdentity, Credential, User
from api.models.schemas import VaultGetRequest, VaultGetResponse
from api.services.encryption import decrypt_value
from api.services.budget import check_budget, record_spend
from api.services.audit import log_access
from api.services.auth import get_user_for_agent
import fnmatch

router = APIRouter(prefix="/vault", tags=["vault"])


def _check_permission(agent: AgentIdentity, credential_name: str) -> bool:
    """Check if agent has permission to access a credential by name pattern."""
    try:
        permissions = json.loads(agent.permissions)
    except (json.JSONDecodeError, TypeError):
        permissions = []

    # Empty permissions = access all credentials owned by the user
    if not permissions:
        return True

    # Check if credential name matches any permission pattern
    return any(fnmatch.fnmatch(credential_name, pattern) for pattern in permissions)


@router.post("/get/{credential_name}", response_model=VaultGetResponse)
async def get_credential_value(
    credential_name: str,
    request: Request,
    cost: float = 0.0,
    agent: AgentIdentity = Depends(get_agent_from_key),
    db: AsyncSession = Depends(get_db),
):
    """
    Agent-facing endpoint: retrieve a decrypted credential value.

    - Validates agent API key
    - Checks permissions (name pattern matching)
    - Enforces budget limits
    - Logs the access
    - Returns decrypted value with TTL
    """
    ip = request.client.host if request.client else None
    ua = request.headers.get("user-agent")

    # Get the user who owns this agent
    user = await get_user_for_agent(db, agent)
    if not user:
        raise HTTPException(status_code=500, detail="Agent owner not found")

    # Check permission
    if not _check_permission(agent, credential_name):
        # Find credential for logging
        cred_result = await db.execute(
            select(Credential).where(Credential.user_id == user.id, Credential.name == credential_name)
        )
        cred = cred_result.scalar_one_or_none()
        if cred:
            await log_access(db, agent.id, cred.id, "read", success=False,
                           ip_address=ip, user_agent=ua, error_message="Permission denied")
        raise HTTPException(status_code=403, detail=f"Agent does not have permission to access '{credential_name}'")

    # Find credential
    result = await db.execute(
        select(Credential).where(Credential.user_id == user.id, Credential.name == credential_name)
    )
    cred = result.scalar_one_or_none()
    if not cred:
        raise HTTPException(status_code=404, detail=f"Credential '{credential_name}' not found")

    # Check budget
    allowed, reason = await check_budget(db, agent, cost)
    if not allowed:
        await log_access(db, agent.id, cred.id, "read", success=False,
                       ip_address=ip, user_agent=ua, error_message=reason)
        raise HTTPException(status_code=429, detail=reason)

    # Decrypt and return
    try:
        value = decrypt_value(cred.encrypted_value)
    except ValueError as e:
        await log_access(db, agent.id, cred.id, "read", success=False,
                       ip_address=ip, user_agent=ua, error_message=str(e))
        raise HTTPException(status_code=500, detail="Failed to decrypt credential")

    # Record spend and audit
    await record_spend(db, agent, cost)
    await log_access(db, agent.id, cred.id, "read", success=True, ip_address=ip, user_agent=ua)

    return VaultGetResponse(
        credential_id=cred.id,
        name=cred.name,
        provider=cred.provider,
        value=value,
        ttl_seconds=300,
    )


@router.get("/list", response_model=list[str])
async def list_available_credentials(
    agent: AgentIdentity = Depends(get_agent_from_key),
    db: AsyncSession = Depends(get_db),
):
    """List credential names accessible to this agent."""
    user = await get_user_for_agent(db, agent)
    if not user:
        raise HTTPException(status_code=500, detail="Agent owner not found")

    result = await db.execute(
        select(Credential.name).where(Credential.user_id == user.id)
    )
    all_names = [row[0] for row in result.all()]

    # Filter by permissions
    return [name for name in all_names if _check_permission(agent, name)]
