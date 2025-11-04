from fastapi import FastAPI
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import os
import re
import json
import time
import requests
from difflib import SequenceMatcher
from collections import OrderedDict

app = FastAPI(title="Examforge Exam-Engine API", version="0.4.7")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://host.docker.internal:11434")
GEN_MODEL = os.getenv("GEN_MODEL", "llama3:8b")
OLLAMA_TIMEOUT = int(os.getenv("OLLAMA_TIMEOUT", "600"))
TEMP = float(os.getenv("GEN_TEMPERATURE", "0.2"))
TOP_P = float(os.getenv("GEN_TOP_P", "0.9"))

# Simple LRU cache
class LRU(OrderedDict):
    def __init__(self, capacity: int = 32):
        super().__init__()
        self.capacity = capacity
    def get(self, key):
        if key in self:
            val = super().pop(key)
            super().__setitem__(key, val)
            return val
        return None
    def put(self, key, val):
        if key in self:
            super().pop(key)
        elif len(self) >= self.capacity:
            self.popitem(last=False)
        super().__setitem__(key, val)

cache = LRU(32)


@app.get("/health")
async def health() -> JSONResponse:
    return JSONResponse({"status": "ok", "model": GEN_MODEL, "timeout": OLLAMA_TIMEOUT})
@app.post("/v1/debug/clear_cache")
async def clear_cache() -> JSONResponse:
    try:
        cache.clear()
        return JSONResponse({"cleared": True})
    except Exception:
        return JSONResponse({"cleared": False}, status_code=500)


@app.get("/v1/ollama/models")
async def list_models() -> JSONResponse:
    try:
        r = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=5)
        return JSONResponse(r.json())
    except Exception as e:
        return JSONResponse({"error": repr(e)}, status_code=500)


@app.get("/v1/debug/ping")
async def debug_ping() -> JSONResponse:
    try:
        r = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=2)
        return JSONResponse({"ollama": r.status_code})
    except Exception as e:
        return JSONResponse({"ollama_error": repr(e)}, status_code=500)


def _similar(a: str, b: str) -> float:
    return SequenceMatcher(None, a, b).ratio() if a and b else 0.0


def _validate_evidence(passages: list[dict], refs: list[str]) -> list[dict]:
    out = []
    by_key: dict[tuple[str, int | None], str] = {}
    for p in passages:
        key = (p.get("doc_id", ""), p.get("metadata", {}).get("page"))
        by_key[key] = p.get("text", "")

    for r in refs:
        m = re.match(r"([^:]+):(\d+):(.*)", r or "")
        status = "invalid"
        if m:
            doc_id, page_s, quote = m.group(1), m.group(2), (m.group(3) or "").strip()
            page = int(page_s)
            chunk = by_key.get((doc_id, page), "")
            if quote and chunk:
                if quote in chunk:
                    status = "verbatim"
                else:
                    sim = _similar(quote, chunk)
                    status = "paraphrased" if sim >= 0.92 else "invalid"
            out.append({"ref": r, "status": status})
        else:
            out.append({"ref": r, "status": "invalid"})
    return out


FEWSHOT = (
    "Example 1:\n"
    "CONTEXT:\nDOC d1 PAGE 2: Cells divide uncontrollably in malignant tumors.\n"
    "OUTPUT JSON:\n{\"type\":\"mcq\",\"payload\":{\"stem\":\"Which statement is supported by the context?\",\"options\":[{\"text\":\"Malignant tumors involve uncontrolled cell division\",\"correct\":true},{\"text\":\"Benign tumors always invade\",\"correct\":false},{\"text\":\"All tumors are infectious\",\"correct\":false},{\"text\":\"Tumors cannot recur\",\"correct\":false}],\"rationale\":\"The context states malignant tumors divide uncontrollably.\",\"evidence\":[\"d1:2:divide uncontrollably\"]}}\n"
)


def _prompt_for_mcq(question: str, passages: list[dict]) -> str:
    context_lines = []
    for p in passages[:3]:
        doc_id = p.get("doc_id", "")
        page = p.get("metadata", {}).get("page", "")
        txt = ((p.get("text", "") or "").strip())[:800]
        context_lines.append(f"DOC {doc_id} PAGE {page}: {txt}")
    context = "\n".join(context_lines)
    return (
        FEWSHOT +
        "You are an exam generator. Use the CONTEXT to create a multiple-choice question (MCQ) that can be answered strictly from the context.\n"
        "Output strict JSON with keys: type, payload. payload has: stem, options (array of exactly 4 with {text, correct}), rationale, evidence (array of strings).\n"
        "Constraints: exactly one option must have correct=true; do not use choices like 'All of the above', 'None of the above', or 'Both A and B'. Keep options concise.\n"
        "Evidence strings MUST be in the format doc_id:page:quote (verbatim from context).\n"
        f"QUESTION: {question}\n"
        f"CONTEXT:\n{context}\n"
        "Return only JSON."
    )


