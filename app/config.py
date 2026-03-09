from __future__ import annotations

from dataclasses import dataclass
import os


@dataclass(frozen=True)
class Settings:
    db_path: str = os.getenv("EMAIL_RAG_DB_PATH", "data/email_rag.db")
    ollama_base_url: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    embed_model: str = os.getenv("EMAIL_RAG_EMBED_MODEL", "nomic-embed-text")
    llm_model: str = os.getenv("EMAIL_RAG_LLM_MODEL", "llama3.1:8b")
    retrieval_top_k: int = int(os.getenv("EMAIL_RAG_TOP_K", "5"))
    max_answer_context: int = int(os.getenv("EMAIL_RAG_MAX_CONTEXT", "3"))
    rewrite_model: str = os.getenv("EMAIL_RAG_REWRITE_MODEL", os.getenv("EMAIL_RAG_LLM_MODEL", "llama3.1:8b"))
    rewrite_enabled: bool = os.getenv("EMAIL_RAG_REWRITE_ENABLED", "1") not in {"0", "false", "False"}
    rewrite_system_prompt: str = os.getenv(
        "EMAIL_RAG_REWRITE_SYSTEM_PROMPT",
        "You are a search-query rewriting assistant for local email retrieval. Convert the user's request into a rich retrieval query that improves recall and precision. Include likely synonyms, alternate phrasing, entities, dates/time hints, and topic keywords. Keep factual meaning unchanged. Output a single plain-text search query only, no explanations.",
    )


settings = Settings()
