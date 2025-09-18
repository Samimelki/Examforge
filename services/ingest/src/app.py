from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Examforge Ingest API", version="0.1.0")
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
    # Stub: we don't persist yet in Sprint 1
    doc_id = "doc_" + (filename or file.filename)
    return JSONResponse({
        "document_id": doc_id,
        "storage_uri": f"minio://uploads/{doc_id}",
        "status": "received",
    })
