from __future__ import annotations

from fastapi.testclient import TestClient

from app.api import main as api_main
from app.db import connect, init_db


def test_health_and_query(tmp_path):
    db_path = tmp_path / "api.db"
    conn = connect(str(db_path))
    init_db(conn)
    api_main._conn = conn

    # seed one email
    conn.execute(
        """
        INSERT INTO emails(source_type, source_path, source_ref, subject, sender, date, body, body_preview, body_hash)
        VALUES('mbox','x','offset:0:0','Hello','Alice','2026','launch timeline approved','launch timeline approved','uniq1')
        """
    )
    conn.execute(
        """
        INSERT INTO embeddings(email_id, dim, vector_json)
        VALUES(1, 128, ?)
        """,
        ('[0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0]',),
    )
    conn.commit()

    c = TestClient(api_main.app)
    health = c.get("/health")
    assert health.status_code == 200
    assert health.json()["status"] == "ok"

    res = c.post("/query", json={"query": "launch timeline", "mode": "search", "top_k": 3})
    assert res.status_code == 200
    payload = res.json()
    assert payload["mode"] == "search"
    assert len(payload["results"]) >= 1
    assert 0.0 <= payload["overall_confidence"] <= 1.0
