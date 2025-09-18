# Seeds

Add small sample documents for local dev and tests.

## Files
- `docs/sample-1.pdf`
- `docs/sample-2.pdf`
- `slides/sample-deck.pptx`

## Gold retrieval set (example)
`gold/retrieval.jsonl` — one JSON per line:
```
{"query": "What is photosynthesis?", "answers": [{"doc_id": "doc1", "chunk_id": "c-12"}]}
```

## Notes
- Keep files small (<2MB) and public domain or licensed for redistribution.
- Update indices after adding files.
