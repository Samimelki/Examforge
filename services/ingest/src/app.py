from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import boto3
import os
import uuid
import psycopg
import io
import pdfplumber
from pdfminer.pdfparser import PDFSyntaxError
from opensearchpy import OpenSearch
from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams, PointStruct
import re
import requests

S3_ENDPOINT = os.getenv("S3_ENDPOINT", "http://localhost:9002")
S3_ACCESS_KEY = os.getenv("S3_ACCESS_KEY", "admin")
S3_SECRET_KEY = os.getenv("S3_SECRET_KEY", "adminadmin")
S3_BUCKET = os.getenv("S3_BUCKET", "examforge")
PG_DSN = os.getenv("PG_DSN", "postgresql://examforge:examforge@localhost:5432/examforge")
OS_HOST = os.getenv("OS_HOST", "http://opensearch:9200")
OS_INDEX = os.getenv("OS_INDEX", "chunks")
EMBED_URL = os.getenv("EMBED_URL", "http://embed:7002/v1/embed")
GROBID_URL = os.getenv("GROBID_URL", "http://grobid:8070")
QDRANT_HOST = os.getenv("QDRANT_HOST", "qdrant")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", "6333"))
QDRANT_COLLECTION = os.getenv("QDRANT_COLLECTION", "chunks")
QDRANT_RECREATE_ON_DIM_CHANGE = os.getenv("QDRANT_RECREATE_ON_DIM_CHANGE", "true").lower() == "true"

s3 = boto3.client(
    "s3",
    endpoint_url=S3_ENDPOINT,
    aws_access_key_id=S3_ACCESS_KEY,
    aws_secret_access_key=S3_SECRET_KEY,
)

os_client = OpenSearch(OS_HOST, use_ssl=False, verify_certs=False)
qdrant = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)


def ensure_bucket(bucket: str) -> None:
    try:
        s3.head_bucket(Bucket=bucket)
    except Exception:
        s3.create_bucket(Bucket=bucket)


