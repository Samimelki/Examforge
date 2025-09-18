# Seeds

Add small sample documents for local dev and tests.

## Folders
- `seeds/docs/` — put tiny PDFs here (≤2MB)
- `seeds/slides/` — put tiny PPTX decks here (≤2MB)

You can keep placeholders committed with `.gitkeep` files; actual documents are optional and can be ignored by git if preferred.

## Gold retrieval set (example)
`gold/retrieval.jsonl` — one JSON per line:
```
{"query": "What is photosynthesis?", "answers": [{"doc_id": "doc1", "chunk_id": "c-12"}]}
```

## Quick demo (Sprint 1)
1) Bring up the stack:
   - `make dev-up`
2) Open Teacher UI at http://localhost:3101
3) Upload a small PDF or PPTX (from `seeds/docs/` or `seeds/slides/`).
   - You should see: `Uploaded: doc_<filename>`
4) Ask a question in the input box.
   - You should see a stub MCQ with placeholder evidence.

Notes
- Keep sample files small and public-domain (or licensed for redistribution).
- Full ingestion/retrieval is implemented in Sprint 2; this Sprint returns stubbed answers for the demo.
