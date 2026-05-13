"""Integration tests — full API flow through HTTP endpoints."""

import pytest
import pytest_asyncio
from httpx import AsyncClient


@pytest.mark.asyncio
class TestHealthEndpoints:
    async def test_health(self, client: AsyncClient):
        resp = await client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["version"] == "1.0.0"

    async def test_root(self, client: AsyncClient):
        resp = await client.get("/")
        assert resp.status_code == 200
        assert resp.json()["name"] == "AgentVault"


@pytest.mark.asyncio
class TestUserFlow:
    async def test_create_user(self, client: AsyncClient):
        resp = await client.post("/api/v1/users", json={"email": "test@example.com"})
        assert resp.status_code == 201
        data = resp.json()
        assert data["email"] == "test@example.com"
        assert data["plan"] == "free"

    async def test_create_user_idempotent(self, client: AsyncClient):
        await client.post("/api/v1/users", json={"email": "dup@example.com"})
        resp = await client.post("/api/v1/users", json={"email": "dup@example.com"})
        assert resp.status_code == 201  # returns existing user


@pytest.mark.asyncio
class TestAgentFlow:
    async def _create_user(self, client: AsyncClient) -> str:
        resp = await client.post("/api/v1/users", json={"email": "agent-test@example.com"})
        return resp.json()["email"]

    async def test_create_agent(self, client: AsyncClient):
        email = await self._create_user(client)
        resp = await client.post(
            "/api/v1/agents",
            json={"name": "Test Agent", "permissions": ["stripe_*"]},
            headers={"Authorization": f"Bearer {email}"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "Test Agent"
        assert "api_key" in data
        assert data["api_key"].startswith("avk_")

    async def test_list_agents(self, client: AsyncClient):
        email = await self._create_user(client)
        headers = {"Authorization": f"Bearer {email}"}
        await client.post("/api/v1/agents", json={"name": "A1"}, headers=headers)
        await client.post("/api/v1/agents", json={"name": "A2"}, headers=headers)

        resp = await client.get("/api/v1/agents", headers=headers)
        assert resp.status_code == 200
        assert len(resp.json()) == 2

    async def test_agent_plan_limit(self, client: AsyncClient):
        email = await self._create_user(client)
        headers = {"Authorization": f"Bearer {email}"}
        # Free plan = 3 agents max
        for i in range(3):
            resp = await client.post("/api/v1/agents", json={"name": f"A{i}"}, headers=headers)
            assert resp.status_code == 201

        resp = await client.post("/api/v1/agents", json={"name": "A4"}, headers=headers)
        assert resp.status_code == 403

    async def test_update_agent(self, client: AsyncClient):
        email = await self._create_user(client)
        headers = {"Authorization": f"Bearer {email}"}
        resp = await client.post("/api/v1/agents", json={"name": "Original"}, headers=headers)
        agent_id = resp.json()["id"]

        resp = await client.patch(
            f"/api/v1/agents/{agent_id}",
            json={"name": "Updated", "active": False},
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json()["name"] == "Updated"
        assert resp.json()["active"] is False

    async def test_delete_agent(self, client: AsyncClient):
        email = await self._create_user(client)
        headers = {"Authorization": f"Bearer {email}"}
        resp = await client.post("/api/v1/agents", json={"name": "ToDelete"}, headers=headers)
        agent_id = resp.json()["id"]

        resp = await client.delete(f"/api/v1/agents/{agent_id}", headers=headers)
        assert resp.status_code == 204


@pytest.mark.asyncio
class TestCredentialFlow:
    async def _setup(self, client: AsyncClient):
        resp = await client.post("/api/v1/users", json={"email": "cred-test@example.com"})
        email = resp.json()["email"]
        headers = {"Authorization": f"Bearer {email}"}
        return email, headers

    async def test_create_credential(self, client: AsyncClient):
        email, headers = await self._setup(client)
        resp = await client.post(
            "/api/v1/credentials",
            json={"name": "stripe_key", "provider": "stripe", "value": "sk_live_abc123"},
            headers=headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "stripe_key"
        assert data["provider"] == "stripe"
        # Value should NOT be in the response
        assert "value" not in data or "encrypted" not in str(data.get("value", ""))

    async def test_duplicate_credential_name(self, client: AsyncClient):
        email, headers = await self._setup(client)
        await client.post(
            "/api/v1/credentials",
            json={"name": "dup_key", "value": "val1"},
            headers=headers,
        )
        resp = await client.post(
            "/api/v1/credentials",
            json={"name": "dup_key", "value": "val2"},
            headers=headers,
        )
        assert resp.status_code == 409

    async def test_credential_plan_limit(self, client: AsyncClient):
        email, headers = await self._setup(client)
        # Free plan = 10 credentials max
        for i in range(10):
            resp = await client.post(
                "/api/v1/credentials",
                json={"name": f"key_{i}", "value": f"val_{i}"},
                headers=headers,
            )
            assert resp.status_code == 201

        resp = await client.post(
            "/api/v1/credentials",
            json={"name": "key_11", "value": "val_11"},
            headers=headers,
        )
        assert resp.status_code == 403

    async def test_list_credentials(self, client: AsyncClient):
        email, headers = await self._setup(client)
        await client.post("/api/v1/credentials", json={"name": "k1", "value": "v1"}, headers=headers)
        await client.post("/api/v1/credentials", json={"name": "k2", "value": "v2"}, headers=headers)

        resp = await client.get("/api/v1/credentials", headers=headers)
        assert resp.status_code == 200
        assert len(resp.json()) == 2

    async def test_update_credential(self, client: AsyncClient):
        email, headers = await self._setup(client)
        resp = await client.post(
            "/api/v1/credentials",
            json={"name": "update_me", "value": "old_value"},
            headers=headers,
        )
        cred_id = resp.json()["id"]

        resp = await client.patch(
            f"/api/v1/credentials/{cred_id}",
            json={"name": "updated_name"},
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json()["name"] == "updated_name"


@pytest.mark.asyncio
class TestVaultProxy:
    async def _full_setup(self, client: AsyncClient):
        """Create user, agent, credential and return (agent_api_key, headers)."""
        resp = await client.post("/api/v1/users", json={"email": "vault-test@example.com"})
        email = resp.json()["email"]
        user_headers = {"Authorization": f"Bearer {email}"}

        # Create agent
        resp = await client.post(
            "/api/v1/agents",
            json={"name": "Vault Agent", "permissions": ["stripe_*", "openai_key"]},
            headers=user_headers,
        )
        api_key = resp.json()["api_key"]

        # Create credentials
        await client.post(
            "/api/v1/credentials",
            json={"name": "stripe_key", "provider": "stripe", "value": "sk_live_secret123"},
            headers=user_headers,
        )
        await client.post(
            "/api/v1/credentials",
            json={"name": "openai_key", "provider": "openai", "value": "sk-openai-abc"},
            headers=user_headers,
        )
        await client.post(
            "/api/v1/credentials",
            json={"name": "twilio_sid", "provider": "twilio", "value": "AC_twilio_secret"},
            headers=user_headers,
        )

        return api_key, user_headers

    async def test_get_credential_via_vault(self, client: AsyncClient):
        api_key, _ = await self._full_setup(client)
        resp = await client.post(
            "/api/v1/vault/get/stripe_key",
            headers={"X-Agent-Key": api_key},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["value"] == "sk_live_secret123"
        assert data["name"] == "stripe_key"
        assert data["ttl_seconds"] == 300

    async def test_permission_denied(self, client: AsyncClient):
        api_key, _ = await self._full_setup(client)
        # Agent has permissions for stripe_* and openai_key, NOT twilio_sid
        resp = await client.post(
            "/api/v1/vault/get/twilio_sid",
            headers={"X-Agent-Key": api_key},
        )
        assert resp.status_code == 403

    async def test_credential_not_found(self, client: AsyncClient):
        api_key, _ = await self._full_setup(client)
        # Use a name matching the agent's stripe_* permission pattern but not stored
        resp = await client.post(
            "/api/v1/vault/get/stripe_nonexistent",
            headers={"X-Agent-Key": api_key},
        )
        assert resp.status_code == 404

    async def test_invalid_agent_key(self, client: AsyncClient):
        resp = await client.post(
            "/api/v1/vault/get/stripe_key",
            headers={"X-Agent-Key": "avk_invalid_key"},
        )
        assert resp.status_code == 401

    async def test_list_available_credentials(self, client: AsyncClient):
        api_key, _ = await self._full_setup(client)
        resp = await client.get(
            "/api/v1/vault/list",
            headers={"X-Agent-Key": api_key},
        )
        assert resp.status_code == 200
        names = resp.json()
        assert "stripe_key" in names
        assert "openai_key" in names
        # twilio_sid should NOT be visible (no permission)
        assert "twilio_sid" not in names

    async def test_vault_with_cost_tracking(self, client: AsyncClient):
        api_key, _ = await self._full_setup(client)
        resp = await client.post(
            "/api/v1/vault/get/stripe_key",
            headers={"X-Agent-Key": api_key},
            params={"cost": 0.50},
        )
        assert resp.status_code == 200


@pytest.mark.asyncio
class TestBudgetEnforcement:
    async def _setup_with_budget(self, client: AsyncClient):
        resp = await client.post("/api/v1/users", json={"email": "budget-test@example.com"})
        email = resp.json()["email"]
        user_headers = {"Authorization": f"Bearer {email}"}

        # Create agent with tight daily budget
        resp = await client.post(
            "/api/v1/agents",
            json={"name": "Budget Agent", "budget_daily": 1.00, "budget_monthly": 10.00},
            headers=user_headers,
        )
        api_key = resp.json()["api_key"]

        # Create credential
        await client.post(
            "/api/v1/credentials",
            json={"name": "test_key", "value": "secret_value"},
            headers=user_headers,
        )

        return api_key, user_headers

    async def test_budget_enforcement_blocks_overspend(self, client: AsyncClient):
        api_key, _ = await self._setup_with_budget(client)

        # Spend $0.80 — should succeed
        resp = await client.post(
            "/api/v1/vault/get/test_key",
            headers={"X-Agent-Key": api_key},
            params={"cost": 0.80},
        )
        assert resp.status_code == 200

        # Spend another $0.30 — should exceed $1.00 daily limit
        resp = await client.post(
            "/api/v1/vault/get/test_key",
            headers={"X-Agent-Key": api_key},
            params={"cost": 0.30},
        )
        assert resp.status_code == 429
        assert "budget" in resp.json()["detail"].lower()

    async def test_zero_cost_always_allowed(self, client: AsyncClient):
        api_key, _ = await self._setup_with_budget(client)

        # Zero-cost access should always work
        for _ in range(5):
            resp = await client.post(
                "/api/v1/vault/get/test_key",
                headers={"X-Agent-Key": api_key},
                params={"cost": 0.0},
            )
            assert resp.status_code == 200


@pytest.mark.asyncio
class TestAuditLogs:
    async def test_audit_log_requires_pro(self, client: AsyncClient):
        resp = await client.post("/api/v1/users", json={"email": "audit-test@example.com"})
        email = resp.json()["email"]

        resp = await client.get(
            "/api/v1/audit/logs",
            headers={"Authorization": f"Bearer {email}"},
        )
        # Free plan should be blocked
        assert resp.status_code == 403
