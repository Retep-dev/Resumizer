import io
import re

import docx
import pdfplumber

from app.services.text_utils import normalize

SUPPORTED_EXTENSIONS = (".pdf", ".docx", ".txt", ".md")


class DocumentError(Exception):
    """The file can't be turned into resume text. `code` is 'validation_failed' or 'parsing_failed'."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


MAX_PDF_PAGES = 10
MAX_RESUME_CHARS = 40000


def extract_text_from_pdf(file_bytes: bytes) -> str:
    """Extract text from PDF bytes. Uses layout-aware extraction so columns don't interleave."""
    pages = []
    try:
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            if len(pdf.pages) > MAX_PDF_PAGES:
                raise DocumentError("validation_failed", f"This PDF has {len(pdf.pages)} pages. Upload a resume of {MAX_PDF_PAGES} pages or fewer.")
            for page in pdf.pages:
                text = page.extract_text(x_tolerance=1.5, y_tolerance=3) or ""
                if text.strip():
                    pages.append(text)
    except DocumentError:
        raise
    except Exception as e:  # corrupt or encrypted PDF
        raise DocumentError("parsing_failed", f"This PDF couldn't be opened ({type(e).__name__}). Try exporting it again or upload a DOCX.")
    return "\n\n".join(pages)


def extract_text_from_docx(file_bytes: bytes) -> str:
    """Extract paragraphs and table cells (many resume templates use tables for layout)."""
    try:
        document = docx.Document(io.BytesIO(file_bytes))
    except Exception:
        raise DocumentError("parsing_failed", "This DOCX file couldn't be opened. Re-save it in Word or upload a PDF.")
    lines = [p.text for p in document.paragraphs if p.text.strip()]
    for table in document.tables:
        for row in table.rows:
            seen = []
            for cell in row.cells:
                t = cell.text.strip()
                if t and t not in seen:  # merged cells repeat their text
                    seen.append(t)
            lines.extend(seen)
    return "\n".join(lines)


def _clean(text: str) -> str:
    t = normalize(text)
    t = t.replace("ﬁ", "fi").replace("ﬂ", "fl")
    t = re.sub(r"(\w)-\n(\w)", r"\1\2", t)  # re-join words hyphenated across lines
    t = re.sub(r"\n{3,}", "\n\n", t)
    return t.strip()


def extract_text_from_file(file_bytes: bytes, filename: str) -> str:
    """Unified extractor for PDF, DOCX, TXT and MD. Raises DocumentError."""
    name = (filename or "").lower()
    if name.endswith(".doc"):
        raise DocumentError("validation_failed", "Legacy .doc files aren't supported. Save your resume as DOCX or PDF and upload it again.")
    if not name.endswith(SUPPORTED_EXTENSIONS):
        raise DocumentError("validation_failed", "Upload a PDF, DOCX, TXT or MD file.")
    if not file_bytes:
        raise DocumentError("validation_failed", "The uploaded file is empty.")
    # The extension must match the file's real format (stops renamed binaries and zip bombs posing as PDFs).
    if name.endswith(".pdf") and not file_bytes[:1024].lstrip().startswith(b"%PDF"):
        raise DocumentError("validation_failed", "This file isn't a valid PDF. Export your resume as PDF again, or upload a DOCX.")
    if name.endswith(".docx") and not file_bytes.startswith(b"PK"):
        raise DocumentError("validation_failed", "This file isn't a valid DOCX. Re-save it in Word, or upload a PDF.")
    if name.endswith((".txt", ".md")) and b"\x00" in file_bytes[:4096]:
        raise DocumentError("validation_failed", "This text file contains binary data. Upload a PDF, DOCX or plain-text resume.")
    if name.endswith(".pdf"):
        text = extract_text_from_pdf(file_bytes)
    elif name.endswith(".docx"):
        text = extract_text_from_docx(file_bytes)
    else:
        text = file_bytes.decode("utf-8", errors="ignore")
    text = _clean(text)
    if len(text) > MAX_RESUME_CHARS:
        raise DocumentError("validation_failed", "This document is much longer than a resume. Upload a resume of about 10 pages or fewer.")
    return text
