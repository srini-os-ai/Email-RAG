from __future__ import annotations

import requests

from app.config import settings


class QueryRewriter:
    def __init__(self, base_url: str | None = None, model: str | None = None, system_prompt: str | None = None):
        self.base_url = base_url or settings.ollama_base_url
        self.model = model or settings.rewrite_model
        self.system_prompt = system_prompt or settings.rewrite_system_prompt

    def build_prompt(self, query: str) -> str:
        return (
            f"System:\n{self.system_prompt}\n\n"
            "User Query:\n"
            f"{query}\n\n"
            "Return only the rewritten search query."
        )

    def rewrite(self, query: str) -> tuple[str, str]:
        prompt = self.build_prompt(query)
        try:
            resp = requests.post(
                f"{self.base_url}/api/generate",
                json={"model": self.model, "prompt": prompt, "stream": False},
                timeout=45,
            )
            resp.raise_for_status()
            data = resp.json()
            rewritten = (data.get("response") or "").strip().replace("\n", " ")
            if rewritten:
                return rewritten, prompt
        except Exception:
            pass
        return query, prompt
