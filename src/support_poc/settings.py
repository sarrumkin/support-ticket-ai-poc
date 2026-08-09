from __future__ import annotations

import os

from pydantic import Field

from support_poc.contracts import StrictModel


class Settings(StrictModel):
    generator_provider: str = "fixture"
    groq_api_key: str | None = None
    groq_model: str = "qwen/qwen3.6-27b"
    intent_threshold: float = Field(default=0.45, ge=0.0, le=1.0)
    semantic_threshold: float = Field(default=0.82, ge=0.0, le=1.0)
    semantic_top_k: int = Field(default=3, ge=1, le=10)
    embedding_model: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            generator_provider=os.getenv("SUPPORT_POC_GENERATOR", "fixture"),
            groq_api_key=os.getenv("GROQ_API_KEY") or None,
            groq_model=os.getenv("SUPPORT_POC_GROQ_MODEL", "qwen/qwen3.6-27b"),
            intent_threshold=float(os.getenv("SUPPORT_POC_INTENT_THRESHOLD", "0.45")),
            semantic_threshold=float(os.getenv("SUPPORT_POC_SEMANTIC_THRESHOLD", "0.82")),
            semantic_top_k=int(os.getenv("SUPPORT_POC_SEMANTIC_TOP_K", "3")),
            embedding_model=os.getenv(
                "SUPPORT_POC_EMBEDDING_MODEL",
                "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
            ),
        )
