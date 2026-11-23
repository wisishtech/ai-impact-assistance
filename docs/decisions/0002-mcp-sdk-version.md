# 0002 Pin the server to MCP Python SDK 1.x

**Status:** Accepted

## Context
`mcp` 2.x renamed `FastMCP` and changed APIs. An unpinned dependency pulled 2.x and broke the server. Separately, MCP's DNS-rebinding protection returned `421 Misdirected Request` behind Container Apps until the public host name was allowed.

## Decision
- Server: `mcp>=1.20,<2` (currently 1.30), `stateless_http=True`, `TransportSecuritySettings(allowed_hosts=[...])` from the `ALLOWED_HOSTS` setting.
- The code-first agent needs `mcp>=2.2` (Agent Framework), so it lives in its own uv project (`agent_code/`). A 2.x client talks to the 1.x server over standard streamable HTTP.

## Consequences
- Server upgrades to 2.x are a planned change, not an accident.
- Two Python environments in one repo, each with its own lock file.
