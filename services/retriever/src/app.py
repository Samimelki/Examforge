from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from opensearchpy import OpenSearch
from qdrant_client import QdrantClient
import os
import requests
import hashlib

app = FastAPI(title="Examforge Retriever API", version="0.3.1")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health() -> JSONResponse:
    return JSONResponse({"status": "ok"})

OS_HOST = os.getenv("OS_HOST", "http://opensearch:9200")
OS_INDEX = os.getenv("OS_INDEX", "chunks")
QDRANT_HOST = os.getenv("QDRANT_HOST", "qdrant")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", "6333"))
QDRANT_COLLECTION = os.getenv("QDRANT_COLLECTION", "chunks")
EMBED_URL = os.getenv("EMBED_URL", "http://embed:7002/v1/embed")

os_client = OpenSearch(OS_HOST, use_ssl=False, verify_certs=False)
qdrant = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)


def _sig(doc_id: str, page: int | None, text: str) -> str:
    key = f"{doc_id}|{page}|{(text or '')[:160]}".encode("utf-8")
    return hashlib.sha1(key).hexdigest()


@app.post("/v1/retrieve")
async def retrieve(body: dict) -> JSONResponse:
    query = body.get("query", "")
    top_k = int(body.get("top_k", 5))
    bm25_size = int(os.getenv("BM25_SEARCH_SIZE", "12"))
    dense_size = int(os.getenv("DENSE_SEARCH_SIZE", "24"))

    all_results: list[dict] = []

    # Sparse
    try:
        resp = os_client.search(index=OS_INDEX, body={
            "size": bm25_size,
            "query": {"match": {"text": query}},
            "_source": ["document_id", "page", "text"],
            "highlight": {
                "fields": {"text": {}},
                "fragment_size": 240,
                "number_of_fragments": 2,
                "pre_tags": [""],
                "post_tags": [""],
            },
        })
        for hit in resp.get("hits", {}).get("hits", []):
            src = hit.get("_source", {})
            hl_parts = hit.get("highlight", {}).get("text", [])
            snippet = " ... ".join(hl_parts) if hl_parts else src.get("text", "")
            all_results.append({
                "doc_id": src.get("document_id", ""),
                "chunk_id": hit.get("_id", ""),
                "text": snippet,
                "score": float(hit.get("_score", 0.0)),
                "metadata": {"page": src.get("page")},
                "source": "bm25",
            })
    except Exception as e:
        print("[retriever] OpenSearch error", repr(e))

    # Dense
    try:
        emb = requests.post(EMBED_URL, json={"texts": [query]}, timeout=30).json()
        qvec = emb.get("vectors", [[0]])[0]
        hits = qdrant.search(collection_name=QDRANT_COLLECTION, query_vector=qvec, limit=dense_size, with_payload=True)
        for h in hits:
            payload = h.payload or {}
            all_results.append({
                "doc_id": payload.get("document_id", ""),
                "chunk_id": str(h.id),
                "text": payload.get("text", ""),
                "score": float(h.score or 0.0),
                "metadata": {"page": payload.get("page")},
                "source": "dense",
            })
    except Exception as e:
        print("[retriever] Qdrant error", repr(e))

    # Deduplicate and cap per document
    merged: dict[str, dict] = {}
    per_doc: dict[str, int] = {}
    for r in all_results:
        text = (r.get("text", "") or "").strip()
        if len(text) < 60:
            continue
        sig = _sig(r.get("doc_id", ""), r.get("metadata", {}).get("page"), text)
        if sig not in merged or r.get("score", 0.0) > merged[sig].get("score", 0.0):
            r["text"] = text[:800]
            # enforce max 1 snippet per doc
            doc = r.get("doc_id", "")
            if per_doc.get(doc, 0) >= 1:
                continue
            per_doc[doc] = per_doc.get(doc, 0) + 1
            merged[sig] = r

    # Sort by score desc and truncate
    final_passages = sorted(merged.values(), key=lambda x: x.get("score", 0.0), reverse=True)[:top_k]

    return JSONResponse({"query": query, "passages": final_passages})
