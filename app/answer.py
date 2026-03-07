from __future__ import annotations

import requests

from app.config import settings
from app.retrieval import evidence_coverage


class AnswerGenerator:
    def __init__(self, base_url: str | None = None, model: str | None = None):
        self.base_url = base_url or settings.ollama_base_url
        self.model = model or settings.llm_model

    def answer(self, query: str, contexts: list[dict]) -> str:
        if not contexts:
            return "No supporting emails found."
        prompt = build_prompt(query, contexts)
        try:
            resp = requests.post(
                f"{self.base_url}/api/generate",
                json={"model": self.model, "prompt": prompt, "stream": False},
                timeout=60,
            )
            resp.raise_for_status()
            data = resp.json()
            text = data.get("response", "").strip()
            if text:
                return text
        except Exception:
            pass
        return fallback_answer(query, contexts)


def build_prompt(query: str, contexts: list[dict]) -> str:
    blocks = []
    for i, c in enumerate(contexts, 1):
        blocks.append(
            f"[Email {i}] Subject: {c['subject']}\\nFrom: {c['sender']}\\nDate: {c['date']}\\nBody: {c['body']}"
        )
    joined = "\\n\\n".join(blocks)
    return (
        "You are answering questions using the provided emails only. "
        "Cite Email numbers in-line and keep answer concise.\\n\\n"
        f"Question: {query}\\n\\nEvidence:\\n{joined}"
    )


def fallback_answer(query: str, contexts: list[dict]) -> str:
    bullets = []
    for i, c in enumerate(contexts, 1):
        bullets.append(f"Email {i}: {c['subject']} ({c['date']})")
    return "Based on the top matching emails:\n- " + "\n- ".join(bullets)


def answer_coverage(query: str, answer_text: str) -> float:
    return evidence_coverage(query, answer_text)
