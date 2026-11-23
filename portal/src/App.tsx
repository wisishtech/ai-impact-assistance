import { useEffect, useState } from 'react'
import Chat from './Chat'
import Drafts from './Drafts'
import { currentUser, signOut } from './auth'

export default function App () {
  const [signedIn, setSignedIn] = useState(false)
  const [name, setName] = useState('')

  useEffect(() => {
    if (signedIn) currentUser().then(a => setName(a?.name ?? a?.username ?? ''))
  }, [signedIn])

  return (
    <div className='app'>
      <header>
        <h1>Impact Evidence Assistant</h1>
        <div className='user'>
          {name && <span>{name}</span>}
          {signedIn && <button onClick={() => signOut().then(() => location.reload())}>Sign out</button>}
        </div>
      </header>
      <main>
        <section className='chat'><Chat onReady={() => setSignedIn(true)} /></section>
        <Drafts enabled={signedIn} />
      </main>
    </div>
  )
}
