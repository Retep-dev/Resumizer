"""In-memory store of what each analysis session was based on, for the coach.

Replaces the previous ChromaDB index, which (a) relied on an embedding model
that NVIDIA has retired, (b) fell back to random 'FakeEmbeddings' vectors, and
(c) lived on Render's ephemeral disk. A resume and posting fit comfortably in
the model's context, so the coach now sees them in full instead of four
retrieved fragments.

Sessions expire after SESSION_TTL_SECONDS and are lost on restart; the
frontend therefore also sends the analysis with each chat request.
"""
from __future__ import annotations

import threading
import time
from collections import OrderedDict
from dataclasses import dataclass
from typing import Optional

from app.config import settings

MAX_SESSIONS = 500


@dataclass
class SessionContext:
    resume_text: str
    job_description: str
    analysis: dict
    created: float


_lock = threading.Lock()
_sessions: "OrderedDict[str, SessionContext]" = OrderedDict()


def save_session(session_id: str, resume_text: str, job_description: str, analysis: dict) -> None:
    with _lock:
        _sessions[session_id] = SessionContext(resume_text[:12000], job_description[:10000], analysis, time.time())
        _sessions.move_to_end(session_id)
        while len(_sessions) > MAX_SESSIONS:
            _sessions.popitem(last=False)


def get_session(session_id: str) -> Optional[SessionContext]:
    with _lock:
        ctx = _sessions.get(session_id)
        if ctx and time.time() - ctx.created > settings.SESSION_TTL_SECONDS:
            del _sessions[session_id]
            return None
        return ctx


def clear_sessions() -> None:
    with _lock:
        _sessions.clear()
