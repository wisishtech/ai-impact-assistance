using './main.bicep'

// Temporary test environment: same design as dev, its own resources, small model capacity.
param env = 'test'
param location = 'eastus'
param swaLocation = 'eastus2'
param minReplicas = 1
param embedCapacity = 20
param chatCapacity = 20

// Same Entra API app and SharePoint site/lists as dev (temporary test; see docs/environments.md)
param mcpApiClientId = 'e496647c-7753-4289-bc1d-790ba8dc1463'
param spSiteId = 'wisishtech.sharepoint.com,9be26958-dc7b-48c1-a6bf-340888198cae,4e9afb85-451c-405e-86c4-6add17ba9b8e'
param spResultsListId = 'fa428e9c-b043-45ec-bdbe-5194c2cf78cc'
param spDraftsListId = '8ad7128e-660a-44eb-9c59-dc5a5848466a'
param portalOrigins = 'http://localhost:5173'
