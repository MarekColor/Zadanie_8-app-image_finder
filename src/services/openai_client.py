from __future__ import annotations

from openai import OpenAI
from src.config import settings


def get_openai_client() -> OpenAI:
    if not settings.openai_api_key:
        raise RuntimeError("Missing OPENAI_API_KEY in environment (.env).")
    return OpenAI(api_key=settings.openai_api_key)
