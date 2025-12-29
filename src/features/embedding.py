from __future__ import annotations

from typing import List

from src.services.openai_client import get_openai_client
from src.config import settings


def embed_text(text: str) -> List[float]:
    client = get_openai_client()
    resp = client.embeddings.create(model=settings.embedding_model, input=text)
    return resp.data[0].embedding
