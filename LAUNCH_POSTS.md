# AgentVault — Launch Posts

Drafts for Brett to post when ready. Builder voice; problem first; no superlatives.

---

## Show HN

**Title:** Show HN: AgentVault – credential vault for AI agents (per-agent keys, budgets, audit)

**Body:**

AI agents need API keys – Stripe, OpenAI, Twilio, whatever. The current options are bad: hardcode them in the agent's config (leaks in logs, no rotation), pass via env vars at spawn (no per-agent isolation, no budget caps, no revocation without redeploy), or roll your own vault (which is real work — encryption at rest and in transit, audit logs, key rotation, budget tracking).

AgentVault is the third option as a service. One avk_ key per agent identity. fnmatch permission patterns (["stripe_*", "openai_*"]). Daily and monthly spending budgets per agent, enforced server-side with HTTP 429. Full audit log of every read. Credentials are stored with column-level Fernet encryption — the vault key is separate from the DB.

It's MCP-native: drop the stdio server into Claude Desktop / Cursor / Cline and your agent gets `list_credentials`, `get_credential(name, cost?)`, and `vault_status` tools.

Live: https://agentvault-api-production.up.railway.app
Docs: https://agentvault-api-production.up.railway.app/docs
Repo: https://github.com/bch1212/agentvault (MIT)
PyPI client: `pip install agentkeyring`

Caveats: V1 is one-week-old. No dashboard UI yet (planned). Auth uses Bearer-email as a fallback while I wire Clerk JWTs. Self-host with `bash deploy.sh` if you'd rather. 34 unit tests + 10 prod smoke checks pass.

Happy to answer architecture or pricing questions.

---

## r/ClaudeAI

**Title:** I built a credential vault for AI agents — MCP server included

I kept hitting the same problem with agentic workflows: I want my Claude/Cursor agent to call Stripe or send a SendGrid email, but I don't want to paste the live API key into the prompt or env file. Once it's there, I can't rotate it without redeploying everything, and I have no idea what the agent actually did with it.

So I built AgentVault. Each agent gets a unique avk_ key. The agent calls `vault.get_credential("stripe_key", cost=0.05)` via MCP and gets the decrypted value back with a 300s TTL. I get an audit log row with IP, timestamp, and the credential used. Daily/monthly budget caps per agent prevent runaway charges (returns 429 once the cap is hit). fnmatch permission patterns let me scope an agent to just `stripe_*` or `openai_*`.

Live + open source: https://github.com/bch1212/agentvault
Free tier is 3 agents + 10 credentials. Paid tiers add audit logs, budgets, team access.

MCP config (drop into claude_desktop_config.json):

```json
{
  "mcpServers": {
    "agentvault": {
      "command": "npx",
      "args": ["-y", "agentvault-mcp"],
      "env": {
        "AGENTVAULT_API_URL": "https://agentvault-api-production.up.railway.app",
        "AGENTVAULT_AGENT_KEY": "avk_..."
      }
    }
  }
}
```

Curious what people think — especially folks running multi-agent setups.

---

## r/AI_Agents

**Title:** Stop hardcoding API keys in your agent prompts — open-source credential vault, MCP-native

If you've built more than one agent, you've felt this: the agent needs an API key, so you paste it into the system prompt or pass it in env, and now you have:

