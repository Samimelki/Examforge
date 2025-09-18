from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Examforge Embed API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health() -> JSONResponse:
    return JSONResponse({"status": "ok"})


@app.post("/v1/embed")
async def embed_texts(body: dict) -> JSONResponse:
    texts = body.get("texts", [])
    # Stub: return zero vectors
    dim = 8
    vectors = [[0.0] * dim for _ in texts]
    return JSONResponse({"vectors": vectors, "dim": dim})
