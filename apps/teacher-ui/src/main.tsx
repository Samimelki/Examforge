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

const endpoints = {
  ingest: 'http://localhost:7001',
  embed: 'http://localhost:7002',
  retriever: 'http://localhost:7003',
  exam: 'http://localhost:7004',
}

function App() {
  const [status, setStatus] = React.useState<Record<string, string>>({})
  const [uploadMsg, setUploadMsg] = React.useState<string>('')
  const [question, setQuestion] = React.useState<string>('')
  const [answer, setAnswer] = React.useState<any>(null)
  const [uploadBusy, setUploadBusy] = React.useState<boolean>(false)
  const [genBusy, setGenBusy] = React.useState<boolean>(false)

  const allHealthy = ['ingest', 'embed', 'retriever', 'exam'].every((k) => status[k] === 'ok')

  React.useEffect(() => {
    async function run() {
      const results = await Promise.all([
        pingWithRetry(endpoints.ingest + '/health'),
        pingWithRetry(endpoints.embed + '/health'),
        pingWithRetry(endpoints.retriever + '/health'),
        pingWithRetry(endpoints.exam + '/health'),
      ])
      setStatus({ ingest: results[0] ? 'ok' : 'fail', embed: results[1] ? 'ok' : 'fail', retriever: results[2] ? 'ok' : 'fail', exam: results[3] ? 'ok' : 'fail' })
    }
    run()
  }, [])

  async function onUpload(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault()
    const form = e.currentTarget as HTMLFormElement
    const fileInput = (form.elements.namedItem('file') as HTMLInputElement)
    const file = fileInput?.files?.[0]
    if (!file) return
    setUploadBusy(true)
    setUploadMsg('')
    try {
      const fd = new FormData()
      fd.append('file', file)
      fd.append('filename', file.name)
      fd.append('mime', file.type || 'application/octet-stream')
      const res = await fetch(endpoints.ingest + '/v1/documents/upload', { method: 'POST', body: fd })
      const data = await res.json()
      setUploadMsg(res.ok ? `Uploaded: ${data.document_id}` : `Upload failed: ${res.status}`)
    } catch (err: any) {
      setUploadMsg('Upload error')
    } finally {
      setUploadBusy(false)
      form.reset()
    }
  }

  async function onAsk(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault()
    if (!question.trim()) return
    setGenBusy(true)
    setAnswer(null)
    try {
      const ret = await fetch(endpoints.retriever + '/v1/retrieve', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: question, top_k: 5, rerank: false }),
      })
      const retData = await ret.json()
      const passages = retData.passages || []
      const gen = await fetch(endpoints.exam + '/v1/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question_type: 'mcq', passages }),
      })
      const genData = await gen.json()
      setAnswer(genData)
    } catch (err) {
      setAnswer({ error: 'Failed to generate answer' })
    } finally {
      setGenBusy(false)
    }
  }

  return (
    <div style={{ fontFamily: 'system-ui, sans-serif', padding: 16, maxWidth: 800 }}>
      <h1>Examforge — Teacher</h1>

      {!allHealthy && (
        <div style={{ background: '#fff3cd', border: '1px solid #ffeeba', padding: 8, borderRadius: 6, marginBottom: 12 }}>
          Some services are unhealthy; actions may fail.
        </div>
      )}

      <section>
        <h3>Service health</h3>
        <ul>
          {['ingest', 'embed', 'retriever', 'exam'].map((k) => (
            <li key={k}>
              {k}: {status[k] ?? '...'}
            </li>
          ))}
        </ul>
      </section>

      <section style={{ marginTop: 24 }}>
        <h3>Upload PDF / PPTX</h3>
        <form onSubmit={onUpload}>
          <input type="file" name="file" accept="application/pdf,application/vnd.openxmlformats-officedocument.presentationml.presentation" />
          <button type="submit" disabled={uploadBusy} style={{ marginLeft: 8 }}>
            {uploadBusy ? 'Uploading...' : 'Upload'}
          </button>
        </form>
        {uploadMsg && <p>{uploadMsg}</p>}
      </section>

      <section style={{ marginTop: 24 }}>
        <h3>Ask a question</h3>
        <form onSubmit={onAsk}>
          <input
            type="text"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder="Type your question..."
            style={{ width: '70%' }}
          />
          <button type="submit" disabled={genBusy || !question.trim() || !allHealthy} style={{ marginLeft: 8 }}>
            {genBusy ? 'Generating...' : 'Ask'}
          </button>
        </form>
        {answer && (
          <div style={{ marginTop: 12, padding: 12, border: '1px solid #ddd', borderRadius: 6 }}>
            {answer.error && <p>{answer.error}</p>}
            {!answer.error && answer.type === 'mcq' && (
              <div>
                <p><strong>MCQ:</strong> {answer.payload?.stem}</p>
                <ol type="A">
                  {answer.payload?.options?.map((opt: any, idx: number) => (
                    <li key={idx}>{opt.text}</li>
                  ))}
                </ol>
                {answer.payload?.evidence && (
                  <p>
                    <em>Evidence:</em> {answer.payload.evidence.map((e: any) => e.ref).join(', ')}
                  </p>
                )}
              </div>
            )}
            {!answer.error && answer.type === 'saq' && (
              <div>
                <p><strong>Prompt:</strong> {answer.payload?.prompt}</p>
                <p><strong>Expected:</strong> {answer.payload?.expected_answer}</p>
                {answer.payload?.evidence && (
                  <p>
                    <em>Evidence:</em> {answer.payload.evidence.map((e: any) => e.ref).join(', ')}
                  </p>
                )}
              </div>
            )}
          </div>
        )}
      </section>
    </div>
  )
}

createRoot(document.getElementById('root')!).render(<App />)
