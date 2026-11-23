import { Components } from 'botframework-webchat'
import { FluentThemeProvider } from 'botframework-webchat-fluent-theme'
import { useEffect, useState } from 'react'
import {
  CopilotStudioClient,
  CopilotStudioWebChat,
  type CopilotStudioWebChatConnection
} from '@microsoft/agents-copilotstudio-client'
import { agentSettings } from './settings'
import { COPILOT_SCOPE, getToken } from './auth'

const { BasicWebChat, Composer } = Components

export default function Chat ({ onReady }: { onReady: () => void }) {
  const [connection, setConnection] = useState<CopilotStudioWebChatConnection | null>(null)
  const [error, setError] = useState('')

  useEffect(() => {
    (async () => {
      try {
        const token = await getToken(COPILOT_SCOPE)
        const client = new CopilotStudioClient(agentSettings, token)
        setConnection(CopilotStudioWebChat.createConnection(client, { showTyping: true }))
        onReady()
      } catch (e) {
        console.error(e)
        setError(String(e))
      }
    })()
  }, [])

  if (error) return <p className='error'>Could not connect to the agent: {error}</p>
  if (!connection) return <p className='muted'>Signing in…</p>

  return (
    <FluentThemeProvider>
      <Composer directLine={connection}>
        <BasicWebChat />
      </Composer>
    </FluentThemeProvider>
  )
}
