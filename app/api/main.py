from __future__ import annotations

import threading

from fastapi import BackgroundTasks, FastAPI, HTTPException

from app.answer import AnswerGenerator, answer_coverage
from app.config import settings
from app.db import connect, get_latest_ingest_job, init_db
from app.embedding import Embedder
from app.ingest import ingest_source
from app.models import IngestStartRequest, IngestStatusResponse, QueryRequest, QueryResponse, SearchResult
from app.retrieval import overall_confidence, retrieve


app = FastAPI(title="email-rag-mvp", version="0.1.0")

_conn = connect(settings.db_path)
init_db(_conn)
_lock = threading.Lock()


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


def _start_ingest(source_path: str, source_type: str) -> None:
    with _lock:
        ingest_source(_conn, source_path=source_path, source_type=source_type)


@app.post("/ingest/start", response_model=IngestStatusResponse)
def start_ingest(payload: IngestStartRequest, bg: BackgroundTasks):
    latest = get_latest_ingest_job(_conn)
    if latest and latest["status"] == "running":
        raise HTTPException(status_code=409, detail="Ingestion already running")
    bg.add_task(_start_ingest, payload.source_path, payload.source_type)
    return ingest_status()


@app.get("/ingest/status", response_model=IngestStatusResponse)
def ingest_status():
    latest = get_latest_ingest_job(_conn)
    if latest is None:
        return IngestStatusResponse(
            job_id=None,
            status="idle",
            source_path=None,
            source_type=None,
            started_at=None,
            ended_at=None,
            processed_emails=0,
            total_emails_estimate=0,
            processed_bytes=0,
            total_bytes=0,
            throughput_eps=0.0,
            eta_seconds=0.0,
            message="no ingestion job yet",
        )
    return IngestStatusResponse(
        job_id=latest["id"],
        status=latest["status"],
        source_path=latest["source_path"],
        source_type=latest["source_type"],
        started_at=latest["started_at"],
        ended_at=latest["ended_at"],
        processed_emails=latest["processed_emails"],
        total_emails_estimate=latest["total_emails_estimate"],
        processed_bytes=latest["processed_bytes"],
        total_bytes=latest["total_bytes"],
        throughput_eps=latest["throughput_eps"],
        eta_seconds=latest["eta_seconds"],
        message=latest["message"],
    )


@app.post("/query", response_model=QueryResponse)
def query(payload: QueryRequest):
    top_k = payload.top_k or settings.retrieval_top_k
    embedder = Embedder()
    qvec = embedder.embed(payload.query)
    rows = retrieve(_conn, qvec, payload.query, top_k=top_k)
    result_models: list[SearchResult] = []
    for row in rows:
        result_models.append(
            SearchResult(
                email_id=row["email_id"],
                source_ref=row["source_ref"],
                subject=row["subject"],
                sender=row["sender"],
                date=row["date"],
                snippet=row["snippet"],
                retrieval_score=row["retrieval_score"],
                coverage_score=row["coverage_score"],
                confidence=row["confidence"],
            )
        )

    answer = None
    a_cov = 0.0
    if payload.mode == "ask":
        ans = AnswerGenerator()
        contexts = rows[: settings.max_answer_context]
        answer = ans.answer(payload.query, contexts)
        a_cov = answer_coverage(payload.query, answer or "")

    o_conf = overall_confidence([r.confidence for r in result_models], a_cov)
    return QueryResponse(
        query=payload.query,
        mode=payload.mode,
        results=result_models,
        answer=answer,
        overall_confidence=round(o_conf, 4),
    )
