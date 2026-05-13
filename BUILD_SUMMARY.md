# AgentVault — Build Summary

**Built:** 2026-05-13
**Status:** LIVE on Railway 2026-05-13. 34/34 unit tests + 10/10 prod smoke checks pass.
**URL:** https://agentvault-api-production.up.railway.app
**Docs:** https://agentvault-api-production.up.railway.app/docs
**Location:** `/Users/bretthalverson/Projects/agentic-builds/Build Prompts from OpenClaw/agentvault/`

## Review fixes applied during deploy

1. `api/main.py` — `mcp_server.mount_to_fastapi()` doesn't exist on FastMCP; replaced with a `GET /mcp` info endpoint. The MCP server runs as a stdio subprocess in client configs.
2. `api/main.py` — `from api.database import engine` captured `None` at import time before `init_db()` rebound the name. Switched to `from api import database` + `database.engine` so the lifespan reads the live binding.
3. `api/database.py` — Railway sets `DATABASE_URL=postgresql://...` but the async engine needs `postgresql+asyncpg://...`. Added `_normalize_async_url()` to rewrite at engine construction.
4. `mcp_server/server.py` — Tools called `{API_BASE}/vault/...` but the API is mounted at `/api/v1/vault/...`. Now appends `/api/v1` and keeps `/health` on the bare base.

## Stripe prices (live mode)

- Pro: `price_1TWbss54riYeMScuAt53muVi`
- Business: `price_1TWbsu54riYeMScuJxbztLZI`
- Enterprise: `price_1TWbsw54riYeMScuDxtYp7Bh`

## Remaining manual steps

