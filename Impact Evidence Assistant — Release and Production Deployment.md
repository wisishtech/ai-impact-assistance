# Impact Evidence Assistant — Release and Production Deployment

This document takes the working build from the blueprint to a production service: it explains what each environment is and where it physically runs, gives the commands to create them, automates every deployment with GitHub Actions, gates releases on evaluation scores, and covers the pilot, monitoring, rollback and ownership.

## As built: how releases work today

One environment (dev) is live and every server release now goes through GitHub Actions with a quality gate, a health check and automatic rollback. Test and production environments, the pilot and the agent pipeline in later sections are still plans; each section below starts with a note on its status.

**What runs where**

| Part | Where | How it is released |
| --- | --- | --- |
| MCP server 0.1.4 | Azure Container Apps ca-iea-mcp-dev, East US, single-revision mode | Release MCP server workflow (manual, version number as input) |
| Web portal | Azure Static Web Apps swa-iea-dev (Free), East US 2 | Deploy portal workflow on every push to portal/ |
| Copilot Studio agent and approval flow | Power Platform IEA-Sandbox, solution Impact Evidence Assistant | Published in Copilot Studio; solution exported to agent/solution with pac |
| Search index and documents | Azure AI Search srch-iea-dev, index iea-chunks-v1 | Ingestion scripts run by hand |
| Azure resources | rg-iea-dev | infra/main.bicep; what-if compared against dev by a workflow |

