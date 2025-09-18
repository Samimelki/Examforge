from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Examforge Retriever API", version="0.1.0")
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


@app.post("/v1/retrieve")
async def retrieve(body: dict) -> JSONResponse:
    query = body.get("query", "")
    return JSONResponse({
        "query": query,
        "passages": [
            {"doc_id": "stub", "chunk_id": "c1", "text": "example passage", "score": 1.0, "metadata": {}},
        ],
    })
