import uuid
from typing import List, Dict, Optional
from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.config import settings
from app.services.document_parser import extract_text_from_file
from app.agents.pipeline import run_resumizer_pipeline
from app.agents.career_coach_agent import chat_with_career_coach
from app.services.rag_service import index_documents_for_rag
from app.schemas.resume import AnalysisResult

app = FastAPI(
    title="Resumizer API",
    description="Multi-Agent Resume Scoring, Skill Gap Analysis & AI Career Coach API",
    version="1.0.0"
)

# Enable CORS for React frontend development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class AnalyzeResponse(BaseModel):
    session_id: str
    analysis: AnalysisResult


class ChatRequest(BaseModel):
    session_id: str
    message: str
    chat_history: Optional[List[Dict[str, str]]] = []


class ChatResponse(BaseModel):
    reply: str


class ExportRequest(BaseModel):
    markdown_content: str
    format: str = "markdown"


@app.get("/")
def root():
    return {"message": "Resumizer API is running smoothly!", "version": "1.0.0"}


@app.post("/api/v1/analyze", response_model=AnalyzeResponse)
async def analyze_resume(
    file: UploadFile = File(...),
    job_description: str = Form(...)
):
    """
    Primary endpoint: Uploads resume PDF/DOCX + Job Description,
    executes multi-agent analysis pipeline, and indexes document for RAG.
    """
    if not job_description or not job_description.strip():
        raise HTTPException(status_code=400, detail="Job description cannot be empty.")

    try:
        file_bytes = await file.read()
        raw_resume_text = extract_text_from_file(file_bytes, file.filename)
        
        if not raw_resume_text or not raw_resume_text.strip():
            raise HTTPException(status_code=400, detail="Could not extract readable text from uploaded file.")

        session_id = str(uuid.uuid4())

        # Execute multi-agent analysis pipeline
        analysis_result = await run_resumizer_pipeline(raw_resume_text, job_description)

        # Index text into ChromaDB for RAG Chat Coach
        index_documents_for_rag(session_id, raw_resume_text, job_description)

        return AnalyzeResponse(
            session_id=session_id,
            analysis=analysis_result
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Pipeline error: {str(e)}")


@app.post("/api/v1/chat", response_model=ChatResponse)
async def chat_coach(request: ChatRequest):
    """
    Conversational endpoint: RAG-backed Career Coach agent.
    """
    if not request.message or not request.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty.")

    try:
        reply = await chat_with_career_coach(
            session_id=request.session_id,
            user_message=request.message,
            chat_history=request.chat_history
        )
        return ChatResponse(reply=reply)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat error: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host=settings.HOST, port=settings.PORT, reload=True)
