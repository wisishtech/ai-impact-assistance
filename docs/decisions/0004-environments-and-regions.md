# 0004 Environments, region and billing

**Status:** Accepted

## Context
- East US 2 had no capacity for the services needed; East US did.
- The Power Platform Developer environment ran out of Copilot Studio credits and cannot use pay-as-you-go.

## Decision
- Azure resources in **East US** (`rg-iea-dev`). Static Web Apps Free in **East US 2** (Free tier is not offered in East US; static hosting only).
- Power Platform **IEA-Sandbox** (Sandbox type) with a pay-as-you-go billing plan linked to the Azure subscription; the agent and flow live in the *Impact Evidence Assistant* solution.
- Dataverse team mapped to the `IEA-AllStaff` Entra group so the agent and custom connector can be shared with the group.

## Consequences
- Usage is billed to Azure and covered by the resource-group budget alert.
- Promotion to test/production uses solution export/import (`pac solution export`).
