// Impact Evidence Assistant: Azure resources for one environment (dev / test / prod).
// Not in Bicep (tenant-level or Microsoft 365): Entra app registrations and groups,
// SharePoint site/lists, Graph Sites.Selected grant, Power Platform. See docs/decisions/0004.

targetScope = 'resourceGroup'

@description('Environment short name, e.g. dev, test, prod')
param env string = 'dev'
param location string = resourceGroup().location
@description('Static Web Apps Free is not offered in every region')
param swaLocation string = 'eastus2'

// Names default to a pattern; dev passes its existing names (see dev.bicepparam).
param searchName string = 'srch-iea-${env}'
param aiName string = 'aif-iea-${env}'
@allowed(['AIServices', 'OpenAI'])
param aiKind string = 'AIServices'
param storageName string = 'stiea${env}${uniqueString(resourceGroup().id)}'
param acrName string = 'acriea${env}${uniqueString(resourceGroup().id)}'
param keyVaultName string = 'kv-iea-${env}-${take(uniqueString(resourceGroup().id), 5)}'
param logName string = 'log-iea-${env}'
param appInsightsName string = 'appi-iea-${env}'
param containerEnvName string = 'cae-iea-${env}'
param containerAppName string = 'ca-iea-mcp-${env}'
param staticWebAppName string = 'swa-iea-${env}'

@description('Container image. First deploy of a new environment: leave the placeholder, then the release workflow pushes the real image.')
param image string = 'mcr.microsoft.com/k8se/quickstart:latest'

// App settings for the MCP server (non-secret IDs)
param tenantId string = tenant().tenantId
param mcpApiClientId string
param spSiteId string
param spResultsListId string
param spDraftsListId string
param portalOrigins string = 'http://localhost:5173'
param searchIndex string = 'iea-chunks-v1'
param embedDeployment string = 'text-embedding-3-small'
param chatDeployment string = 'gpt-4.1-mini'
param minReplicas int = 1

var tags = { app: 'impact-evidence-assistant', env: env }

// ---------- Monitoring ----------
resource log 'Microsoft.OperationalInsights/workspaces@2023-09-01' = {
  name: logName
  location: location
  tags: tags
  properties: { sku: { name: 'PerGB2018' }, retentionInDays: 30 }
}

resource appi 'Microsoft.Insights/components@2020-02-02' = {
  name: appInsightsName
  location: location
  tags: tags
  kind: 'web'
  properties: { Application_Type: 'web', WorkspaceResourceId: log.id }
}

// ---------- Data and AI ----------
resource storage 'Microsoft.Storage/storageAccounts@2023-05-01' = {
  name: storageName
  location: location
  tags: tags
  sku: { name: 'Standard_LRS' }
  kind: 'StorageV2'
  properties: { minimumTlsVersion: 'TLS1_2', allowBlobPublicAccess: false }
}

resource ai 'Microsoft.CognitiveServices/accounts@2024-10-01' = {
  name: aiName
  location: location
  tags: tags
  kind: aiKind
  sku: { name: 'S0' }
  identity: { type: 'SystemAssigned' }
  properties: { customSubDomainName: aiName, publicNetworkAccess: 'Enabled' }
}

resource embed 'Microsoft.CognitiveServices/accounts/deployments@2024-10-01' = {
  parent: ai
  name: embedDeployment
  sku: { name: 'Standard', capacity: 120 }
  properties: { model: { format: 'OpenAI', name: 'text-embedding-3-small', version: '1' } }
}

resource chat 'Microsoft.CognitiveServices/accounts/deployments@2024-10-01' = {
  parent: ai
  name: chatDeployment
  dependsOn: [embed] // deployments on one account must be created one at a time
  sku: { name: 'GlobalStandard', capacity: 50 }
  properties: { model: { format: 'OpenAI', name: 'gpt-4.1-mini', version: '2025-04-14' } }
}

resource search 'Microsoft.Search/searchServices@2023-11-01' = {
  name: searchName
  location: location
  tags: tags
  sku: { name: 'basic' }
  identity: { type: 'SystemAssigned' }
  properties: {
    replicaCount: 1
    partitionCount: 1
    semanticSearch: 'free'
    authOptions: { aadOrApiKey: { aadAuthFailureMode: 'http401WithBearerChallenge' } }
  }
}