- Purchase `agentvault.dev`, add the zone at Cloudflare, then `railway domain agentvault.dev` (the zone is not yet at Cloudflare under Brett's account).
- Add a Stripe webhook → `https://agentvault.dev/api/v1/billing/webhook` once the custom domain is live.
- (Optional) Provision Clerk for full JWT auth. The Bearer-email fallback works for MVP/smoke tests.

---

## What AgentVault Is

AI-native credential management SaaS for autonomous AI agents. Stores API keys with column-level Fernet encryption, issues unique keys to registered agent identities, proxies decrypted values with TTL, enforces per-agent spending budgets, logs every access, and exposes itself as an MCP server.

## Pricing
- **Free:** 3 agents, 10 credentials
- **Pro $49/mo:** 25 agents, 100 credentials, audit logs, auto-rotation
- **Business $149/mo:** unlimited, budget controls, team access
- **Enterprise $499/mo:** SSO, compliance reports, custom retention

---

## Project Structure

```
agentvault/
├── api/
│   ├── main.py              # FastAPI app + lifespan
│   ├── __main__.py           # python -m api entry
│   ├── config.py             # Pydantic settings
│   ├── database.py           # Async SQLAlchemy engine
│   ├── models/
│   │   ├── db.py             # ORM: User, AgentIdentity, Credential, AccessLog, BudgetUsage
│   │   └── schemas.py        # Pydantic request/response models
│   ├── services/
│   │   ├── encryption.py     # Fernet encrypt/decrypt
│   │   ├── auth.py           # avk_ key generation, SHA-256 hashing
│   │   ├── budget.py         # Per-agent daily/monthly spend tracking
│   │   ├── audit.py          # Access log writer + query
│   │   └── alerts.py         # SendGrid budget/rotation emails
│   ├── middleware/
│   │   ├── agent_auth.py     # X-Agent-Key header validation
│   │   └── user_auth.py      # Bearer token (Clerk JWT / email)
│   └── routers/
│       ├── users.py          # POST /users
│       ├── agents.py         # CRUD agent identities
│       ├── credentials.py    # CRUD encrypted credentials
│       ├── vault.py          # Agent proxy: /vault/get/{name}, /vault/list
│       ├── audit.py          # /audit/logs (Pro+ only)
│       ├── budgets.py        # GET/PUT budgets (Business+ only)
│       └── billing.py        # Stripe checkout/portal/webhook
├── mcp_server/
│   ├── server.py             # FastMCP tools (list, get, status)
│   └── __main__.py           # python -m mcp_server
├── tests/
│   ├── conftest.py           # SQLite in-memory fixtures
│   ├── test_encryption.py    # 5 tests — Fernet roundtrip
│   ├── test_auth.py          # 6 tests — API key gen + hashing
│   └── test_api.py           # 23 tests — full HTTP integration
├── deploy.sh                 # Railway + Stripe deploy (idempotent)
├── Dockerfile
├── railway.toml
├── requirements.txt
├── pytest.ini
├── .env.example
├── .gitignore
├── CLAUDE.md
└── BUILD_SUMMARY.md          # this file
```

---

## API Endpoints

### User-facing (`Authorization: Bearer <email-or-jwt>`)
- `POST /api/v1/users` — register
- `POST /api/v1/agents` — create agent (returns one-time `api_key`)
- `GET /api/v1/agents` — list agents
- `GET /api/v1/agents/{id}` — get agent
- `PATCH /api/v1/agents/{id}` — update agent
- `DELETE /api/v1/agents/{id}` — delete agent
- `POST /api/v1/credentials` — create encrypted credential
- `GET /api/v1/credentials` — list (metadata only, no values)
- `PATCH /api/v1/credentials/{id}` — update / rotate
- `DELETE /api/v1/credentials/{id}` — delete
- `GET /api/v1/audit/logs` — query audit logs (Pro+)
- `GET /api/v1/budgets/{agent_id}` — budget status (Business+)
- `PUT /api/v1/budgets/{agent_id}` — set limits (Business+)
- `POST /api/v1/billing/checkout` — Stripe Checkout session
- `POST /api/v1/billing/portal` — Stripe customer portal
- `POST /api/v1/billing/webhook` — Stripe webhook receiver

### Agent-facing (`X-Agent-Key: avk_...`)
- `POST /api/v1/vault/get/{name}?cost=0.50` — retrieve decrypted value (TTL 300s)
- `GET /api/v1/vault/list` — list accessible credential names

### Public
- `GET /health` — liveness check
- `GET /` — service info
- `GET /docs` — auto-generated OpenAPI
- `GET /mcp` — MCP SSE transport

---

## Data Model

```
users (id, email, clerk_id, plan, stripe_customer_id, stripe_subscription_id, created_at)
agent_identities (id, user_id, name, api_key_hash, api_key_prefix, permissions, budget_daily, budget_monthly, active)
credentials (id, user_id, name, provider, encrypted_value, rotation_interval_hours, last_rotated, metadata_json)
credential_access_logs (id, agent_id, credential_id, action, ip_address, user_agent, success, error_message, timestamp)
budget_usage (id, agent_id, period_type, period_start, amount_used, limit_amount)
```

---

## Key Patterns Used

| Pattern | Why |
|---|---|
| `python -m api.main` + `os.getenv("PORT")` | Railway exec's startCommand without shell; `$PORT` doesn't expand |
| Fernet column-level encryption | Stronger than just at-rest disk encryption; key separate from DB |
| `avk_` prefix on agent keys | Recognizable, like `sk_live_` / `whsec_` |
| SHA-256 hash for stored keys | Constant-time comparison, never store plaintext |
| fnmatch permissions (`["stripe_*"]`) | Flexible scoping without complex policy engine |
| `UUID` path params (not `str`) | SQLAlchemy needs typed UUIDs for Postgres + SQLite both |
| Lifespan startup hook for `Base.metadata.create_all` | Auto-bootstrap schema; swap to Alembic later |

---

## Test Coverage (34 tests, all passing)

**`test_encryption.py` (5):**
- Encrypt/decrypt roundtrip
- Different ciphertexts per call (nonce)
- Decrypt garbage raises ValueError
- Empty string roundtrip
- Long value roundtrip (10k chars)

**`test_auth.py` (6):**
- Keys have `avk_` prefix
- 100 keys all unique
- Key length > 40 chars
- Hash deterministic
- Different keys → different hashes
- Prefix extraction works

**`test_api.py` (23):**
- Health + root endpoints
- User creation idempotent
- Agent CRUD (create, list, update, delete)
- Agent plan limits enforced (free = 3 max)
- Credential CRUD
- Duplicate credential name → 409
- Credential plan limits (free = 10 max)
- Vault proxy returns decrypted value
- Permission denial (403 for non-matching pattern)
- 404 for missing credential
- 401 for invalid agent key
- Vault list filtered by permissions
- Cost tracking via query param
- Budget enforcement blocks at limit (429)
- Zero-cost always allowed
- Audit logs gated to Pro plan (403 on free)

Run: `cd agentvault && python -m pytest -v`

---

## Deploy Steps

```bash
cd agentvault
bash deploy.sh
```

`deploy.sh` does:
1. Loads `../.deploy-secrets.env`
2. Generates `VAULT_ENCRYPTION_KEY` if missing (saved to `.env`)
3. Creates Stripe products + prices (idempotent via `lookup_key`)
4. `railway init` + `railway link`
5. Sets env vars via `railway variables set`
6. `railway up --detach`

### Manual steps after deploy
1. Add Postgres plugin in Railway dashboard (auto-sets `DATABASE_URL`)
2. Configure custom domain → `agentvault.dev`
3. Add Stripe webhook endpoint → `https://agentvault.dev/api/v1/billing/webhook`
4. Provision Clerk app, set `CLERK_SECRET_KEY` + `CLERK_JWKS_URL`

---

## What's Still TODO (Phase 2)

- **Frontend:** Next.js dashboard on Vercel (not yet built)
- **Auto-rotation framework:** OpenAI/Stripe/Twilio/SendGrid provider-specific rotation jobs (stub in place via `rotation_interval_hours` + `last_rotated` columns)
- **Clerk JWT validation:** `user_auth.py` currently accepts email-as-token for MVP; swap to full JWKS validation
- **Alembic migrations:** currently using `Base.metadata.create_all` on startup
- **Slack alerts:** SendGrid email works; Slack webhook integration for Business+ alerts
- **Compliance reports:** Enterprise tier feature
- **Distribution:** GitHub repo creation, PyPI publish (`agentvault` package), Anthropic MCP Registry, awesome-mcp-servers PR, launch posts

---

## Quickstart for Agents

Once deployed, any AI agent (Claude, Cursor, custom) can use it:

```python
import httpx

# One-time: user creates agent identity in dashboard, copies avk_... key
AGENT_KEY = "avk_xxxxx..."

# Agent retrieves credential
resp = httpx.post(
    "https://agentvault.dev/api/v1/vault/get/stripe_key",
    headers={"X-Agent-Key": AGENT_KEY},
    params={"cost": 0.05},  # optional budget tracking
)
stripe_key = resp.json()["value"]
```

Or via MCP (in Claude Desktop / Cursor config):
```json
{
  "mcpServers": {
    "agentvault": {
      "command": "python",
      "args": ["-m", "mcp_server"],
      "env": {
        "AGENTVAULT_API_URL": "https://agentvault.dev",
        "AGENTVAULT_AGENT_KEY": "avk_..."
      }
    }
  }
}
```

Then in Claude: `vault.get_credential("stripe_key")` → returns the decrypted value.