def _ask_ollama(prompt: str, stream: bool) -> requests.Response:
    return requests.post(
        f"{OLLAMA_BASE_URL}/api/generate",
        json={"model": GEN_MODEL, "prompt": prompt, "stream": stream, "options": {"temperature": TEMP, "top_p": TOP_P}},
        timeout=OLLAMA_TIMEOUT,
        stream=stream,
    )


def _ask_ollama_stream(prompt: str):
    resp = _ask_ollama(prompt, stream=True)
    resp.raise_for_status()
    return resp


@app.post("/v1/generate/stream")
async def generate_stream(body: dict):
    question = body.get("question", "")
    passages = body.get("passages", [])
    prompt = _prompt_for_mcq(question, passages)

    def iter_ndjson():
        t0 = time.time()
        buffer_parts: list[str] = []
        try:
            with _ask_ollama_stream(prompt) as r:
                for line in r.iter_lines(decode_unicode=True):
                    if not line:
                        continue
                    try:
                        obj = json.loads(line)
                        if "response" in obj:
                            delta = obj["response"]
                            buffer_parts.append(delta)
                            yield json.dumps({"type": "partial", "delta": delta}) + "\n"
                        if obj.get("done"):
                            break
                    except Exception:
                        continue
            latency_ms = int((time.time() - t0) * 1000)
            full = "".join(buffer_parts).strip()
            # Try to parse JSON from full
            result = None
            start = full.find("{")
            end = full.rfind("}")
            if start != -1 and end != -1 and end > start:
                try:
                    result = json.loads(full[start : end + 1])
                except Exception:
                    result = None
            if not isinstance(result, dict):
                # Fallback minimal structure
                result = {"type": "mcq", "payload": {"stem": question or "Generated", "options": [], "rationale": "", "evidence": []}}
            # Validate evidence
            ev = result.get("payload", {}).get("evidence", [])
            if isinstance(ev, list):
                validations = _validate_evidence(passages, [str(x) for x in ev])
                result["payload"]["evidence_validation"] = validations
            meta = {"type": "final", "result": result, "engine": "ollama", "model": GEN_MODEL, "latency_ms": latency_ms}
            yield json.dumps(meta) + "\n"
        except Exception as e:
            yield json.dumps({"type": "error", "message": repr(e)}) + "\n"

    return StreamingResponse(iter_ndjson(), media_type="application/x-ndjson")


@app.post("/v1/generate")
async def generate(body: dict) -> JSONResponse:
    qtype = body.get("question_type", "mcq")
    question = body.get("question", "")
    passages = body.get("passages", [])
    no_cache = bool(body.get("no_cache", False))

    if qtype != "mcq":
        qtype = "mcq"

    # Cache key by question + doc ids
    doc_key = ",".join(sorted({p.get("doc_id", "") for p in passages}))
    key = f"{question}|{doc_key}"
    if not no_cache:
        cached = cache.get(key)
        if cached:
            return JSONResponse(cached)

    prompt = _prompt_for_mcq(question, passages)
    t0 = time.time()
    try:
        r = _ask_ollama(prompt, stream=False)
        if r.ok:
            data = r.json().get("response", "")
            start = data.find("{")
            end = data.rfind("}")
            if start != -1 and end != -1 and end > start:
                result = json.loads(data[start : end + 1])
                used = "ollama"
            else:
                result = None
                used = "fallback"
        else:
            result = None
            used = "fallback"
    except Exception:
        result = None
        used = "fallback"

    if not isinstance(result, dict):
        result = {"type": "mcq", "payload": {"stem": question or "Generated", "options": [
            {"text": "A", "correct": True}, {"text": "B", "correct": False}, {"text": "C", "correct": False}, {"text": "D", "correct": False}
        ], "rationale": "", "evidence": []}}

    # Normalize: ensure exactly one correct option
    try:
        opts = result.get("payload", {}).get("options", [])
        if isinstance(opts, list) and opts:
            # If multiple marked correct, keep only the first as correct
            first_correct_found = False
            for opt in opts:
                if isinstance(opt, dict) and opt.get("correct") is True:
                    if not first_correct_found:
                        first_correct_found = True
                    else:
                        opt["correct"] = False
            # If none marked correct, set the first as correct
            if not first_correct_found and isinstance(opts[0], dict):
                opts[0]["correct"] = True
                for opt in opts[1:]:
                    if isinstance(opt, dict):
                        opt["correct"] = False
    except Exception:
        pass

    latency_ms = int((time.time() - t0) * 1000)
    ev = result.get("payload", {}).get("evidence", [])
    if isinstance(ev, list):
        validations = _validate_evidence(passages, [str(x) for x in ev])
        result["payload"]["evidence_validation"] = validations

    result["engine"] = used
    result["model"] = GEN_MODEL
    result["latency_ms"] = latency_ms
    cache.put(key, result)
    return JSONResponse(result)
