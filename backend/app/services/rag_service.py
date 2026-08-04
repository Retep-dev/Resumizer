import os
from typing import List
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from app.config import settings


def get_embedding_model():
    """Returns NVIDIAEmbeddings if available, otherwise falls back to lightweight FakeEmbeddings."""
    if settings.NVIDIA_API_KEY and "your-key-here" not in settings.NVIDIA_API_KEY.lower():
        try:
            from langchain_nvidia_ai_endpoints import NVIDIAEmbeddings
            return NVIDIAEmbeddings(
                model="nvidia/nv-embedqa-e5-v5",
                nvidia_api_key=settings.NVIDIA_API_KEY
            )
        except Exception as e:
            print(f"[Warning] Could not initialize NVIDIAEmbeddings: {e}")

    # Lightweight fast embeddings fallback (avoids 300MB SentenceTransformer model download)
    from langchain_community.embeddings import FakeEmbeddings
    return FakeEmbeddings(size=384)


def index_documents_for_rag(session_id: str, resume_text: str, job_description: str) -> Chroma:
    """
    Chunks and indexes the parsed resume and job description into ChromaDB.
    Returns the initialized Chroma vectorstore for the specific session.
    """
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    
    docs = []
    # Resume chunks
    resume_chunks = text_splitter.split_text(resume_text)
    for i, chunk in enumerate(resume_chunks):
        docs.append({
            "text": chunk,
            "metadata": {"source": "resume", "session_id": session_id, "chunk_id": f"resume_{i}"}
        })
        
    # Job Description chunks
    jd_chunks = text_splitter.split_text(job_description)
    for i, chunk in enumerate(jd_chunks):
        docs.append({
            "text": chunk,
            "metadata": {"source": "job_description", "session_id": session_id, "chunk_id": f"jd_{i}"}
        })

    texts = [d["text"] for d in docs]
    metadatas = [d["metadata"] for d in docs]

    persist_dir = os.path.join(settings.CHROMA_DB_DIR, session_id)
    vectorstore = Chroma.from_texts(
        texts=texts,
        embedding=get_embedding_model(),
        metadatas=metadatas,
        persist_directory=persist_dir
    )
    return vectorstore


def get_vectorstore_for_session(session_id: str) -> Chroma:
    """Retrieves an existing Chroma vectorstore for a session."""
    persist_dir = os.path.join(settings.CHROMA_DB_DIR, session_id)
    return Chroma(
        persist_directory=persist_dir,
        embedding_function=get_embedding_model()
    )
