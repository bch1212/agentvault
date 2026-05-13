"""Pydantic request/response schemas."""

from pydantic import BaseModel, EmailStr, Field
from datetime import datetime
from uuid import UUID
from typing import Optional


# ── Users ──

class UserCreate(BaseModel):
    email: str
    clerk_id: Optional[str] = None

class UserResponse(BaseModel):
    id: UUID
    email: str
    plan: str
    created_at: datetime
    model_config = {"from_attributes": True}


# ── Agent Identities ──

class AgentCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    permissions: list[str] = Field(default_factory=list)
    budget_daily: Optional[float] = None
    budget_monthly: Optional[float] = None

class AgentUpdate(BaseModel):
    name: Optional[str] = None
    permissions: Optional[list[str]] = None
    budget_daily: Optional[float] = None
    budget_monthly: Optional[float] = None
    active: Optional[bool] = None

class AgentResponse(BaseModel):
    id: UUID
    name: str
    api_key_prefix: str
    permissions: str
    budget_daily: Optional[float]
    budget_monthly: Optional[float]
    active: bool
    created_at: datetime
    model_config = {"from_attributes": True}

class AgentCreatedResponse(AgentResponse):
    """Returned only on creation — includes the full API key (shown once)."""
    api_key: str


# ── Credentials ──

class CredentialCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    provider: Optional[str] = None
    value: str = Field(..., min_length=1)
    rotation_interval_hours: Optional[int] = None
    metadata: dict = Field(default_factory=dict)

class CredentialUpdate(BaseModel):
    name: Optional[str] = None
    provider: Optional[str] = None
    value: Optional[str] = None
    rotation_interval_hours: Optional[int] = None
    metadata: Optional[dict] = None

class CredentialResponse(BaseModel):
    id: UUID
    name: str
    provider: Optional[str]
    rotation_interval_hours: Optional[int]
    last_rotated: Optional[datetime]
    created_at: datetime
    model_config = {"from_attributes": True}

class CredentialValueResponse(BaseModel):
    """Returned by the vault proxy — includes the decrypted value with TTL."""
    credential_id: UUID
    name: str
    value: str
    expires_in_seconds: int = 300  # 5-minute TTL


# ── Vault Proxy ──

class VaultGetRequest(BaseModel):
    credential_name: str
    cost: float = 0.0  # optional cost to track against budget

class VaultGetResponse(BaseModel):
    credential_id: UUID
    name: str
    provider: Optional[str]
    value: str
    ttl_seconds: int = 300


# ── Audit Logs ──

class AuditLogResponse(BaseModel):
    id: UUID
    agent_id: UUID
    credential_id: UUID
    action: str
    ip_address: Optional[str]
    success: bool
    error_message: Optional[str]
    timestamp: datetime
    model_config = {"from_attributes": True}

class AuditLogFilter(BaseModel):
    agent_id: Optional[UUID] = None
    credential_id: Optional[UUID] = None
    action: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    limit: int = Field(default=100, le=1000)
    offset: int = 0


# ── Budget ──

class BudgetResponse(BaseModel):
    agent_id: UUID
    agent_name: str
    daily_used: float
    daily_limit: Optional[float]
    monthly_used: float
    monthly_limit: Optional[float]

class BudgetSetRequest(BaseModel):
    budget_daily: Optional[float] = None
    budget_monthly: Optional[float] = None


# ── Stripe ──

class CheckoutRequest(BaseModel):
    price_id: str
    success_url: str = ""
    cancel_url: str = ""

class CheckoutResponse(BaseModel):
    checkout_url: str

class PortalResponse(BaseModel):
    portal_url: str


# ── Health ──

class HealthResponse(BaseModel):
    status: str = "ok"
    version: str = "1.0.0"
    environment: str = "production"
