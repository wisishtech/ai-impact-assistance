# Security controls

| Area | Control |
|---|---|
| Identity | All users sign in with Entra ID. Copilot Studio uses "Authenticate with Microsoft"; the portal uses MSAL (public client, no secret in the browser). |
| API access | The MCP server accepts only Entra access tokens for `api://<iea-mcp-api>` with scope `Evidence.Read`; signature, issuer, audience and expiry are checked (`auth.py`). `/healthz` is the only unauthenticated route. |
| Document permissions | Each passage carries `group_ids`. Every search adds `group_ids/any(g: search.in(g, '<user groups>'))`. Users with no groups get no results. |
| Injection | User-provided filter values are quote-escaped before building OData filters; `top` is capped at 8. |
| Service-to-service | The container app uses a system-assigned managed identity: Search Index Data Reader on the index, Graph `Sites.Selected` (write) on the knowledge site only. No keys in code or images. |
| Secrets | `.env` is git-ignored and docker-ignored. Client secrets for Copilot Studio connections live in Key Vault. |
| Network | HTTPS only (`allowInsecure: false`). DNS-rebinding protection with an allowed-hosts list on the MCP endpoint. CORS allows only the local dev origin and the hosted portal. |
| Writes | The only write is `submit_draft_for_review`. It requires user confirmation (instructions) and, in the code-first agent, an explicit human approval in code. Reviewers approve in Power Automate. |
| Least privilege | Separate app registrations: API, Copilot client, agent auth, web chat, evaluation. Restricted library readable only by `IEA-Restricted`; Draft Reviews editable by `IEA-Reviewers`. |
| Kill switch | `MAINTENANCE_MODE=true` makes every tool return a "temporarily unavailable" message without touching data. |
| Logging | Tool calls traced to Application Insights with user object ID and hit counts, not document text. |
| Testing | 24 automated tests (filters, token validation, tool output, permission integration). Release gate requires 0 permission leaks. |
| Cost guard | Azure budget alert at $50 on the resource group; container app min replicas 1, max 3; single-revision mode. |

## Known gaps (next steps)
- Move the portal to a custom domain with security headers (`staticwebapp.config.json`).
- Add rate limiting per user on the MCP server.
- Rotate Copilot connection client secrets on a schedule, or switch to federated credentials.
- Add a Conditional Access policy requiring MFA for the API.
