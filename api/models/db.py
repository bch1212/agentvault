"""SQLAlchemy ORM models for AgentVault."""

import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Column, String, Boolean, Integer, Float, DateTime, ForeignKey, Text, Enum as SAEnum
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from api.database import Base
import enum


def utcnow():
    return datetime.now(timezone.utc)


def new_uuid():
    return uuid.uuid4()


class PlanType(str, enum.Enum):
    free = "free"
    pro = "pro"
    business = "business"
    enterprise = "enterprise"


class PeriodType(str, enum.Enum):
    daily = "daily"
    monthly = "monthly"


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    email = Column(String(255), unique=True, nullable=False, index=True)
    clerk_id = Column(String(255), unique=True, nullable=True)
    plan = Column(SAEnum(PlanType), default=PlanType.free, nullable=False)
    stripe_customer_id = Column(String(255), nullable=True)
    stripe_subscription_id = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    agents = relationship("AgentIdentity", back_populates="user", cascade="all, delete-orphan")
    credentials = relationship("Credential", back_populates="user", cascade="all, delete-orphan")


class AgentIdentity(Base):
    __tablename__ = "agent_identities"

    id = Column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(255), nullable=False)
    api_key_hash = Column(String(255), nullable=False, unique=True)
    api_key_prefix = Column(String(12), nullable=False)  # first 8 chars for identification
    permissions = Column(Text, default="[]")  # JSON array of credential name patterns
    budget_daily = Column(Float, nullable=True)  # dollars
    budget_monthly = Column(Float, nullable=True)
    active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    user = relationship("User", back_populates="agents")
    access_logs = relationship("CredentialAccessLog", back_populates="agent", cascade="all, delete-orphan")
    budget_usage = relationship("BudgetUsage", back_populates="agent", cascade="all, delete-orphan")


class Credential(Base):
    __tablename__ = "credentials"

    id = Column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(255), nullable=False, index=True)
    provider = Column(String(100), nullable=True)  # e.g., "openai", "stripe", "twilio"
    encrypted_value = Column(Text, nullable=False)
    rotation_interval_hours = Column(Integer, nullable=True)
    last_rotated = Column(DateTime(timezone=True), nullable=True)
    metadata_json = Column(Text, default="{}")
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    user = relationship("User", back_populates="credentials")
    access_logs = relationship("CredentialAccessLog", back_populates="credential", cascade="all, delete-orphan")


class CredentialAccessLog(Base):
    __tablename__ = "credential_access_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    agent_id = Column(UUID(as_uuid=True), ForeignKey("agent_identities.id", ondelete="CASCADE"), nullable=False)
    credential_id = Column(UUID(as_uuid=True), ForeignKey("credentials.id", ondelete="CASCADE"), nullable=False)
    action = Column(String(50), nullable=False)  # "read", "rotate", "revoke"
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(500), nullable=True)
    success = Column(Boolean, default=True, nullable=False)
    error_message = Column(Text, nullable=True)
    timestamp = Column(DateTime(timezone=True), default=utcnow, nullable=False, index=True)

    agent = relationship("AgentIdentity", back_populates="access_logs")
    credential = relationship("Credential", back_populates="access_logs")


class BudgetUsage(Base):
    __tablename__ = "budget_usage"

    id = Column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    agent_id = Column(UUID(as_uuid=True), ForeignKey("agent_identities.id", ondelete="CASCADE"), nullable=False)
    period_type = Column(SAEnum(PeriodType), nullable=False)
    period_start = Column(DateTime(timezone=True), nullable=False)
    amount_used = Column(Float, default=0.0, nullable=False)
    limit_amount = Column(Float, nullable=False)

    agent = relationship("AgentIdentity", back_populates="budget_usage")
