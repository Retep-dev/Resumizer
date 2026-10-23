"""Ask a model for JSON, validate it against a Pydantic model, repair once."""
from __future__ import annotations

import json
import re
from typing import Dict, List, Optional, Tuple, Type, TypeVar

from pydantic import BaseModel, ValidationError

from app.llm.provider import ChatClient, ProviderError

T = TypeVar("T", bound=BaseModel)


class AgentOutputError(Exception):
    """The model answered, but not with valid, usable data."""

    def __init__(self, message: str, model: Optional[str] = None):
        super().__init__(message)
        self.message = message
        self.model = model


def extract_json(text: str):
    """Pull the first JSON object out of a model reply (handles ``` fences and prose)."""
    if not text:
        raise ValueError("empty reply")
    t = text.strip()
    fence = re.search(r"```(?:json)?\s*(.*?)```", t, re.DOTALL | re.IGNORECASE)
    if fence:
        t = fence.group(1).strip()
    start = t.find("{")
    if start == -1:
        raise ValueError("no JSON object in reply")
    depth, in_str, esc = 0, False, False
    for i in range(start, len(t)):
        ch = t[i]
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
        elif ch == '"':
            in_str = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return json.loads(t[start : i + 1])
    raise ValueError("unterminated JSON object")


async def complete_json(
    client: ChatClient,
    system: str,
    user: str,
    schema: Type[T],
    *,
    temperature: float = 0.1,
    max_tokens: int = 3000,
) -> Tuple[T, str]:
    """Returns (validated object, model used). Raises ProviderError or AgentOutputError."""
    messages: List[Dict[str, str]] = [{"role": "system", "content": system}, {"role": "user", "content": user}]
    last_err = ""
    model_used = None
    for attempt in range(2):
        completion = await client.complete(messages, temperature=temperature, max_tokens=max_tokens, json_mode=True)
        model_used = completion.model
        try:
            data = extract_json(completion.text)
            return schema.model_validate(data), completion.model
        except (ValueError, ValidationError) as e:
            last_err = str(e)[:600]
            if attempt == 0:
                messages = messages + [
                    {"role": "assistant", "content": completion.text[:4000]},
                    {"role": "user", "content": f"That reply was not valid JSON for the required schema. Error: {last_err}\nReply again with only the corrected JSON object."},
                ]
    raise AgentOutputError(f"Model output did not match the expected format: {last_err}", model_used)


__all__ = ["complete_json", "extract_json", "AgentOutputError", "ProviderError"]
