# Runbook: Impact Evidence Assistant (dev)

| Item | Value |
|---|---|
| Owner | Repository owner (AI Solutions) |
| Portal | https://white-dune-0fcfdb00f.6.azurestaticapps.net |
| MCP server | https://ca-iea-mcp-dev.jollyhill-fc3ac0bc.eastus.azurecontainerapps.io (`/healthz`) |
| Azure | Subscription `11ccf494-…`, resource group `rg-iea-dev` (East US) |
| Power Platform | Environment **IEA-Sandbox**, solution **Impact Evidence Assistant** |
| Teams app | Impact Evidence Assistant (shared with `IEA-AllStaff`) |

## Health check (2 minutes)
```powershell
curl.exe https://ca-iea-mcp-dev.jollyhill-fc3ac0bc.eastus.azurecontainerapps.io/healthz   # expect: ok
az containerapp revision list -n ca-iea-mcp-dev -g rg-iea-dev --query "[?properties.active].{name:name, health:properties.healthState}" -o table
```
Then ask one known question in Teams and check the citation.

## Release the server
1. Change code, run `uv run --env-file .env pytest -q`.
2. If instructions, test set, sources or server code changed: `uv run python eval/run_eval.py`, commit `eval/results/summary.json`.
3. Push to `main`; CI must be green.
4. GitHub → Actions → **Release MCP server** → Run workflow → version `x.y.z`.
5. The workflow re-checks the gate, deploys, checks `/healthz` and rolls back automatically if it fails.

## Roll back by hand
```powershell
az containerapp update -n ca-iea-mcp-dev -g rg-iea-dev --image acrieadev9498.azurecr.io/iea-mcp:<previous-version> --revision-suffix rollback-<hhmm>
```

## Turn the assistant off (kill switch)
```powershell
az containerapp update -n ca-iea-mcp-dev -g rg-iea-dev --set-env-vars MAINTENANCE_MODE=true
```
Every tool then answers "temporarily unavailable". Set it back to `false` to restore.

## Update agent instructions
Edit `agent/instructions.md` → paste into Copilot Studio (Build → Instructions) → Save → Publish → re-run the eval → commit both.

## Add or remove a document
1. Add a row to `data/sources.csv` (set `access_group`).
2. Run ingestion: `extract.py` → `build_chunks.py` → `embed_and_upload.py`.
3. Re-run the eval (the fingerprint includes `sources.csv`).

## Give someone access
| Need | Do |
|---|---|
| Use the assistant | Add to Entra group `IEA-AllStaff` |
| See restricted documents | Also add to `IEA-Restricted` |
| Approve drafts | Add to `IEA-Reviewers` |
New users open the user-connections link once to create their IEA Server connection.

## Rotate secrets (every 6 months)
`iea-copilot-client` and `iea-agent-auth` client secrets (Key Vault: `copilot-client-secret`, `agent-auth-secret`):
```powershell
az ad app credential reset --id <appId> --display-name rotated-<yyyymm> --years 1 --query password -o tsv
```
Store in Key Vault, update the connection in Copilot Studio, test in Teams, then delete the old secret.

## Costs
- Budget alert: $50 on `rg-iea-dev`.
- Biggest fixed costs: AI Search Basic and one always-on container replica.
- To pause the server: `az containerapp update -n ca-iea-mcp-dev -g rg-iea-dev --min-replicas 0` (first request after idle is slow; Copilot may show "couldn't load this tool's contract" until it warms up).

## Known issues
| Symptom | Cause | Fix |
|---|---|---|
| Portal "Failed to fetch" on My drafts | Portal address missing from `PORTAL_ORIGIN` | Set `PORTAL_ORIGIN=http://localhost:5173,<portal URL>` |
| `421 Misdirected Request` | Host not in `ALLOWED_HOSTS` | Add the host name |
| "Connector information unavailable" for a new user | Connector not shared / no connection | Share connector with `IEA-AllStaff`; user creates connection |
| GitHub login `AADSTS700213` | Federated credential subject mismatch | Use the subject printed by `azure/login` (includes owner/repo IDs) |
