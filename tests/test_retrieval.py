from __future__ import annotations

from app.db import insert_email, upsert_embedding
from app.embedding import local_hash_embedding
from app.retrieval import overall_confidence, result_confidence, retrieve


def test_retrieval_confidence_values(temp_db):
    body = "Budget is approved for hiring and platform expansion"
    eid = insert_email(
        temp_db,
        source_type="mbox",
        source_path="x",
        source_ref="offset:0:0",
        subject="Budget",
        sender="A",
        date="2026",
        body=body,
        body_preview=body,
        body_hash="h1",
    )
    assert eid is not None
    upsert_embedding(temp_db, eid, local_hash_embedding(body))

    q = "budget hiring"
    rows = retrieve(temp_db, local_hash_embedding(q), q, top_k=5)
    assert len(rows) == 1
    assert 0.0 <= rows[0]["confidence"] <= 1.0
    assert rows[0]["coverage_score"] > 0


def test_overall_confidence_combines_inputs():
    r = result_confidence(0.8, 0.5)
    assert round(r, 2) == 0.71
    o = overall_confidence([0.7, 0.8], answer_coverage=0.5)
    assert 0.0 <= o <= 1.0