1. No per-agent isolation (one key for all agents, can't tell who did what)
2. No revocation without redeploy
3. No budget control (an agent in a loop can rack up real $)
4. No audit trail
5. The plaintext key floating in your logs

AgentVault is a small service that fixes this. One `avk_` key per agent. Permission patterns. Per-agent daily/monthly $ caps. Audit log of every access. The actual secrets are Fernet-encrypted at the column level — losing the DB doesn't lose your keys.

It's MCP-native, so Claude/Cursor/Cline can use it directly with a 3-line config. Or hit the HTTP API: `POST /api/v1/vault/get/stripe_key?cost=0.05` with `X-Agent-Key: avk_...`.

MIT licensed. Self-host or use the live tier (free up to 3 agents/10 credentials).

GitHub: https://github.com/bch1212/agentvault

---

## Twitter — single

Built AgentVault: credential vault for AI agents.

- avk_ key per agent
- Fernet-encrypted secrets
- Per-agent $ budgets (429 on overage)
- Audit log
- MCP-native — drop into Claude Desktop in 3 lines

Free tier. Open source. https://github.com/bch1212/agentvault

---

## Twitter — thread

1/ I built AgentVault — a credential vault for AI agents. Open source, MIT, live.

The pitch: stop pasting API keys into agent prompts. Issue per-agent keys, enforce budgets, audit every access.

https://github.com/bch1212/agentvault

2/ The problem: I want my Claude agent to call Stripe. Three bad options today:

- Hardcode key → leaks in logs, can't rotate
- Env var → no per-agent isolation, no budget control
- Build your own vault → real work

Option 3 as a service. ↓

3/ Each agent identity gets a unique `avk_` key (SHA-256 hashed at rest). Permission patterns like `["stripe_*", "openai_*"]` scope what each can access. Daily/monthly $ caps with 429 enforcement.

The actual secrets: column-level Fernet encryption. Key separate from DB.

4/ MCP-native. Drop into Claude Desktop / Cursor / Cline:

```json
"agentvault": {
  "command": "npx",
  "args": ["-y", "agentvault-mcp"],
  "env": { "AGENTVAULT_API_URL": "...", "AGENTVAULT_AGENT_KEY": "avk_..." }
}
```

Now agents call `vault.get_credential("stripe_key")`.

5/ Free tier: 3 agents, 10 credentials. Paid tiers add audit logs ($49), budgets ($149), SSO/compliance ($499).

Self-host the whole thing if you'd rather: `bash deploy.sh`.

Demo: https://agentvault-api-production.up.railway.app/docs
Code: https://github.com/bch1212/agentvault

---

## Product Hunt

**Tagline:** Credential vault for AI agents — per-agent keys, budgets, audit logs.

**Description:**

AI agents need API keys to do anything useful, and pasting them into prompts or env vars is a security and ops nightmare. AgentVault gives each agent identity a unique `avk_` key, encrypts every stored secret with Fernet (column-level, key separate from DB), enforces per-agent daily and monthly spending budgets, and writes an audit log row for every access. fnmatch permission patterns scope what each agent can see.

It's MCP-native — three lines of JSON in Claude Desktop / Cursor / Cline and your agent gets `list_credentials`, `get_credential`, and `vault_status` tools.

Free tier (3 agents, 10 credentials). Paid tiers add audit logs ($49), budget controls ($149), SSO and compliance reports ($499). MIT licensed; self-host or use the live API.

**Maker comment:**

I built AgentVault because I kept running into the same wall with my own agent projects — I wanted Claude to call Stripe for me, but I didn't want the live key in the prompt and I had no way to cap how much it could spend. Now each of my agents has its own avk_ key with a $5/day cap, and I can see every access in the audit log. Hope it's useful for others doing agentic work. AMA.

---

## LinkedIn

I've been building autonomous AI products for a year, and one problem kept coming back: credential management.

Every agent needs API keys. Stripe, OpenAI, Twilio, internal services. The default pattern — hardcode in the prompt or pass via env — gives up four things you actually need: per-agent isolation, revocability without redeploy, spending controls, and an audit trail.

I built AgentVault to fix that pattern. Each agent identity gets a unique `avk_` key. Credentials are stored with column-level Fernet encryption. fnmatch permission patterns scope what each agent can read. Daily and monthly spending budgets enforce caps with HTTP 429 once you hit them. Every access is logged with IP, timestamp, and credential ID.

It's MCP-native, so Claude Desktop, Cursor, and Cline can use it with a three-line config. Or hit the HTTP API directly. Free tier covers 3 agents and 10 credentials; paid tiers add audit logs, budgets, and enterprise features.

MIT licensed, self-hostable, and live: https://github.com/bch1212/agentvault

If you're running agents in production, I'd love feedback on what's missing.

---

## Discord (engineering channel — short)

Just shipped AgentVault — credential vault for AI agents.

- Per-agent `avk_` keys
- Fernet-encrypted secrets
- Per-agent $ budgets (429 on overage)
- Audit log
- MCP-native

`claude mcp add agentvault npx -y agentvault-mcp -e AGENTVAULT_API_URL=https://agentvault-api-production.up.railway.app -e AGENTVAULT_AGENT_KEY=avk_...`

https://github.com/bch1212/agentvault
