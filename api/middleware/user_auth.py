"""User authentication dependency — validates admin API key or Clerk JWT.

For MVP, we use a simple admin-key approach: the user passes their account API key
in the Authorization header. Clerk JWT validation can be layered in later.
"""

from fastapi import Header, HTTPException, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from api.database import get_db
from api.models.db import User


async def get_current_user(
    authorization: str = Header(...),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Authenticate user via Authorization header.
    Accepts: 'Bearer <clerk_jwt>' or 'ApiKey <user_api_key>'
    For MVP, we look up by email passed as a simple token.
    In production, this validates Clerk JWTs.
    """
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization header")

    parts = authorization.split(" ", 1)
    if len(parts) != 2:
        raise HTTPException(status_code=401, detail="Invalid Authorization format. Use 'Bearer <token>'")

    scheme, token = parts

    # For MVP: treat token as user email lookup (will be replaced by Clerk JWT)
    # In production: validate JWT, extract clerk_id, lookup user
    if scheme.lower() == "bearer":
        # Try clerk_id lookup first
        result = await db.execute(select(User).where(User.clerk_id == token))
        user = result.scalar_one_or_none()
        if not user:
            # Try email lookup (dev convenience)
            result = await db.execute(select(User).where(User.email == token))
            user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        return user

    raise HTTPException(status_code=401, detail="Unsupported auth scheme")
