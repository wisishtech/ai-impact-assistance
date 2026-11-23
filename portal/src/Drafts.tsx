import { useEffect, useState } from 'react'
import { settings } from './settings'
import { getToken } from './auth'

type Draft = Record<string, unknown>

const STATUS_CLASS: Record<string, string> = {
  Approved: 'ok',
  'Changes requested': 'warn',
  Pending: 'muted'
}

export default function Drafts ({ enabled }: { enabled: boolean }) {
  const [drafts, setDrafts] = useState<Draft[] | null>(null)
  const [error, setError] = useState('')

  async function load () {
    setError('')
    try {
      const token = await getToken(settings.apiScope)
      const res = await fetch(`${settings.mcpBaseUrl}/api/my-drafts`, {
        headers: { Authorization: `Bearer ${token}` }
      })
      if (!res.ok) throw new Error(`${res.status} ${res.statusText}`)
      const body = await res.json()
      setDrafts(Array.isArray(body) ? body : (body.drafts ?? body.items ?? []))
    } catch (e) {
      console.error(e)
      setError(String(e))
    }
  }

  // wait until the chat sign-in finished, so two popups never open together
  useEffect(() => { if (enabled) load() }, [enabled])

  const val = (d: Draft, ...keys: string[]) => {
    for (const k of keys) if (d[k] != null && d[k] !== '') return String(d[k])
    return ''
  }

  return (
    <aside className='drafts'>
      <div className='drafts-head'>
        <h2>My drafts</h2>
        <button onClick={load} disabled={!enabled}>Refresh</button>
      </div>
      {error && <p className='error'>{error}</p>}
      {!error && drafts === null && <p className='muted'>Loading…</p>}
      {drafts?.length === 0 && <p className='muted'>No drafts submitted yet.</p>}
      <ul>
        {drafts?.map((d, i) => {
          const status = val(d, 'Status', 'status') || 'Pending'
          return (
            <li key={i}>
              <div className='row'>
                <strong>{val(d, 'Program', 'program')} {val(d, 'IndicatorId', 'indicator_id')}</strong>
                <span className={`badge ${STATUS_CLASS[status] ?? 'muted'}`}>{status}</span>
              </div>
              {val(d, 'ReviewerComment', 'reviewer_comment') &&
                <p className='comment'>Reviewer: {val(d, 'ReviewerComment', 'reviewer_comment')}</p>}
              {val(d, 'DecisionDate', 'decision_date') &&
                <p className='muted small'>Decided {new Date(val(d, 'DecisionDate', 'decision_date')).toLocaleDateString()}</p>}
            </li>
          )
        })}
      </ul>
    </aside>
  )
}
