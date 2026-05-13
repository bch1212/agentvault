# MCP directory submission copy

Pre-written copy for the directories that require manual web-form submission. Open the corresponding URL, paste, submit.

---

## mcp.so

URL: https://mcp.so/submit

```
Server Name: AgentVault
GitHub: https://github.com/bch1212/agentvault
npm: agentvault-mcp
PyPI client: agentkeyring
Tagline: AI-native credential vault for autonomous agents.

Description:
AgentVault is a credential vault built for AI agents. Per-agent avk_ API keys (SHA-256 hashed at rest), column-level Fernet encryption for stored secrets, fnmatch permission patterns ([\"stripe_*\", \"openai_*\"]), per-agent daily and monthly spending budgets enforced with HTTP 429, and a complete audit log. Live at https://agentvault-api-production.up.railway.app — Free tier 3 agents/10 credentials; Pro $49; Business $149; Enterprise $499.

Tools: list_credentials, get_credential(name, cost?), vault_status
License: MIT
```

---

## PulseMCP

URL: https://www.pulsemcp.com/submit

```
Name: AgentVault
GitHub: https://github.com/bch1212/agentvault
Live URL: https://agentvault-api-production.up.railway.app
Category: Security / Secrets Management
Pricing: Free + paid tiers ($49, $149, $499)
Description:
Credential vault for AI agents. Per-agent avk_ keys, Fernet column-level encryption, fnmatch permissions, budget enforcement with 429, audit logs. MCP server `agentvault-mcp` on npm; Python client `agentkeyring` on PyPI. 34 unit tests + 10 production smoke checks pass.
```

---

## MCPize

URL: https://mcpize.com/submit (or paid placement)

Same blurb as above plus pricing tier selection. MCPize is mostly paid placement; defer.

---

## Glama

No manual submission needed. Glama auto-crawls GitHub for repos with topics `mcp`, `model-context-protocol`, `mcp-server` (all set on bch1212/agentvault) plus a `glama.json` at the repo root (committed). Typical indexing lag: 1–3 days. To accelerate: paste the GitHub URL in the Glama Discord (https://discord.gg/C3eCXhYWtJ).

---

## Smithery

No manual submission needed. Smithery auto-imports any npm package with the `mcp-server` keyword. The package.json for `agentvault-mcp` includes that keyword + the `smithery.yaml` config schema at repo root. Indexing happens within hours of `npm publish`.

---

## Anthropic MCP Registry

Handled automatically by `.github/workflows/publish-mcp.yml` — runs `OIDC exchange → POST /v0/publish` once Brett adds `NPM_TOKEN` and triggers the workflow (see `PUBLISH_HANDOFF.md`).
