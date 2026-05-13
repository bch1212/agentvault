# AgentVault

AI-native credential management SaaS for autonomous AI agents.

## What It Does
- Stores API keys/secrets with Fernet column-level encryption
- Issues unique API keys to registered "agent identities"
- Proxy endpoint: agents call `/api/v1/vault/get/{credential_name}` with their API key
- Per-agent daily/monthly spending budgets
- Full audit logs of every vault access
- MCP server interface (stdio + SSE on `/mcp`)
- Stripe billing (Free / Pro $49 / Business $149 / Enterprise $499)

## Stack
- **Backend:** FastAPI (Python 3.12) on Railway
- **Database:** Postgres (asyncpg + SQLAlchemy async)
- **Encryption:** Fernet (cryptography lib) — column-level, not just at-rest
- **Auth:** Clerk (user) + custom API keys (agents)
- **Payments:** Stripe Checkout + webhooks
- **Alerts:** SendGrid
- **MCP:** FastMCP library

## Project Structure
```
agentvault/
├── api/
│   ├── main.py              # FastAPI app + lifespan
│   ├── config.py             # Pydantic settings
│   ├── database.py           # SQLAlchemy async engine
│   ├── models/
│   │   ├── db.py             # ORM models (User, Agent, Credential, etc.)
│   │   └── schemas.py        # Pydantic request/response schemas
│   ├── services/
│   │   ├── encryption.py     # Fernet encrypt/decrypt
│   │   ├── auth.py           # API key gen, hashing, agent lookup
│   │   ├── budget.py         # Budget enforcement + tracking
│   │   ├── audit.py          # Audit log service
│   │   └── alerts.py         # SendGrid email alerts
│   ├── middleware/
│   │   ├── agent_auth.py     # X-Agent-Key header validation
│   │   └── user_auth.py      # Authorization header (Clerk JWT / email)
│   └── routers/
│       ├── users.py          # POST /users
│       ├── agents.py         # CRUD agent identities
│       ├── credentials.py    # CRUD encrypted credentials
│       ├── vault.py          # Agent-facing proxy endpoint
│       ├── audit.py          # Query audit logs
│       ├── budgets.py        # Budget management
│       └── billing.py        # Stripe checkout/webhooks/portal
├── mcp_server/
│   ├── server.py             # FastMCP tools (list, get, status)
│   └── __main__.py           # python -m mcp_server
├── tests/
│   ├── conftest.py           # SQLite fixtures, test client
│   ├── test_encryption.py    # Encryption roundtrip tests
│   ├── test_auth.py          # API key tests
│   └── test_api.py           # Full integration tests
├── deploy.sh                 # Railway deploy script
├── Dockerfile
├── railway.toml
└── requirements.txt
```

## Running Locally
```bash
pip install -r requirements.txt
cp .env.example .env
# Fill in .env values
python -m api.main
```

## Running Tests
```bash
pip install -r requirements.txt
cd agentvault && python -m pytest -v
```

## Deploy
```bash
cd agentvault && bash deploy.sh
```

## Key Patterns
- Railway PORT: read via `os.getenv("PORT", "8000")` in Python, never `$PORT` in startCommand
- Agent API keys: `avk_` prefix, SHA-256 hashed for storage, prefix saved for identification
- Credentials: Fernet-encrypted at column level before DB write
- Permissions: JSON array of fnmatch patterns (e.g., `["stripe_*", "openai_key"]`)
- Budget: per-agent daily/monthly counters, checked on every vault access with cost > 0
