"""Credential CRUD endpoints (user-facing, not agent-facing)."""

from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from api.database import get_db
from api.middleware.user_auth import get_current_user
from api.models.db import Credential, User
from api.models.schemas import CredentialCreate, CredentialUpdate, CredentialResponse
from api.services.encryption import encrypt_value
from api.config import get_settings
import json

router = APIRouter(prefix="/credentials", tags=["credentials"])


@router.post("", response_model=CredentialResponse, status_code=201)
async def create_credential(
    body: CredentialCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Store a new credential with column-level encryption."""
    # Check plan limits
    settings = get_settings()
    limits = settings.plan_limits.get(user.plan.value, settings.plan_limits["free"])
    max_creds = limits["max_credentials"]

    if max_creds > 0:
        count_result = await db.execute(
            select(func.count()).select_from(Credential).where(Credential.user_id == user.id)
        )
        current_count = count_result.scalar()
        if current_count >= max_creds:
            raise HTTPException(
                status_code=403,
                detail=f"Credential limit reached ({max_creds}). Upgrade your plan for more.",
            )

    # Check for duplicate name
    existing = await db.execute(
        select(Credential).where(Credential.user_id == user.id, Credential.name == body.name)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail=f"Credential '{body.name}' already exists")

    encrypted = encrypt_value(body.value)
    cred = Credential(
        user_id=user.id,
        name=body.name,
        provider=body.provider,
        encrypted_value=encrypted,
        rotation_interval_hours=body.rotation_interval_hours,
        metadata_json=json.dumps(body.metadata),
    )
    db.add(cred)
    await db.flush()
    return cred


@router.get("", response_model=list[CredentialResponse])
async def list_credentials(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all credentials (names only, no values)."""
    result = await db.execute(
        select(Credential).where(Credential.user_id == user.id).order_by(Credential.created_at.desc())
    )
    return list(result.scalars().all())


@router.get("/{credential_id}", response_model=CredentialResponse)
async def get_credential(
    credential_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get credential metadata (no value)."""
    result = await db.execute(
        select(Credential).where(Credential.id == credential_id, Credential.user_id == user.id)
    )
    cred = result.scalar_one_or_none()
    if not cred:
        raise HTTPException(status_code=404, detail="Credential not found")
    return cred


@router.patch("/{credential_id}", response_model=CredentialResponse)
async def update_credential(
    credential_id: UUID,
    body: CredentialUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update a credential. If value is provided, re-encrypts it."""
    result = await db.execute(
        select(Credential).where(Credential.id == credential_id, Credential.user_id == user.id)
    )
    cred = result.scalar_one_or_none()
    if not cred:
        raise HTTPException(status_code=404, detail="Credential not found")

    if body.name is not None:
        cred.name = body.name
    if body.provider is not None:
        cred.provider = body.provider
    if body.value is not None:
        cred.encrypted_value = encrypt_value(body.value)
    if body.rotation_interval_hours is not None:
        cred.rotation_interval_hours = body.rotation_interval_hours
    if body.metadata is not None:
        cred.metadata_json = json.dumps(body.metadata)

    await db.flush()
    return cred


@router.delete("/{credential_id}", status_code=204)
async def delete_credential(
    credential_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a credential."""
    result = await db.execute(
        select(Credential).where(Credential.id == credential_id, Credential.user_id == user.id)
    )
    cred = result.scalar_one_or_none()
    if not cred:
        raise HTTPException(status_code=404, detail="Credential not found")
    await db.delete(cred)
