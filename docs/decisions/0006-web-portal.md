# 0006 Web portal through the Microsoft 365 Agents SDK

**Status:** Accepted

## Context
The agent uses "Authenticate with Microsoft", which hides the embed code, and the new Copilot Studio UI has no manual authentication option. Agents made in the new UI run on the GitHub Copilot harness, which the Agents SDK client older than 1.10 rejects.

## Decision
- React + TypeScript portal using MSAL (app `iea-webchat`, delegated `CopilotStudio.Copilots.Invoke`) and `@microsoft/agents-copilotstudio-client` **1.10.2**, which discovers the harness's conversation endpoints.
- The same sign-in also gets an `Evidence.Read` token to show "My drafts" from the MCP server.
- Hosted on Azure Static Web Apps (Free), deployed by GitHub Actions (the local SWA CLI deploy binary failed on Windows).

## Consequences
- No secrets in the browser; users see only their own drafts.
- CORS on the MCP server must list each portal origin (`PORTAL_ORIGIN`, comma-separated).
