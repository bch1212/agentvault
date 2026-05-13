"""Authentication services — API key generation, hashing, and verification."""

import secrets
import hashlib
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from api.models.db import AgentIdentity, User


def generate_api_key() -> str:
    """Generate a secure agent API key with 'avk_' prefix."""
    return f"avk_{secrets.token_urlsafe(48)}"


def hash_api_key(api_key: str) -> str:
    """SHA-256 hash of API key for storage."""
    return hashlib.sha256(api_key.encode()).hexdigest()


def get_key_prefix(api_key: str) -> str:
    """Extract prefix for display (first 12 chars)."""
    return api_key[:12]


async def authenticate_agent(db: AsyncSession, api_key: str) -> AgentIdentity | None:
    """Verify an agent API key and return the agent if valid and active."""
    key_hash = hash_api_key(api_key)
    result = await db.execute(
        select(AgentIdentity).where(
            AgentIdentity.api_key_hash == key_hash,
            AgentIdentity.active == True,
        )
    )
    return result.scalar_one_or_none()


async def get_user_for_agent(db: AsyncSession, agent: AgentIdentity) -> User | None:
    """Fetch the user who owns an agent identity."""
    result = await db.execute(select(User).where(User.id == agent.user_id))
    return result.scalar_one_or_none()


async def get_or_create_user(db: AsyncSession, email: str, clerk_id: str | None = None) -> User:
    """Get existing user by email or create a new one."""
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if user:
        return user
    user = User(email=email, clerk_id=clerk_id)
    db.add(user)
    await db.flush()
    return user
