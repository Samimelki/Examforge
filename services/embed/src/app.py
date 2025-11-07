from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import os
import hashlib
import requests

app = FastAPI(title="Examforge Embed API", version="0.4.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

EMBED_DIM = int(os.getenv("EMBED_DIM", "768"))
SEED = os.getenv("EMBED_SEED", "examforge-seed")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://host.docker.internal:11434")
OLLAMA_MODEL = os.getenv("EMBED_MODEL", "nomic-embed-text")


def _hash_to_unit_float(hex_str: str) -> float:
    val = int(hex_str[:8], 16)
    return (val / 0xFFFFFFFF) * 2.0 - 1.0


def _embed_hash(text: str, dim: int) -> list[float]:
    text = (text or "").strip()
    vec: list[float] = []
    for i in range(dim):
        h = hashlib.sha256()
        h.update(SEED.encode("utf-8"))
        h.update(b"|")
        h.update(str(i).encode("utf-8"))
        h.update(b"|")
        h.update(text.encode("utf-8"))
        vec.append(_hash_to_unit_float(h.hexdigest()))
    return vec


def _embed_ollama(texts: list[str]) -> tuple[list[list[float]], int] | None:
    try:
        resp = requests.post(
            f"{OLLAMA_BASE_URL}/api/embeddings",
            json={"model": OLLAMA_MODEL, "input": texts},
            timeout=60,
        )
        if not resp.ok:
            return None
        data = resp.json()
        if "embeddings" in data:
            vectors = data["embeddings"]
        elif "embedding" in data:
            vectors = [data["embedding"]]
        else:
            return None
        dim = len(vectors[0]) if vectors and isinstance(vectors[0], list) else EMBED_DIM
        return vectors, dim
    except Exception:
        return None


@app.get("/health")
async def health() -> JSONResponse:
    return JSONResponse({"status": "ok", "dim": EMBED_DIM, "model": OLLAMA_MODEL})


@app.post("/v1/embed")
async def embed_texts(body: dict) -> JSONResponse:
    texts = body.get("texts", [])
    prefer_ollama = bool(body.get("prefer_ollama", True))
    if prefer_ollama:
        res = _embed_ollama(texts)
        if res is not None:
            vectors, dim = res
            return JSONResponse({"vectors": vectors, "dim": dim, "used": "ollama"})
    vectors = [_embed_hash(t, EMBED_DIM) for t in texts]
    return JSONResponse({"vectors": vectors, "dim": EMBED_DIM, "used": "hash"})
