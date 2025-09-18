import React from 'react'
import { createRoot } from 'react-dom/client'

async function pingWithRetry(url: string, attempts = 4, delayMs = 500): Promise<boolean> {
  for (let i = 0; i < attempts; i++) {
    try {
      const res = await fetch(url, { cache: 'no-store' })
      if (res.ok) return true
    } catch {}
    await new Promise((r) => setTimeout(r, delayMs * Math.pow(2, i)))
  }
  return false
}

function App() {
  const [status, setStatus] = React.useState<Record<string, string>>({})
  React.useEffect(() => {
    async function run() {
      const results = await Promise.all([
        pingWithRetry('http://localhost:7001/health'),
        pingWithRetry('http://localhost:7002/health'),
        pingWithRetry('http://localhost:7003/health'),
        pingWithRetry('http://localhost:7004/health'),
      ])
      setStatus({ ingest: results[0] ? 'ok' : 'fail', embed: results[1] ? 'ok' : 'fail', retriever: results[2] ? 'ok' : 'fail', exam: results[3] ? 'ok' : 'fail' })
    }
    run()
  }, [])
  return (
    <div style={{ fontFamily: 'system-ui, sans-serif', padding: 16 }}>
      <h1>Examforge — Teacher</h1>
      <ul>
        {['ingest', 'embed', 'retriever', 'exam'].map((k) => (
          <li key={k}>
            {k}: {status[k] ?? '...'}
          </li>
        ))}
      </ul>
    </div>
  )
}

createRoot(document.getElementById('root')!).render(<App />)
