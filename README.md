# AgentVault

**AI-native credential management for autonomous agents.** Store API keys with column-level Fernet encryption, issue unique `avk_` keys to registered agent identities, proxy decrypted values with TTL, enforce per-agent spending budgets, log every access, and expose everything as an MCP server.

- **Live API:** https://agentvault-api-production.up.railway.app
- **Docs:** https://agentvault-api-production.up.railway.app/docs
- **Status:** Production (Railway + Postgres + Stripe live)

## Why

Autonomous agents need API keys to do anything useful — Stripe, OpenAI, SendGrid, your own internal services. Three bad options today:

1. **Hardcode in the agent prompt or config.** Leaks in logs, can't rotate, no audit trail.
2. **Pass via env vars at spawn.** No per-agent isolation, no budget controls, no revocation without redeploy.
3. **Roll your own vault.** Real work — encryption at rest *and* in transit, audit logs, key rotation, budget tracking.

AgentVault is option 3 as a service. One `avk_` key per agent. Permission patterns (`["stripe_*", "openai_*"]`). Daily/monthly spending caps. Full access log. MCP-native so agents can `vault.get_credential("stripe_key")` and get a TTL-bound decrypted value back.

## Quickstart

### Direct HTTP

```python
import httpx

resp = httpx.post(
    "https://agentvault-api-production.up.railway.app/api/v1/vault/get/stripe_key",
    headers={"X-Agent-Key": "avk_..."},
    params={"cost": 0.05},
)
stripe_key = resp.json()["value"]
```

### MCP (Claude Desktop / Cursor / Cline)

```json
{
  "mcpServers": {
    "agentvault": {
      "command": "python",
      "args": ["-m", "mcp_server"],
      "env": {
        "AGENTVAULT_API_URL": "https://agentvault-api-production.up.railway.app",
        "AGENTVAULT_AGENT_KEY": "avk_..."
      }
    }
  }
}
```

Then in Claude: `vault.get_credential("stripe_key")` returns the decrypted value.

## How it works

- **Column-level Fernet encryption** — credentials are encrypted with `VAULT_ENCRYPTION_KEY` *before* they hit the database. Stronger than at-rest disk encryption alone.
- **`avk_` agent keys** — SHA-256 hashed at rest, never stored plaintext. Recognizable prefix like `sk_live_` / `whsec_`.
- **Permission patterns** — `["stripe_*", "openai_*"]` scopes an agent without a full policy engine. fnmatch-based.
- **Budget enforcement** — daily and monthly caps per agent. `/vault/get?cost=0.05` records the spend; 429 once the cap is hit.
- **Audit log** — every access (success or denied) goes into `credential_access_logs` with IP, user-agent, error reason.
- **MCP server** — `mcp_server/` exposes `list_credentials`, `get_credential`, `vault_status`, `set_budget`, `view_audit_log` as stdio MCP tools.

## Pricing

| Tier | $/mo | Agents | Credentials | Audit | Rotation | Budgets | Team |
|---|---|---|---|---|---|---|---|
| Free | $0 | 3 | 10 | – | – | – | – |
| Pro | $49 | 25 | 100 | ✓ | ✓ | – | – |
| Business | $149 | ∞ | ∞ | ✓ | ✓ | ✓ | ✓ |
| Enterprise | $499 | ∞ | ∞ | ✓ | ✓ | ✓ | ✓ + SSO + compliance |

## Self-host

```bash
git clone https://github.com/bch1212/agentvault
cd agentvault
pip install -r requirements.txt
cp .env.example .env  # then fill in VAULT_ENCRYPTION_KEY and DATABASE_URL
python -m api.main
```

Run tests:

```bash
python -m pytest -v   # 34 tests
```

Deploy to Railway:

```bash
bash deploy.sh
```

## Architecture

```
api/
├── main.py                 # FastAPI + lifespan
├── database.py             # Async SQLAlchemy (auto-rewrites postgresql:// → postgresql+asyncpg://)
├── services/
│   ├── encryption.py       # Fernet encrypt/decrypt
│   ├── auth.py             # avk_ key gen + SHA-256 hashing
│   ├── budget.py           # Per-agent spend tracking
│   ├── audit.py            # Access log
│   └── alerts.py           # SendGrid alerts
├── middleware/             # X-Agent-Key + Bearer auth
└── routers/                # users, agents, credentials, vault, audit, budgets, billing
mcp_server/                 # FastMCP stdio server
tests/                      # 34 tests, SQLite in-memory
```

## License

MIT.
