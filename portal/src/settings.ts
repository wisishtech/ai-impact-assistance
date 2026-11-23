// Public IDs only (no secrets). Safe to commit.
import { ConnectionSettings } from '@microsoft/agents-copilotstudio-client'

export const settings = {
  tenantId: 'cd379f63-f29d-4b01-869f-552fe56bbc29',
  appClientId: '9518ea29-5725-4927-a111-1b36d85c52bc', // iea-webchat
  mcpBaseUrl: 'https://ca-iea-mcp-dev.jollyhill-fc3ac0bc.eastus.azurecontainerapps.io',
  apiScope: 'api://e496647c-7753-4289-bc1d-790ba8dc1463/Evidence.Read' // iea-mcp-api
}

export const agentSettings = new ConnectionSettings({
  environmentId: '2fdab0a1-be1d-e6df-958a-e2d7190c14f3', // IEA-Sandbox
  schemaName: 'iea_impactevidenceassistant_Qsernw',
  cloud: 'Prod',
  copilotAgentType: 'Published'
})
