from __future__ import annotations

import hashlib
import math

import requests

from app.config import settings


class Embedder:
    def __init__(self, base_url: str | None = None, model: str | None = None):
        self.base_url = base_url or settings.ollama_base_url
        self.model = model or settings.embed_model

    def embed(self, text: str) -> list[float]:
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
                return [float(x) for x in vec]
        except Exception:
            pass
        return local_hash_embedding(text)


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
