#!/usr/bin/env node
/**
 * agentvault-mcp — Model Context Protocol server for AgentVault.
 *
 * Exposes vault.get / vault.list / vault.status as MCP tools.
 * Configure with AGENTVAULT_API_URL and AGENTVAULT_AGENT_KEY env vars.
 */
import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from "@modelcontextprotocol/sdk/types.js";

const RAW_BASE = (process.env.AGENTVAULT_API_URL ?? "http://localhost:8000").replace(/\/+$/, "");
const API_BASE = RAW_BASE.endsWith("/api/v1") ? RAW_BASE : `${RAW_BASE}/api/v1`;
const HEALTH_BASE = RAW_BASE.endsWith("/api/v1") ? RAW_BASE.slice(0, -"/api/v1".length) : RAW_BASE;
const AGENT_KEY = process.env.AGENTVAULT_AGENT_KEY ?? "";

if (!AGENT_KEY) {
  // eslint-disable-next-line no-console
  console.error("[agentvault-mcp] WARNING: AGENTVAULT_AGENT_KEY is empty. Set an avk_ key.");
}

function authHeaders(): HeadersInit {
  return {
    "X-Agent-Key": AGENT_KEY,
    "Content-Type": "application/json",
  };
}

async function listCredentials(): Promise<string> {
  const resp = await fetch(`${API_BASE}/vault/list`, { headers: authHeaders() });
  if (!resp.ok) {
    return `Error: ${resp.status} — ${await resp.text()}`;
  }
  const names = (await resp.json()) as string[];
  if (names.length === 0) return "No credentials available to this agent.";
  return `Available credentials:\n${names.map((n) => `  - ${n}`).join("\n")}`;
}

async function getCredential(name: string, cost = 0): Promise<string> {
  const url = `${API_BASE}/vault/get/${encodeURIComponent(name)}?cost=${cost}`;
  const resp = await fetch(url, { method: "POST", headers: authHeaders() });
  if (!resp.ok) {
    return `Error: ${resp.status} — ${await resp.text()}`;
  }
  const data = (await resp.json()) as { value: string };
  return data.value;
}

async function vaultStatus(): Promise<string> {
  try {
    const resp = await fetch(`${HEALTH_BASE}/health`);
    if (!resp.ok) return `Vault returned ${resp.status}`;
    const data = (await resp.json()) as { version?: string; environment?: string };
    return `Vault connected: ${HEALTH_BASE} (v${data.version ?? "?"}, ${data.environment ?? "?"})`;
  } catch (e) {
    return `Cannot reach vault at ${HEALTH_BASE}: ${(e as Error).message}`;
  }
}

const server = new Server(
  {
    name: "agentvault",
    version: "0.1.0",
  },
  {
    capabilities: { tools: {} },
  }
);

server.setRequestHandler(ListToolsRequestSchema, async () => ({
  tools: [
    {
      name: "list_credentials",
      description: "List all credential names available to this agent.",
      inputSchema: { type: "object", properties: {}, required: [] },
    },
    {
      name: "get_credential",
      description: "Retrieve a decrypted credential value from the vault (TTL 300s). Optional `cost` charges this agent's budget.",
      inputSchema: {
        type: "object",
        properties: {
          name: { type: "string", description: "Credential name, e.g. stripe_key" },
          cost: { type: "number", description: "Optional cost to record against this agent's budget", default: 0 },
        },
        required: ["name"],
      },
    },
    {
      name: "vault_status",
      description: "Check vault connection status and version.",
      inputSchema: { type: "object", properties: {}, required: [] },
    },
  ],
}));

server.setRequestHandler(CallToolRequestSchema, async (req) => {
  const { name, arguments: args } = req.params;
  let text: string;
  if (name === "list_credentials") {
    text = await listCredentials();
  } else if (name === "get_credential") {
    const credName = (args?.name as string) ?? "";
    const cost = typeof args?.cost === "number" ? (args.cost as number) : 0;
    text = await getCredential(credName, cost);
  } else if (name === "vault_status") {
    text = await vaultStatus();
  } else {
    text = `Unknown tool: ${name}`;
  }
  return { content: [{ type: "text", text }] };
});

const transport = new StdioServerTransport();
await server.connect(transport);
