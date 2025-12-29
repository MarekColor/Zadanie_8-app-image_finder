from __future__ import annotations

import os
from dataclasses import dataclass
from dotenv import load_dotenv

# Load .env as early as possible
load_dotenv()


@dataclass(frozen=True)
class Settings:
    # Qdrant
    qdrant_url: str = os.getenv("QDRANT_URL", "http://localhost:6333")
    qdrant_api_key: str = os.getenv("QDRANT_API_KEY", "")
    qdrant_collection: str = os.getenv("QDRANT_COLLECTION", "image_finder")

    # OpenAI
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")

    # Models (keep aligned with your course project defaults)
    vlm_model: str = os.getenv("VLM_MODEL", "gpt-4o-mini")
    embedding_model: str = os.getenv("EMBEDDING_MODEL", "text-embedding-3-large")

    # Embedding dimension for text-embedding-3-large is 3072 (keep consistent with collection config)
    embedding_dim: int = int(os.getenv("EMBEDDING_DIM", "3072"))

    # App behavior
    top_k: int = int(os.getenv("TOP_K", "12"))


settings = Settings()
