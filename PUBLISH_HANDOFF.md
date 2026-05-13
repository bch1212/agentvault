# agentvault-mcp publish handoff

The npm + MCP Registry publish workflow is set up at `.github/workflows/publish-mcp.yml`.

**One manual step is needed before it can run.** GitHub doesn't let secrets be read back via API, so I can't copy `NPM_TOKEN` autonomously.

1. Go to https://github.com/bch1212/agentvault/settings/secrets/actions
2. Click "New repository secret"
3. Name: `NPM_TOKEN`. Value: the same npm automation token used on `bch1212/injectshield`.
4. Then trigger the workflow:

```bash
gh workflow run publish-mcp.yml --repo bch1212/agentvault
# or push a tag:
git tag mcp-v0.1.0 && git push origin mcp-v0.1.0
```

The workflow will:
- Install + build the TypeScript MCP server
- `npm publish --provenance` to `agentvault-mcp`
- Exchange GitHub Actions OIDC for an MCP Registry JWT
- Submit `server.json` to `io.github.bch1212/agentvault` in the Anthropic MCP Registry

It's idempotent — re-running with the same version is safe.

The Python SDK is already published:
- `pip install agentkeyring`
- https://pypi.org/project/agentkeyring/
