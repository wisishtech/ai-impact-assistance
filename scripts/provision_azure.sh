#!/usr/bin/env bash
# Provision Azure resources for the Impact Evidence Assistant.
# Run in Git Bash:  bash scripts/provision_azure.sh [dev|test|prod]
# Safe to re-run: anything that already exists is skipped.
set -euo pipefail
export MSYS_NO_PATHCONV=1          # stop Git Bash turning /subscriptions/... into C:/Program Files/Git/...

# ---------- Settings ----------
ENV=${1:-dev}
LOC=${LOC:-eastus}
RG=rg-iea-$ENV
SRCH=srch-iea-$ENV
AOAI=aif-iea-$ENV
LAW=log-iea-$ENV
APPI=appi-iea-$ENV
CAE=cae-iea-$ENV

# Globally unique names. Dev already exists with these names; other environments get a stable suffix.
SUB=$(az account show --query id -o tsv)
SUFFIX=$(echo -n "$SUB-$ENV" | md5sum | cut -c1-5)
if [ "$ENV" = "dev" ]; then
  ST=${ST:-stieadev5954}
  ACR=${ACR:-acrieadev9498}
  KV=${KV:-kv-iea-dev-25551}
else
  ST=${ST:-stiea${ENV}${SUFFIX}}
  ACR=${ACR:-acriea${ENV}${SUFFIX}}
  KV=${KV:-kv-iea-${ENV}-${SUFFIX}}
fi

ME=$(az ad signed-in-user show --query id -o tsv)
exists() { az resource show -g "$RG" -n "$1" --resource-type "$2" -o none 2>/dev/null; }
step() { echo; echo "==> $*"; }

# ---------- 1. Resource group ----------
step "Resource group $RG ($LOC)"
az group create -n "$RG" -l "$LOC" -o none

# ---------- 2. Azure AI Search ----------
step "Azure AI Search $SRCH"
if exists "$SRCH" Microsoft.Search/searchServices; then echo "exists, skipping"; else
  az search service create -n "$SRCH" -g "$RG" -l "$LOC" --sku basic \
    --semantic-search free --auth-options aadOrApiKey \
    --aad-auth-failure-mode http401WithBearerChallenge --identity-type SystemAssigned -o none
fi

# ---------- 3. Azure OpenAI + models ----------
step "Azure OpenAI $AOAI"
if exists "$AOAI" Microsoft.CognitiveServices/accounts; then echo "exists, skipping"; else
  az cognitiveservices account create -n "$AOAI" -g "$RG" -l "$LOC" \
    --kind OpenAI --sku S0 --custom-domain "$AOAI" -o none
fi

deploy_model() {  # name version sku
  if az cognitiveservices account deployment show -n "$AOAI" -g "$RG" --deployment-name "$1" -o none 2>/dev/null; then
    echo "model $1 exists, skipping"
  else
    az cognitiveservices account deployment create -n "$AOAI" -g "$RG" \
      --deployment-name "$1" --model-name "$1" --model-version "$2" \
      --model-format OpenAI --sku-name "$3" --sku-capacity 50 -o none
  fi
}
deploy_model text-embedding-3-small 1 Standard
deploy_model gpt-4.1-mini 2025-04-14 GlobalStandard

# ---------- 4. Storage, registry, Key Vault ----------
step "Storage $ST"
if exists "$ST" Microsoft.Storage/storageAccounts; then echo "exists, skipping"; else
  az storage account create -n "$ST" -g "$RG" -l "$LOC" --sku Standard_LRS \
    --allow-blob-public-access false --min-tls-version TLS1_2 -o none
fi

step "Container registry $ACR"
if exists "$ACR" Microsoft.ContainerRegistry/registries; then echo "exists, skipping"; else
  az acr create -n "$ACR" -g "$RG" --sku Basic -o none
fi

step "Key Vault $KV"
if exists "$KV" Microsoft.KeyVault/vaults; then echo "exists, skipping"; else
  az keyvault create -n "$KV" -g "$RG" -l "$LOC" --enable-rbac-authorization true -o none
fi

# ---------- 5. Monitoring ----------
step "Log Analytics $LAW"
if exists "$LAW" Microsoft.OperationalInsights/workspaces; then echo "exists, skipping"; else
  az monitor log-analytics workspace create -n "$LAW" -g "$RG" -l "$LOC" -o none
fi
LAW_ID=$(az monitor log-analytics workspace show -n "$LAW" -g "$RG" --query id -o tsv)

step "Application Insights $APPI"
if exists "$APPI" Microsoft.Insights/components; then echo "exists, skipping"; else
  az monitor app-insights component create --app "$APPI" -g "$RG" -l "$LOC" --workspace "$LAW_ID" -o none
fi

# ---------- 6. Container Apps environment ----------
step "Container Apps environment $CAE"
if exists "$CAE" Microsoft.App/managedEnvironments; then echo "exists, skipping"; else
  az containerapp env create -n "$CAE" -g "$RG" -l "$LOC" \
    --logs-workspace-id "$(az monitor log-analytics workspace show -n "$LAW" -g "$RG" --query customerId -o tsv)" \
    --logs-workspace-key "$(az monitor log-analytics workspace get-shared-keys -n "$LAW" -g "$RG" --query primarySharedKey -o tsv)" \
    -o none
fi

# ---------- 7. Role assignments ----------
step "Role assignments"
SRCH_ID=$(az search service show -n "$SRCH" -g "$RG" --query id -o tsv)
AOAI_ID=$(az cognitiveservices account show -n "$AOAI" -g "$RG" --query id -o tsv)
KV_ID=$(az keyvault show -n "$KV" --query id -o tsv)
SRCH_MI=$(az search service show -n "$SRCH" -g "$RG" --query identity.principalId -o tsv)

assign() {  # principalId principalType role scope
  az role assignment create --assignee-object-id "$1" --assignee-principal-type "$2" \
    --role "$3" --scope "$4" -o none 2>/dev/null || echo "  ($3 already assigned)"
}
# You (the builder), so local scripts work without keys
assign "$ME" User "Search Service Contributor"     "$SRCH_ID"
assign "$ME" User "Search Index Data Contributor"  "$SRCH_ID"
assign "$ME" User "Cognitive Services OpenAI User" "$AOAI_ID"
assign "$ME" User "Key Vault Secrets Officer"      "$KV_ID"
# The search service, so it can vectorize queries with OpenAI
assign "$SRCH_MI" ServicePrincipal "Cognitive Services OpenAI User" "$AOAI_ID"

# ---------- 8. Summary for .env ----------
step "Done. Values for .env:"
cat <<EOF
AZURE_TENANT_ID=$(az account show --query tenantId -o tsv)
AZURE_SUBSCRIPTION_ID=$SUB
SEARCH_ENDPOINT=https://$SRCH.search.windows.net
SEARCH_INDEX=iea-chunks-v1
AOAI_ENDPOINT=https://$AOAI.openai.azure.com
AOAI_EMBED_DEPLOYMENT=text-embedding-3-small
AOAI_CHAT_DEPLOYMENT=gpt-4.1-mini
STORAGE_ACCOUNT=$ST
ACR_NAME=$ACR
KEY_VAULT=$KV
APPLICATIONINSIGHTS_CONNECTION_STRING=$(az monitor app-insights component show --app "$APPI" -g "$RG" --query connectionString -o tsv)
EOF

echo
echo "Budget: set it in the portal (Cost Management > Budgets); the CLI budget command is unreliable."