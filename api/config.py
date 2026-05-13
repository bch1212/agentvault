"""Application configuration loaded from environment variables."""

from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql+asyncpg://localhost:5432/agentvault"

    # Encryption
    vault_encryption_key: str = ""

    # Stripe
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""
    stripe_price_pro: str = ""
    stripe_price_business: str = ""
    stripe_price_enterprise: str = ""

    # SendGrid
    sendgrid_api_key: str = ""
    sendgrid_from_email: str = "alerts@agentvault.dev"

    # Clerk
    clerk_secret_key: str = ""
    clerk_publishable_key: str = ""
    clerk_jwks_url: str = ""

    # App
    api_base_url: str = "http://localhost:8000"
    port: int = 8000
    environment: str = "development"

    # Plan limits
    plan_limits: dict = {
        "free": {"max_agents": 3, "max_credentials": 10, "audit_logs": False, "auto_rotation": False, "budget_controls": False, "team_access": False},
        "pro": {"max_agents": 25, "max_credentials": 100, "audit_logs": True, "auto_rotation": True, "budget_controls": False, "team_access": False},
        "business": {"max_agents": -1, "max_credentials": -1, "audit_logs": True, "auto_rotation": True, "budget_controls": True, "team_access": True},
        "enterprise": {"max_agents": -1, "max_credentials": -1, "audit_logs": True, "auto_rotation": True, "budget_controls": True, "team_access": True},
    }

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


@lru_cache()
def get_settings() -> Settings:
    return Settings()
