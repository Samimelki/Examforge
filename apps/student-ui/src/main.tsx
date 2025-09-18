import React from 'react'
import { createRoot } from 'react-dom/client'

function App() {
  return (
    <div style={{ fontFamily: 'system-ui, sans-serif', padding: 16 }}>
      <h1>Examforge — Student</h1>
      <p>Welcome. Student app coming in Sprint 4.</p>
    </div>
  )
}

createRoot(document.getElementById('root')!).render(<App />)
