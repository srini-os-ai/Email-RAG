from __future__ import annotations

from app.ingest import ingest_source


def test_incremental_ingest_only_new_data(temp_db, sample_mbox):
    job1 = ingest_source(temp_db, str(sample_mbox), "mbox")
    assert job1 > 0

    count1 = temp_db.execute("SELECT COUNT(*) c FROM emails").fetchone()["c"]
    assert count1 == 2

    # second run with unchanged file should add zero
    job2 = ingest_source(temp_db, str(sample_mbox), "mbox")
    assert job2 > job1
    count2 = temp_db.execute("SELECT COUNT(*) c FROM emails").fetchone()["c"]
    assert count2 == 2

    # append one new email
    with sample_mbox.open("a", encoding="utf-8") as f:
        f.write(
            """
From c@example.com Sat Jan  3 00:00:00 2026
Subject: New roadmap
From: C <c@example.com>
Date: Mon, 03 Jan 2026 11:00:00 -0500

Roadmap updated with security milestone.
"""
        )

    ingest_source(temp_db, str(sample_mbox), "mbox")
    count3 = temp_db.execute("SELECT COUNT(*) c FROM emails").fetchone()["c"]
    assert count3 == 3
