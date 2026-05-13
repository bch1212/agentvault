# agentvault-mcp

MCP server for [AgentVault](https://github.com/bch1212/agentvault) — AI-native credential vault for autonomous agents.

## Install

```bash
npx -y agentvault-mcp
```

## Claude Desktop / Cursor config

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

## Tools

- `list_credentials()` — list names this agent can read.
- `get_credential(name, cost?)` — retrieve a decrypted value; optional `cost` charges the agent's budget.
- `vault_status()` — check API connectivity.

Get an `avk_` key by creating an agent identity at the live API (`POST /api/v1/agents`) or via the dashboard (coming soon).

## License

MIT.
