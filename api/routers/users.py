"""User management endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from api.database import get_db
from api.models.schemas import UserCreate, UserResponse
from api.services.auth import get_or_create_user

router = APIRouter(prefix="/users", tags=["users"])


@router.post("", response_model=UserResponse, status_code=201)
async def create_user(body: UserCreate, db: AsyncSession = Depends(get_db)):
    """Register a new user (or return existing)."""
    user = await get_or_create_user(db, email=body.email, clerk_id=body.clerk_id)
    return user
