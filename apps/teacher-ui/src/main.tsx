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
  const [passages, setPassages] = React.useState<any[]>([])
  const [uploadBusy, setUploadBusy] = React.useState<boolean>(false)
  const [genBusy, setGenBusy] = React.useState<boolean>(false)
  const fileRef = React.useRef<HTMLInputElement>(null)
  const [dragOver, setDragOver] = React.useState<boolean>(false)

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

  async function handleFile(file: File) {
    setUploadBusy(true)
    setUploadMsg('')
    try {
      const fd = new FormData()
      fd.append('file', file)
      fd.append('filename', file.name)
      fd.append('mime', file.type || 'application/octet-stream')
      const res = await fetch(endpoints.ingest + '/v1/documents/upload', { method: 'POST', body: fd })
      const data = await res.json()
      if (res.ok) {
        setUploadMsg(`Uploaded: ${data.document_id}`)
        // Auto-parse PDFs
        const isPdf = (file.type === 'application/pdf') || /\.pdf$/i.test(file.name)
        if (isPdf && data.storage_uri) {
          const parseRes = await fetch(`${endpoints.ingest}/v1/documents/parse?document_id=${encodeURIComponent(data.document_id)}&s3_uri=${encodeURIComponent(data.storage_uri)}`, { method: 'POST' })
          const parseJson = await parseRes.json()
          setUploadMsg(parseRes.ok ? `Uploaded and parsed: ${parseJson.chunks || parseJson.pages || 0} chunks` : `Uploaded; parse failed: ${parseJson.reason || parseRes.status}`)
        }
      } else {
        setUploadMsg(`Upload failed: ${res.status}`)
      }
    } catch (err: any) {
      setUploadMsg('Upload error')
    } finally {
      setUploadBusy(false)
    }
  }

  async function onUpload(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault()
    const form = e.currentTarget as HTMLFormElement
    const fileInput = (form.elements.namedItem('file') as HTMLInputElement)
    const file = fileInput?.files?.[0]
    if (!file) return
    await handleFile(file)
    form.reset()
  }

  async function onAsk(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault()
    if (!question.trim()) return
    setGenBusy(true)
    setAnswer(null)
    setPassages([])
    try {
      const ret = await fetch(endpoints.retriever + '/v1/retrieve', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: question, top_k: 5, rerank: false }),
      })
      const retData = await ret.json()
      // Deduplicate by doc_id + page + text signature (first 64 chars)
      const seen = new Set<string>()
      const deduped = (retData.passages || []).filter((p: any) => {
        const sig = `${p.doc_id}:${p?.metadata?.page}:${(p.text || '').slice(0,64)}`
        if (seen.has(sig)) return false
        seen.add(sig)
        return true
      })
      setPassages(deduped)
      const gen = await fetch(endpoints.exam + '/v1/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question_type: 'mcq', question: question, passages: deduped, no_cache: true }),
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
          <input
            ref={fileRef}
            id="file-input"
            aria-label="Upload PDF or PPTX"
            type="file"
            name="file"
            accept="application/pdf,application/vnd.openxmlformats-officedocument.presentationml.presentation"
            onChange={(e) => {
              const f = e.currentTarget.files?.[0]
              if (f) {
                void handleFile(f)
                e.currentTarget.value = ''
              }
            }}
            style={{ display: 'none' }}
          />
          <button type="button" onClick={() => fileRef.current?.click()} disabled={uploadBusy}>
            {uploadBusy ? 'Uploading...' : 'Choose file'}
          </button>
          <button type="submit" disabled={uploadBusy} style={{ marginLeft: 8 }}>
            {uploadBusy ? 'Uploading...' : 'Upload'}
          </button>
        </form>
        <div
          onDragOver={(e) => { e.preventDefault(); setDragOver(true) }}
          onDragLeave={() => setDragOver(false)}
          onDrop={(e) => {
            e.preventDefault();
            setDragOver(false);
            const f = e.dataTransfer.files?.[0]
            if (f) void handleFile(f)
          }}
          style={{ marginTop: 12, padding: 16, border: '2px dashed #bbb', borderColor: dragOver ? '#4caf50' : '#bbb', borderRadius: 8, textAlign: 'center' }}
        >
          Drag & drop a PDF here
        </div>
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
                    <li key={idx} style={{ color: opt.correct ? 'green' : undefined, fontWeight: opt.correct ? 600 : 400 }}>
                      {opt.text} {opt.correct ? '(Correct)' : ''}
                    </li>
                  ))}
                </ol>
                {Array.isArray(answer.payload?.evidence_validation) && answer.payload.evidence_validation.length > 0 && (
                  <div>
                    <strong>Evidence:</strong>
                    <ul>
                      {answer.payload.evidence_validation.map((e: any, i: number) => (
                        <li key={i} style={{ color: e.status === 'verbatim' ? 'green' : e.status === 'paraphrased' ? 'orange' : 'red' }}>
                          {e.ref} ({e.status})
                        </li>
                      ))}
                    </ul>
                  </div>
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

      {passages.length > 0 && (
        <section style={{ marginTop: 24 }}>
          <h3>Retrieved passages</h3>
          {passages.map((p, i) => (
            <div key={i} style={{ padding: 8, border: '1px dashed #ccc', borderRadius: 6, marginBottom: 8 }}>
              <div style={{ fontSize: 12, color: '#555' }}>doc: {p.doc_id} • page: {p?.metadata?.page ?? '-'} • score: {typeof p.score === 'number' ? p.score.toFixed(2) : String(p.score)}</div>
              <div>{p.text}</div>
            </div>
          ))}
        </section>
      )}
    </div>
  )
}

createRoot(document.getElementById('root')!).render(<App />)
