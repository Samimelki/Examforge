from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Examforge Exam-Engine API", version="0.1.0")
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


@app.post("/v1/generate")
async def generate(body: dict) -> JSONResponse:
    qtype = body.get("question_type", "mcq")
    if qtype == "mcq":
        payload = {
            "stem": "Stub stem",
            "options": [
                {"text": "A", "correct": True},
                {"text": "B", "correct": False},
                {"text": "C", "correct": False},
                {"text": "D", "correct": False},
            ],
            "rationale": "Stub rationale",
            "evidence": [{"ref": "doc:1:quote"}],
        }
        return JSONResponse({"type": "mcq", "payload": payload})
    else:
        payload = {
            "prompt": "Stub prompt",
            "expected_answer": "Stub answer",
            "rubric": ["Key point 1"],
            "evidence": [{"ref": "doc:1:quote"}],
        }
        return JSONResponse({"type": "saq", "payload": payload})