resource kv 'Microsoft.KeyVault/vaults@2023-07-01' = {
  name: keyVaultName
  location: location
  tags: tags
  properties: {
    tenantId: tenantId
    sku: { family: 'A', name: 'standard' }
    enableRbacAuthorization: true
    enableSoftDelete: true
  }
}

// ---------- Hosting ----------
resource acr 'Microsoft.ContainerRegistry/registries@2023-07-01' = {
  name: acrName
  location: location
  tags: tags
  sku: { name: 'Basic' }
  properties: { adminUserEnabled: false }
}

resource cae 'Microsoft.App/managedEnvironments@2024-03-01' = {
  name: containerEnvName
  location: location
  tags: tags
  properties: {
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: log.properties.customerId
        sharedKey: log.listKeys().primarySharedKey
      }
    }
  }
}

resource app 'Microsoft.App/containerApps@2024-03-01' = {
  name: containerAppName
  location: location
  tags: tags
  identity: { type: 'SystemAssigned' }
  properties: {
    managedEnvironmentId: cae.id
    configuration: {
      activeRevisionsMode: 'Single'
      ingress: { external: true, targetPort: 8000, allowInsecure: false, transport: 'auto' }
      registries: [ { server: acr.properties.loginServer, identity: 'system' } ]
    }
    template: {
      containers: [
        {
          name: containerAppName
          image: image
          resources: { cpu: json('0.5'), memory: '1Gi' }
          env: [
            { name: 'AZURE_TENANT_ID', value: tenantId }
            { name: 'SEARCH_ENDPOINT', value: 'https://${search.name}.search.windows.net' }
            { name: 'SEARCH_INDEX', value: searchIndex }
            { name: 'MCP_API_CLIENT_ID', value: mcpApiClientId }
            { name: 'SP_SITE_ID', value: spSiteId }
            { name: 'SP_RESULTS_LIST_ID', value: spResultsListId }
            { name: 'SP_DRAFTS_LIST_ID', value: spDraftsListId }
            { name: 'APPLICATIONINSIGHTS_CONNECTION_STRING', value: appi.properties.ConnectionString }
            { name: 'ALLOWED_HOSTS', value: '${containerAppName}.${cae.properties.defaultDomain},localhost:*' }
            { name: 'PORTAL_ORIGIN', value: portalOrigins }
          ]
          probes: [
            { type: 'Liveness', httpGet: { path: '/healthz', port: 8000 }, periodSeconds: 30 }
          ]
        }
      ]
      scale: { minReplicas: minReplicas, maxReplicas: 3 }
    }
  }
}

resource swa 'Microsoft.Web/staticSites@2023-12-01' = {
  name: staticWebAppName
  location: swaLocation
  tags: tags
  sku: { name: 'Free', tier: 'Free' }
  properties: {}
}

// ---------- Role assignments (least privilege) ----------
var roles = {
  acrPull: '7f951dda-4ed3-4680-a7ca-43fe172d538d'
  searchIndexDataReader: '1407120a-92aa-4202-b7e9-c0e197c71c8f'
  cognitiveServicesOpenAIUser: '5e0bd9bd-7b93-4f28-af87-19fc36ad61bd'
  storageBlobDataReader: '2a2b9908-6ea1-4ae2-8e65-a410df84e7d1'
}

resource appAcrPull 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: acr
  name: guid(acr.id, app.id, roles.acrPull)
  properties: {
    principalId: app.identity.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roles.acrPull)
  }
}

resource appSearchReader 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: search
  name: guid(search.id, app.id, roles.searchIndexDataReader)
  properties: {
    principalId: app.identity.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roles.searchIndexDataReader)
  }
}

// Search calls the embedding model for query vectorization (integrated vectorizer)
resource searchUsesOpenAI 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: ai
  name: guid(ai.id, search.id, roles.cognitiveServicesOpenAIUser)
  properties: {
    principalId: search.identity.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roles.cognitiveServicesOpenAIUser)
  }
}

output searchEndpoint string = 'https://${search.name}.search.windows.net'
output aiEndpoint string = 'https://${aiName}.openai.azure.com'
output acrLoginServer string = acr.properties.loginServer
output containerAppFqdn string = app.properties.configuration.ingress.fqdn
output containerAppPrincipalId string = app.identity.principalId
output portalUrl string = 'https://${swa.properties.defaultHostname}'
