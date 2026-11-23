# 0001 Architecture: Copilot Studio front end, MCP server as the single data gate

**Status:** Accepted

## Context
Staff work in Teams and Microsoft 365. The assistant must answer from IREX documents, respect document permissions and be reachable from several channels (Teams, M365 Copilot, web, code).

## Decision
- Copilot Studio hosts the conversational agent for Teams and M365 Copilot.
- A Python MCP server on Azure Container Apps is the only path to data (search, indicators, draft submission).
- Every channel passes the user's Entra token to the MCP server, which enforces permissions.

## Consequences
- Permissions are enforced once, in code we test, not per channel.
- New channels (portal, code-first agent) reuse the same tools without new data access.
- One more service to run and monitor; kept small (3 tools, 1 route).
