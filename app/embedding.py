from __future__ import annotations

import hashlib
import math

import requests

from app.config import settings


class Embedder:
    def __init__(self, base_url: str | None = None, model: str | None = None):
        self.base_url = base_url or settings.ollama_base_url
        self.model = model or settings.embed_model
        self.last_backend = "unknown"
        self.last_model = self.model

    def embed_with_info(self, text: str) -> tuple[list[float], str, str]:
        try:
            resp = requests.post(
                f"{self.base_url}/api/embeddings",
                json={"model": self.model, "prompt": text},
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()
            vec = data.get("embedding")
            if isinstance(vec, list) and vec:
                self.last_backend = "ollama"
                self.last_model = self.model
                return [float(x) for x in vec], self.last_backend, self.last_model
        except Exception:
            pass
        self.last_backend = "local_hash_fallback"
        self.last_model = "local-hash-128d"
        return local_hash_embedding(text), self.last_backend, self.last_model

    def embed(self, text: str) -> list[float]:
        vec, _, _ = self.embed_with_info(text)
        return vec


def local_hash_embedding(text: str, dim: int = 128) -> list[float]:
    vec = [0.0] * dim
    for tok in text.lower().split():
        h = hashlib.sha256(tok.encode("utf-8")).digest()
        idx = int.from_bytes(h[:2], "little") % dim
        sign = 1.0 if (h[2] % 2 == 0) else -1.0
        vec[idx] += sign
    norm = math.sqrt(sum(v * v for v in vec))
    if norm == 0:
        return vec
    return [v / norm for v in vec]
