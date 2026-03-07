from __future__ import annotations

import json
import math
import re

from app.db import list_embeddings


TOKEN_RE = re.compile(r"[a-zA-Z0-9_]+")


def cosine(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def _query_tokens(query: str) -> set[str]:
    return set(TOKEN_RE.findall(query.lower()))


def evidence_coverage(query: str, text: str) -> float:
    q = _query_tokens(query)
    if not q:
        return 0.0
    t = set(TOKEN_RE.findall(text.lower()))
    return len(q & t) / len(q)


def result_confidence(retrieval_score: float, coverage_score: float) -> float:
    # deterministic blend: retrieval carries more weight than lexical coverage
    return max(0.0, min(1.0, 0.7 * retrieval_score + 0.3 * coverage_score))


def overall_confidence(result_confidences: list[float], answer_coverage: float) -> float:
    if not result_confidences:
        return 0.0
    base = sum(result_confidences) / len(result_confidences)
    return max(0.0, min(1.0, 0.8 * base + 0.2 * answer_coverage))


def retrieve(conn, query_embedding: list[float], query: str, top_k: int = 5) -> list[dict]:
    rows = list_embeddings(conn)
    scored = []
    for row in rows:
        vec = json.loads(row["vector_json"])
        retr = max(0.0, cosine(query_embedding, vec))
        cov = evidence_coverage(query, row["body"])
        conf = result_confidence(retr, cov)
        scored.append(
            {
                "email_id": row["email_id"],
                "source_ref": row["source_ref"],
                "subject": row["subject"],
                "sender": row["sender"],
                "date": row["date"],
                "snippet": row["body_preview"],
                "retrieval_score": round(retr, 4),
                "coverage_score": round(cov, 4),
                "confidence": round(conf, 4),
                "body": row["body"],
            }
        )
    scored.sort(key=lambda r: r["confidence"], reverse=True)
    return scored[:top_k]
