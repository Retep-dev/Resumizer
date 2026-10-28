import sys
from pathlib import Path

# Add backend directory to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import os
import logging
import traceback
import uuid
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from app.agents import AnalysisUnavailable, chat_with_career_coach, run_resumizer_pipeline
from app.config import settings
from app.llm import ProviderError, get_client
from app.schemas.resume import AnalysisResult
from app.services.document_parser import DocumentError, extract_text_from_file
from app.services.session_store import get_session, save_session

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
log = logging.getLogger("resumizer.api")

MAX_UPLOAD_BYTES = 10 * 1024 * 1024
MIN_JD_WORDS = 25
MIN_RESUME_CHARS = 200

app = FastAPI(
    title="Resumizer API",
    description="Resume analysis against a job description, grounded rewrites, interview prep and a career coach.",
    version="2.0.0",
)

# Enable CORS for React frontend & Vercel cross-origin requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


def fail(status: int, code: str, message: str, **extra) -> HTTPException:
    """Errors use {"detail": {"code": ..., "message": ...}} so clients can react to the cause."""
    return HTTPException(status_code=status, detail={"code": code, "message": message, **extra})


class AnalyzeResponse(BaseModel):
    session_id: str
    analysis: AnalysisResult


class ChatTurn(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    session_id: str
    message: str
    chat_history: Optional[List[ChatTurn]] = []
    # Optional copy of the analysis the user is looking at, so the coach still
    # works after a server restart clears the in-memory session.
    analysis: Optional[Dict[str, Any]] = None
    job_description: Optional[str] = Field(default=None, max_length=20000)


class ChatResponse(BaseModel):
    reply: str
    grounded_on: str = Field(description="'session' (server copy of resume text) or 'client_analysis'")


@app.api_route("/", methods=["GET", "HEAD"])
@app.api_route("/health", methods=["GET", "HEAD"])
def root():
    return {"status": "ok", "message": "Resumizer API is running smoothly!", "version": app.version}


@app.get("/api/v1/status")
def ai_status():
    """Which models the server will use. Never includes the API key."""
    from app.llm.router import routing_status
    retired = set()
    for task in settings.TASKS:
        retired |= set(getattr(get_client(task), "retired", set()))
    return {
        "api_key_configured": settings.api_key_configured,
        "model_chain": settings.model_chain,
        "tasks": routing_status(),
        "paid_providers_allowed": settings.ALLOW_PAID_PROVIDERS,
        "retired_this_process": sorted(retired),
        "commit": (os.getenv("RENDER_GIT_COMMIT") or "")[:7] or None,
    }


@app.post("/api/v1/analyze", response_model=AnalyzeResponse)
async def analyze_resume(file: UploadFile = File(...), job_description: str = Form(...)):
    """Upload a resume and a job description; returns a grounded analysis with per-stage status."""
    if not settings.api_key_configured:
        log.warning("NVIDIA_API_KEY not configured; analysis will be rule-based only")

    jd = (job_description or "").strip()
    if not jd:
        raise fail(400, "validation_failed", "Job description cannot be empty.")
    if len(jd.split()) < MIN_JD_WORDS:
        raise fail(400, "validation_failed", f"Paste the full job description (at least {MIN_JD_WORDS} words) so the match is meaningful.")

    file_bytes = await file.read()
    if len(file_bytes) > MAX_UPLOAD_BYTES:
        raise fail(413, "validation_failed", "The file is larger than 10 MB.")
    try:
        raw_text = extract_text_from_file(file_bytes, file.filename or "")
    except DocumentError as e:
        raise fail(422 if e.code == "parsing_failed" else 400, e.code, e.message)
    if len(raw_text) < MIN_RESUME_CHARS:
        raise fail(422, "parsing_failed",
                   f"Could not extract readable text from uploaded file (found {len(raw_text)} characters). "
                   "Scanned or image-only PDFs have no text layer; export a text-based PDF or DOCX.")

    try:
        analysis = await run_resumizer_pipeline(raw_text, jd)
    except AnalysisUnavailable as e:
        raise fail(503, "ai_unavailable", e.message, provider=e.reason)
    except Exception:
        log.error("Pipeline error\n%s", traceback.format_exc())
        raise fail(500, "internal_error", "The analysis failed unexpectedly. Try again; if it keeps happening, check the server logs.")

    session_id = str(uuid.uuid4())
    save_session(session_id, raw_text, jd, analysis.model_dump())
    log.info("Analysis %s finished with status=%s stages=%s", session_id, analysis.status,
             {k: v.status for k, v in analysis.stages.items()})
    return AnalyzeResponse(session_id=session_id, analysis=analysis)


@app.post("/api/v1/chat", response_model=ChatResponse)
async def chat_coach(request: ChatRequest):
    """Career coach grounded in the analysed resume and job description."""
    message = (request.message or "").strip()
    if not message:
        raise fail(400, "validation_failed", "Message cannot be empty.")
    if len(message) > 4000:
        raise fail(400, "validation_failed", "Keep messages under 4,000 characters.")

    ctx = get_session(request.session_id)
    if ctx:
        resume_text, jd, analysis, grounded_on = ctx.resume_text, ctx.job_description, ctx.analysis, "session"
    elif request.analysis and request.analysis.get("resume_data"):
        resume_text, jd, analysis, grounded_on = None, request.job_description or "", request.analysis, "client_analysis"
    else:
        raise fail(404, "session_expired", "This analysis session has expired. Run the analysis again to keep chatting.")

    try:
        reply = await chat_with_career_coach(
            message, [t.model_dump() for t in (request.chat_history or [])], resume_text, jd, analysis
        )
    except ProviderError as e:
        status = 429 if e.kind == "rate_limited" else 503
        raise fail(status, "ai_unavailable", "The coach couldn't answer: " + e.message, provider=e.public())
    except Exception:
        log.error("Chat error\n%s", traceback.format_exc())
        raise fail(500, "internal_error", "The coach failed unexpectedly.")
    return ChatResponse(reply=reply, grounded_on=grounded_on)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host=settings.HOST, port=settings.PORT, reload=True)