**Workflows in .github/workflows/**

| Workflow | Trigger | What it does |
| --- | --- | --- |
| CI (ci.yml) | Every push and pull request | Server unit tests; eval freshness and threshold checks; portal type-check and build; Bicep compile |
| Release MCP server (release-server.yml) | Manual, version input | Gate (tests + eval checks), build image in ACR, deploy a new revision, check /healthz for up to 5 minutes, roll back to the previous image if it fails |
| Deploy portal (portal.yml) | Push to portal/ | npm ci, build, upload to Static Web Apps with the deployment token secret |
| Infra what-if (dev) (infra-whatif.yml) | Manual and pull requests touching infra/ | Shows what Bicep would change in rg-iea-dev; changes nothing |

**Release gates as implemented**

| Check | Rule | Latest |
| --- | --- | --- |
| Restricted documents leaked to an all-staff user | 0 | 0 |
| Expected document in top 5 | at least 0.85 | 1.00 |
| Reviewer finds restricted documents | at least 0.85 | 1.00 |
| Groundedness (1 to 5) | at least 4.0 | 5.0 |
| Correctness | at least 0.75 | 1.00 |
| Out-of-scope questions refused | at least 0.90 | 1.00 |
| Eval results match current code | fingerprint of instructions, test set, sources.csv and server code must match | match |

The eval itself runs on a workstation, because it signs in as two real test users; CI checks the committed eval/results/summary.json.

**GitHub to Azure sign-in (OIDC, no stored passwords)**

1. App registration iea-github-deploy with Contributor on rg-iea-dev.
2. Role Based Access Control Administrator on rg-iea-dev with a condition that allows assigning only AcrPull, Search Index Data Reader and Cognitive Services OpenAI User (needed for Bicep what-if).
3. Federated credentials whose subject includes the owner and repository IDs, as GitHub now sends them: repo:wisishtech@154911146/ai-impact-assistance@1466938759:ref:refs/heads/main, and the same with :pull\_request.
4. Repository variables (not secrets): AZURE\_CLIENT\_ID, AZURE\_TENANT\_ID, AZURE\_SUBSCRIPTION\_ID.

**Release a new server version**

1. Change code; run uv run --env-file .env pytest -q.
2. If instructions, test set, sources or server code changed, run uv run python eval/run\_eval.py and commit eval/results/summary.json.
3. Push to main and wait for CI to pass.
4. GitHub, Actions, Release MCP server, Run workflow, enter the version (for example 0.1.5).
5. Check the run ends with healthy; otherwise the workflow has already rolled back.

**Still planned**

- [ ] Test and production environments (resource groups, Power Platform environments, GitHub environments with approvals), created from infra/main.bicep
- [ ] Pipeline for the Copilot Studio solution (pac solution import into test and production)
- [ ] Pilot with 4 to 6 staff and a go / revise / stop decision
- [ ] Azure Monitor alerts and a workbook dashboard
- [ ] Scheduled weekly eval

## Release path

&#91;embedded content: release path · 4 stages, 3 gates\]

Every release follows this path; any stage can roll back to the previous good release in under 15 minutes (see Operations runbook), and the full gate checklists are under Release gates.

## Environments: what they are and where they run

**Status:** only dev exists: Azure rg-iea-dev (East US), Power Platform IEA-Sandbox (Sandbox, pay-as-you-go; the Developer environment ran out of credits and cannot use pay-as-you-go). Test and production are still to be created with the commands below.

An "environment" is a complete, separate copy of the system: its own Azure resources, its own Copilot Studio agent, its own app registrations and its own data. You run three so that experiments in dev can never break what pilot users or production users rely on.

**Each environment is made of four parts, each created in a different place.**

| Part | What it is | Created where | Created by |
| --- | --- | --- | --- |
| Azure resource group | Search, OpenAI, Container App, Key Vault, logs, Static Web App | Your Azure subscription (Azure portal / `az` / `azd`) | `azd provision` from Bicep |
| Power Platform environment | Holds the Copilot Studio agent and the Power Automate flow | Power Platform admin center in your Microsoft 365 tenant | `pac admin create` |
| Entra app registrations | `iea-mcp-api-<env>`, `iea-copilot-client-<env>`, `iea-agent-auth-<env>`, `iea-webchat-<env>` | Microsoft Entra ID (same tenant) | `scripts/setup_entra.sh <env>` |
| GitHub environment | Holds the deployment identity, variables and approval rules for that environment | GitHub repo → Settings → Environments | `gh api` |

SharePoint is shared: one `IEA Knowledge` site holds the documents; dev and test can point at a copy site (`iea-knowledge-test`) if you need to change content without affecting production.

**The three environments.**

|  | Dev | Test | Production |
| --- | --- | --- | --- |
| Purpose | Building and debugging | Automated evaluation, user acceptance, pilot | Live use by staff |
| Azure resource group | `rg-iea-dev` | `rg-iea-test` | `rg-iea-prod` |
| Azure region | East US 2 | East US 2 | East US 2 |
| MCP server URL | `ca-iea-mcp-dev.<region>.azurecontainerapps.io/mcp` | `ca-iea-mcp-test…` | `ca-iea-mcp-prod…` (or a custom domain) |
| Power Platform environment | `IEA-Dev` (Developer type) | `IEA-Test` (Sandbox type) | `IEA-Prod` (Production type) |
| Agent installed as | Unmanaged solution (editable) | Managed solution | Managed solution |
| Search tier / replicas | Basic / 1 | Basic / 1 | Basic / 2 (availability) |
| Container Apps min replicas | 0 (scale to zero) | 0 | 1 (no cold start) |
| Who can use it | You | You, testers, pilot users | Approved staff groups |
| Deployed by | You, from your laptop or on push | GitHub Actions on merge to `main` | GitHub Actions after a named approver clicks Approve |

**Create the cloud side of each environment**

```bash
# Azure: one azd environment per stage; Bicep creates the resource group and everything in it
azd env new iea-test  && azd env set AZURE_LOCATION eastus2 && azd provision -e iea-test
azd env new iea-prod  && azd env set AZURE_LOCATION eastus2 && azd provision -e iea-prod

# Power Platform: environments for the agent
pac admin create --name "IEA-Test" --type Sandbox    --region unitedstates
pac admin create --name "IEA-Prod" --type Production --region unitedstates
pac env list

# Entra: app registrations per environment (same commands as the blueprint, with a suffix)
bash scripts/setup_entra.sh test
bash scripts/setup_entra.sh prod
```

**Rules.** Nothing in test or production is changed by hand; every change goes through a pull request and the pipeline. Each environment has its own app registrations and secrets, so a dev credential can never reach production data.

## Infrastructure as code

**As built:** azd was not used. infra/main.bicep defines every Azure resource for one environment (Search, AI, storage, registry, Key Vault, Log Analytics, App Insights, Container Apps, Static Web Apps, 3 role assignments), with infra/dev.bicepparam holding dev's existing names. It is checked by az bicep build in CI and compared with dev by the Infra what-if workflow. Bicep role-assignment names differ from those the CLI created in dev, so use it to create new environments, not to redeploy over dev.

The Azure CLI script in the blueprint is replaced here by Bicep templates, so test and production are created from the same files and any environment can be rebuilt in minutes. The Azure Developer CLI (`azd`) runs them.

**Files**

```
azure.yaml                     tells azd what to provision and what to deploy
infra/
├── main.bicep                 creates the resource group and calls each module
├── main.parameters.json       values azd fills from the environment (name, location)
└── modules/
    ├── search.bicep           Azure AI Search, semantic ranker, managed identity
    ├── openai.bicep           Azure OpenAI account + embedding and chat deployments
    ├── monitoring.bicep       Log Analytics, Application Insights, alert rules
    ├── registry.bicep         Container Registry
    ├── keyvault.bicep         Key Vault (RBAC mode)
    ├── containerapp.bicep     Container Apps environment + MCP server app
    ├── staticweb.bicep        Static Web App for the chat page
    └── roles.bicep            least-privilege role assignments
```

**`azure.yaml`**

```yaml
name: impact-evidence-assistant
services:
  mcp:
    project: .
    language: python
    host: containerapp
    docker:
      path: mcp_server/Dockerfile
      context: .
  web:
    project: web/public
    host: staticwebapp
```

**`infra/main.bicep` (core)**

```bicep
targetScope = 'subscription'
param environmentName string          // dev | test | prod (from azd)
param location string = 'eastus2'
param searchReplicas int = environmentName == 'prod' ? 2 : 1
param minReplicas int = environmentName == 'prod' ? 1 : 0
var tags = { 'azd-env-name': environmentName, project: 'iea' }
var token = uniqueString(subscription().id, environmentName)

resource rg 'Microsoft.Resources/resourceGroups@2024-03-01' = {
  name: 'rg-iea-${environmentName}', location: location, tags: tags }

module monitoring 'modules/monitoring.bicep' = { scope: rg, name: 'monitoring', params: { location: location, name: 'iea-${environmentName}' } }
module search 'modules/search.bicep' = { scope: rg, name: 'search', params: { location: location, name: 'srch-iea-${environmentName}', replicas: searchReplicas } }
module openai 'modules/openai.bicep' = { scope: rg, name: 'openai', params: { location: location, name: 'aif-iea-${environmentName}' } }
module registry 'modules/registry.bicep' = { scope: rg, name: 'registry', params: { location: location, name: 'acriea${token}' } }
module kv 'modules/keyvault.bicep' = { scope: rg, name: 'kv', params: { location: location, name: 'kv-iea-${take(token, 8)}' } }
module app 'modules/containerapp.bicep' = {
  scope: rg, name: 'app'
  params: {
    location: location, name: 'ca-iea-mcp-${environmentName}', minReplicas: minReplicas
    registryServer: registry.outputs.loginServer, logAnalyticsId: monitoring.outputs.workspaceId
    appInsightsConnection: monitoring.outputs.connectionString
    searchEndpoint: search.outputs.endpoint, searchIndex: 'iea-chunks-v1'
  }
}
module roles 'modules/roles.bicep' = { scope: rg, name: 'roles', params: {
  appPrincipalId: app.outputs.principalId, searchName: search.outputs.name, openaiPrincipal: search.outputs.principalId,
  openaiName: openai.outputs.name, registryName: registry.outputs.name, keyVaultName: kv.outputs.name } }
module web 'modules/staticweb.bicep' = { scope: rg, name: 'web', params: { name: 'swa-iea-${environmentName}' } }

output MCP_URL string = 'https://${app.outputs.fqdn}/mcp'
output SEARCH_ENDPOINT string = search.outputs.endpoint
output AZURE_CONTAINER_REGISTRY_ENDPOINT string = registry.outputs.loginServer
```

**`infra/modules/containerapp.bicep` (key settings)**

```bicep
resource app 'Microsoft.App/containerApps@2024-03-01' = {
  name: name
  location: location
  tags: { 'azd-service-name': 'mcp' }        // azd deploys the image here
  identity: { type: 'SystemAssigned' }
  properties: {
    managedEnvironmentId: env.id
    configuration: {
      activeRevisionsMode: 'Multiple'          // keeps old revisions for instant rollback
      ingress: { external: true, targetPort: 8000, transport: 'auto' }
      registries: [ { server: registryServer, identity: 'system' } ]
    }
    template: {
      containers: [ { name: 'mcp', image: 'mcr.microsoft.com/k8se/quickstart:latest'   // replaced on deploy
        resources: { cpu: json('0.5'), memory: '1Gi' }
        env: [ { name: 'SEARCH_ENDPOINT', value: searchEndpoint }, { name: 'SEARCH_INDEX', value: searchIndex }
               { name: 'APPLICATIONINSIGHTS_CONNECTION_STRING', value: appInsightsConnection } ]
        probes: [ { type: 'Liveness', httpGet: { path: '/healthz', port: 8000 } } ] } ]
      scale: { minReplicas: minReplicas, maxReplicas: 5 }
    }
  }
}
output principalId string = app.identity.principalId
output fqdn string = app.properties.configuration.ingress.fqdn
```

**Role assignments in `roles.bicep`**

| Identity | Role | Scope | Why |
| --- | --- | --- | --- |
| MCP server | Search Index Data Reader | Search service | Query only; cannot change the index |
| MCP server | AcrPull | Container Registry | Pull its image |
| MCP server | Key Vault Secrets User | Key Vault | Read settings stored as secrets |
| Search service | Cognitive Services OpenAI User | OpenAI account | Vectorize queries |
| GitHub deploy identity | Contributor + User Access Administrator (conditions: only the roles above) | Resource group | Deploy and assign the roles above |
| GitHub ingestion identity | Search Index Data Contributor, Search Service Contributor | Search service | Build new index versions |

Microsoft Graph `Sites.Selected` for the server and the SharePoint site grant cannot be set in Bicep; `scripts/grant_graph.sh <env>` runs the commands from the blueprint after each new environment is created.

**Commands**

```bash
azd init --environment iea-dev          # once, in the repo root (uses azure.yaml)
azd provision -e iea-dev                # create or update all Azure resources
azd deploy mcp -e iea-dev               # build the image, push it, roll out a new revision
azd deploy web -e iea-dev               # publish the chat page
azd env get-values -e iea-dev           # outputs, e.g. MCP_URL, for .env and pipelines
az deployment sub what-if --location eastus2 --template-file infra/main.bicep \
  --parameters environmentName=prod     # preview changes before production
```

## CI/CD pipelines

**As built:** the workflows in use are ci.yml, release-server.yml, portal.yml and infra-whatif.yml (see As built at the top). The federated credential subject must include owner and repository IDs; the name-only subject in the commands below fails with AADSTS700213. Variables go in the Variables tab, not Secrets. agent.yml is not built yet.

GitHub Actions builds, tests, evaluates and deploys everything; you never deploy to test or production from a laptop. Three things ship (the MCP server, the search index, the Copilot Studio agent), and all of them pass the same evaluation gate.

**1. Connect GitHub to Azure without secrets (OpenID Connect), once per environment**

```bash
ENV=test; REPO=<github-user>/impact-evidence-assistant
RG_ID=$(az group show -n rg-iea-$ENV --query id -o tsv)

DEPLOY=$(az ad app create --display-name gh-iea-deploy-$ENV --query appId -o tsv)
az ad sp create --id $DEPLOY
az ad app federated-credential create --id $DEPLOY --parameters "{
  \"name\": \"gh-$ENV\", \"issuer\": \"https://token.actions.githubusercontent.com\",
  \"subject\": \"repo:$REPO:environment:$ENV\", \"audiences\": [\"api://AzureADTokenExchange\"]}"
az role assignment create --assignee $DEPLOY --role Contributor --scope $RG_ID
az role assignment create --assignee $DEPLOY --role "User Access Administrator" --scope $RG_ID
az role assignment create --assignee $DEPLOY --role "Search Index Data Contributor" \
  --scope $(az search service show -n srch-iea-$ENV -g rg-iea-$ENV --query id -o tsv)
```

**2. Create GitHub environments, approval rules and variables**

```bash
for ENV in dev test prod; do gh api -X PUT repos/$REPO/environments/$ENV; done
# Production needs a named reviewer (your GitHub user ID: gh api user --jq .id)
gh api -X PUT repos/$REPO/environments/prod \
  -F "reviewers[][type]=User" -F "reviewers[][id]=<your user id>"

gh variable set AZURE_CLIENT_ID       --env test --body $DEPLOY
gh variable set AZURE_TENANT_ID       --env test --body <tenant id>
gh variable set AZURE_SUBSCRIPTION_ID --env test --body <subscription id>
gh variable set AZURE_ENV_NAME        --env test --body iea-test
gh variable set POWERPLATFORM_URL     --env test --body <IEA-Test environment URL>
gh secret   set EVAL_USER_TOKEN_CACHE --env test < eval/.token_cache.json   # cached tokens for eval test users
```

**3. Workflows (`.github/workflows/`)**

| Workflow | Runs when | What it does |
| --- | --- | --- |
| `ci.yml` | Every pull request | Lint, unit and permission tests, Bicep build, container build |
| `deploy.yml` | Merge to `main` (test); release tag `v*` (prod, after approval) | Provision, deploy server and web page, rebuild index if data changed, run evaluation, enforce thresholds |
| `agent.yml` | Release tag `v*` | Import the agent solution as managed into IEA-Test, then IEA-Prod after approval |
| `nightly-eval.yml` | Every Monday 06:00 UTC | Runs the evaluation against production and posts the scores |

**`ci.yml`**

```yaml
name: ci
on: [pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v5
      - run: uv sync --frozen
      - run: uv run ruff check .
      - run: uv run pytest -q mcp_server/tests
      - run: az bicep build --file infra/main.bicep
      - run: docker build -f mcp_server/Dockerfile -t iea-mcp:ci .
```

**`deploy.yml`**

```yaml
name: deploy
on:
  push: { branches: [main] }
  release: { types: [published] }
permissions: { id-token: write, contents: read }
jobs:
  deploy:
    runs-on: ubuntu-latest
    environment: ${{ github.event_name == 'release' && 'prod' || 'test' }}   # prod waits for approval
    env:
      AZURE_CLIENT_ID: ${{ vars.AZURE_CLIENT_ID }}
      AZURE_TENANT_ID: ${{ vars.AZURE_TENANT_ID }}
      AZURE_SUBSCRIPTION_ID: ${{ vars.AZURE_SUBSCRIPTION_ID }}
      AZURE_ENV_NAME: ${{ vars.AZURE_ENV_NAME }}
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v5
      - uses: Azure/setup-azd@v2
      - uses: azure/login@v2
        with: { client-id: ${{ env.AZURE_CLIENT_ID }}, tenant-id: ${{ env.AZURE_TENANT_ID }}, subscription-id: ${{ env.AZURE_SUBSCRIPTION_ID }} }
      - run: azd auth login --client-id $AZURE_CLIENT_ID --federated-credential-provider github --tenant-id $AZURE_TENANT_ID
      - run: azd provision --no-prompt
      - run: azd deploy --no-prompt
      - name: Rebuild index if content changed
        run: |
          if git diff --name-only HEAD~1 | grep -qE '^(data/|ingestion/)'; then
            NEW=iea-chunks-$(date +%Y%m%d%H%M)
            uv run python -m ingestion.build_chunks
            uv run python -m ingestion.create_index $NEW
            SEARCH_INDEX=$NEW uv run python -m ingestion.embed_and_upload
            echo "CANDIDATE_INDEX=$NEW" >> $GITHUB_ENV
          fi
      - name: Evaluate
        run: |
          eval "$(azd env get-values)"
          uv run python eval/run_eval.py eval/results/${{ github.sha }}.csv
          uv run python eval/check_thresholds.py eval/results/${{ github.sha }}.csv
      - name: Promote new index
        if: env.CANDIDATE_INDEX != ''
        run: az containerapp update -n ca-iea-mcp-${AZURE_ENV_NAME#iea-} -g rg-${AZURE_ENV_NAME} --set-env-vars SEARCH_INDEX=$CANDIDATE_INDEX
      - uses: actions/upload-artifact@v4
        with: { name: eval-${{ github.sha }}, path: eval/results/ }
```

The evaluation runs before the new index is promoted, so a worse index never goes live. For the candidate index to be evaluated, `run_eval.py` accepts an index override that the MCP server reads from a test-only header in non-production environments; leave this off in production.

**`agent.yml` (Copilot Studio agent)**

```yaml
name: agent
on: { release: { types: [published] } }
jobs:
  import:
    strategy: { max-parallel: 1, matrix: { env: [test, prod] } }
    runs-on: ubuntu-latest
    environment: ${{ matrix.env }}
    steps:
      - uses: actions/checkout@v4
      - uses: microsoft/powerplatform-actions/actions-install@v1
      - uses: microsoft/powerplatform-actions/pack-solution@v1
        with: { solution-folder: agent/solution, solution-file: out/iea_managed.zip, solution-type: Managed }
      - uses: microsoft/powerplatform-actions/import-solution@v1
        with:
          environment-url: ${{ vars.POWERPLATFORM_URL }}
          app-id: ${{ vars.PP_APP_ID }}
          client-secret: ${{ secrets.PP_CLIENT_SECRET }}
          tenant-id: ${{ vars.AZURE_TENANT_ID }}
          solution-file: out/iea_managed.zip
          use-deployment-settings-file: true
          deployment-settings-file: agent/settings.${{ matrix.env }}.json
```

`agent/settings.<env>.json` holds the environment variables (MCP server URL) and connection references for that environment, so one solution file works everywhere. `PP_APP_ID` is an app registration added as an application user in each Power Platform environment (`pac admin assign-user` or the admin center); after importing, publish the agent once and re-enter the OAuth connection for the MCP tool in that environment.

**Index releases (blue/green).** Every content change creates a new versioned index; the server's `SEARCH_INDEX` setting decides which one is live. Promotion and rollback are a one-line setting change. Keep the previous index for 14 days.

## Release gates

**As built:** Gate 1 is automated (eval/check\_thresholds.py and eval/check\_fresh.py in CI and in the release workflow; thresholds in the As built table at the top). Gates 2 and 3 need the test environment and the pilot, which are not built yet.

A release moves forward only when every item for its stage is ticked; any unticked item is a no-go.

**Gate 1 — Dev to test**

- [ ] Unit and integration tests pass, including the zero-leak permission test
- [ ] Bicep `what-if` reviewed; no unexpected deletions
- [ ] No secrets in code; dependency scan has no critical findings
- [ ] Decision notes and CHANGELOG updated

**Gate 2 — Test to pilot**

- [ ] Evaluation thresholds met: accuracy 85%+, citations 90%+, ungrounded under 5%, refusals 90%+, leaks 0
- [ ] Prompt-injection and expired-token tests pass
- [ ] Usability test done with 3–5 people; blocking issues fixed
- [ ] Responsible AI card and runbook reviewed by the business owner
- [ ] Privacy and security review signed off by IT
- [ ] Pilot users briefed; feedback channel open

**Gate 3 — Pilot to production**

- [ ] Pilot success measures met (see Pilot plan)
- [ ] No open severity-1 or severity-2 incidents
- [ ] Monitoring alerts tested by firing each once
- [ ] Rollback rehearsed in test, under 15 minutes
- [ ] Named business owner, technical owner and support contact recorded
- [ ] Cost at pilot volume within the approved budget
- [ ] Go decision recorded in `docs/decisions/` with who approved it

## Pilot plan

**Status:** not started. End-to-end tests so far used three test accounts (program.officer, restricted.reviewer, admin) in Teams, Microsoft 365 Copilot, the portal and the command-line agent.

A short pilot with 10–15 real users, run in the test environment, decides go, revise or stop, using measures agreed before it starts. It ends when the measures below have enough data, not on a fixed date.

**Users.** 4–6 program officers, 3–4 M&E staff, 2–3 communications staff, and 2 reviewers for the approval flow. Include at least one French- or Arabic-speaking user.

For the portfolio version, run the same pilot with 5–8 volunteer peers as guest users in the test tenant, and say so in the write-up.

**Schedule.**

1. **Start:** 30-minute onboarding; each user completes five set tasks; check logs daily
2. **Use:** normal work on real questions; short feedback call after each batch of fixes
3. **Close:** survey, interviews with 3 users, final evaluation run, go/revise/stop memo

**Measures.**

| Measure | Source | Go threshold |
| --- | --- | --- |
| Weekly active users | App Insights | 70%+ of pilot users each week |
| Answers rated helpful | Thumbs up/down in Teams | 75%+ |
| Drafts approved without major edits | Draft Reviews list | 60%+ |
| Time to draft a progress section | Timed tasks vs. baseline | At least 50% faster |
| Accuracy on the fixed test set | Final eval run | No drop from pre-pilot |
| Permission leaks or data incidents | Logs, user reports | 0 |
| Cost per active user per month | Azure Cost Management | Within agreed budget |

**Feedback loop.** Every thumbs-down and comment goes to a GitHub issue labelled `pilot-feedback`. Fix weekly; release fixes through the normal pipeline, never by hand.

**Decision.** The memo recommends **go** (all thresholds met), **revise** (fixable gaps; extend 2 weeks), or **stop** (value not shown). Stopping is a valid, documented outcome.

## Monitoring and alerts

**As built:** tool calls are traced to App Insights appi-iea-dev. Usage queries (calls per day, users per week, searches with no results) are in docs/sustained-use.md. Alerts, the dashboard and the scheduled eval are not set up yet.

The MCP server sends OpenTelemetry traces to Application Insights (`azure-monitor-opentelemetry`), so every tool call, its latency and its outcome can be queried and alerted on.

**What each tool call logs.** Hashed user ID, tool name, filters used, number of hits, top document IDs, latency, token counts, error code. Never the full question, answer or document text.

**Dashboard (Azure Workbook).** Calls per day, active users, p50/p95 latency, error rate, "not found" rate, cost per day, helpful-rating rate.

**Alerts.**

| Alert | Condition | Severity | Action |
| --- | --- | --- | --- |
| Server down | Health probe fails 3 times in 5 minutes | Sev 1 | Email + Teams to technical owner |
| Auth failures spike | 401/403 rate above 10% for 15 minutes | Sev 2 | Check app registration, token config |
| Possible leak | Restricted doc ID returned to a user outside `IEA-Restricted` (log query) | Sev 1 | Disable agent; investigate |
| Slow answers | p95 tool latency above 8 seconds for 30 minutes | Sev 3 | Check search and model throttling |
| "Not found" spike | Rate doubles vs. 7-day average | Sev 3 | Check index health and recent content changes |
| Spend | Daily cost above 150% of forecast | Sev 2 | Review usage; check for loops |
| Quality drift | Weekly scheduled eval drops 5+ points on any metric | Sev 2 | Open issue; compare with last good run |

**Scheduled evaluation.** A GitHub Actions cron job runs the 50-question test set against production every Monday and posts the scores, so quality drift is caught even when nobody complains.

## Operations runbook

**As built:** docs/runbook.md is written from the live system (health check, release, rollback, kill switch with MAINTENANCE\_MODE, access, secret rotation, known issues). docs/operations-log.md records each release and fix.

The runbook (`docs/runbook.md`) lets someone other than the builder keep the assistant running; each procedure below has numbered steps there.

**Incident severity.**

| Severity | Example | Response time | First step |
| --- | --- | --- | --- |
| Sev 1 | Possible data leak; service down | 1 hour | Disable the agent in Copilot Studio (unpublish) |
| Sev 2 | Wrong answers spreading; auth failing for many users | 1 business day | Roll back to last good release |
| Sev 3 | Slow answers; one bad document | 1 week | Open an issue; fix in next release |

**Rollback (target: under 15 minutes).**

1. MCP server: in Container Apps, shift 100% of traffic to the previous revision (set multiple-revision mode in containerapp.bicep so old revisions are kept and this is one command).
2. Index: set the index-name setting back to the previous version.
3. Agent: re-import the previous managed solution version from the GitHub release.
4. Confirm with the smoke test; record the incident and cause.

**Kill switch.** Unpublishing the agent stops all user access immediately. Setting the server's `MAINTENANCE_MODE=true` makes every tool return a polite "temporarily unavailable" message.

**Content refresh (monthly).**

1. Content owner adds or retires documents in SharePoint and updates `sources.csv` through a pull request.
2. The pipeline builds a new index version, runs evaluation, and promotes it only if scores hold.
3. Retired documents disappear when the new index goes live; the old index is kept 14 days.

**Routine tasks.**

- Weekly: review the Monday eval scores and pilot feedback issues
- Monthly: content refresh; review costs; rotate the client secret if not using certificates
- Quarterly: access review of Entra groups; review the responsible AI card; check for model version retirements and test the replacement model before the deadline
- After any model or prompt change: full evaluation before release

## Cost management

**As built:** a $50 budget alert covers rg-iea-dev. Copilot Studio usage is billed to Azure through the IEADevelopment billing plan. The container app runs one replica (min 1, max 3) in single-revision mode, after old active revisions were found each keeping a paid replica running. The cost sheet is not written yet.

Cost is tracked per environment from day one, and the cost sheet turns real pilot usage into a monthly forecast before anyone approves production.

**Cost drivers.**

| Item | Type | How to control it |
| --- | --- | --- |
| Azure AI Search Basic | Fixed monthly, per replica | One replica outside production; delete dev between sessions |
| Semantic ranker | Per 1,000 requests after the free 1,000 a month | Cap `top`; skip semantic for simple filter queries |
| Chat and embedding tokens | Per token | Small model; short passages; cap answer length |
| Container Apps | Per second of use | Scale to zero in dev and test |
| Copilot Studio | Licensing or per-message capacity | Confirm IREX's license model with IT before production |
| Log Analytics | Per GB ingested | Log counts and IDs, not text; 30-day retention |

**Cost sheet (`docs/cost-sheet.md`).** Measured cost per question and per draft from the eval and pilot, then a forecast for 50 and 500 users at observed usage. Fill the prices from the Azure pricing calculator on the day you write it, and date the sheet.

**Guardrails.** Azure budget with alerts at 50%, 80% and 100%; per-user rate limit in the MCP server (for example 60 tool calls an hour); daily spend alert from the monitoring section.

## Ownership, governance and retirement

No release reaches production without named owners, and the assistant has written conditions for when it should be changed or switched off.

**Roles.**

| Role | Who | Responsible for |
| --- | --- | --- |
| Business owner | Head of M&E (or delegate) | Value, go/no-go, approving content scope |
| Technical owner | Applied AI specialist | Pipelines, releases, incidents, evaluation |
| Content owner | Knowledge manager | Which documents are in, metadata, monthly refresh |
| Reviewers | `IEA-Reviewers` group | Approving drafts |
| IT security | IT team | Access reviews, app registrations, security sign-off |

**Change control.** Any change to the model, prompt, tools, data scope or permissions is a release: pull request, evaluation, gate, release notes. A change that widens data access or adds a tool that writes data needs the business owner's and IT security's approval.

**Retirement.** Retire or redesign the assistant if any of these holds for two consecutive months: usage below 30% of the target group, helpful rating below 60%, a repeated leak or serious incident, or a cheaper approach that meets the need. Retirement steps: announce 30 days ahead, unpublish the agent, export logs and the final evaluation, delete the index and app registrations, archive the repo with a closing note.

## Versioning and release notes

**As built:** server images are versioned 0.1.0 to 0.1.4 (0.1.3: readable citations and multi-origin CORS; 0.1.4: first release through GitHub Actions). Revision names follow the version, for example v0-1-4-1.

One version number covers the server image, index version and agent solution together, so any release can be traced and rebuilt.

**Scheme.** Semantic versioning: `MAJOR.MINOR.PATCH`.

- **Major:** new tool, data scope or permission model change
- **Minor:** prompt, model, chunking or new documents
- **Patch:** bug fixes with no behavior change

**Planned releases.**

| Version | Contents | Goes to |
| --- | --- | --- |
| v0.1 | Q&A with citations, security filters | Dev |
| v0.2 | Indicator tool, drafter, approval flow | Dev |
| v0.3 | Evaluation thresholds met after improvement loops | Test |
| v0.9 | Pilot release | Test (pilot users) |
| v1.0 | Production release after Gate 3 | Production |

**Release notes template (GitHub release).**

```markdown
## v0.9.0 — 2027-01-15
What changed: section-based chunking; French test questions added
Evaluation: accuracy 87% (+6), citations 92% (+3), ungrounded 3%, leaks 0
Cost: $0.021 per question (was $0.027)
Known limits: Arabic accuracy 71%; tables in PDFs often missed
Image digest: sha256:…   Index: iea-chunks-v5   Agent solution: 0.9.0
Approved by: <business owner>, <date>
Rollback: previous release v0.8.2
```

The numbers in the template are illustrative; every real release fills them from its own evaluation run.

## Sources

- [Azure Developer CLI overview (Microsoft Learn)](https://learn.microsoft.com/azure/developer/azure-developer-cli/overview)
- [Publish and deploy your agent: channels (Microsoft Learn)](https://learn.microsoft.com/en-gb/microsoft-Copilot-studio/publication-fundamentals-publish-channels)
- [Configure user authentication in Copilot Studio (Microsoft Learn)](https://learn.microsoft.com/microsoft-copilot-studio/configuration-end-user-authentication)
- [Connect your agent to an existing MCP server (Microsoft Learn)](https://learn.microsoft.com/microsoft-copilot-studio/mcp-add-existing-server-to-agent)
- [Azure AI Search pricing](https://azure.microsoft.com/en-us/pricing/details/search/)

Pipelines, Bicep and commands are written against current tool versions but have not been run end to end; check action and API versions when you first run them.
