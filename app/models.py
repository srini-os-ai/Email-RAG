from __future__ import annotations

from dataclasses import dataclass, asdict


@dataclass
class IngestStartRequest:
    source_path: str
    source_type: str = "mbox"

    @classmethod
    def from_dict(cls, data: dict):
        source_type = data.get("source_type", "mbox")
        if source_type not in {"mbox", "text"}:
            raise ValueError("source_type must be mbox or text")
        source_path = data.get("source_path", "")
        if not source_path:
            raise ValueError("source_path is required")
        return cls(source_path=source_path, source_type=source_type)

    def model_dump(self):
        return asdict(self)


@dataclass
class SearchResult:
    email_id: int
    source_ref: str
    subject: str
    sender: str
    date: str
    snippet: str
    retrieval_score: float
    coverage_score: float
    confidence: float

    def model_dump(self):
        return asdict(self)


@dataclass
class QueryRequest:
    query: str
    mode: str = "search"
    top_k: int | None = None

    @classmethod
    def from_dict(cls, data: dict):
        mode = data.get("mode", "search")
        if mode != "search":
            raise ValueError("mode must be search")
        query = (data.get("query") or "").strip()
        if not query:
            raise ValueError("query is required")
        top_k = data.get("top_k")
        return cls(query=query, mode=mode, top_k=top_k)

    def model_dump(self):
        return asdict(self)


@dataclass
class QueryResponse:
    query: str
    mode: str
    results: list[SearchResult]
    answer: str | None
    overall_confidence: float
    embedding_backend: str
    embedding_model: str
    rewritten_query: str | None = None
    llm_prompt_used: str | None = None

    def model_dump(self):
        out = asdict(self)
        out["results"] = [r.model_dump() if hasattr(r, "model_dump") else r for r in self.results]
        return out


@dataclass
class IngestStatusResponse:
    job_id: int | None
    status: str
    source_path: str | None
    source_type: str | None
    started_at: str | None
    ended_at: str | None
    processed_emails: int
    total_emails_estimate: int
    processed_bytes: int
    total_bytes: int
    throughput_eps: float
    eta_seconds: float
    message: str
    embedding_backend: str | None = None
    embedding_model: str | None = None

    def model_dump(self):
        return asdict(self)