def init_schema():
    with psycopg.connect(PG_DSN) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                create table if not exists documents (
                    id uuid primary key,
                    filename text not null,
                    mime text,
                    storage_uri text not null,
                    created_at timestamp default now()
                )
                """
            )
            cur.execute(
                """
                create table if not exists chunks (
                    id uuid primary key,
                    document_id uuid references documents(id) on delete cascade,
                    ordinal int not null,
                    page int,
                    text text not null
                )
                """
            )
            conn.commit()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    init_schema()
    # Ensure OS index
    if not os_client.indices.exists(index=OS_INDEX):
        os_client.indices.create(index=OS_INDEX, body={
            "settings": {"index": {"number_of_shards": 1, "number_of_replicas": 0}},
            "mappings": {"properties": {"document_id": {"type": "keyword"}, "page": {"type": "integer"}, "text": {"type": "text"}}},
        })
    # Ensure Qdrant collection exists matching embed dim
    try:
        resp = requests.post(EMBED_URL, json={"texts": [""], "prefer_ollama": True}, timeout=5)
        dim = resp.json().get("dim", 128)
    except Exception:
        dim = 128
    try:
        info = qdrant.get_collection(QDRANT_COLLECTION)
        current = info.config.params.vectors.size  # type: ignore[attr-defined]
        if int(current) != int(dim) and QDRANT_RECREATE_ON_DIM_CHANGE:
            qdrant.recreate_collection(
                collection_name=QDRANT_COLLECTION,
                vectors_config=VectorParams(size=dim, distance=Distance.COSINE),
            )
    except Exception:
        qdrant.recreate_collection(
            collection_name=QDRANT_COLLECTION,
            vectors_config=VectorParams(size=dim, distance=Distance.COSINE),
        )
    yield
    # Shutdown code can go here if needed


app = FastAPI(title="Examforge Ingest API", version="0.5.1", lifespan=lifespan)
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


@app.post("/v1/documents/upload")
async def upload_document(
    file: UploadFile = File(...),
    filename: str | None = Form(default=None),
    mime: str | None = Form(default=None),
) -> JSONResponse:
    ensure_bucket(S3_BUCKET)
    raw = await file.read()
    doc_id = str(uuid.uuid4())
    name = filename or file.filename or f"upload-{doc_id}"
    key = f"uploads/{doc_id}/{name}"
    s3.put_object(Bucket=S3_BUCKET, Key=key, Body=raw, ContentType=mime or file.content_type or "application/octet-stream")
    storage_uri = f"s3://{S3_BUCKET}/{key}"

    with psycopg.connect(PG_DSN) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "insert into documents (id, filename, mime, storage_uri) values (%s, %s, %s, %s)",
                (doc_id, name, mime or file.content_type, storage_uri),
            )
            conn.commit()

    return JSONResponse({
        "document_id": doc_id,
        "storage_uri": storage_uri,
        "status": "stored",
    })


@app.post("/v1/documents/parse")
async def parse_document(document_id: str, s3_uri: str) -> JSONResponse:
    if not s3_uri.lower().endswith(".pdf"):
        return JSONResponse({"status": "skipped", "reason": "non-pdf"}, status_code=400)

    if not s3_uri.startswith("s3://"):
        return JSONResponse({"status": "error", "reason": "invalid s3 uri"}, status_code=400)
    _, bucket_key = s3_uri.split("s3://", 1)
    bucket, key = bucket_key.split("/", 1)
    obj = s3.get_object(Bucket=bucket, Key=key)
    data = obj["Body"].read()

    if not data.startswith(b"%PDF-"):
        return JSONResponse({"status": "error", "reason": "file is not a valid PDF"}, status_code=400)

    # Utilities for cleaning and chunking
    def _clean(text: str) -> str:
        t = text.replace("\xa0", " ")
        # Fix hyphenated line breaks: word-\nword -> wordword
        t = re.sub(r"-\n(?=\w)", "", t)
        # Replace newlines with spaces
        t = re.sub(r"\s*\n\s*", " ", t)
        # Remove bracketed citation markers like [1], [12,13]
        t = re.sub(r"\[(?:\d+[\s,;-]*)+\]", "", t)
        # Collapse multiple spaces
        t = re.sub(r"\s{2,}", " ", t)
        return t.strip()

    def _chunks(text: str, chunk_size: int = 800, overlap: int = 200) -> list[str]:
        if chunk_size <= 0:
            return [text]
        chunks: list[str] = []
        start = 0
        n = len(text)
        while start < n:
            end = min(n, start + chunk_size)
            chunks.append(text[start:end])
            if end == n:
                break
            start = max(0, end - overlap)
        return chunks

    def _extract_two_columns(page) -> str:
        try:
            words = page.extract_words() or []
        except Exception:
            words = []
        if not words:
            return page.extract_text() or ""
        width = getattr(page, "width", None) or 0
        mid = width / 2 if width else None
        left: list[dict] = []
        right: list[dict] = []
        for w in words:
            if mid and w.get("x0", 0) < mid * 0.98 and w.get("x1", 0) <= mid * 1.02:
                left.append(w)
            else:
                right.append(w)
        def assemble(ws: list[dict]) -> str:
            if not ws:
                return ""
            ws = sorted(ws, key=lambda x: (x.get("top", 0), x.get("x0", 0)))
            lines: list[str] = []
            buf: list[str] = []
            current_top: float | None = None
            for w in ws:
                top = float(w.get("top", 0))
                if current_top is None or abs(top - current_top) > 4.5:
                    if buf:
                        lines.append(" ".join(buf))
                        buf = []
                    current_top = top
                txt = str(w.get("text", "")).strip()
                if txt:
                    buf.append(txt)
            if buf:
                lines.append(" ".join(buf))
            return "\n".join(lines)
        left_text = assemble(left)
        right_text = assemble(right)
        combined = (left_text + "\n" + right_text).strip()
        return combined or (page.extract_text() or "")

    # Try GROBID first for structure-aware text
    page_texts: list[tuple[int, str]] = []
    used_engine = "grobid"
    try:
        r = requests.post(f"{GROBID_URL}/api/processFulltextDocument", files={"input": ("doc.pdf", data, "application/pdf")}, data={"consolidateHeader": 0, "consolidateCitations": 0}, timeout=60)
        if r.ok:
            xml = r.text
            # Naive extraction: strip tags and split by <p>
            paras = re.split(r"</?p[^>]*>", xml, flags=re.IGNORECASE)
            cleaned_paras = [ _clean(re.sub(r"<[^>]+>", " ", p)) for p in paras ]
            cleaned_paras = [p for p in cleaned_paras if len(p) > 0]
            # assign pseudo pages incrementally
            for idx, p in enumerate(cleaned_paras, start=1):
                page_texts.append((idx, p))
        else:
            used_engine = "pdfplumber"
    except Exception:
        used_engine = "pdfplumber"

    if used_engine == "pdfplumber":
        try:
            with pdfplumber.open(io.BytesIO(data)) as pdf:
                for i, page in enumerate(pdf.pages, start=1):
                    raw = _extract_two_columns(page)
                    cleaned = _clean(raw)
                    if cleaned:
                        page_texts.append((i, cleaned))
        except PDFSyntaxError:
            return JSONResponse({"status": "error", "reason": "failed to parse PDF"}, status_code=400)

    # Build sentence-aware overlapping chunks across pages
    def _sentences(text: str) -> list[str]:
        parts = re.split(r"(?<=[.!?])\s+", text)
        return [p.strip() for p in parts if len(p.strip()) > 0]

    chunk_records: list[tuple[int, str]] = []  # (page, text)
    target = 400
    overlap = 100
    for page_num, txt in page_texts:
        sents = _sentences(txt)
        buf = ""
        for s in sents:
            if not buf:
                buf = s
            elif len(buf) + 1 + len(s) <= target:
                buf += " " + s
            else:
                if len(buf) > 40:
                    chunk_records.append((page_num, buf))
                # start next window with tail overlap
                tail = buf[-overlap:]
                buf = (tail + " " + s).strip()
        if buf and len(buf) > 40:
            chunk_records.append((page_num, buf))

    # Embed all chunk texts
    try:
        texts_for_embed = [t for _, t in chunk_records]
        emb_res = requests.post(EMBED_URL, json={"texts": texts_for_embed, "prefer_ollama": True}, timeout=120)
        emb_json = emb_res.json() if emb_res.ok else {"vectors": []}
        vectors = emb_json.get("vectors", [])
    except Exception:
        vectors = []

    with psycopg.connect(PG_DSN) as conn:
        with conn.cursor() as cur:
            cur.execute("delete from chunks where document_id = %s", (document_id,))
            ordinal = 0
            points: list[PointStruct] = []
            for idx, (page_num, txt) in enumerate(chunk_records):
                chunk_id = str(uuid.uuid4())
                cur.execute(
                    "insert into chunks (id, document_id, ordinal, page, text) values (%s, %s, %s, %s, %s)",
                    (chunk_id, document_id, ordinal, page_num, txt),
                )
                os_client.index(index=OS_INDEX, id=chunk_id, body={
                    "document_id": document_id,
                    "page": page_num,
                    "text": txt,
                })
                vec = vectors[idx] if idx < len(vectors) else None
                if isinstance(vec, list) and vec:
                    points.append(PointStruct(id=chunk_id, vector=vec, payload={
                        "document_id": document_id,
                        "page": page_num,
                        "text": txt,
                    }))
                ordinal += 1
            if points:
                qdrant.upsert(collection_name=QDRANT_COLLECTION, points=points)
            conn.commit()

    return JSONResponse({"status": "parsed", "pages": len(page_texts), "chunks": len(chunk_records), "indexed": len(chunk_records), "qdrant_points": len(vectors)})
