import {
  PublicClientApplication,
  InteractionRequiredAuthError,
  type AccountInfo
} from '@azure/msal-browser'
import { CopilotStudioClient } from '@microsoft/agents-copilotstudio-client'
import { settings, agentSettings } from './settings'

const msal = new PublicClientApplication({
  auth: {
    clientId: settings.appClientId,
    authority: `https://login.microsoftonline.com/${settings.tenantId}`,
    redirectUri: window.location.origin
  },
  cache: { cacheLocation: 'sessionStorage' }
})

const ready = msal.initialize()

// Copilot Studio (Power Platform API) scope for this agent
export const COPILOT_SCOPE = CopilotStudioClient.scopeFromSettings(agentSettings)

// Only one sign-in popup may be open at a time, so token requests run one after another.
let queue: Promise<unknown> = Promise.resolve()

export function getToken (scope: string): Promise<string> {
  const next = queue.then(() => acquire(scope))
  queue = next.catch(() => undefined)
  return next
}

async function acquire (scope: string): Promise<string> {
  await ready
  const account = msal.getAllAccounts()[0]
  if (account) {
    try {
      const r = await msal.acquireTokenSilent({ scopes: [scope], account })
      return r.accessToken
    } catch (e) {
      if (!(e instanceof InteractionRequiredAuthError)) throw e
    }
  }
  const r = await msal.acquireTokenPopup({ scopes: [scope] })
  msal.setActiveAccount(r.account)
  return r.accessToken
}

export async function currentUser (): Promise<AccountInfo | null> {
  await ready
  return msal.getActiveAccount() ?? msal.getAllAccounts()[0] ?? null
}

export async function signOut (): Promise<void> {
  await ready
  await msal.logoutPopup()
}
