import io
from typing import Union
import pdfplumber
import docx


def extract_text_from_pdf(file_bytes: bytes) -> str:
    """Extract clean text from PDF file bytes using pdfplumber."""
    extracted_text = []
    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                extracted_text.append(text)
    return "\n\n".join(extracted_text)


def extract_text_from_docx(file_bytes: bytes) -> str:
    """Extract text from DOCX file bytes using python-docx."""
    doc = docx.Document(io.BytesIO(file_bytes))
    paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
    return "\n".join(paragraphs)


def extract_text_from_file(file_bytes: bytes, filename: str) -> str:
    """Unified file text extractor supporting PDF, DOCX, TXT, and MD."""
    filename_lower = filename.lower()
    if filename_lower.endswith(".pdf"):
        return extract_text_from_pdf(file_bytes)
    elif filename_lower.endswith(".docx") or filename_lower.endswith(".doc"):
        return extract_text_from_docx(file_bytes)
    elif filename_lower.endswith(".txt") or filename_lower.endswith(".md"):
        return file_bytes.decode("utf-8", errors="ignore")
    else:
        # Fallback to UTF-8 decoding
        return file_bytes.decode("utf-8", errors="ignore")
